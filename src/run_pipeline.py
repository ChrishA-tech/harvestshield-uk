"""End-to-end HarvestShield UK runner:
1. Generates synthetic UK Defra crops + Met Office rainfall + Sentinel-2 spectral + HMRC/FSA import data
   with ~3% corrupt / cloud-obscured rows to test Pandera quarantine.
2. Runs Pandera ingestion, UK GDPR HMAC-SHA256 pseudonymisation, DuckDB persistence & Parquet quarantine.
3. Computes regional GDD, SPEI waterlogging anomalies, and T-Learner causal supply-shock uplift.
4. Trains region-grouped LightGBM + MAPIE 90% conformal models & PyTorch SentinelCropStressNet (logged to MLflow).
5. Generates docs/ERROR_ANALYSIS_REPORT.md and exercises the LangGraph Defra BTOM copilot.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.agents.biosecurity_copilot import HS_CODE_BTOM_REGISTRY, BiosecurityCopilot
from src.analytics.crop_weather_econometrics import (
    compute_spei_waterlogging_anomalies,
    estimate_supply_shock_t_learner,
)
from src.evaluation.error_analysis import generate_error_analysis_report
from src.ingestion.agri_trade_pipeline import (
    DEFAULT_DUCKDB_PATH,
    DEFAULT_QUARANTINE_PATH,
    FARMING_REGION_TO_ITL1,
    persist_to_duckdb,
    run_agri_trade_ingestion,
)
from src.ingestion.live_agri_connectors import fetch_live_uk_fsa_and_agri_weather
from src.models.yield_and_satellite import (
    DEFAULT_MLFLOW_URI,
    train_conformal_yield_and_delay_models,
    train_sentinel_crop_stress_net,
)

DEFAULT_RAW_DATA_PATH = Path("data/raw/uk_agri_trade_synthetic.parquet")


def generate_uk_synthetic_dataset(
    n_rows: int = 360,
    corrupt_rate: float = 0.03,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic UK Defra/Met Office/Sentinel-2/HMRC records with ~3% corrupt rows."""
    rng = np.random.default_rng(seed)
    farming_regions = list(FARMING_REGION_TO_ITL1.keys())
    hs_codes = list(HS_CODE_BTOM_REGISTRY.keys())

    # Regional climate profiles (rainfall mm/month, temp °C)
    region_climate = {
        "East Anglia": (58.0, 7.0, 15.5),
        "Lincolnshire": (62.0, 6.5, 14.8),
        "Yorkshire": (76.0, 5.5, 13.5),
        "West Midlands": (88.0, 6.0, 14.0),
        "South West": (108.0, 7.5, 14.8),
        "Scotland": (122.0, 4.0, 11.5),
    }

    records: list[dict[str, object]] = []
    for i in range(n_rows):
        region = farming_regions[i % len(farming_regions)]
        itl1 = FARMING_REGION_TO_ITL1[region]
        base_rain, base_tmin, base_tmax = region_climate[region]

        hs_code = hs_codes[i % len(hs_codes)]
        btom_tier = HS_CODE_BTOM_REGISTRY[hs_code]["btom_risk_tier"]

        wet_winter_shock = bool(rng.random() < 0.25)
        rainfall_mm = float(
            np.clip(
                base_rain * (1.85 if wet_winter_shock else 1.0) + rng.normal(0.0, 18.0),
                18.0,
                260.0,
            )
        )
        t_min_c = float(base_tmin + rng.normal(0.0, 2.2))
        t_max_c = float(max(t_min_c + 3.0, base_tmax + rng.normal(0.0, 2.5)))
        soil_moisture_pct = float(
            np.clip(24.0 + 0.26 * rainfall_mm + rng.normal(0.0, 4.0), 12.0, 92.0)
        )
        cloud_cover_pct = float(
            np.clip(32.0 + (22.0 if wet_winter_shock else 0.0) + rng.normal(0.0, 14.0), 2.0, 78.0)
        )
        ndvi = float(
            np.clip(
                0.68 - (0.18 if wet_winter_shock else 0.0) + rng.normal(0.0, 0.06),
                -0.25,
                0.92,
            )
        )
        ndwi = float(
            np.clip(
                -0.18 + (0.34 if wet_winter_shock else 0.0) + rng.normal(0.0, 0.05),
                -0.65,
                0.78,
            )
        )

        # Domestic crop yield deviations & supply-shock import surge / wholesale prices
        yield_t1m = float(
            (-11.5 if wet_winter_shock else 1.5)
            - 0.04 * max(rainfall_mm - 95.0, 0.0)
            + 12.0 * (ndvi - 0.55)
            + rng.normal(0.0, 1.8)
        )
        yield_t3m = float(yield_t1m * 1.18 + rng.normal(0.0, 1.4))

        import_tonnes = float(
            np.clip(
                950.0
                + (520.0 if wet_winter_shock else 0.0)
                + 18.0 * max(-yield_t1m, 0.0)
                + rng.normal(0.0, 95.0),
                50.0,
                6000.0,
            )
        )
        wholesale_price_index = float(
            100.0
            + (14.5 if wet_winter_shock else 0.0)
            + 0.45 * max(-yield_t1m, 0.0)
            + rng.normal(0.0, 2.5)
        )
        tier_delay = {"Low": 4.0, "Medium": 14.0, "High": 28.0}[btom_tier]
        port_delay_hours = float(
            np.clip(
                tier_delay + 0.003 * import_tonnes + (4.5 if wet_winter_shock else 0.0) + rng.normal(0, 1.8),
                1.0,
                96.0,
            )
        )

        records.append(
            {
                "record_id": f"UK-AGRI-{i:05d}",
                "farming_region": region,
                "itl1_region": itl1,
                "hs_code": hs_code,
                "btom_risk_tier": btom_tier,
                "importer_eori": f"GB{100000000000 + i}",
                "farm_id": f"DEFRA-CPH-{i:04d}",
                "t_min_c": round(t_min_c, 2),
                "t_max_c": round(t_max_c, 2),
                "rainfall_mm": round(rainfall_mm, 2),
                "soil_moisture_pct": round(soil_moisture_pct, 2),
                "cloud_cover_pct": round(cloud_cover_pct, 2),
                "ndvi": round(ndvi, 4),
                "ndwi": round(ndwi, 4),
                "import_tonnes": round(import_tonnes, 2),
                "wholesale_price_index": round(wholesale_price_index, 2),
                "yield_deviation_t1m_pct": round(yield_t1m, 3),
                "yield_deviation_t3m_pct": round(yield_t3m, 3),
                "port_delay_hours": round(port_delay_hours, 2),
                "supply_shock": int(wet_winter_shock),
            }
        )

    df = pd.DataFrame(records)

    # Inject ~3% realistic corrupt / cloud-obscured violations
    n_corrupt = max(4, int(round(n_rows * corrupt_rate)))
    corrupt_indices = rng.choice(n_rows, size=n_corrupt, replace=False)
    for k, idx in enumerate(corrupt_indices):
        mode = k % 5
        if mode == 0:
            df.loc[idx, "cloud_cover_pct"] = 94.5  # Exceeds 80% Sentinel-2 contract
        elif mode == 1:
            df.loc[idx, "ndvi"] = 1.42  # Out of [-1.0, 1.0] spectral bounds
        elif mode == 2:
            df.loc[idx, "import_tonnes"] = -250.0  # Negative import tonnage
        elif mode == 3:
            df.loc[idx, "hs_code"] = "BADHS"  # Invalid 8-digit CN/HS code
        else:
            df.loc[idx, "itl1_region"] = "Atlantis"  # Invalid UK ITL1 region

    return df


