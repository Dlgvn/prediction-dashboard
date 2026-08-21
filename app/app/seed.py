"""Seed the PriceRow table from the three historical CSV sources.

Column mapping follows the D-05b/D-05c-corrected 16-series contract:
  - `AN Data.csv`         -> hdan, ppan ONLY (D-05b retires its other columns)
  - `AN price weekly.csv` -> baltic_an, ammonia, urea_black_sea, urea_china,
                              natural_gas_jkm, natural_gas_henry_hub,
                              natural_gas_uk, natural_gas_netherlands,
                              corn_us, corn_china (D-05c keeps both urea series)
  - `Diesel Data.csv`     -> diesel_usd_ton, urals, fx_rate, brent

D-06b: multi-entry months in BOTH AN Data.csv and AN price weekly.csv are
collapsed by AVERAGING (skipping NaN), not by taking the last entry. This
overrides the "take the last entry per month" collapse sketched in
`docs/plans/2026-08-21-reflex-dashboard-implementation.md` line 259.

D-02: seeding upserts by `date` rather than duplicating or failing on re-run.

Run as: `python -m app.seed "<an data path>" "<an weekly path>" "<diesel path>"`
(never wired into app startup — standalone script per ARCHITECTURE.md Pattern 3).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from app.models import PriceRow

# All 16 series columns written to PriceRow, in schema order.
SERIES_COLUMNS = [
    "hdan",
    "ppan",
    "baltic_an",
    "ammonia",
    "urea_black_sea",
    "urea_china",
    "natural_gas_jkm",
    "natural_gas_henry_hub",
    "natural_gas_uk",
    "natural_gas_netherlands",
    "corn_us",
    "corn_china",
    "diesel_usd_ton",
    "urals",
    "fx_rate",
    "brent",
]


def _clean_numeric(series: pd.Series) -> pd.Series:
    """Coerce a messy string Series to float.

    Strips whitespace, removes ',' thousands separators, maps '' and the
    literal 'nan' to NaN, then casts to float. Builds a fresh Series rather
    than mutating slices in place (pandas 3.0 copy-on-write, see STACK.md).
    """
    cleaned = series.astype(str).str.strip().str.replace(",", "", regex=False)
    cleaned = cleaned.replace({"": None, "nan": None, "None": None})
    return cleaned.astype(float)


def parse_an_data(path) -> pd.DataFrame:
    """Parse AN Data.csv. Per D-05b: ONLY date, hdan, ppan are extracted."""
    raw = pd.read_csv(path, dtype=str)
    raw.columns = [c.strip() for c in raw.columns]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw["Date"], format="%m/%d/%Y")
    out["hdan"] = _clean_numeric(raw["HDAN"])
    out["ppan"] = _clean_numeric(raw["PPAN"])
    return out


def parse_an_weekly(path) -> pd.DataFrame:
    """Parse AN price weekly.csv. Per D-05c both urea series are kept."""
    raw = pd.read_csv(path, dtype=str)
    raw.columns = [c.strip() for c in raw.columns]

    mapping = {
        "Natural Gas - Japan/Korea LNG": "natural_gas_jkm",
        "Natural Gas - Henry Hub": "natural_gas_henry_hub",
        "Natural Gas - UK": "natural_gas_uk",
        "Natural Gas - Netherlands": "natural_gas_netherlands",
        "Corn - US": "corn_us",
        "Corn - China": "corn_china",
        "Baltic AN": "baltic_an",
        "Middle East Ammonia": "ammonia",
        "Black Sea Urea": "urea_black_sea",
        "China Urea": "urea_china",
    }

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw["Week Ending"], format="%Y.%m.%d")
    for src_col, dst_col in mapping.items():
        out[dst_col] = _clean_numeric(raw[src_col])

    # Reorder to the documented 11-column contract order.
    return out[
        [
            "date",
            "baltic_an",
            "ammonia",
            "urea_black_sea",
            "urea_china",
            "natural_gas_jkm",
            "natural_gas_henry_hub",
            "natural_gas_uk",
            "natural_gas_netherlands",
            "corn_us",
            "corn_china",
        ]
    ]


def parse_diesel_data(path) -> pd.DataFrame:
    """Parse Diesel Data.csv. Brent now sourced here per D-05b (longer history)."""
    raw = pd.read_csv(path, dtype=str)
    raw.columns = [c.strip() for c in raw.columns]

    raw = raw[raw["Date"].notna() & (raw["Date"].str.strip() != "")]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw["Date"], format="%Y-%m")
    out["diesel_usd_ton"] = _clean_numeric(raw["Import_Volume_Price_per_ton_USD"])
    out["urals"] = _clean_numeric(raw["URALS_Crude _Oil_(USD/BBL)"])
    out["fx_rate"] = _clean_numeric(raw["FX_rate"])
    out["brent"] = _clean_numeric(raw["BRENT_Crude_oil_(USD/BBL)"])
    return out.reset_index(drop=True)


def _collapse_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse multi-entry months to one row per month via mean (D-06b).

    NaN entries are skipped by the mean; a month where every entry is NaN
    for a column stays NaN (never 0.0).
    """
    working = df.copy()
    working["month"] = working["date"].dt.to_period("M")
    numeric_cols = [c for c in working.columns if c not in ("date", "month")]
    collapsed = working.groupby("month", as_index=False)[numeric_cols].mean()
    return collapsed


