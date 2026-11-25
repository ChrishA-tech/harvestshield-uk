"""UK agro-meteorological econometrics: Growing Degree Days (GDD),
SPEI waterlogging anomalies, and Two-Model (T-Learner) causal supply-shock analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

UK_FARMING_REGIONS: tuple[str, ...] = (
    "East Anglia",
    "Lincolnshire",
    "Yorkshire",
    "West Midlands",
    "South West",
    "Scotland",
)


def compute_growing_degree_days(
    t_min_c: pd.Series | np.ndarray,
    t_max_c: pd.Series | np.ndarray,
    t_base_c: float = 5.0,
    days_in_period: float = 30.0,
) -> np.ndarray:
    """Compute Growing Degree Days (GDD) above base temperature (default 5.0°C for UK cereals)."""
    t_mean = (np.asarray(t_min_c, dtype=float) + np.asarray(t_max_c, dtype=float)) / 2.0
    daily_gdd = np.maximum(0.0, t_mean - t_base_c)
    return daily_gdd * float(days_in_period)


def compute_pet_thornthwaite_approx(
    t_mean_c: pd.Series | np.ndarray,
    latitude_deg: float = 52.5,
) -> np.ndarray:
    """Approximate monthly Potential Evapotranspiration (mm) for UK latitudes."""
    t_pos = np.maximum(0.0, np.asarray(t_mean_c, dtype=float))
    # Calibrated UK monthly PET approximation (~15 mm in winter, ~85-105 mm in summer)
    lat_adj = max(0.85, 1.0 - 0.012 * (latitude_deg - 52.0))
    return (12.0 + 3.8 * (t_pos ** 1.12)) * lat_adj


def compute_spei_waterlogging_anomalies(
    df: pd.DataFrame,
    region_col: str = "farming_region",
    rainfall_col: str = "rainfall_mm",
    t_min_col: str = "t_min_c",
    t_max_col: str = "t_max_c",
    waterlog_threshold: float = 1.25,
) -> pd.DataFrame:
    """Compute regional GDD, climatic water balance (P - PET), SPEI z-score anomalies,
    and waterlogging flags across UK farming regions.
    """
    out = df.copy()
    t_mean = (out[t_min_col].astype(float) + out[t_max_col].astype(float)) / 2.0
    out["gdd"] = compute_growing_degree_days(out[t_min_col], out[t_max_col])
    out["pet_mm"] = compute_pet_thornthwaite_approx(t_mean)
    out["water_balance_mm"] = out[rainfall_col].astype(float) - out["pet_mm"]

    # Standardize climatic water balance within each UK farming region to derive SPEI
    group_stats = out.groupby(region_col)["water_balance_mm"].transform
    region_mean = group_stats("mean")
    region_std = group_stats("std").replace(0.0, np.nan).fillna(1.0)
    out["spei"] = (out["water_balance_mm"] - region_mean) / region_std
    out["waterlogging_anomaly"] = out["spei"] >= waterlog_threshold
    return out


@dataclass
class TLearnerSupplyShockResult:
    """Causal estimates from the Two-Model (T-Learner) supply-shock estimator."""

    ate_import_uplift_tonnes: float
    ate_import_uplift_pct: float
    ate_price_uplift_pct: float
    wholesale_price_elasticity: float
    treated_count: int
    control_count: int
    enriched_df: pd.DataFrame


def estimate_supply_shock_t_learner(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    treatment_col: str = "supply_shock",
    import_outcome_col: str = "import_tonnes",
    price_outcome_col: str = "wholesale_price_index",
    yield_dev_col: str = "yield_deviation_pct",
    random_state: int = 42,
) -> TLearnerSupplyShockResult:
    """Estimate causal supply-shock import surge uplift and wholesale food price elasticity
    using a Two-Model (T-Learner) meta-learner.

    Model 1 (treated):  mu_1(X) = E[Y | X, T=1]
    Model 0 (control):  mu_0(X) = E[Y | X, T=0]
    CATE(X) = mu_1(X) - mu_0(X), ATE = mean(CATE(X))
    """
    work = df.copy()
    if treatment_col not in work.columns:
        # Derive binary domestic supply shock if not supplied explicitly
        spei_series = work["spei"] if "spei" in work.columns else pd.Series(0.0, index=work.index)
        work[treatment_col] = ((spei_series >= 1.25) | (work[yield_dev_col] <= -8.0)).astype(int)

    default_features = [
        c
        for c in (
            "gdd",
            "spei",
            "rainfall_mm",
            "t_min_c",
            "t_max_c",
            "ndvi",
            "ndwi",
            "soil_moisture_pct",
        )
        if c in work.columns
    ]
    features = feature_cols or default_features
    if not features:
        raise ValueError("No feature columns available for T-Learner estimation.")

    X = work[features].astype(float).to_numpy()
    t = work[treatment_col].astype(int).to_numpy()
    y_import = work[import_outcome_col].astype(float).to_numpy()
    y_price = work[price_outcome_col].astype(float).to_numpy()

    treated_mask = t == 1
    control_mask = t == 0
    if treated_mask.sum() < 5 or control_mask.sum() < 5:
        raise ValueError(
            f"Insufficient treated ({treated_mask.sum()}) or control ({control_mask.sum()}) samples."
        )

    def _fit_pair(y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        mu_1 = GradientBoostingRegressor(
            n_estimators=80, max_depth=3, learning_rate=0.06, random_state=random_state
        )
        mu_0 = GradientBoostingRegressor(
            n_estimators=80, max_depth=3, learning_rate=0.06, random_state=random_state
        )
        mu_1.fit(X[treated_mask], y[treated_mask])
        mu_0.fit(X[control_mask], y[control_mask])
        pred_1 = mu_1.predict(X)
        pred_0 = mu_0.predict(X)
        return pred_1 - pred_0, pred_1, pred_0

    cate_import, pred1_imp, pred0_imp = _fit_pair(y_import)
    cate_price, pred1_prc, pred0_prc = _fit_pair(y_price)

    work["cate_import_uplift_tonnes"] = cate_import
    safe_base_imp = np.maximum(np.abs(pred0_imp), 1.0)
    work["cate_import_uplift_pct"] = (cate_import / safe_base_imp) * 100.0

    safe_base_prc = np.maximum(np.abs(pred0_prc), 1.0)
    cate_price_pct = (cate_price / safe_base_prc) * 100.0
    work["cate_price_uplift_pct"] = cate_price_pct

    ate_import_tonnes = float(np.mean(cate_import))
    ate_import_pct = float(np.mean(work["cate_import_uplift_pct"]))
    ate_price_pct = float(np.mean(cate_price_pct))

    # Price elasticity of domestic yield shock: %Delta(Wholesale Price) / %Delta(Domestic Supply)
    # Under supply shock, mean domestic yield deviation drop drives wholesale price increase.
    if yield_dev_col in work.columns:
        treated_yield_drop = float(np.mean(work.loc[treated_mask, yield_dev_col]))
        control_yield_dev = float(np.mean(work.loc[control_mask, yield_dev_col]))
        supply_change_pct = treated_yield_drop - control_yield_dev
        if abs(supply_change_pct) < 0.5:
            supply_change_pct = -5.0
        price_elasticity = float(ate_price_pct / supply_change_pct)
    else:
        price_elasticity = float(-ate_price_pct / max(abs(ate_import_pct), 1.0))

    return TLearnerSupplyShockResult(
        ate_import_uplift_tonnes=ate_import_tonnes,
        ate_import_uplift_pct=ate_import_pct,
        ate_price_uplift_pct=ate_price_pct,
        wholesale_price_elasticity=price_elasticity,
        treated_count=int(treated_mask.sum()),
        control_count=int(control_mask.sum()),
        enriched_df=work,
    )
