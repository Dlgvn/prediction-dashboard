"""Tests for DashboardState.load_rows — the app's sole DB read path."""

from app.models import PriceRow
from app.state import DashboardState


def test_load_rows_orders_ascending_by_date(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2020-02-01", hdan=2.0))
    session.add(PriceRow(date="2022-08-01", hdan=3.0))
    session.commit()

    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    assert len(state.rows) == 3
    assert state.rows[0].date == "2020-02-01"
    assert state.rows[1].date == "2022-08-01"
    assert state.rows[2].date == "2026-01-01"


def test_load_rows_empty_table_does_not_raise(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    assert state.rows == []


def test_load_rows_nulls_stay_none(session, monkeypatch):
    session.add(PriceRow(date="2013-01-01"))
    session.commit()

    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    assert len(state.rows) == 1
    assert state.rows[0].hdan is None
    assert state.rows[0].natural_gas_jkm is None


def test_load_rows_reassigns_not_appends(session, monkeypatch):
    session.add(PriceRow(date="2021-01-01", hdan=1.0))
    session.add(PriceRow(date="2021-02-01", hdan=2.0))
    session.commit()

    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.load_rows()

    assert len(state.rows) == 2
