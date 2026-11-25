"""Streamlit dashboard for UK regional crop stress monitoring,
conformal yield forecasting, and Defra BTOM / FSA border biosecurity copilot.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from src.agents.biosecurity_copilot import HS_CODE_BTOM_REGISTRY, BiosecurityCopilot
from src.analytics.crop_weather_econometrics import UK_FARMING_REGIONS
from src.app.main import HarvestForecastRequest, forecast_harvest
from src.ingestion.agri_trade_pipeline import DEFAULT_DUCKDB_PATH, DEFAULT_QUARANTINE_PATH

st.set_page_config(
    page_title="HarvestShield UK — Crop Stress & Border Biosecurity",
    layout="wide",
)

st.title("HarvestShield UK")
st.caption(
    "UK Crop Yield & Supply Chain Disruption Forecasting, Sentinel-2 Crop Stress AI, "
    "and Defra BTOM / FSA Border Biosecurity Copilot"
)

tab_crop, tab_copilot, tab_audit = st.tabs(
    ["Crop Stress & Yield Forecast", "Defra BTOM / FSA Copilot", "Data Quarantine & Error Audit"]
)

with tab_crop:
    st.subheader("Regional Harvest & Port Clearance Conformal Forecaster")
    col1, col2, col3 = st.columns(3)
    with col1:
        region = st.selectbox("UK Farming Region", list(UK_FARMING_REGIONS))
        hs_code = st.selectbox("8-Digit CN/HS Code", list(HS_CODE_BTOM_REGISTRY.keys()))
    with col2:
        t_min = st.slider("Min Temp (°C)", -2.0, 18.0, 5.5)
        t_max = st.slider("Max Temp (°C)", 4.0, 28.0, 14.0)
        rainfall = st.slider("Monthly Rainfall (mm)", 10.0, 220.0, 95.0)
    with col3:
        cloud_cover = st.slider("Sentinel-2 Cloud Cover (%)", 0.0, 100.0, 30.0)
        ndvi = st.slider("NDVI", -1.0, 1.0, 0.58)
        ndwi = st.slider("NDWI", -1.0, 1.0, -0.10)

    if st.button("Run 90% Conformal Forecast", type="primary"):
        res = forecast_harvest(
            HarvestForecastRequest(
                farming_region=region,
                hs_code=hs_code,
                t_min_c=t_min,
                t_max_c=t_max,
                rainfall_mm=rainfall,
                ndvi=ndvi,
                ndwi=ndwi,
                cloud_cover_pct=cloud_cover,
            )
        )
        if res.fallback_used:
            st.warning(f"Weather-only fallback activated: {res.fallback_reason}")
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "t+1m Yield Deviation",
            f"{res.yield_deviation_t1m_pct:+.2f} pp",
            f"90% CI [{res.yield_t1m_lower_90:.2f}, {res.yield_t1m_upper_90:.2f}]",
        )
        m2.metric(
            "t+3m Yield Deviation",
            f"{res.yield_deviation_t3m_pct:+.2f} pp",
            f"90% CI [{res.yield_t3m_lower_90:.2f}, {res.yield_t3m_upper_90:.2f}]",
        )
        m3.metric(
            "UK Port Delay Risk",
            f"{res.port_delay_hours:.1f} hrs",
            f"90% CI [{res.port_delay_lower_90:.1f}, {res.port_delay_upper_90:.1f}]",
        )

    if DEFAULT_DUCKDB_PATH.exists():
        with duckdb.connect(str(DEFAULT_DUCKDB_PATH), read_only=True) as con:
            df_clean = con.execute("SELECT * FROM agri_trade_clean LIMIT 200").fetchdf()
        st.dataframe(df_clean, use_container_width=True)

with tab_copilot:
    st.subheader("Defra BTOM / IPAFFS / FSA Border Compliance Copilot")
    query_text = st.text_area(
        "Compliance Question",
        value="What BTOM SPS risk tier, IPAFFS CHED, and certificates apply to HS 02013000 boneless beef?",
    )
    hs_input = st.text_input("Optional 8-digit HS Code", value="02013000")
    if st.button("Verify Compliance Rules"):
        copilot = BiosecurityCopilot()
        answer = copilot.ask(query=query_text, hs_code=hs_input or None)
        if answer["blocked"]:
            st.error(answer["answer"])
        else:
            st.info(
                f"BTOM Risk Tier: **{answer['btom_risk_tier']}** | "
                f"Citations Verified: `{answer['citations_verified']}` | "
                f"Fallback Used: `{answer['used_deterministic_fallback']}`"
            )
            st.markdown(answer["answer"])

with tab_audit:
    st.subheader("Dead-Letter Quarantine & Sliced Error Analysis")
    if DEFAULT_QUARANTINE_PATH.exists():
        q_df = pd.read_parquet(DEFAULT_QUARANTINE_PATH)
        st.write(f"Quarantined records: {len(q_df)}")
        st.dataframe(q_df, use_container_width=True)
    report_path = Path("docs/ERROR_ANALYSIS_REPORT.md")
    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))
