# HarvestShield UK — 300-Capability Skills & Architecture Matrix

This matrix maps **300 concrete capabilities** across six technical pillars directly to the implemented files, classes, functions, and verification suites in `harvestshield-uk`.

---

## Pillar 1: Agri-Trade Ingestion & Quality Gates (Skills 001–050)

| # | Capability | Implementation File | Function / Symbol |
|---:|---|---|---|
| 001 | Live UK Food Standards Agency (FSA) Food Alerts API polling (`_limit=50`) | `src/ingestion/live_agri_connectors.py` | `_fetch_fsa_alerts_json` |
| 002 | Live FSA allergen alert keyword extraction (`allergen`, `undeclared`) | `src/ingestion/live_agri_connectors.py` | `_summarise_fsa_alerts` |
| 003 | Live FSA pathogen & recall signal parsing (`salmonella`, `listeria`, `mycotoxin`) | `src/ingestion/live_agri_connectors.py` | `_summarise_fsa_alerts` |
| 004 | Live Open-Meteo UK regional agro-meteorological API polling | `src/ingestion/live_agri_connectors.py` | `_fetch_open_meteo_region` |
| 005 | UK farming region latitude/longitude spatial anchor mapping (6 regions) | `src/ingestion/live_agri_connectors.py` | `UK_REGION_COORDINATES` |
| 006 | 30-day rolling precipitation sum normalization to monthly rainfall (mm) | `src/ingestion/live_agri_connectors.py` | `_extract_region_weather` |
| 007 | Hourly Open-Meteo root-zone `soil_moisture_0_to_7cm` saturation scaling | `src/ingestion/live_agri_connectors.py` | `_extract_region_weather` |
| 008 | Daily min/max 2m air temperature aggregation (`Europe/London`) | `src/ingestion/live_agri_connectors.py` | `_extract_region_weather` |
| 009 | Tenacity exponential-backoff HTTP retry policy (3 attempts) on FSA feed | `src/ingestion/live_agri_connectors.py` | `_fetch_fsa_alerts_json` |
| 010 | Tenacity exponential-backoff HTTP retry policy (3 attempts) on Open-Meteo feed | `src/ingestion/live_agri_connectors.py` | `_fetch_open_meteo_region` |
| 011 | Graceful `LIVE_FSA_AGRI_DEGRADED` offline fallback on HTTP/timeout failures | `src/ingestion/live_agri_connectors.py` | `_offline_degraded_weather_and_fsa` |
| 012 | `LIVE_FSA_OPENMETEO` vs `LIVE_FSA_AGRI_DEGRADED` provenance tagging | `src/ingestion/live_agri_connectors.py` | `fetch_live_uk_fsa_and_agri_weather` |
| 013 | Injectable `httpx.Client` dependency for deterministic transport testing | `src/ingestion/live_agri_connectors.py` | `fetch_live_uk_fsa_and_agri_weather` |
| 014 | Coupling FSA alert pressure into BTOM Medium/High port delay estimates | `src/ingestion/live_agri_connectors.py` | `_build_calibrated_agri_trade_rows` |
| 015 | Coupling FSA alert pressure into UK wholesale food price index | `src/ingestion/live_agri_connectors.py` | `_build_calibrated_agri_trade_rows` |
| 016 | Sentinel-2 NDVI/NDWI spectral synthesis calibrated to rainfall anomalies | `src/ingestion/live_agri_connectors.py` | `_build_calibrated_agri_trade_rows` |
| 017 | Live connector end-to-end validation & quarantine invocation | `src/ingestion/live_agri_connectors.py` | `fetch_live_uk_fsa_and_agri_weather` |
| 018 | DataFrame `attrs` observability metadata (`total_rows`, `quarantined_rows`) | `src/ingestion/live_agri_connectors.py` | `fetch_live_uk_fsa_and_agri_weather` |
| 019 | Canonical UK ITL1 12-region enumeration contract | `src/ingestion/agri_trade_pipeline.py` | `UK_ITL1_REGIONS` |
| 020 | UK agricultural-region-to-ITL1 mapping (`East Anglia` -> `East of England`, etc.) | `src/ingestion/agri_trade_pipeline.py` | `FARMING_REGION_TO_ITL1` |
| 021 | Pandera `AgriTradeSchema` declarative quality contract builder | `src/ingestion/agri_trade_pipeline.py` | `build_agri_trade_schema` |
| 022 | Strict 8-digit CN/HS commodity code regex gate (`^\d{8}$`) | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 023 | Non-negative HMRC agri-import tonnage validation (`import_tonnes >= 0.0`) | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 024 | Sentinel-2 optical cloud cover ceiling gate (`0 <= cloud_cover_pct <= 80.0`) | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 025 | Normalized Difference Vegetation Index physical bounds (`-1.0 <= ndvi <= 1.0`) | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 026 | Normalized Difference Water Index physical bounds (`-1.0 <= ndwi <= 1.0`) | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 027 | Importer EORI minimum-length contract check (`min_value=5`) | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 028 | Farm CPH identifier minimum-length contract check (`min_value=3`) | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 029 | Safe numeric coercion pre-pass isolating non-numeric strings without aborting batch | `src/ingestion/agri_trade_pipeline.py` | `_collect_invalid_indices` |
| 030 | Missing/null identifier detection across mandatory string columns | `src/ingestion/agri_trade_pipeline.py` | `_collect_invalid_indices` |
| 031 | Lazy Pandera multi-error aggregation (`lazy=True`, `SchemaErrors`) | `src/ingestion/agri_trade_pipeline.py` | `_collect_invalid_indices` |
| 032 | Row-level multi-violation `quarantine_reason` annotation | `src/ingestion/agri_trade_pipeline.py` | `run_agri_trade_ingestion` |
| 033 | UK GDPR deterministic HMAC-SHA256 pseudonymisation (`hmac_<hex>`) | `src/ingestion/agri_trade_pipeline.py` | `pseudonymise_identifier` |
| 034 | Environment-driven HMAC secret key injection (`HARVESTSHIELD_HMAC_KEY`) | `src/ingestion/agri_trade_pipeline.py` | `pseudonymise_identifier` |
| 035 | NaN/None safe handling in GDPR pseudonymisation | `src/ingestion/agri_trade_pipeline.py` | `pseudonymise_identifier` |
| 036 | Automated stripping of raw `importer_eori` and `farm_id` columns post-hashing | `src/ingestion/agri_trade_pipeline.py` | `pseudonymise_gdpr_columns` |
| 037 | GDPR pseudonymisation applied to dead-letter quarantine rows prior to disk write | `src/ingestion/agri_trade_pipeline.py` | `run_agri_trade_ingestion` |
| 038 | DuckDB analytical table persistence (`agri_trade_clean`) | `src/ingestion/agri_trade_pipeline.py` | `persist_to_duckdb` |
| 039 | Zero-copy DuckDB view registration for clean pandas DataFrames | `src/ingestion/agri_trade_pipeline.py` | `persist_to_duckdb` |
| 040 | Parquet Dead-Letter Quarantine persistence (`data/quarantine/agri_quarantine.parquet`) | `src/ingestion/agri_trade_pipeline.py` | `persist_quarantine_parquet` |
| 041 | Mixed corrupt object-column stringification for fault-tolerant Parquet writes | `src/ingestion/agri_trade_pipeline.py` | `persist_quarantine_parquet` |
| 042 | Structured `IngestionResult` dataclass telemetry (`total_rows`, `clean_rows`, `quarantined_rows`) | `src/ingestion/agri_trade_pipeline.py` | `IngestionResult` |
| 043 | Configurable DuckDB & Parquet output path overrides for isolated testing | `src/ingestion/agri_trade_pipeline.py` | `run_agri_trade_ingestion` |
| 044 | Synthetic UK agri-trade dataset generator with controllable corruption rate (~3%) | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 045 | Five-mode corruption injection (cloud >80%, NDVI >1, negative tonnes, bad HS, bad ITL1) | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 046 | Raw synthetic Parquet staging (`data/raw/uk_agri_trade_synthetic.parquet`) | `src/run_pipeline.py` | `run_end_to_end_pipeline` |
| 047 | Automated quarantine test verifying cloud-obscured (>80%) row isolation | `tests/test_contracts_and_errors.py` | `test_quarantine_contracts_and_gdpr_eori_hashing` |
| 048 | Automated DuckDB scan verifying raw EORI absence in persisted records | `tests/test_contracts_and_errors.py` | `test_quarantine_contracts_and_gdpr_eori_hashing` |
| 049 | Automated mocked live FSA + Open-Meteo ingestion verification | `tests/test_contracts_and_errors.py` | `test_live_fsa_openmeteo_connectors_and_degraded_fallback` |
| 050 | Automated degraded-feed fallback test (`LIVE_FSA_AGRI_DEGRADED`) on HTTP 503 | `tests/test_contracts_and_errors.py` | `test_live_fsa_openmeteo_connectors_and_degraded_fallback` |

