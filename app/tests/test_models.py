"""Schema field coverage and constraint tests for PriceRow / AppSetting."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AppSetting, PriceRow


def test_pricerow_full_round_trip(session):
    row = PriceRow(
        date="2026-07-01",
        hdan=500.00,
        ppan=550.00,
        baltic_an=326.625,
        ammonia=925.00,
        urea_black_sea=567.375,
        urea_china=475.00,
        natural_gas_jkm=53.9675,
        natural_gas_henry_hub=8.8675,
        natural_gas_uk=38.45,
        natural_gas_netherlands=71.535,
        corn_us=250.4525,
        corn_china=397.195,
        diesel_usd_ton=955.16,
        urals=78.14,
        fx_rate=3186.09,
        brent=96.55,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    fetched = session.get(PriceRow, row.id)
    assert fetched.date == "2026-07-01"
    assert fetched.hdan == 500.00
    assert fetched.ppan == 550.00
    assert fetched.baltic_an == 326.625
    assert fetched.ammonia == 925.00
    assert fetched.urea_black_sea == 567.375
    assert fetched.urea_china == 475.00
    assert fetched.natural_gas_jkm == 53.9675
    assert fetched.natural_gas_henry_hub == 8.8675
    assert fetched.natural_gas_uk == 38.45
    assert fetched.natural_gas_netherlands == 71.535
    assert fetched.corn_us == 250.4525
    assert fetched.corn_china == 397.195
    assert fetched.diesel_usd_ton == 955.16
    assert fetched.urals == 78.14
    assert fetched.fx_rate == 3186.09
    assert fetched.brent == 96.55


def test_pricerow_nullable_columns(session):
    row = PriceRow(date="2013-01-01")
    session.add(row)
    session.commit()
    session.refresh(row)

    fetched = session.get(PriceRow, row.id)
    for field in (
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
    ):
        assert getattr(fetched, field) is None


def test_pricerow_no_bare_natural_gas_or_urea_attribute():
    fields = set(PriceRow.model_fields.keys())
    assert "natural_gas" not in fields
    assert "urea" not in fields


def test_pricerow_no_markup_pct_attribute():
    fields = set(PriceRow.model_fields.keys())
    assert "markup_pct" not in fields


def test_pricerow_duplicate_date_rejected(session):
    session.add(PriceRow(date="2020-05-01"))
    session.commit()

    session.add(PriceRow(date="2020-05-01"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_appsetting_round_trip_and_unique_key(session):
    setting = AppSetting(key="markup_pct", value=0.15)
    session.add(setting)
    session.commit()
    session.refresh(setting)

    fetched = session.get(AppSetting, setting.id)
    assert fetched.key == "markup_pct"
    assert fetched.value == 0.15

    session.add(AppSetting(key="markup_pct", value=0.20))
    with pytest.raises(IntegrityError):
        session.commit()
