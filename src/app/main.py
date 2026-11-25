"""FastAPI service exposing /health, /forecast-harvest (with Sentinel-2 cloud-cover
weather-only fallback), and /compliance-copilot (LangGraph Defra BTOM / FSA workflow).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.agents.biosecurity_copilot import BiosecurityCopilot
from src.analytics.crop_weather_econometrics import (
    compute_spei_waterlogging_anomalies,
)
from src.ingestion.agri_trade_pipeline import DEFAULT_DUCKDB_PATH, FARMING_REGION_TO_ITL1
from src.models.yield_and_satellite import (
    ConformalForecastBundle,
    train_conformal_yield_and_delay_models,
)

app = FastAPI(
    title="HarvestShield UK API",
    version="0.1.0",
    description=(
        "UK Crop Yield & Supply Chain Disruption Forecasting, Multispectral Satellite Crop "
        "Stress AI, and Defra BTOM / FSA Border Biosecurity Compliance Copilot"
    ),
)


class HarvestForecastRequest(BaseModel):
    """Input payload for county/region harvest yield and port clearance forecasting."""

    farming_region: str = Field(default="East Anglia", description="UK agricultural region")
    hs_code: str = Field(default="10019900", pattern=r"^\d{8}$")
    t_min_c: float = Field(default=6.0)
    t_max_c: float = Field(default=14.0)
    rainfall_mm: float = Field(default=85.0, ge=0.0)
    soil_moisture_pct: float = Field(default=38.0, ge=0.0, le=100.0)
    import_tonnes: float = Field(default=1250.0, ge=0.0)
    ndvi: float | None = Field(default=0.62)
    ndwi: float | None = Field(default=-0.12)
    cloud_cover_pct: float = Field(default=25.0, ge=0.0, le=100.0)
    spei_override: float | None = Field(default=None)


class HarvestForecastResponse(BaseModel):
    """90% conformal forecast for t+1m, t+3m crop yield deviation and port clearance delay."""

    farming_region: str
    hs_code: str
    fallback_used: bool
    fallback_reason: str | None
    model_mode: str
    yield_deviation_t1m_pct: float
    yield_t1m_lower_90: float
    yield_t1m_upper_90: float
    yield_deviation_t3m_pct: float
    yield_t3m_lower_90: float
    yield_t3m_upper_90: float
    port_delay_hours: float
    port_delay_lower_90: float
    port_delay_upper_90: float


class ComplianceQueryRequest(BaseModel):
    """Input payload for Defra BTOM / FSA Border Biosecurity Compliance Copilot."""

    query: str
    hs_code: str | None = Field(default=None)
    origin_country: str = Field(default="EU")


class ComplianceQueryResponse(BaseModel):
    """Grounded compliance response with citation verification and deterministic fallback flag."""

    answer: str
    btom_risk_tier: str
    hs_code: str | None
    citations: list[str]
    citations_verified: bool
    verification_notes: str
    used_deterministic_fallback: bool
    blocked: bool
    block_reason: str


def _build_bootstrap_training_frame(seed: int = 42) -> pd.DataFrame:
    """Create a deterministic UK regional calibration frame if DuckDB has not been populated yet."""
    rng = np.random.default_rng(seed)
    regions = list(FARMING_REGION_TO_ITL1.keys())
    rows: list[dict[str, object]] = []
    for i in range(180):
        region = regions[i % len(regions)]
        t_min = float(rng.uniform(2.0, 12.0))
        t_max = float(t_min + rng.uniform(5.0, 10.0))
        rain = float(rng.uniform(35.0, 165.0))
        soil = float(np.clip(22.0 + 0.25 * rain + rng.normal(0, 3.0), 10.0, 85.0))
        cloud = float(rng.uniform(5.0, 78.0))
        ndvi = float(np.clip(0.72 - 0.002 * max(rain - 90.0, 0.0) + rng.normal(0, 0.05), -0.2, 0.9))
        ndwi = float(np.clip(-0.22 + 0.004 * max(rain - 80.0, 0.0) + rng.normal(0, 0.04), -0.6, 0.8))
        imp = float(rng.uniform(400.0, 4500.0))
        rows.append(
            {
                "farming_region": region,
                "itl1_region": FARMING_REGION_TO_ITL1[region],
                "t_min_c": t_min,
                "t_max_c": t_max,
                "rainfall_mm": rain,
                "soil_moisture_pct": soil,
                "cloud_cover_pct": cloud,
                "ndvi": ndvi,
                "ndwi": ndwi,
                "import_tonnes": imp,
            }
        )
    df = compute_spei_waterlogging_anomalies(pd.DataFrame(rows))
    noise = rng.normal(0.0, 1.2, size=len(df))
    df["yield_deviation_t1m_pct"] = -4.2 * df["spei"] + 12.0 * (df["ndvi"] - 0.55) + noise
    df["yield_deviation_t3m_pct"] = -5.1 * df["spei"] + 10.5 * (df["ndvi"] - 0.55) + noise * 1.2
    df["port_delay_hours"] = np.clip(6.0 + 0.004 * df["import_tonnes"] + 2.8 * np.maximum(df["spei"], 0.0) + rng.normal(0, 1.5, size=len(df)), 1.0, 72.0)
    return df


@lru_cache(maxsize=1)
def get_forecast_bundle() -> ConformalForecastBundle:
    """Load processed DuckDB data if available or bootstrap regional conformal models."""
    duckdb_path = Path(DEFAULT_DUCKDB_PATH)
    if duckdb_path.exists():
        try:
            with duckdb.connect(str(duckdb_path), read_only=True) as con:
                df = con.execute("SELECT * FROM agri_trade_clean").fetchdf()
            required = {
                "yield_deviation_t1m_pct",
                "yield_deviation_t3m_pct",
                "port_delay_hours",
                "gdd",
                "spei",
            }
            if len(df) >= 60 and required.issubset(df.columns):
                return train_conformal_yield_and_delay_models(df)
        except Exception:
            pass
    return train_conformal_yield_and_delay_models(_build_bootstrap_training_frame())


@lru_cache(maxsize=1)
def get_copilot() -> BiosecurityCopilot:
    """Return cached LangGraph BiosecurityCopilot instance."""
    return BiosecurityCopilot()


def _extract_scalar_interval(model, X_row: np.ndarray) -> tuple[float, float, float]:
    pred, pis = model.predict_interval(X_row)
    arr = np.asarray(pis, dtype=float)
    lo = float(arr[0, 0, 0] if arr.ndim == 3 else arr[0, 0])
    hi = float(arr[0, 1, 0] if arr.ndim == 3 else arr[0, 1])
    return float(pred[0]), lo, hi


@app.get("/health")
def health() -> dict[str, object]:
    """Liveness and readiness check."""
    duckdb_rows = 0
    if DEFAULT_DUCKDB_PATH.exists():
        try:
            with duckdb.connect(str(DEFAULT_DUCKDB_PATH), read_only=True) as con:
                duckdb_rows = int(
                    con.execute("SELECT COUNT(*) FROM agri_trade_clean").fetchone()[0]
                )
        except Exception:
            duckdb_rows = 0
    return {
        "status": "ok",
        "service": "harvestshield-uk",
        "duckdb_clean_rows": duckdb_rows,
        "cloud_cover_fallback_threshold_pct": 80.0,
    }


@app.post("/forecast-harvest", response_model=HarvestForecastResponse)
def forecast_harvest(req: HarvestForecastRequest) -> HarvestForecastResponse:
    """Predict t+1m and t+3m crop yield deviation and UK port delay risk with 90% conformal
    intervals, automatically falling back to weather-only features when cloud cover > 80%.
    """
    bundle = get_forecast_bundle()
    row_df = pd.DataFrame(
        [
            {
                "farming_region": req.farming_region,
                "t_min_c": req.t_min_c,
                "t_max_c": req.t_max_c,
                "rainfall_mm": req.rainfall_mm,
                "soil_moisture_pct": req.soil_moisture_pct,
                "import_tonnes": req.import_tonnes,
                "ndvi": req.ndvi if req.ndvi is not None else 0.0,
                "ndwi": req.ndwi if req.ndwi is not None else 0.0,
                "cloud_cover_pct": req.cloud_cover_pct,
            }
        ]
    )
    row_df = compute_spei_waterlogging_anomalies(row_df)
    if req.spei_override is not None:
        row_df["spei"] = float(req.spei_override)
    else:
        # Single-row z-score is 0.0; derive calibrated UK water-balance anomaly relative to 25mm baseline
        row_df["spei"] = float((row_df["water_balance_mm"].iloc[0] - 25.0) / 45.0)

    cloud_obscured = req.cloud_cover_pct > 80.0
    missing_spectral = req.ndvi is None or req.ndwi is None
    use_fallback = cloud_obscured or missing_spectral

    if use_fallback:
        reason = (
            f"Sentinel-2 cloud cover {req.cloud_cover_pct:.1f}% > 80.0% limit; "
            "switched to weather-only conformal regressor."
            if cloud_obscured
            else "Missing Sentinel-2 NDVI/NDWI bands; switched to weather-only conformal regressor."
        )
        X_in = row_df[bundle.weather_feature_cols].astype(float).to_numpy()
        p1, l1, u1 = _extract_scalar_interval(bundle.weather_only_t1m, X_in)
        p3, l3, u3 = _extract_scalar_interval(bundle.weather_only_t3m, X_in)
        pd_p, pd_l, pd_u = _extract_scalar_interval(bundle.weather_only_port_delay, X_in)
        mode = "weather_only_fallback"
    else:
        reason = None
        X_in = row_df[bundle.feature_cols].astype(float).to_numpy()
        p1, l1, u1 = _extract_scalar_interval(bundle.model_t1m, X_in)
        p3, l3, u3 = _extract_scalar_interval(bundle.model_t3m, X_in)
        pd_p, pd_l, pd_u = _extract_scalar_interval(bundle.model_port_delay, X_in)
        mode = "multimodal_satellite_weather"

    return HarvestForecastResponse(
        farming_region=req.farming_region,
        hs_code=req.hs_code,
        fallback_used=use_fallback,
        fallback_reason=reason,
        model_mode=mode,
        yield_deviation_t1m_pct=round(p1, 3),
        yield_t1m_lower_90=round(l1, 3),
        yield_t1m_upper_90=round(u1, 3),
        yield_deviation_t3m_pct=round(p3, 3),
        yield_t3m_lower_90=round(l3, 3),
        yield_t3m_upper_90=round(u3, 3),
        port_delay_hours=round(max(0.0, pd_p), 3),
        port_delay_lower_90=round(max(0.0, pd_l), 3),
        port_delay_upper_90=round(max(0.0, pd_u), 3),
    )


@app.post("/compliance-copilot", response_model=ComplianceQueryResponse)
def compliance_copilot(req: ComplianceQueryRequest) -> ComplianceQueryResponse:
    """Query the guardrailed LangGraph Defra BTOM / FSA Border Biosecurity Copilot."""
    copilot = get_copilot()
    out = copilot.ask(
        query=req.query,
        hs_code=req.hs_code,
        origin_country=req.origin_country,
    )
    return ComplianceQueryResponse(**out)
