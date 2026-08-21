"""Tests for app/app/seed.py — CSV parsing, monthly collapse, merge, upsert."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.seed import (  # noqa: E402
    parse_an_data,
    parse_an_weekly,
    parse_diesel_data,
    seed_database,
)

AN_HEADER = (
    "Date,Year, Month , PPAN , HDAN , Baltic AN , Ammonia , Urea , "
    "Natural_gas ,  Brent  ,\n"
)
WEEKLY_HEADER = (
    "Week Ending,Natural Gas - Japan/Korea LNG,Natural Gas - Henry Hub,"
    "Natural Gas - UK,Natural Gas - Netherlands,Corn - US,Corn - China,"
    "Baltic AN,Middle East Ammonia,Black Sea Urea,China Urea\n"
)
DIESEL_HEADER = (
    "Date,Import_Volume_Price_per_ton_USD,FX_rate,"
    "URALS_Crude _Oil_(USD/BBL),BRENT_Crude_oil_(USD/BBL)\n"
)


# --- Task 1: parsers -------------------------------------------------------


def test_parse_an_data_columns_and_values(tmp_path):
    p = tmp_path / "an.csv"
    p.write_text(
        AN_HEADER
        + "7/10/2026,2026,7, 463.56 , 459.24 , 392.50 , 770.00 , 362.00 , "
        "3.24 , 76.00 ,\n"
    )
    df = parse_an_data(p)
    assert list(df.columns) == ["date", "hdan", "ppan"]
    assert df.iloc[0]["hdan"] == pytest.approx(459.24)
    assert df.iloc[0]["ppan"] == pytest.approx(463.56)
    assert df.iloc[0]["date"] == pd.Timestamp("2026-07-10")


def test_parse_an_data_drops_retired_columns(tmp_path):
    p = tmp_path / "an.csv"
    p.write_text(
        AN_HEADER
        + "7/10/2026,2026,7, 463.56 , 459.24 , 392.50 , 770.00 , 362.00 , "
        "3.24 , 76.00 ,\n"
    )
    df = parse_an_data(p)
    forbidden = {
        "baltic_an",
        "ammonia",
        "urea",
        "urea_black_sea",
        "urea_china",
        "natural_gas",
        "brent",
        "Year",
        " Month ",
        "",
    }
    assert forbidden.isdisjoint(set(df.columns))


def test_parse_an_weekly_columns_and_values(tmp_path):
    p = tmp_path / "weekly.csv"
    p.write_text(
        WEEKLY_HEADER
        + "2026.08.14,21.22,2.73,14.9,17.9,180.7,334.49,332.5,562.5,371.5,382.5\n"
    )
    df = parse_an_weekly(p)
    row = df.iloc[0]
    assert row["natural_gas_jkm"] == pytest.approx(21.22)
    assert row["natural_gas_henry_hub"] == pytest.approx(2.73)
    assert row["natural_gas_uk"] == pytest.approx(14.9)
    assert row["natural_gas_netherlands"] == pytest.approx(17.9)
    assert row["corn_us"] == pytest.approx(180.7)
    assert row["corn_china"] == pytest.approx(334.49)
    assert row["baltic_an"] == pytest.approx(332.5)
    assert row["ammonia"] == pytest.approx(562.5)
    assert row["urea_black_sea"] == pytest.approx(371.5)
    assert row["urea_china"] == pytest.approx(382.5)
    assert row["date"] == pd.Timestamp("2026-08-14")


def test_parse_an_weekly_no_bare_urea_column(tmp_path):
    p = tmp_path / "weekly.csv"
    p.write_text(
        WEEKLY_HEADER
        + "2026.08.14,21.22,2.73,14.9,17.9,180.7,334.49,332.5,562.5,371.5,382.5\n"
    )
    df = parse_an_weekly(p)
    assert "urea" not in df.columns
    assert df.iloc[0]["urea_black_sea"] == pytest.approx(371.5)
    assert df.iloc[0]["urea_china"] == pytest.approx(382.5)


def test_parse_an_weekly_columns_exact(tmp_path):
    p = tmp_path / "weekly.csv"
    p.write_text(
        WEEKLY_HEADER
        + "2026.08.14,21.22,2.73,14.9,17.9,180.7,334.49,332.5,562.5,371.5,382.5\n"
    )
    df = parse_an_weekly(p)
    assert list(df.columns) == [
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


def test_parse_diesel_data_values(tmp_path):
    p = tmp_path / "diesel.csv"
    p.write_text(DIESEL_HEADER + '2020-02, 638.50 ," 2,756.95 ", 48.86 , 51.31 \n')
    df = parse_diesel_data(p)
    row = df.iloc[0]
    assert row["diesel_usd_ton"] == pytest.approx(638.50)
    assert row["fx_rate"] == pytest.approx(2756.95)
    assert row["urals"] == pytest.approx(48.86)
    assert row["brent"] == pytest.approx(51.31)
    assert row["date"] == pd.Timestamp("2020-02-01")


def test_parse_diesel_data_drops_blank_trailing_row(tmp_path):
    p = tmp_path / "diesel.csv"
    p.write_text(
        DIESEL_HEADER + '2020-02, 638.50 ," 2,756.95 ", 48.86 , 51.31 \n,,,,\n'
    )
    df = parse_diesel_data(p)
    assert len(df) == 1


def test_blank_numeric_cell_parses_to_nan(tmp_path):
    weekly_p = tmp_path / "weekly.csv"
    weekly_p.write_text(
        WEEKLY_HEADER + "2026.08.21,22.09,2.78,15.7,18.58,186.51,336.81,,,,\n"
    )
    wdf = parse_an_weekly(weekly_p)
    assert pd.isna(wdf.iloc[0]["baltic_an"])

    diesel_p = tmp_path / "diesel.csv"
    diesel_p.write_text(DIESEL_HEADER + "2020-02,,,,\n")
    ddf = parse_diesel_data(diesel_p)
    assert pd.isna(ddf.iloc[0]["diesel_usd_ton"])


# --- Task 2: collapse, merge, upsert ---------------------------------------


def test_monthly_collapse_averages_an_data(tmp_path):
    p = tmp_path / "an.csv"
    p.write_text(
        AN_HEADER
        + "8/1/2022,2022,8, 550.00 , 500.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
        "8/2/2022,2022,8, 550.00 , 500.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
        "8/3/2022,2022,8, 550.00 , 470.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
    )
    df = parse_an_data(p)
    from app.seed import _collapse_monthly

    collapsed = _collapse_monthly(df)
    row = collapsed[collapsed["month"] == pd.Period("2022-08", freq="M")].iloc[0]
    assert row["hdan"] == pytest.approx(490.0)


def test_monthly_collapse_averages_weekly_data(tmp_path):
    p = tmp_path / "weekly.csv"
    p.write_text(
        WEEKLY_HEADER
        + "2013.03.01,1,1,1,1,250.0,1,1,1,1,1\n"
        "2013.03.08,1,1,1,1,260.0,1,1,1,1,1\n"
        "2013.03.15,1,1,1,1,270.0,1,1,1,1,1\n"
        "2013.03.22,1,1,1,1,280.0,1,1,1,1,1\n"
    )
    df = parse_an_weekly(p)
    from app.seed import _collapse_monthly

    collapsed = _collapse_monthly(df)
    row = collapsed[collapsed["month"] == pd.Period("2013-03", freq="M")].iloc[0]
    assert row["corn_us"] == pytest.approx(265.0)


def test_monthly_collapse_ignores_nan(tmp_path):
    p = tmp_path / "an.csv"
    p.write_text(
        AN_HEADER
        + "8/1/2022,2022,8, 550.00 , 500.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
        "8/2/2022,2022,8, 550.00 , , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
        "8/3/2022,2022,8, 550.00 , 400.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
    )
    df = parse_an_data(p)
    from app.seed import _collapse_monthly

    collapsed = _collapse_monthly(df)
    row = collapsed[collapsed["month"] == pd.Period("2022-08", freq="M")].iloc[0]
    assert row["hdan"] == pytest.approx(450.0)


def test_monthly_collapse_all_nan_stays_nan(tmp_path):
    p = tmp_path / "weekly.csv"
    p.write_text(
        WEEKLY_HEADER
        + "2022.04.01,1,1,1,1,1,1,,900,1,1\n"
        "2022.04.08,1,1,1,1,1,1,,900,1,1\n"
    )
    df = parse_an_weekly(p)
    from app.seed import _collapse_monthly

    collapsed = _collapse_monthly(df)
    row = collapsed[collapsed["month"] == pd.Period("2022-04", freq="M")].iloc[0]
    assert pd.isna(row["baltic_an"])
    assert row["baltic_an"] != 0.0


def test_merge_produces_contiguous_month_index(tmp_path):
    an_p = tmp_path / "an.csv"
    an_p.write_text(
        AN_HEADER
        + "8/1/2022,2022,8, 550.00 , 500.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
    )
    weekly_p = tmp_path / "weekly.csv"
    weekly_p.write_text(
        WEEKLY_HEADER
        + "2013.01.10,1,1,1,1,1,1,1,1,1,1\n"
        "2022.08.14,1,1,1,1,1,1,1,1,1,1\n"
    )
    diesel_p = tmp_path / "diesel.csv"
    diesel_p.write_text(
        DIESEL_HEADER
        + '2020-02, 638.50 ," 2,756.95 ", 48.86 , 51.31 \n'
        + '2022-08, 638.50 ," 2,756.95 ", 48.86 , 51.31 \n'
    )

    from app.seed import _build_merged_frame

    merged = _build_merged_frame(
        parse_an_data(an_p), parse_an_weekly(weekly_p), parse_diesel_data(diesel_p)
    )
    months = merged["month"]
    expected = pd.period_range("2013-01", "2022-08", freq="M")
    assert list(months) == list(expected)

    first = merged[merged["month"] == pd.Period("2013-01", freq="M")].iloc[0]
    assert pd.isna(first["hdan"])
    assert pd.isna(first["diesel_usd_ton"])
    assert not pd.isna(first["corn_us"])

    interior = merged[merged["month"] == pd.Period("2015-06", freq="M")].iloc[0]
    for col in [
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
    ]:
        assert pd.isna(interior[col])


def test_date_written_as_month_start_iso_string(tmp_path):
    an_p = tmp_path / "an.csv"
    an_p.write_text(
        AN_HEADER
        + "8/1/2022,2022,8, 550.00 , 500.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
    )
    weekly_p = tmp_path / "weekly.csv"
    weekly_p.write_text(WEEKLY_HEADER + "2022.08.14,1,1,1,1,1,1,1,1,1,1\n")
    diesel_p = tmp_path / "diesel.csv"
    diesel_p.write_text(
        DIESEL_HEADER + '2022-08, 638.50 ," 2,756.95 ", 48.86 , 51.31 \n'
    )

    from app.seed import _build_merged_frame

    merged = _build_merged_frame(
        parse_an_data(an_p), parse_an_weekly(weekly_p), parse_diesel_data(diesel_p)
    )
    assert merged.iloc[0]["date"] == "2022-08-01"
    assert isinstance(merged.iloc[0]["date"], str)


def test_seed_database_idempotent_upsert(tmp_path, session, monkeypatch):
    an_p = tmp_path / "an.csv"
    an_p.write_text(
        AN_HEADER
        + "8/1/2022,2022,8, 550.00 , 500.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
    )
    weekly_p = tmp_path / "weekly.csv"
    weekly_p.write_text(WEEKLY_HEADER + "2022.08.14,1,1,1,1,1,1,1,1,1,1\n")
    diesel_p = tmp_path / "diesel.csv"
    diesel_p.write_text(
        DIESEL_HEADER + '2022-08, 638.50 ," 2,756.95 ", 48.86 , 51.31 \n'
    )

    import app.seed as seed_mod

    monkeypatch.setattr(seed_mod, "_get_session", lambda: session)
    monkeypatch.setattr(session, "close", lambda: None)

    n1 = seed_database(an_p, weekly_p, diesel_p)
    from sqlmodel import select

    from app.models import PriceRow

    count1 = len(session.exec(select(PriceRow)).all())

    # change source value and re-run
    an_p.write_text(
        AN_HEADER
        + "8/1/2022,2022,8, 550.00 , 555.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
    )
    n2 = seed_database(an_p, weekly_p, diesel_p)
    count2 = len(session.exec(select(PriceRow)).all())

    assert count1 == count2
    row = session.exec(
        select(PriceRow).where(PriceRow.date == "2022-08-01")
    ).first()
    assert row.hdan == pytest.approx(555.0)
    assert n1 >= 1
    assert n2 >= 1


def test_seed_database_writes_nan_as_none(tmp_path, session, monkeypatch):
    an_p = tmp_path / "an.csv"
    an_p.write_text(
        AN_HEADER
        + "8/1/2022,2022,8, 550.00 , 500.00 , 300.00 , 900.00 , 500.00 , 50.00 , 90.00 ,\n"
    )
    weekly_p = tmp_path / "weekly.csv"
    weekly_p.write_text(WEEKLY_HEADER + "2013.01.10,1,1,1,1,1,1,1,1,1,1\n")
    diesel_p = tmp_path / "diesel.csv"
    diesel_p.write_text(
        DIESEL_HEADER + '2022-08, 638.50 ," 2,756.95 ", 48.86 , 51.31 \n'
    )

    import app.seed as seed_mod

    monkeypatch.setattr(seed_mod, "_get_session", lambda: session)
    monkeypatch.setattr(session, "close", lambda: None)

    seed_database(an_p, weekly_p, diesel_p)

    from sqlmodel import select

    from app.models import PriceRow

    row = session.exec(
        select(PriceRow).where(PriceRow.date == "2013-01-01")
    ).first()
    assert row.hdan is None
    assert row.diesel_usd_ton is None