---

## Pillar 2: Agro-Meteorological & Causal Econometrics (Skills 051–100)

| # | Capability | Implementation File | Function / Symbol |
|---:|---|---|---|
| 051 | UK farming region canonical tuple (`East Anglia` .. `Scotland`) | `src/analytics/crop_weather_econometrics.py` | `UK_FARMING_REGIONS` |
| 052 | UK cereal base-temperature thermal accumulation (`t_base_c = 5.0°C`) | `src/analytics/crop_weather_econometrics.py` | `compute_growing_degree_days` |
| 053 | Zero-clamped thermal degree day calculation (`max(0, t_mean - t_base)`) | `src/analytics/crop_weather_econometrics.py` | `compute_growing_degree_days` |
| 054 | Monthly-scaled GDD integration (`days_in_period = 30.0`) | `src/analytics/crop_weather_econometrics.py` | `compute_growing_degree_days` |
| 055 | UK latitude-calibrated Potential Evapotranspiration (PET) approximation | `src/analytics/crop_weather_econometrics.py` | `compute_pet_thornthwaite_approx` |
| 056 | Temperature-clamped PET floor preventing negative winter evapotranspiration | `src/analytics/crop_weather_econometrics.py` | `compute_pet_thornthwaite_approx` |
| 057 | Latitude adjustment factor for northern UK catchments (`latitude_deg`) | `src/analytics/crop_weather_econometrics.py` | `compute_pet_thornthwaite_approx` |
| 058 | Climatic water balance computation (`D = rainfall_mm - pet_mm`) | `src/analytics/crop_weather_econometrics.py` | `compute_spei_waterlogging_anomalies` |
| 059 | Region-grouped SPEI z-score standardization across UK catchments | `src/analytics/crop_weather_econometrics.py` | `compute_spei_waterlogging_anomalies` |
| 060 | Zero-variance guard during single-region or small-batch SPEI computation | `src/analytics/crop_weather_econometrics.py` | `compute_spei_waterlogging_anomalies` |
| 061 | Configurable SPEI waterlogging anomaly threshold (`waterlog_threshold=1.25`) | `src/analytics/crop_weather_econometrics.py` | `compute_spei_waterlogging_anomalies` |
| 062 | Boolean `waterlogging_anomaly` risk indicator flagging wet-winter stress | `src/analytics/crop_weather_econometrics.py` | `compute_spei_waterlogging_anomalies` |
| 063 | Single-row inference climatic water-balance SPEI calibration in API | `src/app/main.py` | `forecast_harvest` |
| 064 | Optional `spei_override` support for counterfactual stress testing | `src/app/main.py` | `HarvestForecastRequest` |
| 065 | Two-Model (T-Learner) causal meta-learner formulation (`mu_1(X) - mu_0(X)`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 066 | Treated-regime `GradientBoostingRegressor` response surface `mu_1(X)` | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 067 | Control-regime `GradientBoostingRegressor` response surface `mu_0(X)` | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 068 | Automatic derivation of binary `supply_shock` treatment from SPEI/yield deficit | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 069 | Confounder covariate selection (`gdd`, `spei`, `rainfall_mm`, `ndvi`, `ndwi`, `soil_moisture_pct`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 070 | Sample adequacy assertion for treated and control cohorts (`>= 5`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 071 | Conditional Average Treatment Effect (CATE) import surge tonnage (`cate_import_uplift_tonnes`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 072 | CATE percentage import surge uplift (`cate_import_uplift_pct`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 073 | Counterfactual baseline floor (`max(|pred0|, 1.0)`) preventing zero division | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 074 | Average Treatment Effect (ATE) import tonnage surge summary | `src/analytics/crop_weather_econometrics.py` | `TLearnerSupplyShockResult` |
| 075 | Average Treatment Effect (ATE) import percentage surge summary | `src/analytics/crop_weather_econometrics.py` | `TLearnerSupplyShockResult` |
| 076 | Causal CATE wholesale food price uplift estimation (`cate_price_uplift_pct`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 077 | Causal ATE wholesale food price shock percentage (`ate_price_uplift_pct`) | `src/analytics/crop_weather_econometrics.py` | `TLearnerSupplyShockResult` |
| 078 | Domestic yield-shock wholesale food price elasticity (`%ΔPrice / %ΔSupply`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 079 | Near-zero yield differential stability guard (`abs(supply_change) < 0.5`) | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 080 | Fallback price elasticity calculation when yield deviation column is absent | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 081 | Treated vs. control sample count audit fields in result dataclass | `src/analytics/crop_weather_econometrics.py` | `TLearnerSupplyShockResult` |
| 082 | Enriched DataFrame persistence back to DuckDB with GDD, SPEI, and CATE columns | `src/run_pipeline.py` | `run_end_to_end_pipeline` |
| 083 | Regional climate baselines for East Anglia arable lowland cereals | `src/ingestion/live_agri_connectors.py` | `_offline_degraded_weather_and_fsa` |
| 084 | Regional climate baselines for Lincolnshire fenland horticulture/cereals | `src/ingestion/live_agri_connectors.py` | `_offline_degraded_weather_and_fsa` |
| 085 | Regional climate baselines for Yorkshire mixed arable & livestock | `src/ingestion/live_agri_connectors.py` | `_offline_degraded_weather_and_fsa` |
| 086 | Regional climate baselines for West Midlands pastoral/horticulture | `src/ingestion/live_agri_connectors.py` | `_offline_degraded_weather_and_fsa` |
| 087 | Regional climate baselines for South West high-rainfall grassland | `src/ingestion/live_agri_connectors.py` | `_offline_degraded_weather_and_fsa` |
| 088 | Regional climate baselines for Scotland upland & cool-temperate arable | `src/ingestion/live_agri_connectors.py` | `_offline_degraded_weather_and_fsa` |
| 089 | Wet-winter waterlogging coupled NDVI depression modeling | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 090 | Wet-winter waterlogging coupled NDWI elevation modeling | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 091 | Soil moisture hydrological coupling to cumulative catchment rainfall | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 092 | Domestic yield deficit-driven import substitution surge modeling | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 093 | BTOM risk-tier baseline port inspection dwell hours (`Low`/`Medium`/`High`) | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 094 | `t+3m` compounded crop yield stress horizon propagation | `src/run_pipeline.py` | `generate_uk_synthetic_dataset` |
| 095 | Reproducible random seeding (`random_state=42`) across T-Learner models | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 096 | Custom feature subset override support in T-Learner API | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 097 | Explicit validation error when zero confounder features exist | `src/analytics/crop_weather_econometrics.py` | `estimate_supply_shock_t_learner` |
| 098 | Unit verification of GDD zero-clamping below 5.0°C base | `tests/test_contracts_and_errors.py` | `test_t_learner_supply_shock_uplift_and_econometrics` |
| 099 | Unit verification of positive causal import surge ATE under supply shock | `tests/test_contracts_and_errors.py` | `test_t_learner_supply_shock_uplift_and_econometrics` |
| 100 | Unit verification of finite negative wholesale food price elasticity | `tests/test_contracts_and_errors.py` | `test_t_learner_supply_shock_uplift_and_econometrics` |

---

## Pillar 3: Conformal Yield Forecasting & Sliced Error Audit (Skills 101–150)

| # | Capability | Implementation File | Function / Symbol |
|---:|---|---|---|
| 101 | Multimodal meteorological + Sentinel-2 feature schema (`MULTIMODAL_FEATURES`) | `src/models/yield_and_satellite.py` | `MULTIMODAL_FEATURES` |
| 102 | Weather-only fallback feature schema excluding spectral bands (`WEATHER_ONLY_FEATURES`) | `src/models/yield_and_satellite.py` | `WEATHER_ONLY_FEATURES` |
| 103 | LightGBM gradient-boosted base regressor (`LGBMRegressor`) configuration | `src/models/yield_and_satellite.py` | `_build_conformal_lgbm` |
| 104 | `MAPIE` `CrossConformalRegressor` (jackknife+ / `method="plus"`) wrapper | `src/models/yield_and_satellite.py` | `_build_conformal_lgbm` |
| 105 | Nominal 90% prediction interval calibration (`confidence_level=0.90`) | `src/models/yield_and_satellite.py` | `_build_conformal_lgbm` |
| 106 | Absolute residual conformity score (`conformity_score="absolute"`) | `src/models/yield_and_satellite.py` | `_build_conformal_lgbm` |
| 107 | Spatial leak-free `GroupKFold` cross-validation grouped by agricultural region | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 108 | Dynamic `n_splits` clamping (`max(2, min(5, n_unique_groups))`) for small cohorts | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 109 | `fit_conformalize` group-aware conformal calibration step | `src/models/yield_and_satellite.py` | `_fit_and_eval_conformal` |
| 110 | Unified 2D/3D MAPIE prediction interval bound extraction | `src/models/yield_and_satellite.py` | `_extract_bounds` |
| 111 | County crop yield deviation `t+1m` multimodal conformal predictor | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 112 | County crop yield deviation `t+3m` multimodal conformal predictor | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 113 | UK port clearance delay risk (`port_delay_hours`) conformal predictor | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 114 | Dedicated `t+1m` weather-only fallback conformal model | `src/models/yield_and_satellite.py` | `ConformalForecastBundle` |
| 115 | Dedicated `t+3m` weather-only fallback conformal model | `src/models/yield_and_satellite.py` | `ConformalForecastBundle` |
| 116 | Dedicated port-delay weather-only fallback conformal model | `src/models/yield_and_satellite.py` | `ConformalForecastBundle` |
| 117 | Out-of-fold / conformalized prediction table with 90% bounds (`oof_predictions`) | `src/models/yield_and_satellite.py` | `ConformalForecastBundle` |
| 118 | Mean Absolute Error (MAE) computation across all horizons | `src/models/yield_and_satellite.py` | `_fit_and_eval_conformal` |
| 119 | Root Mean Squared Error (RMSE) computation across all horizons | `src/models/yield_and_satellite.py` | `_fit_and_eval_conformal` |
| 120 | Empirical 90% conformal interval coverage verification (`coverage_90`) | `src/models/yield_and_satellite.py` | `_fit_and_eval_conformal` |
| 121 | Mean conformal interval width tracking (`mean_width`) | `src/models/yield_and_satellite.py` | `_fit_and_eval_conformal` |
| 122 | Weather-only fallback MAE parity logging alongside multimodal MAE | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 123 | Automatic `itl1_region` fallback when `farming_region` column is omitted | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 124 | Single-thread LightGBM (`n_jobs=1`) preventing OpenMP contention | `src/models/yield_and_satellite.py` | `_build_conformal_lgbm` |
| 125 | Structured `ConformalForecastBundle` model & metric container | `src/models/yield_and_satellite.py` | `ConformalForecastBundle` |
| 126 | FastAPI bootstrap calibration dataset when DuckDB is empty | `src/app/main.py` | `_build_bootstrap_training_frame` |
| 127 | DuckDB-backed cached conformal bundle loading (`@lru_cache`) | `src/app/main.py` | `get_forecast_bundle` |
| 128 | Automatic weather-only fallback trigger on `cloud_cover_pct > 80.0` | `src/app/main.py` | `forecast_harvest` |
| 129 | Automatic weather-only fallback trigger when NDVI or NDWI is null | `src/app/main.py` | `forecast_harvest` |
| 130 | Non-negative port clearance delay clamping in API responses | `src/app/main.py` | `forecast_harvest` |
| 131 | Scalar conformal lower/upper interval extraction for API JSON responses | `src/app/main.py` | `_extract_scalar_interval` |
| 132 | Slice-level regression metric evaluator (MAE, RMSE, 90% coverage, width) | `src/evaluation/error_analysis.py` | `_slice_regression_metrics` |
| 133 | Empty-slice NaN-safe handling in error analysis tables | `src/evaluation/error_analysis.py` | `_slice_regression_metrics` |
| 134 | Overall UK all-regions benchmark audit slice | `src/evaluation/error_analysis.py` | `evaluate_yield_slices` |
| 135 | `Arable Eastern Lowlands` slice (East Anglia, Lincolnshire, Yorkshire) | `src/evaluation/error_analysis.py` | `evaluate_yield_slices` |
| 136 | `Pastoral Western Uplands` slice (West Midlands, South West, Scotland, Wales) | `src/evaluation/error_analysis.py` | `evaluate_yield_slices` |
| 137 | `Extreme Wet Winter Anomaly` slice (`SPEI >= 1.25`) | `src/evaluation/error_analysis.py` | `evaluate_yield_slices` |
| 138 | `High-Risk SPS Import Corridor` slice (BTOM High/Medium & elevated port delay) | `src/evaluation/error_analysis.py` | `evaluate_yield_slices` |
| 139 | Markdown report generation (`docs/ERROR_ANALYSIS_REPORT.md`) via `tabulate` | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 140 | Executive summary surfacing `t+3m` MAE, coverage, port MAE, and fallback MAE | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 141 | Domain commentary summarizing regional interval width & cloud fallback dynamics | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 142 | Structured `ErrorAnalysisSummary` dataclass output | `src/evaluation/error_analysis.py` | `ErrorAnalysisSummary` |
| 143 | Automated directory creation for `docs/` before report export | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 144 | Unit test asserting valid conformal interval ordering (`lower <= pred <= upper`) | `tests/test_contracts_and_errors.py` | `test_conformal_yield_and_sentinel_crop_stress_net` |
| 145 | Unit test verifying 90% empirical coverage floor (`>= 0.70`) under `GroupKFold` | `tests/test_contracts_and_errors.py` | `test_conformal_yield_and_sentinel_crop_stress_net` |
| 146 | Unit test verifying all 4 domain slices appear in `ERROR_ANALYSIS_REPORT.md` | `tests/test_contracts_and_errors.py` | `test_error_analysis_report_generation` |
| 147 | Unit test verifying FastAPI clear-sky `multimodal_satellite_weather` path | `tests/test_contracts_and_errors.py` | `test_fastapi_endpoints_and_cloud_cover_fallback` |
| 148 | Unit test verifying FastAPI `weather_only_fallback` path when `cloud_cover_pct > 80` | `tests/test_contracts_and_errors.py` | `test_fastapi_endpoints_and_cloud_cover_fallback` |
| 149 | Interactive Streamlit conformal forecast sliders for `t+1m`, `t+3m`, port delay | `src/app/dashboard.py` | `tab_crop` |
| 150 | Interactive Streamlit fallback warning banner when cloud cover exceeds 80% | `src/app/dashboard.py` | `tab_crop` |

---

## Pillar 4: PyTorch `SentinelCropStressNet` & Remote Sensing (Skills 151–200)

| # | Capability | Implementation File | Function / Symbol |
|---:|---|---|---|
| 151 | Canonical 6-band Sentinel-2 spectral order (`Blue`, `Green`, `Red`, `RedEdge`, `NIR`, `SWIR`) | `src/models/yield_and_satellite.py` | `SENTINEL2_BANDS` |
| 152 | Multi-band 2D CNN encoder (`SentinelCropStressNet`) accepting `(B, 6, H, W)` | `src/models/yield_and_satellite.py` | `SentinelCropStressNet` |
| 153 | First spatial spectral-mixing Conv2d block (`6 -> 24` channels, `3x3`, `padding=1`) | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 154 | `BatchNorm2d(24)` + in-place `ReLU` feature normalization | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 155 | Second convolutional texture block (`24 -> 48` channels) | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 156 | `MaxPool2d(2)` spatial downsampling for canopy patch invariance | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 157 | Third deep spectral-spatial block (`48 -> 64` channels) | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 158 | Resolution-agnostic `AdaptiveAvgPool2d((1, 1))` global pooling | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 159 | Dropout regularization (`p=0.15`) in MLP classification head | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 160 | Two-layer linear classifier head (`64 -> 32 -> 2`) for healthy vs waterlogged | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.__init__` |
| 161 | Logit tensor output (`(batch, 2)`) for CrossEntropy optimization | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.forward` |
| 162 | Inference-safe `@torch.no_grad()` waterlogged probability estimator | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.predict_waterlogged_proba` |
| 163 | Automatic `eval()` / `train()` state restoration after probability inference | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.predict_waterlogged_proba` |
| 164 | Softmax class-1 (`waterlogged`) probability extraction | `src/models/yield_and_satellite.py` | `SentinelCropStressNet.predict_waterlogged_proba` |
| 165 | 6-band Sentinel-2 arable patch simulator (`16x16` default patch size) | `src/models/yield_and_satellite.py` | `generate_sentinel2_patches` |
| 166 | Healthy arable spectral signature (low Red, high RedEdge/NIR, moderate SWIR) | `src/models/yield_and_satellite.py` | `generate_sentinel2_patches` |
| 167 | Waterlogged arable spectral signature (elevated Blue/Green, absorbed SWIR/NIR) | `src/models/yield_and_satellite.py` | `generate_sentinel2_patches` |
| 168 | Stochastic partial cloud haze injection (`0%-80%` cloud cover strata) | `src/models/yield_and_satellite.py` | `generate_sentinel2_patches` |
| 169 | Reflectance clamping to physical TOA/BOA reflectance bounds `[0.0, 1.0]` | `src/models/yield_and_satellite.py` | `generate_sentinel2_patches` |
| 170 | Stratified train/test split (`70/30`) preserving class balance | `src/models/yield_and_satellite.py` | `train_sentinel_crop_stress_net` |
| 171 | PyTorch `TensorDataset` & mini-batch `DataLoader` (`batch_size=32`) | `src/models/yield_and_satellite.py` | `train_sentinel_crop_stress_net` |
| 172 | Adam optimizer training loop (`epochs=24`, `lr=3e-3`) | `src/models/yield_and_satellite.py` | `train_sentinel_crop_stress_net` |
| 173 | `CrossEntropyLoss` optimization for binary waterlogging classification | `src/models/yield_and_satellite.py` | `train_sentinel_crop_stress_net` |
| 174 | Held-out F1 score evaluation (`f1_score(..., zero_division=0)`) | `src/models/yield_and_satellite.py` | `train_sentinel_crop_stress_net` |
| 175 | Binary positive-class Intersection-over-Union (`TP / (TP + FP + FN)`) | `src/models/yield_and_satellite.py` | `compute_binary_iou` |
| 176 | Zero-union edge guard returning `1.0` when both true and pred are empty | `src/models/yield_and_satellite.py` | `compute_binary_iou` |
| 177 | Per-patch evaluation DataFrame retaining `cloud_cover_pct` and `prob_waterlogged` | `src/models/yield_and_satellite.py` | `SatelliteEvaluationResult` |
| 178 | Structured `SatelliteEvaluationResult` container (`model`, `eval_df`, `overall_f1`, `overall_iou`) | `src/models/yield_and_satellite.py` | `SatelliteEvaluationResult` |
| 179 | Overall (`0%-80%` cloud) Sentinel-2 F1/IoU audit bucket | `src/evaluation/error_analysis.py` | `evaluate_satellite_cloud_slices` |
| 180 | `Clear Sky (<= 20% Cloud)` stratified F1/IoU audit | `src/evaluation/error_analysis.py` | `evaluate_satellite_cloud_slices` |
| 181 | `Partial Cloud (20%-50% Cloud)` stratified F1/IoU audit | `src/evaluation/error_analysis.py` | `evaluate_satellite_cloud_slices` |
| 182 | `Heavy Partial Cloud (50%-80% Cloud)` stratified F1/IoU audit | `src/evaluation/error_analysis.py` | `evaluate_satellite_cloud_slices` |
| 183 | Empty cloud-stratum guard returning `0.0` F1/IoU without crash | `src/evaluation/error_analysis.py` | `evaluate_satellite_cloud_slices` |
| 184 | Reproducible PyTorch & NumPy RNG seeding (`torch.manual_seed`) | `src/models/yield_and_satellite.py` | `train_sentinel_crop_stress_net` |
| 185 | macOS dual-OpenMP safety (`KMP_DUPLICATE_LIB_OK=TRUE`, `OMP_NUM_THREADS=1`) | `src/__init__.py` | `os.environ.setdefault` |
| 186 | Spectral NDVI quality gate rejecting values outside `[-1.0, 1.0]` | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 187 | Spectral NDWI quality gate rejecting values outside `[-1.0, 1.0]` | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 188 | Optical cloud-cover quality gate quarantining `cloud_cover_pct > 80.0` | `src/ingestion/agri_trade_pipeline.py` | `AgriTradeSchema` |
| 189 | Multimodal yield model consumption of `ndvi`, `ndwi`, and `cloud_cover_pct` | `src/models/yield_and_satellite.py` | `MULTIMODAL_FEATURES` |
| 190 | Satellite-to-weather live inference fallback integration | `src/app/main.py` | `forecast_harvest` |
| 191 | Streamlit interactive NDVI/NDWI/Cloud-Cover simulation sliders | `src/app/dashboard.py` | `tab_crop` |
| 192 | Satellite F1/IoU reporting in end-to-end runner summary | `src/run_pipeline.py` | `run_end_to_end_pipeline` |
| 193 | `ERROR_ANALYSIS_REPORT.md` Sentinel-2 partial cloud Markdown table export | `src/evaluation/error_analysis.py` | `generate_error_analysis_report` |
| 194 | Unit test asserting `(4, 6, 16, 16) -> (4, 2)` CNN forward tensor shape | `tests/test_contracts_and_errors.py` | `test_conformal_yield_and_sentinel_crop_stress_net` |
| 195 | Unit test asserting Sentinel-2 held-out F1 and IoU performance bounds | `tests/test_contracts_and_errors.py` | `test_conformal_yield_and_sentinel_crop_stress_net` |
| 196 | Unit test verifying Clear Sky & Heavy Partial Cloud slices in error report | `tests/test_contracts_and_errors.py` | `test_error_analysis_report_generation` |
| 197 | Unit test rejecting `ndvi=1.35` into dead-letter quarantine | `tests/test_contracts_and_errors.py` | `test_quarantine_contracts_and_gdpr_eori_hashing` |
| 198 | Unit test rejecting `cloud_cover_pct=92.0` into dead-letter quarantine | `tests/test_contracts_and_errors.py` | `test_quarantine_contracts_and_gdpr_eori_hashing` |
| 199 | Docker image OpenMP runtime dependency (`libgomp1`) for PyTorch + LightGBM | `Dockerfile` | `apt-get install libgomp1` |
| 200 | Hardware-agnostic CPU inference support across macOS ARM64 & Linux x86_64 | `src/models/yield_and_satellite.py` | `SentinelCropStressNet` |

---

## Pillar 5: Guardrailed LangGraph Defra/FSA RAG & Biosecurity Copilot (Skills 201–250)

| # | Capability | Implementation File | Function / Symbol |
|---:|---|---|---|
| 201 | Statutory Defra BTOM High/Medium/Low Markdown corpus document | `data/regulatory_docs/btom_risk_tiers.md` | `BTOM-HIGH-01..LOW-03` |
| 202 | Statutory IPAFFS & CHED documentary workflow Markdown document | `data/regulatory_docs/ipaffs_ched_rules.md` | `IPAFFS-04` |
| 203 | Statutory UK Plant Health & Phytosanitary Manual Markdown document | `data/regulatory_docs/uk_phytosanitary_manual.md` | `PHYTO-05` |
| 204 | Statutory FSA Food Law allergens & recalls Markdown document | `data/regulatory_docs/fsa_food_law_allergens_recalls.md` | `FSA-LAW-06` |
| 205 | On-disk multi-format regulatory corpus loader (`.pdf`, `.md`, `.txt`) | `src/agents/biosecurity_copilot.py` | `load_btom_regulatory_corpus` |
| 206 | `pypdf.PdfReader` text extraction across multi-page statutory PDFs | `src/agents/biosecurity_copilot.py` | `_parse_pdf_document` |
| 207 | Multi-section Markdown `[DOC-ID]` parser extracting title, source, & risk scope | `src/agents/biosecurity_copilot.py` | `_parse_markdown_or_text` |
| 208 | Plaintext `.txt` & unsectioned Markdown ingestion with auto-ID generation | `src/agents/biosecurity_copilot.py` | `_parse_markdown_or_text` |
| 209 | Regulatory risk scope classifier (`High`, `Medium`, `Low`) from metadata/prose | `src/agents/biosecurity_copilot.py` | `_infer_risk_scope` |
| 210 | Graceful fallback to built-in `REGULATORY_CORPUS` if `docs_dir` is empty/missing | `src/agents/biosecurity_copilot.py` | `load_btom_regulatory_corpus` |
| 211 | Immutable `RegulatoryDocument` dataclass representation | `src/agents/biosecurity_copilot.py` | `RegulatoryDocument` |
| 212 | Deterministic 8-digit HS/CN-code BTOM risk registry (11 core commodities) | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 213 | HS `07011000` (seed potatoes) High-risk `CHED-PP` mapping | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 214 | HS `06029099` (nursery stock) High-risk `Xylella` attestation mapping | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 215 | HS `02013000` (boneless beef) Medium-risk `CHED-P` + EHC mapping | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 216 | HS `03021400` (Atlantic salmon) Medium-risk `CHED-P` + IUU Catch Cert mapping | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 217 | HS `04069099` (cheese/dairy) Medium-risk `CHED-P` + FSA allergen trace mapping | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 218 | HS `07019090` (ware potatoes) Medium-risk Phytosanitary `Ralstonia` mapping | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 219 | HS `10019900` & `12051090` (wheat/oilseed rape) Low-risk BTOM mapping | `src/agents/biosecurity_copilot.py` | `HS_CODE_BTOM_REGISTRY` |
| 220 | Chapter-level deterministic fallback for uncatalogued 8-digit HS codes | `src/agents/biosecurity_copilot.py` | `lookup_hs_btom_tier` |
| 221 | Alphanumeric corpus & query tokenizer (`_tokenize`) | `src/agents/biosecurity_copilot.py` | `_tokenize` |
| 222 | `BM25Okapi` lexical sparse retrieval scoring | `src/agents/biosecurity_copilot.py` | `HybridRegulatoryRetriever` |
| 223 | `TfidfVectorizer` (`ngram_range=(1, 2)`) cosine similarity scoring | `src/agents/biosecurity_copilot.py` | `HybridRegulatoryRetriever` |
| 224 | Smooth `tanh` BM25 scaling blended with TF-IDF cosine (`0.55 / 0.45`) | `src/agents/biosecurity_copilot.py` | `HybridRegulatoryRetriever.retrieve` |
| 225 | Zero-relevance suppression preventing spurious matches on gibberish queries | `src/agents/biosecurity_copilot.py` | `HybridRegulatoryRetriever.retrieve` |
| 226 | Typed LangGraph workflow state schema (`CopilotState`) | `src/agents/biosecurity_copilot.py` | `CopilotState` |
| 227 | Five-node compiled `StateGraph` orchestration (`guardrail`..`fallback`) | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._compile_graph` |
| 228 | Empty query & missing HS-code input validation guardrail | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._guardrail_node` |
| 229 | Prompt-injection regex defense (`ignore previous instructions`) | `src/agents/biosecurity_copilot.py` | `UNSAFE_BYPASS_PATTERNS` |
| 230 | Biosecurity evasion defense (`bypass IPAFFS/BTOM`, `forge EHC`, `smuggle`) | `src/agents/biosecurity_copilot.py` | `UNSAFE_BYPASS_PATTERNS` |
| 231 | Automatic 8-digit HS-code extraction from natural-language queries | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._guardrail_node` |
| 232 | Top-k hybrid retrieval execution node (`_retrieve_node`) | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._retrieve_node` |
| 233 | Minimum retrieval confidence threshold gating (`min_retrieval_score=0.25`) | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._draft_node` |
| 234 | Grounded answer synthesis with inline bracketed citations (`[DOC-ID]`) | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._draft_node` |
| 235 | Citation-verifier judge node validating all `[DOC-ID]`s against retrieved set | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._citation_verifier_node` |
| 236 | Hallucinated-citation rejection & deterministic fallback rerouting | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._citation_verifier_node` |
| 237 | Tier-consistency check verifying draft reflects deterministic BTOM tier | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._citation_verifier_node` |
| 238 | Deterministic HS-code BTOM lookup fallback node | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._deterministic_fallback_node` |
| 239 | Safe escalation guidance when HS code is unknown and RAG confidence is low | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot._deterministic_fallback_node` |
| 240 | Configurable `docs_dir` constructor argument for custom regulatory corpora | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot.__init__` |
| 241 | Structured JSON-ready response dictionary from `ask()` | `src/agents/biosecurity_copilot.py` | `BiosecurityCopilot.ask` |
| 242 | FastAPI `/compliance-copilot` endpoint wiring (`ComplianceQueryRequest`) | `src/app/main.py` | `compliance_copilot` |
| 243 | Cached `BiosecurityCopilot` singleton in FastAPI (`@lru_cache`) | `src/app/main.py` | `get_copilot` |
| 244 | Streamlit interactive Defra BTOM / FSA Copilot compliance tab | `src/app/dashboard.py` | `tab_copilot` |
| 245 | Pipeline runner compliance verification smoke probe | `src/run_pipeline.py` | `run_end_to_end_pipeline` |
| 246 | Unit test verifying grounded `BTOM-MED-02` / `CHED-P` citations on beef query | `tests/test_contracts_and_errors.py` | `test_langgraph_btom_copilot_citations_guardrails_and_fallback` |
| 247 | Unit test verifying deterministic HS fallback on weak/off-topic query | `tests/test_contracts_and_errors.py` | `test_langgraph_btom_copilot_citations_guardrails_and_fallback` |
| 248 | Unit test verifying unsafe border-bypass prompt rejection | `tests/test_contracts_and_errors.py` | `test_langgraph_btom_copilot_citations_guardrails_and_fallback` |
| 249 | Unit test verifying `.pdf` (`pypdf`), `.md`, `.txt` ingestion in `load_btom_regulatory_corpus` | `tests/test_contracts_and_errors.py` | `test_load_btom_regulatory_corpus_parses_pdf_md_txt` |
| 250 | Unit test verifying FastAPI `/compliance-copilot` response on dairy HS `04069099` | `tests/test_contracts_and_errors.py` | `test_fastapi_endpoints_and_cloud_cover_fallback` |

---

## Pillar 6: MLOps, API, Dashboard, Packaging & Verification (Skills 251–300)

| # | Capability | Implementation File | Function / Symbol |
|---:|---|---|---|
| 251 | PEP 621 package metadata & core dependencies (`httpx`, `tenacity`, `pypdf`, etc.) | `pyproject.toml` | `[project]` |
| 252 | Optional `dev` (`pytest`, `httpx`, `ruff`) and `ui` (`streamlit`, `tabulate`) extras | `pyproject.toml` | `[project.optional-dependencies]` |
| 253 | Python 3.12 Ruff lint configuration (`E`, `F`, `I`, `W`, `UP`, `B`) | `pyproject.toml` | `[tool.ruff.lint]` |
| 254 | Pytest discovery configuration (`testpaths = ["tests"]`, `pythonpath = ["."]`) | `pyproject.toml` | `[tool.pytest.ini_options]` |
| 255 | Production container image (`python:3.12-slim` + `libgomp1` + `curl`) | `Dockerfile` | `FROM python:3.12-slim` |
| 256 | Container `/health` HTTP `HEALTHCHECK` probe | `Dockerfile` | `HEALTHCHECK` |
| 257 | Multi-service `pgvector` (PostgreSQL 16) vector database container | `docker-compose.yml` | `services.pgvector` |
| 258 | Containerized MLflow tracking server backed by SQLite (`mlruns/mlflow.db`) | `docker-compose.yml` | `services.mlflow` |
| 259 | Containerized FastAPI service wired to `pgvector` & `mlflow` volumes | `docker-compose.yml` | `services.api` |
| 260 | GitHub Actions CI pipeline (`ubuntu-latest`, Python 3.12, `uv`) | `.github/workflows/ci.yml` | `lint-and-test` |
| 261 | CI automated Ruff lint check (`ruff check src tests`) | `.github/workflows/ci.yml` | `Lint with ruff` |
| 262 | CI automated end-to-end pipeline smoke execution | `.github/workflows/ci.yml` | `Run end-to-end pipeline smoke check` |
| 263 | CI automated `pytest -v` test suite execution | `.github/workflows/ci.yml` | `Run pytest suite` |
| 264 | MLflow SQLite tracking URI initialization (`sqlite:///mlruns/mlflow.db`) | `src/models/yield_and_satellite.py` | `DEFAULT_MLFLOW_URI` |
| 265 | Automatic `mlruns/` parent directory creation before SQLite connection | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 266 | MLflow experiment logging for GroupKFold conformal hyperparameters & metrics | `src/models/yield_and_satellite.py` | `train_conformal_yield_and_delay_models` |
| 267 | MLflow experiment logging for Sentinel-2 CNN bands, epochs, F1, and IoU | `src/models/yield_and_satellite.py` | `train_sentinel_crop_stress_net` |
| 268 | CLI `--live / --no-live` switch via `argparse.BooleanOptionalAction` (default `True`) | `src/run_pipeline.py` | `parse_args` |
| 269 | End-to-end orchestrator switching cleanly between live & offline data | `src/run_pipeline.py` | `run_end_to_end_pipeline` |
| 270 | Structured CLI run summary output (`feed_status`, coverage, F1/IoU, report path) | `src/run_pipeline.py` | `__main__` |
| 271 | FastAPI application metadata & OpenAPI schema generation | `src/app/main.py` | `app` |
| 272 | FastAPI `/health` readiness check reporting DuckDB clean row count | `src/app/main.py` | `health` |
| 273 | Pydantic request validation (`HarvestForecastRequest`, 8-digit HS regex) | `src/app/main.py` | `HarvestForecastRequest` |
| 274 | Pydantic typed response schema (`HarvestForecastResponse`) | `src/app/main.py` | `HarvestForecastResponse` |
| 275 | Pydantic request/response schemas for biosecurity copilot endpoint | `src/app/main.py` | `ComplianceQueryResponse` |
| 276 | Streamlit wide-layout multipage dashboard (`HarvestShield UK`) | `src/app/dashboard.py` | `st.set_page_config` |
| 277 | Streamlit DuckDB clean agri-trade explorer dataframe view | `src/app/dashboard.py` | `tab_crop` |
| 278 | Streamlit Parquet dead-letter quarantine inspector view | `src/app/dashboard.py` | `tab_audit` |
| 279 | Streamlit live rendering of `docs/ERROR_ANALYSIS_REPORT.md` | `src/app/dashboard.py` | `tab_audit` |
| 280 | Gitignore protection for `.venv`, `mlruns/`, `*.egg-info/`, and runtime data | `.gitignore` | `.gitignore` |
| 281 | Comprehensive architecture & quickstart documentation | `README.md` | `Quickstart` |
| 282 | 300-capability traceability matrix linking requirements to codebase symbols | `docs/SKILLS_MATRIX.md` | `SKILLS_MATRIX.md` |
| 283 | Sliced error & conformal coverage audit report artifact | `docs/ERROR_ANALYSIS_REPORT.md` | `ERROR_ANALYSIS_REPORT.md` |
| 284 | Package initialization setting OpenMP & MLflow hint defaults | `src/__init__.py` | `os.environ.setdefault` |
| 285 | Modular subpackage organization (`ingestion`, `analytics`, `models`, `evaluation`, `agents`, `app`) | `src/` | `__init__.py` |
| 286 | Isolated `tmp_path` test fixtures preventing test side effects on runtime data | `tests/test_contracts_and_errors.py` | `test_quarantine_contracts_and_gdpr_eori_hashing` |
| 287 | FastAPI `TestClient` integration tests across all three REST endpoints | `tests/test_contracts_and_errors.py` | `test_fastapi_endpoints_and_cloud_cover_fallback` |
| 288 | CLI `--live` / `--no-live` parser & degraded fallback pipeline tests | `tests/test_contracts_and_errors.py` | `test_run_pipeline_cli_flags_and_offline_mode` |
| 289 | Mocked `httpx.MockTransport` unit test for FSA & Open-Meteo connectors | `tests/test_contracts_and_errors.py` | `test_live_fsa_openmeteo_connectors_and_degraded_fallback` |
| 290 | Multi-format `.pdf`/`.md`/`.txt` RAG corpus unit test with `pypdf.PdfWriter` | `tests/test_contracts_and_errors.py` | `test_load_btom_regulatory_corpus_parses_pdf_md_txt` |
| 291 | Deterministic HS-code chapter-level fallback test (`03049999 -> Medium`) | `tests/test_contracts_and_errors.py` | `test_langgraph_btom_copilot_citations_guardrails_and_fallback` |
| 292 | Cross-module pipeline data contract continuity (`clean_df` -> `compute_spei` -> `T-Learner` -> `MAPIE`) | `src/run_pipeline.py` | `run_end_to_end_pipeline` |
| 293 | MLflow SQLite artifact/db persistence verification in tests | `tests/test_contracts_and_errors.py` | `test_conformal_yield_and_sentinel_crop_stress_net` |
| 294 | End-to-end verification under `python -m src.run_pipeline --live` | `src/run_pipeline.py` | `run_end_to_end_pipeline` |
| 295 | Reproducible Python 3.12 virtual environment via `uv venv --python 3.12` | `pyproject.toml` | `requires-python` |
| 296 | Zero-secret GDPR configuration via `HARVESTSHIELD_HMAC_KEY` env var | `docker-compose.yml` | `services.api.environment` |
| 297 | Clean container volume mounts for `./data`, `./mlruns`, and `./docs` | `docker-compose.yml` | `services.api.volumes` |
| 298 | Deterministic synthetic fallback preserving identical downstream schema | `src/ingestion/live_agri_connectors.py` | `_build_calibrated_agri_trade_rows` |
| 299 | Live FSA alert metadata propagation into DuckDB clean table (`fsa_alert_count`) | `src/ingestion/live_agri_connectors.py` | `_build_calibrated_agri_trade_rows` |
| 300 | Full regression, contract, lint, and pipeline verification gate before release | `.github/workflows/ci.yml` | `lint-and-test` |
