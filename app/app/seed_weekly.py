"""Seed the WeeklyPriceRow table from AN Data.csv and FX Data.csv.

This script seeds `WeeklyPriceRow` from `AN Data.csv`'s native weekly rows
(HDAN, PPAN, Baltic AN) and `FX Data.csv`'s Weekly column specifically --
never resampled/collapsed from monthly data. It is run standalone (never
wired into app startup, per ARCHITECTURE.md Pattern 3) and requires Plan
01's migration to already be applied (`reflex db migrate`), or it raises
`sqlalchemy.exc.OperationalError: no such table: weeklypricerow`.

AN-family rows (Friday-based week-ending dates) and FX Weekly rows
(Monday-based week-ending dates) are joined via a tolerance-bounded
`pd.merge_asof` (±3 days) rather than a naive/unbounded nearest match, so a
genuine non-match stays NaN/None instead of being misaligned to the wrong
week.

Run as: `python -m app.seed_weekly "<AN Data.csv path>" "<FX Data.csv path>"`
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from app.models import WeeklyPriceRow
from app.seed import _clean_numeric

# Live-verified column layout of FX Data.csv (pandas 3.0.5) -- if this
# drifts, positional slicing below is unsafe and must be re-verified.
FX_EXPECTED_COLUMNS = [
    "Date",
    "Daily",
    "Unnamed: 2",
    "Date.1",
    "Weekly",
    "Unnamed: 5",
    "Date.2",
    "Monthly",
]

WEEKLY_SERIES_COLUMNS = ["hdan", "ppan", "baltic_an", "fx_rate"]

# Friday (AN) -> Monday (FX) week-ending gap, verified this session.
MERGE_TOLERANCE = pd.Timedelta(days=3)


def parse_an_data_weekly(path) -> pd.DataFrame:
    """Parse AN Data.csv at native weekly grain -- NO monthly collapse."""
    raw = pd.read_csv(path, dtype=str)
    raw.columns = [c.strip() for c in raw.columns]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw["Date"], format="%m/%d/%Y")
    out["hdan"] = _clean_numeric(raw["HDAN"])
    out["ppan"] = _clean_numeric(raw["PPAN"])
    out["baltic_an"] = _clean_numeric(raw["Baltic AN"])
    return out.sort_values("date").reset_index(drop=True)


def parse_fx_weekly(path) -> pd.DataFrame:
    """Isolate FX Data.csv's Weekly Date/Value pair by position, not name."""
    df = pd.read_csv(path)
    actual = df.columns.tolist()
    if actual != FX_EXPECTED_COLUMNS:
        raise ValueError(
            f"FX Data.csv column layout changed -- expected {FX_EXPECTED_COLUMNS}, "
            f"got {actual}. Positional slicing is unsafe; update FX_EXPECTED_COLUMNS "
            "and the slice after confirming the new layout."
        )
    weekly = df.iloc[:, 3:5].copy()
    weekly.columns = ["date", "fx_rate"]
    weekly = weekly.dropna()
    weekly["date"] = pd.to_datetime(weekly["date"])
    weekly["fx_rate"] = _clean_numeric(weekly["fx_rate"])
    return weekly.sort_values("date").reset_index(drop=True)


def merge_an_fx_weekly(an_df: pd.DataFrame, fx_df: pd.DataFrame) -> pd.DataFrame:
    """Tolerance-bounded merge_asof: AN (Friday-based) vs FX (Monday-based), ~3-day gap.

    A genuine no-match week keeps fx_rate as NaN -- never forward-filled or
    interpolated.
    """
    an_sorted = an_df.sort_values("date").set_index("date")
    fx_sorted = fx_df.sort_values("date").set_index("date")
    merged = pd.merge_asof(
        an_sorted,
        fx_sorted,
        left_index=True,
        right_index=True,
        direction="nearest",
        tolerance=MERGE_TOLERANCE,
    )
    return merged.reset_index()


def _to_none(value) -> Optional[float]:
    if pd.isna(value):
        return None
    return float(value)


def _get_session():
    import reflex as rx

    return rx.session()


def seed_weekly_database(an_data_path, fx_data_path) -> int:
    """Parse, join and idempotently upsert weekly rows into WeeklyPriceRow.

    Requires Plan 01's migration (`reflex db migrate`) to already be applied
    -- raises sqlalchemy.exc.OperationalError otherwise.
    """
    from sqlmodel import select

    an_df = parse_an_data_weekly(an_data_path)
    fx_df = parse_fx_weekly(fx_data_path)
    merged = merge_an_fx_weekly(an_df, fx_df)

    written = 0
    session = _get_session()
    try:
        for _, row in merged.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            existing = session.exec(
                select(WeeklyPriceRow).where(WeeklyPriceRow.date == date_str)
            ).first()
            if existing is None:
                existing = WeeklyPriceRow(date=date_str)
                session.add(existing)
            for col in WEEKLY_SERIES_COLUMNS:
                setattr(existing, col, _to_none(row[col]))
            written += 1
        session.commit()
    finally:
        session.close()
    return written


if __name__ == "__main__":
    an_path, fx_path = sys.argv[1], sys.argv[2]
    count = seed_weekly_database(Path(an_path), Path(fx_path))
    print(f"Seeded/updated {count} weekly rows.")
