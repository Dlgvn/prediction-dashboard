"""Tests for DashboardState.load_rows — the app's sole DB read path."""

import inspect
import io

import pandas as pd

from app import state as state_module
from app import validators
from app.models import PriceRow
from app.state import SERIES_ATTRS, SERIES_LABELS, DashboardState


def _db_row_count(session):
    return len(session.exec(PriceRow.select()).all())


def _get_db_row(session, row_date):
    return session.exec(PriceRow.select().where(PriceRow.date == row_date)).first()


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


# ---------------------------------------------------------------------------
# Edit path (DATA-02, DATA-04, DATA-05)
# ---------------------------------------------------------------------------


def test_start_edit_accepts_raw_float_from_numeric_cell(session, monkeypatch):
    """Regression: numeric cells pass their raw float value (not a string)
    as start_edit's `current` argument, since Reflex's Var-level string
    casting doesn't force JS number->string conversion for a bare Var. This
    previously crashed validate_numeric with
    AttributeError: 'float' object has no attribute 'strip'.
    """
    session.add(PriceRow(date="2026-01-01", hdan=463.165))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", 463.165)

    assert state.draft_value == "463.165"
    assert state.edit_error == ""


def test_start_edit_accepts_none_from_empty_numeric_cell(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=None))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", None)

    assert state.draft_value == ""


