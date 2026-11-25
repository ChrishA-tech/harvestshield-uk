# HarvestShield UK

**UK Crop Yield & Supply Chain Disruption Forecasting, Multispectral Satellite Crop Stress AI, and Defra BTOM / FSA Border Biosecurity Compliance Copilot**

HarvestShield UK is an end-to-end agricultural intelligence and border biosecurity platform designed around UK Defra crop statistics, Met Office agro-meteorological anomalies, Sentinel-2 multispectral remote sensing, HMRC 8-digit CN/HS agri-food trade flows, and Defra Border Target Operating Model (BTOM) / FSA compliance rules.

## Architecture

1. **Data Contracts & GDPR Ingestion (`src/ingestion/agri_trade_pipeline.py`)**
   - Pandera `AgriTradeSchema` enforcing valid UK ITL1 agricultural regions, 8-digit CN/HS commodity codes, non-negative import tonnage, cloud cover `<= 80%`, and NDVI/NDWI spectral bounds `[-1.0, 1.0]`.
   - UK GDPR pseudonymisation of commercial importer EORI numbers and farm IDs via HMAC-SHA256.
   - Clean rows persisted to DuckDB (`data/processed/harvestshield.duckdb`); violating or cloud-obscured records routed to Parquet dead-letter quarantine (`data/quarantine/agri_quarantine.parquet`).

2. **Agro-Meteorological & Causal Econometrics (`src/analytics/crop_weather_econometrics.py`)**
   - Computes regional Growing Degree Days (GDD, base 5°C) and Standardized Precipitation-Evapotranspiration Index (SPEI) waterlogging anomalies across UK farming regions (East Anglia, Lincolnshire, Yorkshire, West Midlands, South West, Scotland).
   - Two-Model (T-Learner) causal estimator quantifying supply-shock import surge uplift and wholesale food price elasticity.

3. **Yield Conformal Forecasting & Sentinel-2 Deep Learning (`src/models/yield_and_satellite.py`)**
   - Region-grouped LightGBM + `MAPIE` 90% conformal regressor predicting county crop yield deviation (`t+1m`, `t+3m`) and UK port clearance delay risk with `GroupKFold` by agricultural region and MLflow SQLite tracking (`sqlite:///mlruns/mlflow.db`).
   - PyTorch `SentinelCropStressNet` processing 6-band Sentinel-2 patches (`Blue`, `Green`, `Red`, `RedEdge`, `NIR`, `SWIR`) to classify waterlogged vs. healthy arable fields.

4. **Sliced Error Analysis (`src/evaluation/error_analysis.py`)**
   - Generates [`docs/ERROR_ANALYSIS_REPORT.md`](docs/ERROR_ANALYSIS_REPORT.md) auditing MAE/RMSE, 90% conformal coverage across `Arable Eastern Lowlands`, `Pastoral Western Uplands`, `Extreme Wet Winter Anomaly`, and `High-Risk SPS Import Corridor`, plus `SentinelCropStressNet` F1/IoU under partial cloud cover.

5. **Defra BTOM / FSA Border Biosecurity Copilot (`src/agents/biosecurity_copilot.py`)**
   - Guardrailed LangGraph workflow with hybrid BM25 + TF-IDF retrieval over Defra BTOM High/Medium/Low SPS risk tiers, IPAFFS notification & EHC/Phytosanitary Certificate rules, UK Phytosanitary Manuals, and FSA Food Law allergen/recall rules.
   - Citation-verifier judge node and deterministic 8-digit HS-code BTOM risk-tier lookup fallback.

6. **API, UI & End-to-End Runner (`src/app/main.py`, `src/app/dashboard.py`, `src/run_pipeline.py`)**
   - FastAPI endpoints: `/health`, `/forecast-harvest` (with automatic weather-only fallback when Sentinel-2 cloud cover exceeds 80%), and `/compliance-copilot`.
   - Streamlit dashboard for UK regional crop stress monitoring and border compliance queries.

## Quickstart

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]" streamlit tabulate

# Run end-to-end pipeline (generates data, runs ingestion/quarantine, trains models, builds error report)
python -m src.run_pipeline

# Run tests and linter
pytest -v
ruff check src tests

# Start FastAPI service
uvicorn src.app.main:app --reload --port 8000

# Start Streamlit dashboard
streamlit run src/app/dashboard.py
```

## Docker Compose Stack

```bash
docker compose up --build
```

Services:
- `pgvector`: PostgreSQL 16 + pgvector on port `5432`
- `mlflow`: MLflow tracking server backed by SQLite on port `5000`
- `api`: FastAPI HarvestShield service on port `8000`
