"""Tests for app/app/seed_weekly.py -- parsing, column isolation, tolerance
join, and idempotent upsert into WeeklyPriceRow.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.seed_weekly import (  # noqa: E402
    merge_an_fx_weekly,
    parse_an_data_weekly,
    parse_fx_weekly,
    seed_weekly_database,
)

AN_HEADER = (
    "Date,Year, Month , PPAN , HDAN , Baltic AN , Ammonia , Urea , "
    "Natural_gas ,  Brent  ,\n"
)

# Shaped like the real 3-cadence FX Data.csv: Date,Daily,,Date,Weekly,,Date,Monthly
FX_HEADER = "Date,Daily,Unnamed: 2,Date.1,Weekly,Unnamed: 5,Date.2,Monthly\n"


# --- Task 1: parsers, column isolation, tolerance join ----------------------


def test_parse_an_data_weekly_columns_and_values(tmp_path):
    p = tmp_path / "an.csv"
    p.write_text(
        AN_HEADER
        + "7/10/2026,2026,7, 463.56 , 459.24 , 392.50 , 770.00 , 362.00 , "
        "3.24 , 76.00 ,\n"
        "7/17/2026,2026,7, 470.00 , 465.00 , 400.00 , 770.00 , 362.00 , "
        "3.24 , 76.00 ,\n"
    )
    df = parse_an_data_weekly(p)
    assert list(df.columns) == ["date", "hdan", "ppan", "baltic_an"]
    # No monthly collapse: row count in == row count out.
    assert len(df) == 2
    row = df.iloc[0]
    assert row["date"] == pd.Timestamp("2026-07-10")
    assert row["hdan"] == pytest.approx(459.24)
    assert row["ppan"] == pytest.approx(463.56)
    assert row["baltic_an"] == pytest.approx(392.50)


def test_parse_fx_weekly_column_isolation(tmp_path):
    p = tmp_path / "fx.csv"
    p.write_text(
        FX_HEADER
        + "1/4/2010,1111.11,,1/4/2010,2222.22,,1/4/2010,3333.33\n"
        "1/11/2010,1111.44,,1/11/2010,2222.55,,1/11/2010,3333.66\n"
    )
    df = parse_fx_weekly(p)
    assert list(df.columns) == ["date", "fx_rate"]
    values = set(df["fx_rate"].tolist())
    # Only Weekly values should appear -- Daily/Monthly values never leak in.
    assert values == {2222.22, 2222.55}
    assert 1111.11 not in values
    assert 3333.33 not in values


def test_parse_fx_weekly_thousands_separator(tmp_path):
    p = tmp_path / "fx.csv"
    p.write_text(
        FX_HEADER + '1/4/2010,1111.11,,1/4/2010,"3,592.73",,1/4/2010,3333.33\n'
    )
    df = parse_fx_weekly(p)
    assert df.iloc[0]["fx_rate"] == pytest.approx(3592.73)


def test_parse_fx_weekly_rejects_unexpected_layout(tmp_path):
    p = tmp_path / "fx.csv"
    p.write_text("Date,Weekly\n1/4/2010,2222.22\n")
    with pytest.raises(ValueError):
        parse_fx_weekly(p)


def test_merge_an_fx_weekly_tolerance(tmp_path):
    an_p = tmp_path / "an.csv"
    an_p.write_text(
        AN_HEADER
        # Friday 2026-07-10 -- FX Monday 2026-07-13 is 3 days apart (in tolerance)
        + "7/10/2026,2026,7, 463.56 , 459.24 , 392.50 , 770.00 , 362.00 , "
        "3.24 , 76.00 ,\n"
        # Friday 2026-07-17 -- nearest FX date is 2026-07-27, 10 days apart
        # (out of tolerance)
        + "7/17/2026,2026,7, 470.00 , 465.00 , 400.00 , 770.00 , 362.00 , "
        "3.24 , 76.00 ,\n"
    )
    an_df = parse_an_data_weekly(an_p)

    fx_p = tmp_path / "fx.csv"
    fx_p.write_text(
        FX_HEADER
        + "1/1/2000,1,,7/13/2026,2222.22,,1/1/2000,1\n"
        "1/1/2000,1,,7/27/2026,2222.77,,1/1/2000,1\n"
    )
    fx_df = parse_fx_weekly(fx_p)

    merged = merge_an_fx_weekly(an_df, fx_df)
    assert list(merged.columns) == ["date", "hdan", "ppan", "baltic_an", "fx_rate"]

    matched = merged[merged["date"] == pd.Timestamp("2026-07-10")].iloc[0]
    assert matched["fx_rate"] == pytest.approx(2222.22)

    unmatched = merged[merged["date"] == pd.Timestamp("2026-07-17")].iloc[0]
    assert pd.isna(unmatched["fx_rate"])


# --- Task 2: idempotent upsert ----------------------------------------------


def _write_fixture_csvs(tmp_path, hdan_value):
    an_p = tmp_path / "an.csv"
    an_p.write_text(
        AN_HEADER
        + f"7/10/2026,2026,7, 463.56 , {hdan_value} , 392.50 , 770.00 , 362.00 , "
        "3.24 , 76.00 ,\n"
    )
    fx_p = tmp_path / "fx.csv"
    fx_p.write_text(
        FX_HEADER + "1/1/2000,1,,7/13/2026,2222.22,,1/1/2000,1\n"
    )
    return an_p, fx_p


def test_seed_weekly_database_idempotent(tmp_path, session, monkeypatch):
    an_p, fx_p = _write_fixture_csvs(tmp_path, hdan_value="459.24")

    import app.seed_weekly as seed_weekly_mod

    monkeypatch.setattr(seed_weekly_mod, "_get_session", lambda: session)
    monkeypatch.setattr(session, "close", lambda: None)

    n1 = seed_weekly_database(an_p, fx_p)

    from sqlmodel import select

    from app.models import WeeklyPriceRow

    count1 = len(session.exec(select(WeeklyPriceRow)).all())
    assert n1 == 1
    assert count1 == 1

    # Change source value and re-run -- must update in place, not duplicate.
    an_p, fx_p = _write_fixture_csvs(tmp_path, hdan_value="500.00")
    n2 = seed_weekly_database(an_p, fx_p)
    count2 = len(session.exec(select(WeeklyPriceRow)).all())

    assert n2 == 1
    assert count2 == count1

    row = session.exec(
        select(WeeklyPriceRow).where(WeeklyPriceRow.date == "2026-07-10")
    ).first()
    assert row.hdan == pytest.approx(500.00)
    assert row.fx_rate == pytest.approx(2222.22)