def test_commit_edit_updates_db(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("2.5")
    state.commit_edit()

    db_row = _get_db_row(session, "2026-01-01")
    assert db_row.hdan == 2.5
    assert state.rows[0].hdan == 2.5
    assert state.editing_key == ""
    assert state.edit_error == ""


def test_commit_edit_blank_clears_to_none(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("")
    state.commit_edit()

    db_row = _get_db_row(session, "2026-01-01")
    assert db_row.hdan is None


def test_commit_edit_rejects_invalid(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("-5")
    state.commit_edit()

    db_row = _get_db_row(session, "2026-01-01")
    assert db_row.hdan == 1.0
    assert state.editing_key == "2026-01-01:hdan"
    assert state.edit_error == validators.NUMERIC_ERROR


def test_commit_edit_rejects_non_numeric(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("abc")
    state.commit_edit()

    db_row = _get_db_row(session, "2026-01-01")
    assert db_row.hdan == 1.0
    assert state.editing_key == "2026-01-01:hdan"
    assert state.edit_error == validators.NUMERIC_ERROR


def test_commit_edit_date_column_updates_date(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:date", "2026-01-01")
    state.update_draft("2026-01-15")
    state.commit_edit()

    assert _get_db_row(session, "2026-01-01") is None
    assert _get_db_row(session, "2026-01-15") is not None

    state.start_edit("2026-01-15:date", "2026-01-15")
    state.update_draft("2026-02-20")
    state.commit_edit()

    assert _get_db_row(session, "2026-01-15") is not None
    assert state.edit_error == validators.DATE_DUPLICATE_ERROR


def test_cancel_edit_discards(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("999")
    state.cancel_edit()

    db_row = _get_db_row(session, "2026-01-01")
    assert db_row.hdan == 1.0
    assert state.editing_key == ""
    assert state.draft_value == ""
    assert state.edit_error == ""


def test_handle_key_down_enter_commits(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("3.0")
    state.handle_key_down("Enter")

    db_row = _get_db_row(session, "2026-01-01")
    assert db_row.hdan == 3.0
    assert state.editing_key == ""


def test_handle_key_down_escape_cancels(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("999")
    state.handle_key_down("Escape")

    db_row = _get_db_row(session, "2026-01-01")
    assert db_row.hdan == 1.0
    assert state.editing_key == ""


# ---------------------------------------------------------------------------
# Add-row path (DATA-01, D-06, D-06b)
# ---------------------------------------------------------------------------


def test_add_row_creates_unsaved_draft(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.add_row()

    assert len(state.draft_rows) == 1
    assert state.draft_rows[0].date == ""
    assert _db_row_count(session) == before


def test_add_row_disabled_while_draft_pending(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.add_row()
    assert state.can_add_row is False

    state.add_row()
    assert len(state.draft_rows) == 1


def test_draft_numeric_edit_does_not_touch_db(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.add_row()
    state.start_edit(":hdan", "")
    state.update_draft("7")
    state.commit_edit()

    assert _db_row_count(session) == before
    assert state.draft_rows[0].hdan == 7.0


def test_add_row_deferred_persist(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.add_row()
    state.start_edit(":hdan", "")
    state.update_draft("7")
    state.commit_edit()

    state.start_edit(":date", "")
    state.update_draft("2026-06-01")
    state.commit_edit()

    db_row = _get_db_row(session, "2026-06-01")
    assert db_row is not None
    assert db_row.hdan == 7.0
    assert state.draft_rows == []
    assert state.can_add_row is True
    assert any(r.date == "2026-06-01" for r in state.rows)


def test_draft_invalid_date_stays_draft(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.add_row()
    state.start_edit(":date", "")
    state.update_draft("nope")
    state.commit_edit()

    assert _db_row_count(session) == before
    assert len(state.draft_rows) == 1
    assert state.edit_error == validators.DATE_INVALID_ERROR


def test_draft_duplicate_month_rejected(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.add_row()
    state.start_edit(":date", "")
    state.update_draft("2026-01-20")
    state.commit_edit()

    assert _db_row_count(session) == before
    assert state.edit_error == validators.DATE_DUPLICATE_ERROR


# ---------------------------------------------------------------------------
# Delete path (DATA-03, D-07)
# ---------------------------------------------------------------------------


def test_delete_first_click_only_arms(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.request_delete("2026-01-01")

    assert state.pending_delete == "2026-01-01"
    assert _get_db_row(session, "2026-01-01") is not None


def test_delete_second_click_deletes(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.request_delete("2026-01-01")
    state.request_delete("2026-01-01")

    assert _get_db_row(session, "2026-01-01") is None
    assert state.pending_delete == ""
    assert all(r.date != "2026-01-01" for r in state.rows)


def test_delete_other_row_reassigns_arm(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.request_delete("2026-01-01")
    state.request_delete("2026-02-01")

    assert state.pending_delete == "2026-02-01"
    assert _get_db_row(session, "2026-01-01") is not None
    assert _get_db_row(session, "2026-02-01") is not None


def test_cancel_pending_delete_clears(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.request_delete("2026-01-01")
    state.cancel_pending_delete()

    assert state.pending_delete == ""

    state.request_delete("2026-01-01")
    assert _get_db_row(session, "2026-01-01") is not None


# ---------------------------------------------------------------------------
# Persistence across state instances (DATA-05)
# ---------------------------------------------------------------------------


def test_writes_survive_reload(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    # edit
    state.start_edit("2026-01-01:hdan", "1.0")
    state.update_draft("9.0")
    state.commit_edit()

    # add
    state.add_row()
    state.start_edit(":hdan", "")
    state.update_draft("5")
    state.commit_edit()
    state.start_edit(":date", "")
    state.update_draft("2026-06-01")
    state.commit_edit()

    # delete
    state.request_delete("2026-02-01")
    state.request_delete("2026-02-01")

    fresh_state = DashboardState()
    fresh_state.load_rows()

    dates = {r.date: r for r in fresh_state.rows}
    assert dates["2026-01-01"].hdan == 9.0
    assert "2026-02-01" not in dates
    assert dates["2026-06-01"].hdan == 5.0


# ---------------------------------------------------------------------------
# Historical chart (VIS-01, D-03/D-04)
# ---------------------------------------------------------------------------


def test_historical_chart_figure_uses_selected_series(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0, ppan=10.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0, ppan=20.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    figure = state.historical_chart_figure
    assert list(figure.data[0].y) == [1.0, 2.0]

    state.select_series("PPAN")
    assert state.selected_series == "ppan"

    figure = state.historical_chart_figure
    assert list(figure.data[0].y) == [10.0, 20.0]


def test_historical_chart_figure_skips_nulls(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=None))
    session.add(PriceRow(date="2026-03-01", hdan=3.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    figure = state.historical_chart_figure
    assert list(figure.data[0].x) == ["2026-01-01", "2026-03-01"]
    assert list(figure.data[0].y) == [1.0, 3.0]


def test_historical_chart_figure_empty_series_annotates(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=None))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    figure = state.historical_chart_figure
    assert len(figure.data) == 0
    annotations = figure.layout.annotations
    assert any("No data for this series yet." in a.text for a in annotations)


def test_select_series_ignores_unknown_label(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.select_series("Nonexistent")

    assert state.selected_series == "hdan"


def test_chart_figure_does_not_query_db(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    def _raise():
        raise AssertionError("historical_chart_figure must not query the DB")

    monkeypatch.setattr("reflex.session", _raise)

    assert "rx.session" not in inspect.getsource(
        DashboardState.__dict__["historical_chart_figure"].fget
    )
    # Access after monkeypatching session to raise proves no DB round trip.
    figure = state.historical_chart_figure
    assert len(figure.data) == 1


def test_series_labels_cover_all_attrs():
    assert set(SERIES_LABELS) == set(SERIES_ATTRS)
    assert len(SERIES_LABELS) == 16


# ---------------------------------------------------------------------------
# Phase 5 -- forecast state (FCST-01, EXPORT-01)
# ---------------------------------------------------------------------------


def _rows_from_synthetic_history(history):
    """Build a list of in-memory PriceRow objects from the synthetic_history
    fixture's DataFrame, one per row, date taken from the DatetimeIndex.
    Not persisted to the DB -- forecast state only reads self.rows.
    """
    rows = []
    for idx, record in zip(history.index, history.to_dict("records")):
        rows.append(PriceRow(date=idx.strftime("%Y-%m-%d"), **record))
    return rows


def test_set_horizon_clamps_out_of_range(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    state.set_horizon([0])
    assert state.horizon_months == 1

    state.set_horizon([99])
    assert state.horizon_months == 12

    state.set_horizon([7])
    assert state.horizon_months == 7

    state.set_horizon([])
    assert state.horizon_months == 7


def test_forecast_results_shape(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    results = state.forecast_results

    assert set(results.keys()) == {"hdan", "ppan", "diesel_usd_ton", "fx_rate", "diesel_mnt"}
    for key, series in results.items():
        assert len(series) == 4
        for i, entry in enumerate(series, start=1):
            assert set(entry.keys()) == {"month", "base", "bull", "bear"}
            assert entry["month"] == i


def test_forecast_results_empty_history_sets_error(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    results = state.forecast_results

    assert set(results.keys()) == {"hdan", "ppan", "diesel_usd_ton", "fx_rate", "diesel_mnt"}
    for series in results.values():
        assert series == []
    assert state.forecast_error != ""


def test_forecast_results_short_history_sets_error(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)[:5]

    results = state.forecast_results  # noqa: F841 -- must not raise

    assert state.forecast_error != ""


def test_forecast_results_uses_markup_pct(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    rows = _rows_from_synthetic_history(synthetic_history)

    state_zero = DashboardState()
    state_zero.rows = rows
    state_zero.horizon_months = 3
    state_zero.markup_pct = 0.0
    zero_results = state_zero.forecast_results

    state_markup = DashboardState()
    state_markup.rows = rows
    state_markup.horizon_months = 3
    state_markup.markup_pct = 10.0
    markup_results = state_markup.forecast_results

    zero_base = [e["base"] for e in zero_results["diesel_mnt"]]
    markup_base = [e["base"] for e in markup_results["diesel_mnt"]]
    assert zero_base != markup_base


def test_forecast_results_calls_forecast_all_once(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 3

    call_count = {"n": 0}
    real_forecast_all = state_module.forecast_all

    def _counting_forecast_all(history, horizon, markup_pct):
        call_count["n"] += 1
        return real_forecast_all(history, horizon, markup_pct)

    monkeypatch.setattr("app.state.forecast_all", _counting_forecast_all)

    _ = state.forecast_results

    assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# Excel export (EXPORT-01, D-08)
# ---------------------------------------------------------------------------


def test_export_to_excel_roundtrip(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2026-01-01", hdan=1.0, ppan=2.0),
        PriceRow(date="2026-02-01", hdan=3.0, ppan=4.0),
        PriceRow(date="2026-03-01", hdan=5.0, ppan=6.0),
    ]

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data))

    assert len(df) == 3
    assert "date" in df.columns
    for attr in SERIES_ATTRS:
        assert attr in df.columns


def test_export_excludes_id_column(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(id=1, date="2026-01-01", hdan=1.0)]

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data))

    assert "id" not in df.columns


def test_export_empty_rows_does_not_raise(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    data = state._export_bytes()  # noqa: F841 -- must not raise
    df = pd.read_excel(io.BytesIO(data))
    assert len(df) == 0


def test_export_exports_actuals_not_forecast(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=9.5, ppan=8.25)]

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data))

    assert df.iloc[0]["hdan"] == 9.5
    assert df.iloc[0]["ppan"] == 8.25


# ---------------------------------------------------------------------------
# Freshness chips (DATA-06 / D-07)
# ---------------------------------------------------------------------------


def test_freshness_chips_returns_four_entries(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    chips = state.freshness_chips

    assert len(chips) == 4
    assert [c["label"] for c in chips] == ["HDAN", "PPAN", "Diesel USD/t", "FX Rate"]


def test_freshness_chips_uses_max_date_per_series(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2026-01-01", hdan=1.0),
        PriceRow(date="2026-03-01", hdan=None, ppan=5.0),
    ]

    chips = {c["label"]: c for c in state.freshness_chips}

    assert chips["HDAN"]["date"] == "2026-01-01"
    assert chips["PPAN"]["date"] == "2026-03-01"


def test_freshness_chips_ignores_null_values(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2026-01-01", hdan=1.0),
        PriceRow(date="2026-02-01", hdan=None),
    ]

    chips = {c["label"]: c for c in state.freshness_chips}

    assert chips["HDAN"]["date"] == "2026-01-01"


def test_freshness_chips_empty_series_flags_no_data(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=None)]

    chips = {c["label"]: c for c in state.freshness_chips}

    assert chips["HDAN"]["date"] == ""
    assert chips["HDAN"]["has_data"] == "no"


def test_freshness_chips_does_not_query_db(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=1.0)]

    def _raise():
        raise AssertionError("freshness_chips must not query the DB")

    monkeypatch.setattr("reflex.session", _raise)

    assert "rx.session" not in inspect.getsource(
        DashboardState.__dict__["freshness_chips"].fget
    )
    chips = state.freshness_chips
    assert len(chips) == 4




# ---------------------------------------------------------------------------
# Forecast chart figure (VIS-02 / D-04 / D-05)
# ---------------------------------------------------------------------------


def test_forecast_chart_figure_traces(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure

    assert [t.name for t in figure.data] == [
        "Historical",
        "Bear",
        "Expected range",
        "Base forecast",
    ]


def test_forecast_chart_band_fill(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure

    assert figure.data[2].fill == "tonexty"
    assert figure.data[2].fillcolor == "rgba(59,130,246,0.15)"
    assert figure.data[1].line.width == 0
    assert figure.data[2].line.width == 0
    assert figure.data[1].showlegend is False


def test_forecast_chart_base_line_drawn_last(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure

    assert figure.data[3].line.color == "#3B82F6"
    assert len(figure.data) == 4


def test_forecast_chart_historical_window_is_twelve_months(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    rows = _rows_from_synthetic_history(synthetic_history)
    state.rows = rows
    state.horizon_months = 4

    figure = state.forecast_chart_figure

    assert len(figure.data[0].x) <= 12
    last_hist_date = pd.to_datetime(rows[-1].date)
    assert pd.to_datetime(figure.data[0].x[-1]) == last_hist_date


def test_forecast_chart_x_axis_is_continuous_dates(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    rows = _rows_from_synthetic_history(synthetic_history)
    state.rows = rows
    state.horizon_months = 4

    figure = state.forecast_chart_figure

    last_hist_x = pd.to_datetime(figure.data[0].x[-1])
    for trace in figure.data[1:]:
        assert pd.to_datetime(trace.x[0]) >= last_hist_x
        for x in trace.x:
            pd.to_datetime(x)  # must not raise -- confirms datetime-typed


def test_forecast_chart_respects_selected_forecast_series(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4
    state.forecast_series = "hdan"

    hdan_figure = state.forecast_chart_figure
    hdan_base_y = list(hdan_figure.data[3].y)
    hdan_y_title = hdan_figure.layout.yaxis.title.text

    state.forecast_series = "fx_rate"
    fx_figure = state.forecast_chart_figure

    assert list(fx_figure.data[3].y) != hdan_base_y
    assert fx_figure.layout.yaxis.title.text != hdan_y_title


def test_forecast_chart_empty_state(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    figure = state.forecast_chart_figure  # noqa: F841 -- must not raise

    annotations = figure.layout.annotations
    assert any(
        "No forecast available for this series yet." in a.text for a in annotations
    )


# ---------------------------------------------------------------------------
# Chart restyle (D-08/D-09, Phase 6 plan 06-01)
# ---------------------------------------------------------------------------


def test_forecast_chart_has_four_traces_and_forecast_start_marker(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure

    assert len(figure.data) == 4
    shapes = figure.layout.shapes
    assert shapes is not None and len(shapes) >= 1
    annotations = figure.layout.annotations
    assert any("Forecast start" in (a.text or "") for a in annotations)


def test_historical_chart_has_one_trace(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    figure = state.historical_chart_figure
    assert len(figure.data) == 1


def test_charts_do_not_use_confidence_language(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    forecast_figure = state.forecast_chart_figure
    for trace in forecast_figure.data:
        name = trace.name or ""
        assert "confidence" not in name.lower()
        assert "guaranteed" not in name.lower()
    for annotation in forecast_figure.layout.annotations:
        text = annotation.text or ""
        assert "confidence" not in text.lower()
        assert "guaranteed" not in text.lower()


def test_charts_have_transparent_background_populated_and_empty(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)

    populated_state = DashboardState()
    populated_state.rows = _rows_from_synthetic_history(synthetic_history)
    populated_state.horizon_months = 4
    populated_figure = populated_state.forecast_chart_figure
    assert populated_figure.layout.paper_bgcolor == "rgba(0,0,0,0)"

    empty_state = DashboardState()
    empty_state.rows = []
    empty_figure = empty_state.forecast_chart_figure
    assert empty_figure.layout.paper_bgcolor == "rgba(0,0,0,0)"

    empty_hist_figure = empty_state.historical_chart_figure
    assert empty_hist_figure.layout.paper_bgcolor == "rgba(0,0,0,0)"


def test_forecast_chart_traces_have_formatted_hovertemplate(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure
    for trace in figure.data:
        if trace.name == "Bear":
            # Invisible boundary trace intentionally has no tooltip.
            continue
        assert trace.hovertemplate is not None
        assert ",.2f" in trace.hovertemplate


def test_historical_chart_trace_has_formatted_hovertemplate(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    figure = state.historical_chart_figure
    assert figure.data[0].hovertemplate is not None
    assert ",.2f" in figure.data[0].hovertemplate




# ---------------------------------------------------------------------------
# Forecast table rows (FCST-06 / VIS-03)
# ---------------------------------------------------------------------------


def test_forecast_table_rows_shape(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    rows = state.forecast_table_rows

    assert len(rows) == 4
    assert [r["month"] for r in rows] == ["1", "2", "3", "4"]


def test_forecast_table_includes_all_series(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    rows = state.forecast_table_rows

    for series in ("hdan", "ppan", "diesel_usd_ton", "diesel_mnt", "fx_rate"):
        for scenario in ("base", "bull", "bear"):
            assert f"{series}_{scenario}" in rows[0]


def test_forecast_table_values_match_forecast_results(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    results = state.forecast_results
    rows = state.forecast_table_rows

    expected = f"{results['hdan'][1]['base']:,.2f}"
    assert rows[1]["hdan_base"] == expected


def test_forecast_table_rows_empty_when_insufficient_history(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)[:5]

    rows = state.forecast_table_rows

    assert rows == []
    assert state.forecast_error != ""


def test_forecast_table_row_length_follows_horizon(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)

    state.horizon_months = 4
    assert len(state.forecast_table_rows) == 4

    state.horizon_months = 9
    assert len(state.forecast_table_rows) == 9