def run_end_to_end_pipeline(live: bool = True) -> dict[str, object]:
    """Execute the full HarvestShield UK data, econometrics, ML, evaluation, and copilot pipeline."""
    if live:
        clean_df = fetch_live_uk_fsa_and_agri_weather(
            duckdb_path=DEFAULT_DUCKDB_PATH,
            quarantine_path=DEFAULT_QUARANTINE_PATH,
        )
        total_rows = int(clean_df.attrs.get("total_rows", len(clean_df)))
        clean_rows = int(clean_df.attrs.get("clean_rows", len(clean_df)))
        quarantined_rows = int(clean_df.attrs.get("quarantined_rows", 0))
        feed_status = str(clean_df.attrs.get("feed_status", "LIVE_FSA_OPENMETEO"))
    else:
        raw_df = generate_uk_synthetic_dataset(n_rows=360, corrupt_rate=0.03, seed=42)
        DEFAULT_RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        raw_df.to_parquet(DEFAULT_RAW_DATA_PATH, index=False)

        ingestion_res = run_agri_trade_ingestion(
            raw_df,
            duckdb_path=DEFAULT_DUCKDB_PATH,
            quarantine_path=DEFAULT_QUARANTINE_PATH,
        )
        clean_df = ingestion_res.clean_df
        total_rows = ingestion_res.total_rows
        clean_rows = ingestion_res.clean_rows
        quarantined_rows = ingestion_res.quarantined_rows
        feed_status = "OFFLINE_SYNTHETIC"

    enriched_df = compute_spei_waterlogging_anomalies(clean_df)
    causal_res = estimate_supply_shock_t_learner(enriched_df)

    # Persist econometrics-enriched clean dataset back to DuckDB for API & dashboard consumers
    persist_to_duckdb(causal_res.enriched_df, duckdb_path=DEFAULT_DUCKDB_PATH)

    conformal_bundle = train_conformal_yield_and_delay_models(
        causal_res.enriched_df,
        mlflow_tracking_uri=DEFAULT_MLFLOW_URI,
    )

    sat_res = train_sentinel_crop_stress_net(
        n_samples=240,
        mlflow_tracking_uri=DEFAULT_MLFLOW_URI,
    )

    error_summary = generate_error_analysis_report(
        oof_df=conformal_bundle.oof_predictions,
        sat_eval_df=sat_res.eval_df,
        metrics=conformal_bundle.metrics,
    )

    copilot = BiosecurityCopilot()
    copilot_sample = copilot.ask(
        query="What BTOM SPS risk tier and IPAFFS CHED apply to HS 02013000 boneless beef?",
        hs_code="02013000",
    )

    return {
        "feed_status": feed_status,
        "total_rows": total_rows,
        "clean_rows": clean_rows,
        "quarantined_rows": quarantined_rows,
        "ate_import_uplift_tonnes": round(causal_res.ate_import_uplift_tonnes, 2),
        "wholesale_price_elasticity": round(causal_res.wholesale_price_elasticity, 3),
        "t1m_coverage_90": round(conformal_bundle.metrics["t1m_coverage_90"], 3),
        "satellite_overall_f1": round(sat_res.overall_f1, 3),
        "satellite_overall_iou": round(sat_res.overall_iou, 3),
        "error_report_path": str(error_summary.report_path),
        "copilot_verified": copilot_sample["citations_verified"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI options for HarvestShield UK pipeline execution."""
    parser = argparse.ArgumentParser(description="Run the HarvestShield UK end-to-end pipeline.")
    parser.add_argument(
        "--live",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch live FSA Food Alerts and Open-Meteo UK agro-meteorological feeds (default: --live).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    summary = run_end_to_end_pipeline(live=args.live)
    print("HarvestShield UK pipeline complete:")
    for key, val in summary.items():
        print(f"  {key}: {val}")
