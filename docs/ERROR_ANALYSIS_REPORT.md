# HarvestShield UK — Sliced Error Analysis & Conformal Audit Report

## 1. Executive Summary

This report audits **HarvestShield UK** forecasting reliability across UK agro-ecological
slices, extreme waterlogging anomalies, high-risk Defra Border Target Operating Model (BTOM)
import corridors, and Sentinel-2 partial cloud regimes.

- **Horizon t+3m Conformal Yield Deviation**: MAE = `1.549` pp, 90% Coverage = `0.989`
- **UK Port Clearance Delay Risk**: MAE = `4.781` hours
- **Weather-Only Fallback (`cloud_cover_pct > 80%`) t+1m MAE**: `1.213` pp

## 2. Regional & Domain Slice Audit (t+1m Yield Deviation & 90% Conformal Coverage)

| Slice                         |   Samples |   MAE (pp) |   RMSE (pp) |   90% Conformal Coverage |   Mean Width (pp) |
|:------------------------------|----------:|-----------:|------------:|-------------------------:|------------------:|
| Overall (All UK Regions)      |       349 |      1.065 |       1.344 |                    0.997 |             7.089 |
| Arable Eastern Lowlands       |       175 |      1.005 |       1.282 |                    0.994 |             7.045 |
| Pastoral Western Uplands      |       174 |      1.126 |       1.403 |                    1     |             7.133 |
| Extreme Wet Winter Anomaly    |        56 |      0.935 |       1.199 |                    1     |             7.154 |
| High-Risk SPS Import Corridor |       258 |      1.109 |       1.4   |                    0.996 |             7.092 |

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
