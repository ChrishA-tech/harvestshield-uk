"""Region-grouped LightGBM + MAPIE 90% conformal yield & port delay forecasting,
MLflow SQLite experiment tracking, and PyTorch Sentinel-2 multispectral crop stress network.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from mapie.regression import CrossConformalRegressor
from sklearn.metrics import f1_score, mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import GroupKFold, train_test_split
from torch.utils.data import DataLoader, TensorDataset

SENTINEL2_BANDS: tuple[str, ...] = ("Blue", "Green", "Red", "RedEdge", "NIR", "SWIR")

MULTIMODAL_FEATURES: tuple[str, ...] = (
    "gdd",
    "spei",
    "rainfall_mm",
    "t_min_c",
    "t_max_c",
    "soil_moisture_pct",
    "ndvi",
    "ndwi",
    "cloud_cover_pct",
    "import_tonnes",
)

WEATHER_ONLY_FEATURES: tuple[str, ...] = (
    "gdd",
    "spei",
    "rainfall_mm",
    "t_min_c",
    "t_max_c",
    "soil_moisture_pct",
    "import_tonnes",
)

DEFAULT_MLFLOW_URI = "sqlite:///mlruns/mlflow.db"


@dataclass
class ConformalForecastBundle:
    """Trained region-grouped LightGBM + MAPIE conformal models and evaluation metrics."""

    model_t1m: CrossConformalRegressor
    model_t3m: CrossConformalRegressor
    model_port_delay: CrossConformalRegressor
    weather_only_t1m: CrossConformalRegressor
    weather_only_t3m: CrossConformalRegressor
    weather_only_port_delay: CrossConformalRegressor
    feature_cols: list[str]
    weather_feature_cols: list[str]
    oof_predictions: pd.DataFrame
    metrics: dict[str, float]


def _extract_bounds(y_pis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Extract (lower, upper) 1D arrays from MAPIE interval output."""
    arr = np.asarray(y_pis, dtype=float)
    if arr.ndim == 3:
        return arr[:, 0, 0], arr[:, 1, 0]
    return arr[:, 0], arr[:, 1]


def _build_conformal_lgbm(n_splits: int, random_state: int = 42) -> CrossConformalRegressor:
    base = lgb.LGBMRegressor(
        n_estimators=70,
        max_depth=4,
        num_leaves=15,
        learning_rate=0.06,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_samples=10,
        random_state=random_state,
        verbosity=-1,
        n_jobs=1,
    )
    return CrossConformalRegressor(
        estimator=base,
        confidence_level=0.90,
        conformity_score="absolute",
        method="plus",
        cv=GroupKFold(n_splits=n_splits),
        random_state=random_state,
    )


