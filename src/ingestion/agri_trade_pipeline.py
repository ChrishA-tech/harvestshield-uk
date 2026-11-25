"""UK agricultural & border trade ingestion pipeline with Pandera contracts,
UK GDPR HMAC-SHA256 pseudonymisation, DuckDB persistence, and Parquet quarantine.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import pandera.pandas as pa

UK_ITL1_REGIONS: tuple[str, ...] = (
    "North East",
    "North West",
    "Yorkshire and The Humber",
    "East Midlands",
    "West Midlands",
    "East of England",
    "London",
    "South East",
    "South West",
    "Wales",
    "Scotland",
    "Northern Ireland",
)

FARMING_REGION_TO_ITL1: dict[str, str] = {
    "East Anglia": "East of England",
    "Lincolnshire": "East Midlands",
    "Yorkshire": "Yorkshire and The Humber",
    "West Midlands": "West Midlands",
    "South West": "South West",
    "Scotland": "Scotland",
}

DEFAULT_HMAC_KEY = "harvestshield-uk-gdpr-default-key"
DEFAULT_DUCKDB_PATH = Path("data/processed/harvestshield.duckdb")
DEFAULT_QUARANTINE_PATH = Path("data/quarantine/agri_quarantine.parquet")


def pseudonymise_identifier(value: object, secret_key: str | None = None) -> str:
    """Compute a deterministic UK GDPR-compliant HMAC-SHA256 pseudonym."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raw = ""
    else:
        raw = str(value).strip()
    key = (secret_key or os.getenv("HARVESTSHIELD_HMAC_KEY") or DEFAULT_HMAC_KEY).encode("utf-8")
    digest = hmac.new(key, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"hmac_{digest}"


def build_agri_trade_schema() -> pa.DataFrameSchema:
    """Return the Pandera quality contract for UK agri-trade and Sentinel-2 records."""
    return pa.DataFrameSchema(
        columns={
            "record_id": pa.Column(str, nullable=False, coerce=True),
            "itl1_region": pa.Column(
                str,
                checks=pa.Check.isin(UK_ITL1_REGIONS),
                nullable=False,
            ),
            "hs_code": pa.Column(
                str,
                checks=pa.Check.str_matches(r"^\d{8}$"),
                nullable=False,
            ),
            "import_tonnes": pa.Column(
                float,
                checks=pa.Check.ge(0.0),
                nullable=False,
                coerce=True,
            ),
            "cloud_cover_pct": pa.Column(
                float,
                checks=[pa.Check.ge(0.0), pa.Check.le(80.0)],
                nullable=False,
                coerce=True,
            ),
            "ndvi": pa.Column(
                float,
                checks=[pa.Check.ge(-1.0), pa.Check.le(1.0)],
                nullable=False,
                coerce=True,
            ),
            "ndwi": pa.Column(
                float,
                checks=[pa.Check.ge(-1.0), pa.Check.le(1.0)],
                nullable=False,
                coerce=True,
            ),
            "importer_eori": pa.Column(
                str,
                checks=pa.Check.str_length(min_value=5),
                nullable=False,
            ),
            "farm_id": pa.Column(
                str,
                checks=pa.Check.str_length(min_value=3),
                nullable=False,
            ),
        },
        strict=False,
        coerce=True,
    )


AgriTradeSchema = build_agri_trade_schema()


@dataclass
class IngestionResult:
    """Summary of an ingestion, GDPR pseudonymisation, and quarantine run."""

    total_rows: int
    clean_rows: int
    quarantined_rows: int
    clean_df: pd.DataFrame
    quarantine_df: pd.DataFrame
    duckdb_path: Path
    quarantine_path: Path


def _collect_invalid_indices(
    df: pd.DataFrame, schema: pa.DataFrameSchema
) -> tuple[pd.DataFrame, dict[int, list[str]]]:
    """Validate row-by-row when batch coercion hits non-numeric values or schema errors."""
    reasons_by_idx: dict[int, list[str]] = {}
    working = df.copy()

    # Pre-check numeric coercion safely so a single non-numeric string doesn't abort batch validation
    numeric_cols = ("import_tonnes", "cloud_cover_pct", "ndvi", "ndwi")
    for col in numeric_cols:
        if col in working.columns:
            coerced = pd.to_numeric(working[col], errors="coerce")
            bad_mask = coerced.isna() & working[col].notna()
            for idx in working.index[bad_mask]:
                reasons_by_idx.setdefault(int(idx), []).append(f"{col}:non_numeric")
            working[col] = coerced

    # Ensure string columns don't coerce NaN into literal "nan"
    for col in ("record_id", "itl1_region", "hs_code", "importer_eori", "farm_id"):
        if col in working.columns:
            missing_mask = working[col].isna()
            for idx in working.index[missing_mask]:
                reasons_by_idx.setdefault(int(idx), []).append(f"{col}:missing")

    # Run Pandera lazy validation on the subset not already flagged for non-numeric/missing
    candidate_mask = ~working.index.isin(list(reasons_by_idx.keys()))
    candidate_df = working.loc[candidate_mask].copy()

    if not candidate_df.empty:
        try:
            validated_sub = schema.validate(candidate_df, lazy=True)
            working.loc[validated_sub.index, validated_sub.columns] = validated_sub
        except pa.errors.SchemaErrors as exc:
            fc = exc.failure_cases
            if "index" in fc.columns:
                for _, row in fc.iterrows():
                    idx_val = row["index"]
                    if idx_val is not None and not pd.isna(idx_val):
                        col_name = str(row.get("column", "schema"))
                        check_name = str(row.get("check", "invalid"))
                        reasons_by_idx.setdefault(int(idx_val), []).append(
                            f"{col_name}:{check_name}"
                        )
            else:
                for idx in candidate_df.index:
                    reasons_by_idx.setdefault(int(idx), []).append("schema_error")

    return working, reasons_by_idx


def pseudonymise_gdpr_columns(
    df: pd.DataFrame,
    secret_key: str | None = None,
    drop_raw: bool = True,
) -> pd.DataFrame:
    """Apply UK GDPR HMAC-SHA256 pseudonymisation to EORI and farm identifiers."""
    out = df.copy()
    if "importer_eori" in out.columns:
        out["importer_eori_hash"] = out["importer_eori"].apply(
            lambda v: pseudonymise_identifier(v, secret_key=secret_key)
        )
    if "farm_id" in out.columns:
        out["farm_id_hash"] = out["farm_id"].apply(
            lambda v: pseudonymise_identifier(v, secret_key=secret_key)
        )
    if drop_raw:
        out = out.drop(columns=[c for c in ("importer_eori", "farm_id") if c in out.columns])
    return out


def persist_to_duckdb(
    clean_df: pd.DataFrame,
    duckdb_path: Path = DEFAULT_DUCKDB_PATH,
    table_name: str = "agri_trade_clean",
) -> Path:
    """Persist validated, pseudonymised agricultural trade records into DuckDB."""
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(duckdb_path)) as con:
        con.register("clean_df_view", clean_df)
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM clean_df_view")
    return duckdb_path


