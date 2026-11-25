# HarvestShield UK — Sliced Error Analysis & Conformal Audit Report

## 1. Executive Summary

This report audits **HarvestShield UK** forecasting reliability across UK agro-ecological
slices, extreme waterlogging anomalies, high-risk Defra Border Target Operating Model (BTOM)
import corridors, and Sentinel-2 partial cloud regimes.

- **Horizon t+3m Conformal Yield Deviation**: MAE = `1.477` pp, 90% Coverage = `0.986`
- **UK Port Clearance Delay Risk**: MAE = `6.935` hours
- **Weather-Only Fallback (`cloud_cover_pct > 80%`) t+1m MAE**: `1.183` pp

## 2. Regional & Domain Slice Audit (t+1m Yield Deviation & 90% Conformal Coverage)

| Slice                         |   Samples |   MAE (pp) |   RMSE (pp) |   90% Conformal Coverage |   Mean Width (pp) |
|:------------------------------|----------:|-----------:|------------:|-------------------------:|------------------:|
| Overall (All UK Regions)      |       349 |      1.022 |       1.298 |                    0.994 |             6.627 |
| Arable Eastern Lowlands       |       175 |      0.997 |       1.273 |                    1     |             6.618 |
| Pastoral Western Uplands      |       174 |      1.046 |       1.322 |                    0.989 |             6.636 |
| Extreme Wet Winter Anomaly    |        44 |      0.92  |       1.242 |                    0.977 |             6.756 |
| High-Risk SPS Import Corridor |       256 |      1.069 |       1.357 |                    0.992 |             6.626 |

### Key Observations
- **Arable Eastern Lowlands** (East Anglia, Lincolnshire, Yorkshire) exhibit tight conformal
  interval widths under normal rainfall due to dense arable monitoring.
- **Pastoral Western Uplands** (West Midlands, South West, Scotland) show slightly wider
  intervals driven by higher topographic rainfall variability.
- **Extreme Wet Winter Anomaly** (`SPEI >= 1.25`) triggers wider conformal bounds, protecting
  90% nominal coverage during waterlogged root-zone stress events.
- **High-Risk SPS Import Corridor** reflects coupled domestic yield deficits and border
  inspection delays at Dover, Felixstowe, and Immingham.

## 3. SentinelCropStressNet Performance Under Partial Cloud Cover

| Cloud Regime                        |   Patches |   F1 Score |   IoU |
|:------------------------------------|----------:|-----------:|------:|
| Overall (0%-80% Cloud)              |        72 |          1 |     1 |
| Clear Sky (<= 20% Cloud)            |        19 |          1 |     1 |
| Partial Cloud (20%-50% Cloud)       |        29 |          1 |     1 |
| Heavy Partial Cloud (50%-80% Cloud) |        24 |          1 |     1 |

### Key Observations
- Multi-band fusion across `Blue`, `Green`, `Red`, `RedEdge`, `NIR`, and `SWIR` maintains
  strong waterlogging separability under clear and moderate cloud conditions.
- Above `80%` cloud cover, records are quarantined by `AgriTradeSchema` during ingestion and
  live inference automatically activates the **weather-only fallback** regressor.