def _fit_and_eval_conformal(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    n_splits: int,
    random_state: int = 42,
) -> tuple[CrossConformalRegressor, np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    model = _build_conformal_lgbm(n_splits=n_splits, random_state=random_state)
    model.fit_conformalize(X, y, groups=groups)
    y_pred, y_pis = model.predict_interval(X)
    lower, upper = _extract_bounds(y_pis)
    mae = float(mean_absolute_error(y, y_pred))
    rmse = float(root_mean_squared_error(y, y_pred))
    coverage = float(np.mean((y >= lower) & (y <= upper)))
    mean_width = float(np.mean(upper - lower))
    return model, y_pred, lower, upper, {
        "mae": mae,
        "rmse": rmse,
        "coverage_90": coverage,
        "mean_width": mean_width,
    }


def train_conformal_yield_and_delay_models(
    df: pd.DataFrame,
    group_col: str = "farming_region",
    mlflow_tracking_uri: str = DEFAULT_MLFLOW_URI,
    experiment_name: str = "harvestshield_uk_conformal_yield",
    random_state: int = 42,
) -> ConformalForecastBundle:
    """Train region-grouped LightGBM + MAPIE 90% conformal regressors for
    county crop yield deviation (t+1m, t+3m) and UK port clearance delay risk,
    plus weather-only fallback models, logging runs to MLflow SQLite.
    """
    work = df.copy().reset_index(drop=True)
    if group_col not in work.columns:
        group_col = "itl1_region"

    feature_cols = [c for c in MULTIMODAL_FEATURES if c in work.columns]
    weather_cols = [c for c in WEATHER_ONLY_FEATURES if c in work.columns]
    if not feature_cols or not weather_cols:
        raise ValueError("Missing required meteorological/spectral feature columns.")

    X_full = work[feature_cols].astype(float).to_numpy()
    X_weather = work[weather_cols].astype(float).to_numpy()
    groups = work[group_col].astype(str).to_numpy()
    n_unique_groups = int(pd.Series(groups).nunique())
    n_splits = max(2, min(5, n_unique_groups))

    y_t1m = work["yield_deviation_t1m_pct"].astype(float).to_numpy()
    y_t3m = work["yield_deviation_t3m_pct"].astype(float).to_numpy()
    y_delay = work["port_delay_hours"].astype(float).to_numpy()

    m_t1m, pred_t1m, lo_t1m, hi_t1m, met_t1m = _fit_and_eval_conformal(
        X_full, y_t1m, groups, n_splits=n_splits, random_state=random_state
    )
    m_t3m, pred_t3m, lo_t3m, hi_t3m, met_t3m = _fit_and_eval_conformal(
        X_full, y_t3m, groups, n_splits=n_splits, random_state=random_state
    )
    m_delay, pred_delay, lo_delay, hi_delay, met_delay = _fit_and_eval_conformal(
        X_full, y_delay, groups, n_splits=n_splits, random_state=random_state
    )

    # Weather-only fallback models used when Sentinel-2 cloud cover > 80%
    w_t1m, _, _, _, w_met_t1m = _fit_and_eval_conformal(
        X_weather, y_t1m, groups, n_splits=n_splits, random_state=random_state
    )
    w_t3m, _, _, _, w_met_t3m = _fit_and_eval_conformal(
        X_weather, y_t3m, groups, n_splits=n_splits, random_state=random_state
    )
    w_delay, _, _, _, w_met_delay = _fit_and_eval_conformal(
        X_weather, y_delay, groups, n_splits=n_splits, random_state=random_state
    )

    oof = work.copy()
    oof["pred_yield_t1m"] = pred_t1m
    oof["lower_yield_t1m"] = lo_t1m
    oof["upper_yield_t1m"] = hi_t1m
    oof["pred_yield_t3m"] = pred_t3m
    oof["lower_yield_t3m"] = lo_t3m
    oof["upper_yield_t3m"] = hi_t3m
    oof["pred_port_delay_hours"] = pred_delay
    oof["lower_port_delay_hours"] = lo_delay
    oof["upper_port_delay_hours"] = hi_delay

    metrics = {
        "t1m_mae": met_t1m["mae"],
        "t1m_rmse": met_t1m["rmse"],
        "t1m_coverage_90": met_t1m["coverage_90"],
        "t1m_mean_width": met_t1m["mean_width"],
        "t3m_mae": met_t3m["mae"],
        "t3m_rmse": met_t3m["rmse"],
        "t3m_coverage_90": met_t3m["coverage_90"],
        "t3m_mean_width": met_t3m["mean_width"],
        "port_delay_mae": met_delay["mae"],
        "port_delay_rmse": met_delay["rmse"],
        "port_delay_coverage_90": met_delay["coverage_90"],
        "weather_only_t1m_mae": w_met_t1m["mae"],
        "weather_only_t3m_mae": w_met_t3m["mae"],
        "weather_only_port_delay_mae": w_met_delay["mae"],
    }

    if mlflow_tracking_uri.startswith("sqlite:///"):
        db_file = Path(mlflow_tracking_uri.removeprefix("sqlite:///"))
        db_file.parent.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="lgbm_mapie_groupkfold"):
        mlflow.log_params(
            {
                "cv_strategy": "GroupKFold",
                "group_col": group_col,
                "n_splits": n_splits,
                "confidence_level": 0.90,
                "num_samples": len(work),
                "multimodal_features": ",".join(feature_cols),
                "weather_only_features": ",".join(weather_cols),
            }
        )
        mlflow.log_metrics(metrics)

    return ConformalForecastBundle(
        model_t1m=m_t1m,
        model_t3m=m_t3m,
        model_port_delay=m_delay,
        weather_only_t1m=w_t1m,
        weather_only_t3m=w_t3m,
        weather_only_port_delay=w_delay,
        feature_cols=feature_cols,
        weather_feature_cols=weather_cols,
        oof_predictions=oof,
        metrics=metrics,
    )