def _build_merged_frame(
    an_df: pd.DataFrame, weekly_df: pd.DataFrame, diesel_df: pd.DataFrame
) -> pd.DataFrame:
    """Collapse each source monthly, outer-merge on month, reindex contiguous."""
    an_monthly = _collapse_monthly(an_df)
    weekly_monthly = _collapse_monthly(weekly_df)
    diesel_monthly = _collapse_monthly(diesel_df)

    merged = an_monthly.merge(weekly_monthly, on="month", how="outer").merge(
        diesel_monthly, on="month", how="outer"
    )

    min_month = merged["month"].min()
    max_month = merged["month"].max()
    full_index = pd.period_range(min_month, max_month, freq="M")
    merged = (
        merged.set_index("month")
        .reindex(full_index)
        .rename_axis("month")
        .reset_index()
    )

    merged["date"] = merged["month"].dt.start_time.dt.strftime("%Y-%m-01")

    # Ensure every expected series column exists even if a source was empty.
    for col in SERIES_COLUMNS:
        if col not in merged.columns:
            merged[col] = pd.NA

    return merged


def _to_none(value) -> Optional[float]:
    """Convert pandas NaN/NA to Python None; pass through real floats."""
    if pd.isna(value):
        return None
    return float(value)


def _get_session():
    import reflex as rx

    return rx.session()


def seed_database(an_data_path, an_weekly_path, diesel_data_path) -> int:
    """Load, collapse, merge and upsert the three CSV sources into PriceRow.

    Returns the number of rows written or updated.
    """
    an_df = parse_an_data(an_data_path)
    weekly_df = parse_an_weekly(an_weekly_path)
    diesel_df = parse_diesel_data(diesel_data_path)

    merged = _build_merged_frame(an_df, weekly_df, diesel_df)

    written = 0
    session = _get_session()
    try:
        from sqlmodel import select

        for _, row in merged.iterrows():
            date_str = row["date"]
            existing = session.exec(
                select(PriceRow).where(PriceRow.date == date_str)
            ).first()
            if existing is None:
                existing = PriceRow(date=date_str)
                session.add(existing)
            for col in SERIES_COLUMNS:
                setattr(existing, col, _to_none(row[col]))
            written += 1
        session.commit()
    finally:
        session.close()

    return written


if __name__ == "__main__":
    an_path, weekly_path, diesel_path = sys.argv[1], sys.argv[2], sys.argv[3]
    count = seed_database(Path(an_path), Path(weekly_path), Path(diesel_path))
    print(f"Seeded/updated {count} rows.")