def persist_quarantine_parquet(
    quarantine_df: pd.DataFrame,
    quarantine_path: Path = DEFAULT_QUARANTINE_PATH,
) -> Path:
    """Write quarantined records to a Parquet dead-letter table."""
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    to_write = quarantine_df.copy()
    # Stringify non-standard object columns so Parquet serialization never fails on mixed corrupt types
    for col in to_write.columns:
        if to_write[col].dtype == object:
            to_write[col] = to_write[col].astype(str)
    to_write.to_parquet(quarantine_path, index=False)
    return quarantine_path


def run_agri_trade_ingestion(
    raw_df: pd.DataFrame,
    duckdb_path: Path = DEFAULT_DUCKDB_PATH,
    quarantine_path: Path = DEFAULT_QUARANTINE_PATH,
    secret_key: str | None = None,
    schema: pa.DataFrameSchema | None = None,
) -> IngestionResult:
    """Validate raw UK agri-trade & Sentinel-2 records, quarantine violations,
    pseudonymise EORI/farm IDs under UK GDPR, and persist clean data to DuckDB.
    """
    active_schema = schema or AgriTradeSchema
    indexed_raw = raw_df.reset_index(drop=True)
    working, reasons_by_idx = _collect_invalid_indices(indexed_raw, active_schema)

    bad_indices = sorted(reasons_by_idx.keys())
    good_mask = ~indexed_raw.index.isin(bad_indices)

    clean_raw = working.loc[good_mask].copy().reset_index(drop=True)
    clean_df = pseudonymise_gdpr_columns(clean_raw, secret_key=secret_key, drop_raw=True)

    quarantine_raw = indexed_raw.loc[bad_indices].copy().reset_index(drop=True)
    if not quarantine_raw.empty:
        quarantine_raw = pseudonymise_gdpr_columns(
            quarantine_raw, secret_key=secret_key, drop_raw=True
        )
        quarantine_raw["quarantine_reason"] = [
            "; ".join(sorted(set(reasons_by_idx[i]))) for i in bad_indices
        ]
    else:
        quarantine_raw = pseudonymise_gdpr_columns(
            quarantine_raw, secret_key=secret_key, drop_raw=True
        )
        quarantine_raw["quarantine_reason"] = pd.Series(dtype="object")

    persist_to_duckdb(clean_df, duckdb_path=duckdb_path)
    persist_quarantine_parquet(quarantine_raw, quarantine_path=quarantine_path)

    return IngestionResult(
        total_rows=len(indexed_raw),
        clean_rows=len(clean_df),
        quarantined_rows=len(quarantine_raw),
        clean_df=clean_df,
        quarantine_df=quarantine_raw,
        duckdb_path=duckdb_path,
        quarantine_path=quarantine_path,
    )
