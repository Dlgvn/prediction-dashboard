"""SQLite-backed data loader for Phase 2 research scripts.

Reads the `pricerow` table straight from `app/reflex.db` (Phase 1's sole source
of truth per 02-CONTEXT.md's "Established Patterns") using a read-only
connection — research code physically cannot mutate app data (threat T-02-01).
Superseds `backend_research/data_loader.py`'s CSV-parsing approach; this module
never re-parses the source CSVs.
"""

from pathlib import Path

import pandas as pd
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "app" / "reflex.db"

TARGETS = ["hdan", "ppan", "diesel_usd_ton", "fx_rate"]

PREDICTORS = [
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
    "brent",
    "urals",
]


def load_price_history() -> pd.DataFrame:
    """Load the PriceRow table as a wide, month-indexed DataFrame.

    Returns a DataFrame indexed by a monthly pandas PeriodIndex (ascending, no
    duplicates), with TARGETS + PREDICTORS columns cast to float64 (SQL NULL ->
    NaN).
    """
    columns = ["date"] + TARGETS + PREDICTORS
    select_list = ", ".join(columns)
    query = f"SELECT {select_list} FROM pricerow ORDER BY date"

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    df.index = pd.PeriodIndex(pd.to_datetime(df["date"]), freq="M")
    df = df.drop(columns=["date"])

    if not df.index.is_monotonic_increasing:
        raise ValueError(
            "load_price_history: index is not monotonically increasing — "
            f"dates: {list(df.index)}"
        )
    if df.index.has_duplicates:
        dupes = df.index[df.index.duplicated()].tolist()
        raise ValueError(f"load_price_history: duplicate month index values: {dupes}")

    for col in TARGETS + PREDICTORS:
        df[col] = df[col].astype("float64")

    return df


def pct_change_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Percent-change transform (x100), first row dropped (NaN from pct_change)."""
    return (df.pct_change() * 100).iloc[1:]


if __name__ == "__main__":
    frame = load_price_history()
    print(f"shape: {frame.shape}")
    print(f"index min/max: {frame.index.min()} .. {frame.index.max()}")
    print("non-null counts per column:")
    print(frame.count())