class SentinelCropStressNet(nn.Module):
    """PyTorch Multispectral CNN processing 6-band Sentinel-2 patches
    (Blue, Green, Red, RedEdge, NIR, SWIR) to classify waterlogged vs. healthy arable fields.
    """

    def __init__(self, in_channels: int = 6, num_classes: int = 2) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 24, kernel_size=3, padding=1),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True),
            nn.Conv2d(24, 48, kernel_size=3, padding=1),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(48, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.15),
            nn.Linear(64, 32),
            nn.ReLU(inplace=True),
            nn.Linear(32, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning class logits of shape (batch, num_classes)."""
        features = self.encoder(x)
        return self.classifier(features)

    @torch.no_grad()
    def predict_waterlogged_proba(self, x: torch.Tensor) -> np.ndarray:
        """Return probability of waterlogged crop stress (class 1)."""
        was_training = self.training
        self.eval()
        logits = self.forward(x)
        probs = torch.softmax(logits, dim=-1)[:, 1].cpu().numpy()
        if was_training:
            self.train()
        return probs


def generate_sentinel2_patches(
    n_samples: int = 240,
    patch_size: int = 16,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate realistic 6-band Sentinel-2 patches (Blue, Green, Red, RedEdge, NIR, SWIR),
    binary labels (0=healthy arable, 1=waterlogged), and partial cloud cover percentages (0-80%).
    """
    rng = np.random.default_rng(seed)
    patches = np.zeros((n_samples, 6, patch_size, patch_size), dtype=np.float32)
    labels = rng.integers(0, 2, size=n_samples, dtype=np.int64)
    cloud_pct = rng.uniform(0.0, 80.0, size=n_samples).astype(np.float32)

    for i in range(n_samples):
        waterlogged = labels[i] == 1
        # Healthy crop: low Red, high RedEdge & NIR, moderate SWIR
        # Waterlogged field: elevated Blue/Green, lower RedEdge/NIR, strongly absorbed SWIR + surface glint
        if waterlogged:
            means = np.array([0.11, 0.14, 0.12, 0.19, 0.23, 0.08], dtype=np.float32)
            stds = np.array([0.025, 0.025, 0.02, 0.03, 0.035, 0.02], dtype=np.float32)
        else:
            means = np.array([0.05, 0.08, 0.05, 0.28, 0.44, 0.18], dtype=np.float32)
            stds = np.array([0.015, 0.015, 0.015, 0.03, 0.04, 0.025], dtype=np.float32)

        patch = rng.normal(
            loc=means[:, None, None],
            scale=stds[:, None, None],
            size=(6, patch_size, patch_size),
        ).astype(np.float32)

        # Simulate partial cloud haze blending bright reflectance across visible/SWIR bands
        cloud_frac = float(cloud_pct[i]) / 100.0
        if cloud_frac > 0.15:
            cloud_mask = rng.random((1, patch_size, patch_size)) < (cloud_frac * 0.75)
            haze = rng.uniform(0.45, 0.75, size=(6, patch_size, patch_size)).astype(np.float32)
            patch = np.where(cloud_mask, 0.55 * patch + 0.45 * haze, patch)

        patches[i] = np.clip(patch, 0.0, 1.0)

    return patches, labels, cloud_pct


def compute_binary_iou(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Intersection-over-Union (IoU) for the waterlogged positive class."""
    y_t = np.asarray(y_true, dtype=int) == 1
    y_p = np.asarray(y_pred, dtype=int) == 1
    tp = int(np.sum(y_t & y_p))
    union = int(np.sum(y_t | y_p))
    return float(tp / union) if union > 0 else 1.0


@dataclass
class SatelliteEvaluationResult:
    """Trained SentinelCropStressNet and held-out evaluation dataframe."""

    model: SentinelCropStressNet
    eval_df: pd.DataFrame
    overall_f1: float
    overall_iou: float


def train_sentinel_crop_stress_net(
    n_samples: int = 240,
    patch_size: int = 16,
    epochs: int = 24,
    batch_size: int = 32,
    lr: float = 3e-3,
    mlflow_tracking_uri: str = DEFAULT_MLFLOW_URI,
    experiment_name: str = "harvestshield_uk_sentinel2_cnn",
    seed: int = 42,
) -> SatelliteEvaluationResult:
    """Train and evaluate SentinelCropStressNet on 6-band Sentinel-2 patches."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    X, y, cloud_pct = generate_sentinel2_patches(
        n_samples=n_samples, patch_size=patch_size, seed=seed
    )
    indices = np.arange(n_samples)
    tr_idx, te_idx = train_test_split(
        indices, test_size=0.30, stratify=y, random_state=seed
    )

    train_ds = TensorDataset(torch.from_numpy(X[tr_idx]), torch.from_numpy(y[tr_idx]))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    model = SentinelCropStressNet(in_channels=6, num_classes=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for _ in range(epochs):
        for bx, by in train_loader:
            optimizer.zero_grad()
            logits = model(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        probs = model.predict_waterlogged_proba(torch.from_numpy(X[te_idx]))
    preds = (probs >= 0.5).astype(int)
    y_test = y[te_idx]

    overall_f1 = float(f1_score(y_test, preds, zero_division=0))
    overall_iou = compute_binary_iou(y_test, preds)

    eval_df = pd.DataFrame(
        {
            "y_true": y_test,
            "y_pred": preds,
            "prob_waterlogged": probs,
            "cloud_cover_pct": cloud_pct[te_idx],
        }
    )

    if mlflow_tracking_uri.startswith("sqlite:///"):
        db_file = Path(mlflow_tracking_uri.removeprefix("sqlite:///"))
        db_file.parent.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="sentinel2_crop_stress_cnn"):
        mlflow.log_params(
            {
                "bands": ",".join(SENTINEL2_BANDS),
                "patch_size": patch_size,
                "epochs": epochs,
                "n_train": len(tr_idx),
                "n_test": len(te_idx),
            }
        )
        mlflow.log_metrics({"overall_f1": overall_f1, "overall_iou": overall_iou})

    return SatelliteEvaluationResult(
        model=model,
        eval_df=eval_df,
        overall_f1=overall_f1,
        overall_iou=overall_iou,
    )
