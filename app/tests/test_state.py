"""Tests for DashboardState.load_rows — the app's sole DB read path."""

import asyncio
import inspect
import io

import pandas as pd

from app import state as state_module
from app import theme
from app import validators
from app.forecasting import DIESEL_LITERS_PER_TON, MAX_HORIZON_WEEKLY, MODEL_INFO, WEEKLY_MODEL_INFO
from app.models import PriceRow, WeeklyPriceRow
from app.state import (
    FORECAST_SERIES_LABELS,
    FORECAST_TABLE_COLUMNS,
    SERIES_ATTRS,
    SERIES_LABELS,
    TABLE_WINDOW_ROWS,
    WEEKLY_CAPABLE_SERIES,
    WEEKLY_FORECAST_SERIES_LABELS,
    WEEKLY_FORECAST_TABLE_COLUMNS,
    WEEKLY_SERIES_ATTRS,
    DashboardState,
)


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


def test_start_edit_does_not_clobber_pending_error_on_different_cell(session, monkeypatch):
    """Regression (15-CONTEXT.md D-02): a near-simultaneous click on a
    different cell must not wipe an unrendered validation error still
    pending on the cell that produced it.
    """
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-02-01:date", "2026-02-01")
    state.update_draft("2026-01-01")
    state.commit_edit()

    assert state.edit_error == validators.DATE_DUPLICATE_ERROR
    assert state.editing_key == "2026-02-01:date"

    state.start_edit("2026-01-01:hdan", 1.0)

    assert state.edit_error == validators.DATE_DUPLICATE_ERROR
    assert state.editing_key == "2026-02-01:date"


def test_start_edit_on_same_errored_cell_clears_error_and_reopens(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-02-01:date", "2026-02-01")
    state.update_draft("2026-01-01")
    state.commit_edit()

    assert state.edit_error == validators.DATE_DUPLICATE_ERROR
    assert state.editing_key == "2026-02-01:date"

    state.start_edit("2026-02-01:date", "2026-02-01")

    assert state.edit_error == ""
    assert state.editing_key == "2026-02-01:date"
    assert state.draft_value == "2026-02-01"


def test_start_edit_with_no_pending_error_behaves_as_before(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    state.start_edit("2026-01-01:hdan", 1.0)
    assert state.editing_key == "2026-01-01:hdan"
    assert state.edit_error == ""

    state.start_edit("2026-02-01:hdan", 2.0)
    assert state.editing_key == "2026-02-01:hdan"
    assert state.draft_value == "2.0"
    assert state.edit_error == ""


def test_toggle_show_all_history_clears_pending_error_from_different_cell(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.start_edit("2026-02-01:date", "2026-02-01")
    state.update_draft("2026-01-01")
    state.commit_edit()

    assert state.edit_error == validators.DATE_DUPLICATE_ERROR
    assert state.editing_key == "2026-02-01:date"

    state.toggle_show_all_history(True)

    assert state.editing_key == ""
    assert state.draft_value == ""
    assert state.edit_error == ""


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

    series_keys = {"hdan", "ppan", "diesel_usd_ton", "fx_rate", "diesel_mnt"}
    assert set(results.keys()) == series_keys | {"warning"}
    for key in series_keys:
        series = results[key]
        assert len(series) == 4
        for i, entry in enumerate(series, start=1):
            assert set(entry.keys()) == {"month", "base", "bull", "bear"}
            assert entry["month"] == i


def test_forecast_results_surfaces_stale_ppan_warning(
    session, monkeypatch, synthetic_history
):
    """A stale-feature-anchor gap in a PPAN system-member column threads
    through forecast_all -> state.forecast_results -> state.forecast_warning
    without blocking the forecast itself."""
    monkeypatch.setattr("reflex.session", lambda: session)
    history = synthetic_history.copy()
    history.loc[history.index[-1], "urals"] = float("nan")

    state = DashboardState()
    state.rows = _rows_from_synthetic_history(history)
    state.horizon_months = 3

    results = state.forecast_results

    assert len(results["ppan"]) == 3
    assert state.forecast_warning != ""
    assert "urals" in state.forecast_warning
    assert state.forecast_error == ""


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
# Phase 22 -- granularity toggle + independent weekly horizon (WKUI-03/04/06)
# ---------------------------------------------------------------------------


def test_granularity_defaults_to_monthly(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    assert state.granularity == "monthly"


def test_set_granularity_switches_between_monthly_and_weekly(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    state.set_granularity("weekly")
    assert state.granularity == "weekly"

    state.set_granularity("monthly")
    assert state.granularity == "monthly"


def test_set_granularity_ignores_unknown_value(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    state.set_granularity("bogus")

    assert state.granularity == "monthly"


def test_set_granularity_resets_forecast_series_when_not_weekly_capable(
    session, monkeypatch
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.forecast_series = "diesel_mnt"

    state.set_granularity("weekly")

    assert state.forecast_series == "hdan"


def test_set_granularity_keeps_forecast_series_when_already_weekly_capable(
    session, monkeypatch
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.forecast_series = "ppan"

    state.set_granularity("weekly")

    assert state.forecast_series == "ppan"


def test_active_horizon_branches_on_granularity(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.horizon_months = 7
    state.horizon_weeks = 3

    assert state.granularity == "monthly"
    assert state.active_horizon == 7

    state.set_granularity("weekly")
    assert state.active_horizon == 3


def test_horizon_max_branches_on_granularity(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    assert state.horizon_max == 12

    state.set_granularity("weekly")
    assert state.horizon_max == 5


def test_horizon_caption_pluralizes_correctly(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    state.horizon_months = 1
    assert state.horizon_caption == "1 month"
    state.horizon_months = 3
    assert state.horizon_caption == "3 months"

    state.set_granularity("weekly")
    state.horizon_weeks = 1
    assert state.horizon_caption == "1 week"
    state.horizon_weeks = 4
    assert state.horizon_caption == "4 weeks"


def test_set_horizon_writes_horizon_weeks_when_granularity_weekly(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.set_granularity("weekly")
    state.horizon_months = 6  # sentinel -- must stay untouched below

    state.set_horizon([8])

    assert state.horizon_weeks == 5  # clamped to MAX_HORIZON_WEEKLY
    assert state.horizon_months == 6


def test_set_horizon_writes_horizon_months_when_granularity_monthly(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.horizon_weeks = 2  # sentinel -- must stay untouched below

    state.set_horizon([8])

    assert state.horizon_months == 8
    assert state.horizon_weeks == 2


def test_set_horizon_clamps_horizon_weeks_lower_bound(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.set_granularity("weekly")

    state.set_horizon([0])

    assert state.horizon_weeks == 1


# ---------------------------------------------------------------------------
# Phase 22 -- weekly data loading + weekly_forecast_results (WKUI-03/07)
# ---------------------------------------------------------------------------


def _weekly_rows_from_synthetic_history(history):
    """Build a list of in-memory WeeklyPriceRow objects from the
    synthetic_weekly_history fixture's DataFrame, one per row, date taken
    from the DatetimeIndex. Not persisted to the DB.
    """
    rows = []
    for idx, record in zip(history.index, history.to_dict("records")):
        rows.append(WeeklyPriceRow(date=idx.strftime("%Y-%m-%d"), **record))
    return rows


def test_load_weekly_rows_orders_ascending_by_date(session, monkeypatch):
    session.add(WeeklyPriceRow(date="2026-01-01", hdan=1.0))
    session.add(WeeklyPriceRow(date="2020-02-01", hdan=2.0))
    session.add(WeeklyPriceRow(date="2022-08-01", hdan=3.0))
    session.commit()

    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_weekly_rows()

    assert len(state.weekly_rows) == 3
    assert state.weekly_rows[0].date == "2020-02-01"
    assert state.weekly_rows[1].date == "2022-08-01"
    assert state.weekly_rows[2].date == "2026-01-01"


def test_load_weekly_rows_reassigns_not_appends(session, monkeypatch):
    session.add(WeeklyPriceRow(date="2021-01-01", hdan=1.0))
    session.add(WeeklyPriceRow(date="2021-01-08", hdan=2.0))
    session.commit()

    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_weekly_rows()
    state.load_weekly_rows()

    assert len(state.weekly_rows) == 2


def test_weekly_history_df_empty_when_no_rows(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    df = state._weekly_history_df()

    assert df.empty


def test_weekly_history_df_has_expected_columns(session, monkeypatch, synthetic_weekly_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.weekly_rows = _weekly_rows_from_synthetic_history(synthetic_weekly_history)

    df = state._weekly_history_df()

    assert set(df.columns) == set(WEEKLY_SERIES_ATTRS)
    assert len(df) == len(synthetic_weekly_history)


def test_weekly_forecast_results_empty_rows_sets_error(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.weekly_rows = []

    results = state.weekly_forecast_results

    assert set(results.keys()) == set(WEEKLY_FORECAST_SERIES_LABELS)
    for series in results.values():
        assert series == []
    assert state.weekly_forecast_error != ""
    assert state.forecast_error == ""


def test_weekly_forecast_results_populated_calls_forecast_all_weekly_once(
    session, monkeypatch, synthetic_weekly_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.weekly_rows = _weekly_rows_from_synthetic_history(synthetic_weekly_history)
    state.horizon_weeks = 4

    call_count = {"n": 0}
    real_forecast_all_weekly = state_module.forecast_all_weekly

    def _counting_forecast_all_weekly(history, horizon):
        call_count["n"] += 1
        return real_forecast_all_weekly(history, horizon)

    monkeypatch.setattr("app.state.forecast_all_weekly", _counting_forecast_all_weekly)

    results = state.weekly_forecast_results

    assert call_count["n"] == 1
    assert set(results.keys()) == set(WEEKLY_FORECAST_SERIES_LABELS)
    for key in WEEKLY_FORECAST_SERIES_LABELS:
        assert len(results[key]) == 4
    assert state.weekly_forecast_error == ""


def test_weekly_forecast_results_out_of_range_horizon_sets_error(
    session, monkeypatch, synthetic_weekly_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.weekly_rows = _weekly_rows_from_synthetic_history(synthetic_weekly_history)
    state.horizon_weeks = MAX_HORIZON_WEEKLY + 1  # force out of forecast_all_weekly's range

    results = state.weekly_forecast_results

    assert set(results.keys()) == set(WEEKLY_FORECAST_SERIES_LABELS)
    for series in results.values():
        assert series == []
    assert state.weekly_forecast_error != ""


def test_weekly_capable_series_and_labels_are_consistent():
    assert set(WEEKLY_FORECAST_SERIES_LABELS) == WEEKLY_CAPABLE_SERIES
    assert set(WEEKLY_FORECAST_SERIES_LABELS) == {"hdan", "ppan", "fx_rate"}


def test_available_forecast_series_labels_narrows_when_weekly(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.set_granularity("weekly")

    assert state.available_forecast_series_labels == ["HDAN", "PPAN", "FX Rate"]


# ---------------------------------------------------------------------------
# Regression tests for the "forecast doesn't update after adding data" bug:
# WeeklyPriceRow previously had NO write path anywhere in the app (only ever
# populated once by seed_weekly.py), so weekly_forecast_results/summary cards
# in Weekly mode could never reflect anything entered via Data Entry (which
# only ever wrote to the monthly PriceRow table). Fix: add a weekly CSV
# bulk-import path (handle_weekly_csv_upload/confirm_weekly_import) mirroring
# the existing monthly one, targeting WeeklyPriceRow.
# ---------------------------------------------------------------------------


def _weekly_import_csv(rows: list[dict], columns=None) -> bytes:
    columns = columns or ["date", *WEEKLY_SERIES_ATTRS]
    frame = pd.DataFrame(rows, columns=columns)
    return frame.to_csv(index=False).encode()


def _full_weekly_import_row(date: str, value: float = 1.0) -> dict:
    row = {"date": date}
    for attr in WEEKLY_SERIES_ATTRS:
        row[attr] = value
    return row


def test_confirm_weekly_import_writes_rows_and_reloads_weekly_rows(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_weekly_rows()

    csv_bytes = _weekly_import_csv([_full_weekly_import_row("2026-01-02")])
    asyncio.run(state.handle_weekly_csv_upload([_FakeUpload(csv_bytes)]))
    assert state.weekly_import_stage == "preview"
    assert state.weekly_import_added_count == 1

    state.confirm_weekly_import()

    assert state.weekly_import_stage == "done"
    assert "2026-01-02" in [r.date for r in state.weekly_rows]
    db_row = session.exec(
        WeeklyPriceRow.select().where(WeeklyPriceRow.date == "2026-01-02")
    ).first()
    assert db_row is not None
    assert db_row.hdan == 1.0


def test_weekly_forecast_results_updates_after_weekly_csv_import(
    session, monkeypatch, synthetic_weekly_history
):
    """The actual bug-report scenario: after new weekly data lands (via the
    new weekly CSV import), weekly_forecast_results must reflect it without
    any full page reload -- exercising the real handler chain (upload ->
    confirm -> load_weekly_rows -> weekly_forecast_results), not a manual
    var assignment.
    """
    for row in _weekly_rows_from_synthetic_history(synthetic_weekly_history):
        session.add(
            WeeklyPriceRow(
                date=row.date,
                **{attr: getattr(row, attr) for attr in WEEKLY_SERIES_ATTRS},
            )
        )
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_weekly_rows()
    state.horizon_weeks = 3

    before = state.weekly_forecast_results
    before_base = before["hdan"][0]["base"]

    next_date = (
        pd.to_datetime(state.weekly_rows[-1].date) + pd.DateOffset(weeks=1)
    ).strftime("%Y-%m-%d")
    csv_bytes = _weekly_import_csv([_full_weekly_import_row(next_date, value=99999.0)])
    asyncio.run(state.handle_weekly_csv_upload([_FakeUpload(csv_bytes)]))
    state.confirm_weekly_import()

    after = state.weekly_forecast_results
    after_base = after["hdan"][0]["base"]

    assert after_base != before_base, (
        "weekly_forecast_results did not update after new weekly data was imported"
    )


def test_available_forecast_series_labels_full_when_monthly(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    assert state.available_forecast_series_labels == list(FORECAST_SERIES_LABELS.values())


# ---------------------------------------------------------------------------
# Excel export (EXPORT-01, EXPORT-02)
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


def test_export_actuals_sheet_values(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=9.5, ppan=8.25)]

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data))

    assert df.iloc[0]["hdan"] == 9.5
    assert df.iloc[0]["ppan"] == 8.25


def test_export_has_actuals_forecast_and_weekly_sheets(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=9.5, ppan=8.25)]

    data = state._export_bytes()
    xl = pd.ExcelFile(io.BytesIO(data), engine="openpyxl")

    assert xl.sheet_names == ["Actuals", "Forecast", "Weekly"]


def test_export_weekly_sheet_columns(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.weekly_rows = [
        WeeklyPriceRow(date="2026-01-02", hdan=1.1, ppan=2.2, baltic_an=3.3, fx_rate=3450.0),
        WeeklyPriceRow(date="2026-01-09", hdan=1.2, ppan=2.3, baltic_an=3.4, fx_rate=3460.0),
    ]

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data), sheet_name="Weekly")

    assert list(df.columns) == ["date", *WEEKLY_SERIES_ATTRS]


def test_export_weekly_sheet_data_roundtrip(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.weekly_rows = [
        WeeklyPriceRow(date="2026-01-02", hdan=1.1, ppan=2.2, baltic_an=3.3, fx_rate=3450.0),
    ]

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data), sheet_name="Weekly")

    assert len(df) == len(state.weekly_rows)
    assert df.iloc[0]["hdan"] == 1.1
    assert df.iloc[0]["ppan"] == 2.2
    assert df.iloc[0]["baltic_an"] == 3.3
    assert df.iloc[0]["fx_rate"] == 3450.0


def test_export_weekly_sheet_empty_does_not_raise(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.weekly_rows = []

    data = state._export_bytes()  # noqa: F841 -- must not raise
    df = pd.read_excel(io.BytesIO(data), sheet_name="Weekly")

    assert len(df) == 0
    assert list(df.columns) == ["date", *WEEKLY_SERIES_ATTRS]


def test_export_actuals_and_forecast_unaffected_by_weekly_addition(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.weekly_rows = [
        WeeklyPriceRow(date="2026-01-02", hdan=1.1, ppan=2.2, baltic_an=3.3, fx_rate=3450.0),
    ]

    data = state._export_bytes()
    actuals_df = pd.read_excel(io.BytesIO(data), sheet_name="Actuals")
    forecast_df = pd.read_excel(io.BytesIO(data), sheet_name="Forecast")

    assert len(actuals_df) == len(state.rows)
    assert list(forecast_df.columns) == [
        "Month",
        *[label for _, label in FORECAST_TABLE_COLUMNS],
    ]


def test_forecast_sheet_matches_dashboard_table(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    table_rows = state.forecast_table_rows
    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data), sheet_name="Forecast")

    assert len(df) == 4
    assert list(df["Month"]) == [1, 2, 3, 4]

    for table_row, (_, sheet_row) in zip(table_rows, df.iterrows()):
        for key, label in FORECAST_TABLE_COLUMNS:
            raw = table_row[key]
            if raw == "":
                continue
            expected = float(raw.replace(",", ""))
            actual = sheet_row[label]
            assert abs(actual - expected) < 0.005


def test_forecast_sheet_honours_selected_horizon(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)

    state.horizon_months = 2
    data_2 = state._export_bytes()
    df_2 = pd.read_excel(io.BytesIO(data_2), sheet_name="Forecast")

    state.horizon_months = 9
    data_9 = state._export_bytes()
    df_9 = pd.read_excel(io.BytesIO(data_9), sheet_name="Forecast")

    assert len(df_2) == 2
    assert len(df_9) == 9


def test_forecast_sheet_headers_match_table_columns(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 3

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data), sheet_name="Forecast")

    expected_columns = ["Month"] + [label for _, label in FORECAST_TABLE_COLUMNS]
    assert list(df.columns) == expected_columns


def test_export_with_no_history_writes_header_only_forecast_sheet(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data), sheet_name="Forecast")

    expected_columns = ["Month"] + [label for _, label in FORECAST_TABLE_COLUMNS]
    assert len(df) == 0
    assert list(df.columns) == expected_columns


def test_export_does_not_add_forecast_all_call_site(session, monkeypatch, synthetic_history):
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

    state._export_bytes()

    assert call_count["n"] == 1


def test_export_with_no_history_succeeds_silently(session, monkeypatch):
    """Legitimate insufficient-history case: export_to_excel should
    complete normally (actuals-only) with no forecast-failure signal --
    forecast_results already resolves 'not enough history' to an empty
    result internally, without raising, so _export_bytes never hits its
    except-Exception branch for this case."""
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    state.export_to_excel()

    assert state.export_failed is False
    assert state.export_message == "Downloaded prediction_dashboard_prices.xlsx"


def test_export_surfaces_message_when_forecast_computation_raises_unexpectedly(
    session, monkeypatch, synthetic_history
):
    """Genuine unexpected failure (e.g. a statsmodels/VAR bug) inside
    forecast computation must not be silently swallowed: export still
    completes with actuals data (download still triggered), but
    export_failed/export_message must surface that the Forecast sheet is
    incomplete."""
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 3

    def _boom(history, horizon, markup_pct):
        raise RuntimeError("simulated statsmodels convergence failure")

    monkeypatch.setattr("app.state.forecast_all", _boom)

    event = state.export_to_excel()

    # Export must still complete (actuals-only) rather than being blocked.
    assert event is not None
    assert state.export_failed is True
    assert "Forecast" in state.export_message
    assert "Downloaded" in state.export_message


def test_export_bytes_still_produces_actuals_when_forecast_raises_unexpectedly(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 3

    def _boom(history, horizon, markup_pct):
        raise RuntimeError("simulated VAR system failure")

    monkeypatch.setattr("app.state.forecast_all", _boom)

    data = state._export_bytes()
    df = pd.read_excel(io.BytesIO(data), sheet_name="Actuals")

    assert len(df) == len(state.rows)
    assert state._last_export_forecast_failed is True


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
    # 2026-08-26 precision-instrument redesign: ACCENT_FILL retuned
    # alongside ACCENT (teal-cyan #0E7C86, was #2563EB).
    assert figure.data[2].fillcolor == "rgba(14,124,134,0.15)"
    assert figure.data[1].line.width == 0
    assert figure.data[2].line.width == 0
    assert figure.data[1].showlegend is False


def test_forecast_chart_base_line_drawn_last(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure

    # 2026-08-26 precision-instrument redesign: ACCENT retuned to
    # teal-cyan (#0E7C86, was #2563EB).
    assert figure.data[3].line.color == "#0E7C86"
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
# Weekly branching for forecast_chart_figure / forecast_table_rows (WKUI-08)
# ---------------------------------------------------------------------------


def test_forecast_chart_figure_weekly_dates_are_week_spaced(
    session, monkeypatch, synthetic_weekly_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.set_granularity("weekly")
    state.weekly_rows = _weekly_rows_from_synthetic_history(synthetic_weekly_history)
    state.horizon_weeks = 4
    state.forecast_series = "hdan"

    figure = state.forecast_chart_figure

    # data[1] is the "Bear" trace; its x values are [last_hist_date, *fc_dates].
    bridge_x = pd.to_datetime(list(figure.data[1].x))
    assert bridge_x[2] - bridge_x[1] == pd.Timedelta(weeks=1)


def test_forecast_chart_figure_monthly_unchanged(session, monkeypatch, synthetic_history):
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
    assert figure.layout.xaxis.title.text == "Month"


def test_forecast_table_rows_weekly_has_no_diesel_columns(
    session, monkeypatch, synthetic_weekly_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.set_granularity("weekly")
    state.weekly_rows = _weekly_rows_from_synthetic_history(synthetic_weekly_history)
    state.horizon_weeks = 4

    rows = state.forecast_table_rows

    assert rows != []
    for row in rows:
        assert not any(key.startswith("diesel_usd_ton_") or key.startswith("diesel_mnt_") for key in row)
        for series_key in WEEKLY_FORECAST_SERIES_LABELS:
            for scenario in ("base", "bull", "bear"):
                assert f"{series_key}_{scenario}" in row


def test_forecast_table_rows_weekly_dates_are_real_calendar_dates(
    session, monkeypatch, synthetic_weekly_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.set_granularity("weekly")
    state.weekly_rows = _weekly_rows_from_synthetic_history(synthetic_weekly_history)
    state.horizon_weeks = 4

    rows = state.forecast_table_rows

    dates = [pd.to_datetime(row["month"]) for row in rows]
    assert dates == sorted(dates)
    assert len(set(dates)) == len(dates)


def test_forecast_table_rows_weekly_empty_when_no_weekly_rows(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.set_granularity("weekly")
    state.weekly_rows = []

    rows = state.forecast_table_rows

    assert rows == []


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


# ---------------------------------------------------------------------------
# Forecast summary cards (D-10..D-13, Phase 6 plan 06-01)
# ---------------------------------------------------------------------------


def test_summary_cards_length_and_order_empty(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    cards = state.summary_cards

    assert len(cards) == 5
    assert [c["series_key"] for c in cards] == [
        "hdan",
        "ppan",
        "diesel_usd_ton",
        "diesel_mnt",
        "fx_rate",
    ]
    for card in cards:
        assert card["has_data"] == "no"
        assert card["base"] == ""
        assert card["no_data_text"] == "Add pricing data to see a forecast"


def test_summary_cards_length_and_order_populated(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    cards = state.summary_cards

    assert len(cards) == 5
    assert [c["series_key"] for c in cards] == [
        "hdan",
        "ppan",
        "diesel_usd_ton",
        "diesel_mnt",
        "fx_rate",
    ]


# ---------------------------------------------------------------------------
# Phase 22 -- summary_cards dimming/weekly-provenance branching (WKUI-05/07)
# ---------------------------------------------------------------------------


def test_summary_cards_diesel_cards_dimmed_in_weekly_mode(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.set_granularity("weekly")

    cards = {c["series_key"]: c for c in state.summary_cards}

    for key in ("diesel_usd_ton", "diesel_mnt"):
        assert cards[key]["is_dimmed"] == "yes"
        assert cards[key]["cadence_badge"] == "Monthly data only"

    for key in ("hdan", "ppan", "fx_rate"):
        assert cards[key]["is_dimmed"] == "no"
        assert cards[key]["cadence_badge"] == ""


def test_summary_cards_not_dimmed_in_monthly_mode(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    assert state.granularity == "monthly"

    cards = {c["series_key"]: c for c in state.summary_cards}

    for key in ("hdan", "ppan", "diesel_usd_ton", "diesel_mnt", "fx_rate"):
        assert cards[key]["is_dimmed"] == "no"
        assert cards[key]["cadence_badge"] == ""


def test_summary_cards_weekly_capable_cards_read_weekly_results(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    monthly_state = DashboardState()
    monthly_state.rows = _rows_from_synthetic_history(synthetic_history)
    monthly_state.horizon_months = 4
    monthly_cards = monthly_state.summary_cards
    monthly_base = next(c["base"] for c in monthly_cards if c["series_key"] == "hdan")

    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4
    state.set_granularity("weekly")

    fake_weekly_results = {
        "hdan": [{"week": 1, "base": 999.9, "bull": 1000.0, "bear": 900.0}],
        "ppan": [],
        "fx_rate": [],
    }
    monkeypatch.setattr(
        state_module.DashboardState,
        "weekly_forecast_results",
        property(lambda self: fake_weekly_results),
    )

    weekly_cards = {c["series_key"]: c for c in state.summary_cards}

    assert weekly_cards["hdan"]["base"] != monthly_base
    assert weekly_cards["hdan"]["base"] == "999.90"


def test_summary_cards_weekly_model_text_folds_in_monthly_mape(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.set_granularity("weekly")

    fake_weekly_results = {
        "hdan": [{"week": 1, "base": 100.0, "bull": 110.0, "bear": 90.0}],
        "ppan": [],
        "fx_rate": [],
    }
    monkeypatch.setattr(
        state_module.DashboardState,
        "weekly_forecast_results",
        property(lambda self: fake_weekly_results),
    )

    cards = {c["series_key"]: c for c in state.summary_cards}
    weekly_name, weekly_mape = WEEKLY_MODEL_INFO["hdan"]
    _, monthly_mape = MODEL_INFO["hdan"]

    assert weekly_name in cards["hdan"]["model_text"]
    assert f"{weekly_mape:.2f}%" in cards["hdan"]["model_text"]
    assert f"{monthly_mape:.1f}%" in cards["hdan"]["model_text"]


def test_summary_cards_diesel_mnt_model_text_never_weekly(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    monthly_state = DashboardState()
    monthly_state.rows = _rows_from_synthetic_history(synthetic_history)
    monthly_cards = {c["series_key"]: c for c in monthly_state.summary_cards}

    weekly_state = DashboardState()
    weekly_state.rows = _rows_from_synthetic_history(synthetic_history)
    weekly_state.set_granularity("weekly")
    weekly_cards = {c["series_key"]: c for c in weekly_state.summary_cards}

    assert (
        monthly_cards["diesel_mnt"]["model_text"] == weekly_cards["diesel_mnt"]["model_text"]
    )
    assert "MAPE weekly" not in weekly_cards["diesel_mnt"]["model_text"]


def test_summary_cards_key_parity_no_data_branch_carries_dim_keys(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []
    state.weekly_rows = []
    state.set_granularity("weekly")

    cards = {c["series_key"]: c for c in state.summary_cards}

    for key in ("hdan", "ppan", "diesel_usd_ton", "diesel_mnt", "fx_rate"):
        assert "is_dimmed" in cards[key]
        assert "cadence_badge" in cards[key]

    # hdan/ppan/fx_rate are weekly-capable, just dataless -- never dimmed.
    for key in ("hdan", "ppan", "fx_rate"):
        assert cards[key]["is_dimmed"] == "no"
        assert cards[key]["cadence_badge"] == ""

    for key in ("diesel_usd_ton", "diesel_mnt"):
        assert cards[key]["is_dimmed"] == "yes"
        assert cards[key]["cadence_badge"] == "Monthly data only"


def test_summary_cards_all_values_are_strings(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    for card in state.summary_cards:
        assert all(isinstance(v, str) for v in card.values())

    empty_state = DashboardState()
    empty_state.rows = []
    for card in empty_state.summary_cards:
        assert all(isinstance(v, str) for v in card.values())


def test_summary_cards_base_formatted_with_separator(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    cards = {c["series_key"]: c for c in state.summary_cards}

    for card in cards.values():
        assert card["has_data"] == "yes"
        assert "." in card["base"]


def test_summary_cards_horizon_reactive_without_new_state(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)

    state.horizon_months = 3
    cards_3 = {c["series_key"]: c["base"] for c in state.summary_cards}

    state.horizon_months = 6
    cards_6 = {c["series_key"]: c["base"] for c in state.summary_cards}

    assert cards_3 != cards_6


def test_summary_cards_direction_up(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=100.0, ppan=100.0, fx_rate=1.0)]
    state.horizon_months = 1

    fake_results = {
        "hdan": [{"month": 1, "base": 150.0, "bull": 160.0, "bear": 140.0}],
        "ppan": [{"month": 1, "base": 90.0, "bull": 95.0, "bear": 85.0}],
        "diesel_usd_ton": [],
        "diesel_mnt": [],
        "fx_rate": [{"month": 1, "base": 1.0, "bull": 1.1, "bear": 0.9}],
    }
    monkeypatch.setattr(
        state_module.DashboardState,
        "forecast_results",
        property(lambda self: fake_results),
    )

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["direction"] == "up"
    assert cards["hdan"]["arrow"] == "↑"
    assert cards["hdan"]["delta_text"] == "50.0%"


def test_summary_cards_direction_down(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=100.0, ppan=100.0, fx_rate=1.0)]
    state.horizon_months = 1

    fake_results = {
        "hdan": [{"month": 1, "base": 80.0, "bull": 85.0, "bear": 75.0}],
        "ppan": [],
        "diesel_usd_ton": [],
        "diesel_mnt": [],
        "fx_rate": [],
    }
    monkeypatch.setattr(
        state_module.DashboardState,
        "forecast_results",
        property(lambda self: fake_results),
    )

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["direction"] == "down"
    assert cards["hdan"]["arrow"] == "↓"
    assert cards["hdan"]["delta_text"] == "20.0%"


def test_summary_cards_zero_latest_actual_is_flat_no_crash(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-01-01", hdan=0.0)]
    state.horizon_months = 1

    fake_results = {
        "hdan": [{"month": 1, "base": 50.0, "bull": 55.0, "bear": 45.0}],
        "ppan": [],
        "diesel_usd_ton": [],
        "diesel_mnt": [],
        "fx_rate": [],
    }
    monkeypatch.setattr(
        state_module.DashboardState,
        "forecast_results",
        property(lambda self: fake_results),
    )

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["direction"] == "flat"
    assert cards["hdan"]["delta_text"] == ""


def _rows_ascending(n, start="2023-01-01"):
    dates = pd.date_range(start, periods=n, freq="MS")
    return [PriceRow(date=d.strftime("%Y-%m-%d"), hdan=float(i)) for i, d in enumerate(dates)]


def test_visible_rows_windows_to_twelve_most_recent(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    rows = _rows_ascending(20)
    state.rows = rows

    visible = state.visible_rows

    assert len(visible) == TABLE_WINDOW_ROWS
    assert visible[-1].date == rows[-1].date
    assert visible[0].date == rows[8].date


def test_visible_rows_returns_all_when_show_all_history(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    rows = _rows_ascending(20)
    state.rows = rows
    state.show_all_history = True

    assert len(state.visible_rows) == 20


def test_visible_rows_shorter_than_window_returns_all(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    rows = _rows_ascending(3)
    state.rows = rows

    assert len(state.visible_rows) == 3


def test_toggle_show_all_history_cancels_edit_and_pending_delete(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_ascending(20)
    state.editing_key = "2024-01-01:hdan"
    state.draft_value = "9"
    state.edit_error = "x"
    state.pending_delete = "2024-01-01"
    state.draft_rows = [PriceRow(date="")]

    state.toggle_show_all_history(True)

    assert state.editing_key == ""
    assert state.draft_value == ""
    assert state.edit_error == ""
    assert state.pending_delete == ""
    assert len(state.draft_rows) == 1


def test_toggle_show_all_history_never_mutates_rows(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    rows = _rows_ascending(20)
    state.rows = rows
    snapshot = [r.date for r in state.rows]

    state.toggle_show_all_history(True)
    assert [r.date for r in state.rows] == snapshot
    assert len(state.rows) == 20

    state.toggle_show_all_history(False)
    assert [r.date for r in state.rows] == snapshot
    assert len(state.rows) == 20


def test_state_module_assigns_self_rows_exactly_once():
    source = inspect.getsource(state_module)
    lines = [line for line in source.splitlines() if not line.strip().startswith("#")]
    stripped_source = "\n".join(lines)
    assert stripped_source.count("self.rows = ") == 1


def test_history_window_caption_copy(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_ascending(20)

    assert state.history_window_caption == "Showing the most recent 12 months."

    state.show_all_history = True
    assert state.history_window_caption == "Showing full history (20 rows)."


def test_summary_cards_does_not_call_forecast_all_more_than_once(
    session, monkeypatch, synthetic_history
):
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

    _ = state.summary_cards

    assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# _actual_series_for (Phase 8 plan 08-01, Task 1 — single derivation helper)
# ---------------------------------------------------------------------------


def test_actual_series_for_skips_none_values(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-01-01", hdan=10.0),
        PriceRow(date="2025-02-01", hdan=None),
        PriceRow(date="2025-03-01", hdan=30.0),
    ]

    assert state._actual_series_for("hdan") == [
        ("2025-01-01", 10.0),
        ("2025-03-01", 30.0),
    ]


def test_actual_series_for_diesel_mnt_applies_markup(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.markup_pct = 10.0
    state.rows = [PriceRow(date="2025-01-01", diesel_usd_ton=100.0, fx_rate=3.0)]

    series = state._actual_series_for("diesel_mnt")

    assert series == [("2025-01-01", 330.0 / DIESEL_LITERS_PER_TON)]


def test_actual_series_for_diesel_mnt_skips_partial_rows(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-01-01", diesel_usd_ton=100.0, fx_rate=None),
        PriceRow(date="2025-02-01", diesel_usd_ton=None, fx_rate=3.0),
        PriceRow(date="2025-03-01", diesel_usd_ton=100.0, fx_rate=3.0),
    ]

    series = state._actual_series_for("diesel_mnt")

    assert [d for d, _ in series] == ["2025-03-01"]


def test_actual_series_for_empty_rows_returns_empty_list(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    assert state._actual_series_for("hdan") == []


def test_latest_actual_for_diesel_mnt_regression_parity(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.markup_pct = 5.0
    state.rows = [
        PriceRow(date="2025-01-01", diesel_usd_ton=100.0, fx_rate=3.0),
        PriceRow(date="2025-02-01", diesel_usd_ton=110.0, fx_rate=3.1),
    ]

    assert state._latest_actual_for("diesel_mnt") == (
        110.0 * 3.1 * 1.05 / DIESEL_LITERS_PER_TON
    )


# ---------------------------------------------------------------------------
# All-time high/low on summary_cards (FCST-08, Phase 8 plan 08-01 Task 2)
# ---------------------------------------------------------------------------


def test_summary_cards_hilo_text_formats_high_then_low(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-01-01", hdan=10.0),
        PriceRow(date="2025-02-01", hdan=55.5),
        PriceRow(date="2025-03-01", hdan=30.0),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["hilo_text"] == "55.50 / 10.00"
    assert cards["hdan"]["hilo_label"] == "All-time high/low"


def test_summary_cards_hilo_single_value_high_equals_low(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = [PriceRow(date="2025-01-01", hdan=1234.56)]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["hilo_text"] == "1,234.56 / 1,234.56"


def test_summary_cards_hilo_diesel_mnt_uses_markup_derivation(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.markup_pct = 10.0
    state.rows = [
        PriceRow(date="2025-01-01", diesel_usd_ton=100.0, fx_rate=3.0),
        PriceRow(date="2025-02-01", diesel_usd_ton=200.0, fx_rate=3.0),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    # 100*3*1.1=330, 200*3*1.1=660, both divided by DIESEL_LITERS_PER_TON
    low = 330.0 / DIESEL_LITERS_PER_TON
    high = 660.0 / DIESEL_LITERS_PER_TON
    assert cards["diesel_mnt"]["hilo_text"] == f"{high:,.2f} / {low:,.2f}"


def test_summary_cards_hilo_empty_when_no_actuals(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    for card in state.summary_cards:
        assert card["hilo_text"] == ""
        assert card["hilo_label"] == "All-time high/low"


def test_summary_cards_hilo_ignores_visible_rows_window(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    rows = _rows_ascending(20)
    # Put the all-time extreme far outside the TABLE_WINDOW_ROWS window.
    rows[0].hdan = 9999.0
    state.rows = rows

    state.show_all_history = False
    hilo_windowed = {c["series_key"]: c["hilo_text"] for c in state.summary_cards}
    state.show_all_history = True
    hilo_full = {c["series_key"]: c["hilo_text"] for c in state.summary_cards}

    assert "9,999.00" in hilo_windowed["hdan"]
    assert hilo_windowed == hilo_full


# ---------------------------------------------------------------------------
# Year-over-year on summary_cards (FCST-09, Phase 8 plan 08-01 Task 3)
# ---------------------------------------------------------------------------


def _stub_nonempty_forecast_results(monkeypatch):
    """Force forecast_results to a non-empty shape for all summary-card
    series, so summary_cards takes the populated branch regardless of
    MIN_HISTORY_ROWS (forecasting.py) — YoY here is exercised purely via
    self.rows/_actual_series_for, independent of real forecasting.
    """
    fake_results = {
        key: [{"month": 1, "base": 1.0, "bull": 1.0, "bear": 1.0}]
        for key in FORECAST_SERIES_LABELS
    }
    monkeypatch.setattr(
        state_module.DashboardState,
        "forecast_results",
        property(lambda self: fake_results),
    )


def test_summary_cards_yoy_up_matches_calendar_month(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-07-01", hdan=100.0),
        PriceRow(date="2026-07-01", hdan=104.2),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["yoy_direction"] == "up"
    assert cards["hdan"]["yoy_arrow"] == "↑"
    assert cards["hdan"]["yoy_text"] == "4.2% vs. Jul 2025"


def test_summary_cards_yoy_down(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-07-01", hdan=100.0),
        PriceRow(date="2026-07-01", hdan=90.0),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["yoy_direction"] == "down"
    assert cards["hdan"]["yoy_arrow"] == "↓"
    assert cards["hdan"]["yoy_text"] == "10.0% vs. Jul 2025"


def test_summary_cards_yoy_flat_zero_pct(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-07-01", hdan=100.0),
        PriceRow(date="2026-07-01", hdan=100.0),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["yoy_direction"] == "flat"
    assert cards["hdan"]["yoy_arrow"] == "→"
    assert cards["hdan"]["yoy_text"] == "0.0% vs. Jul 2025"


def test_summary_cards_yoy_empty_when_no_prior_year_actual(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    state.rows = [PriceRow(date="2026-07-01", hdan=104.2)]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["yoy_text"] == ""
    assert cards["hdan"]["yoy_arrow"] == ""
    assert cards["hdan"]["yoy_direction"] == "flat"


def test_summary_cards_yoy_empty_when_prior_value_zero(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-07-01", hdan=0.0),
        PriceRow(date="2026-07-01", hdan=104.2),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["yoy_text"] == ""


def test_summary_cards_yoy_matches_month_not_row_offset(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    # 13 rows back from the latest is NOT the same calendar month as the
    # latest, because a month is missing in between (D-02 guard).
    state.rows = [
        PriceRow(date="2025-06-01", hdan=999.0),  # 13 rows back — wrong month
        PriceRow(date="2025-07-01", hdan=100.0),  # correct calendar match
        PriceRow(date="2025-08-01", hdan=50.0),
        PriceRow(date="2025-09-01", hdan=50.0),
        PriceRow(date="2025-10-01", hdan=50.0),
        PriceRow(date="2025-11-01", hdan=50.0),
        PriceRow(date="2025-12-01", hdan=50.0),
        PriceRow(date="2026-01-01", hdan=50.0),
        PriceRow(date="2026-02-01", hdan=50.0),
        PriceRow(date="2026-03-01", hdan=50.0),
        PriceRow(date="2026-04-01", hdan=50.0),
        PriceRow(date="2026-05-01", hdan=50.0),
        PriceRow(date="2026-06-01", hdan=50.0),
        PriceRow(date="2026-07-01", hdan=104.2),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["yoy_text"] == "4.2% vs. Jul 2025"


def test_summary_cards_yoy_ignores_day_of_month(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    state.rows = [
        PriceRow(date="2025-07-01", hdan=100.0),
        PriceRow(date="2026-07-15", hdan=104.2),
    ]

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["yoy_text"] == "4.2% vs. Jul 2025"


def test_summary_cards_yoy_ignores_visible_rows_window(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    _stub_nonempty_forecast_results(monkeypatch)
    state = DashboardState()
    rows = _rows_ascending(20)
    rows[0].hdan = 500.0  # prior-year comparator outside TABLE_WINDOW_ROWS
    state.rows = rows

    state.show_all_history = False
    yoy_windowed = {c["series_key"]: c["yoy_text"] for c in state.summary_cards}
    state.show_all_history = True
    yoy_full = {c["series_key"]: c["yoy_text"] for c in state.summary_cards}

    assert yoy_windowed == yoy_full


# ---------------------------------------------------------------------------
# Phase 10 -- CSV bulk import (IMPORT-01, IMPORT-02)
# ---------------------------------------------------------------------------


class _FakeUpload:
    """Minimal stand-in for rx.UploadFile: async read() + a name attribute."""

    def __init__(self, data: bytes, name: str = "prices.csv"):
        self._data = data
        self.name = name

    async def read(self):
        return self._data


def _import_csv(rows: list[dict], columns=None) -> bytes:
    """Build CSV bytes for a list of row dicts, in the correct schema order.

    Mirrors test_csv_import.py's `_csv` helper.
    """
    columns = columns or ["date", *SERIES_ATTRS]
    frame = pd.DataFrame(rows, columns=columns)
    return frame.to_csv(index=False).encode()


def _full_import_row(date: str, value: float = 1.0) -> dict:
    row = {"date": date}
    for attr in SERIES_ATTRS:
        row[attr] = value
    return row


def test_handle_csv_upload_import_stages_preview_without_writing(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    csv_bytes = _import_csv(
        [_full_import_row("2026-01-01"), _full_import_row("2026-02-01")]
    )
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))

    assert state.import_stage == "preview"
    assert state.import_added_count == 2
    assert _db_row_count(session) == 0


def test_handle_csv_upload_import_malformed_header_sets_error_stage_and_stages_nothing(
    session, monkeypatch
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    bad_columns = ["date", *SERIES_ATTRS[1:]]  # missing column -> header mismatch
    csv_bytes = _import_csv([], columns=bad_columns)
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))

    assert state.import_stage == "error"
    assert state.import_error != ""
    assert state.import_added_count == 0
    assert state._staged_import_rows == []


def test_handle_csv_upload_import_does_not_touch_edit_error(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    state.edit_error = "sentinel"

    csv_bytes = _import_csv([_full_import_row("2026-01-01")])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))

    assert state.edit_error == "sentinel"


def test_handle_csv_upload_does_not_touch_edit_error_or_editing_key(session, monkeypatch):
    """D-03 audit proof: CSV import must not interact with the edit machine
    at all, even while a genuine validation error is pending on an
    open cell.
    """
    session.add(PriceRow(date="2025-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.add_row()
    state.start_edit(":date", "")
    state.update_draft("2025-01-20")
    state.commit_edit()

    assert state.edit_error == validators.DATE_DUPLICATE_ERROR
    editing_key_before = state.editing_key
    draft_value_before = state.draft_value
    draft_rows_before = list(state.draft_rows)

    csv_bytes = _import_csv([_full_import_row("2026-01-01")])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))

    assert state.edit_error == validators.DATE_DUPLICATE_ERROR
    assert state.editing_key == editing_key_before
    assert state.draft_value == draft_value_before
    assert state.draft_rows == draft_rows_before


def test_confirm_import_batch_writes_valid_rows(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    csv_bytes = _import_csv(
        [_full_import_row("2026-01-01"), _full_import_row("2026-02-01")]
    )
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))
    state.confirm_import()

    assert _db_row_count(session) == 2
    assert len(state.rows) == 2
    assert state.import_stage == "done"
    assert state.import_result_text == "Import complete: 2 rows added."


def test_confirm_import_never_overwrites_existing_row(session, monkeypatch):
    """IMPORT-02 non-overwrite proof: an existing row's stored values are
    byte-identical before and after an import containing its month.
    """
    session.add(PriceRow(date="2026-01-01", hdan=100.0, ppan=200.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    before_snapshot = {"date": "2026-01-01"}
    existing = _get_db_row(session, "2026-01-01")
    for attr in SERIES_ATTRS:
        before_snapshot[attr] = getattr(existing, attr)

    # Same month (duplicate date), different attempted values, plus one
    # genuinely new row for a different month.
    duplicate_row = {"date": "2026-01-15", "hdan": 999.0, "ppan": 888.0}
    for attr in SERIES_ATTRS:
        duplicate_row.setdefault(attr, None)
    new_row = _full_import_row("2026-03-01")

    csv_bytes = _import_csv([duplicate_row, new_row])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))

    assert state.import_duplicate_count == 1
    assert state.import_added_count == 1

    state.confirm_import()

    after = _get_db_row(session, "2026-01-01")
    after_snapshot = {"date": after.date}
    for attr in SERIES_ATTRS:
        after_snapshot[attr] = getattr(after, attr)

    assert after_snapshot == before_snapshot
    assert _db_row_count(session) == 2


def test_confirm_import_with_zero_staged_rows_writes_nothing(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    csv_bytes = _import_csv([], columns=["date", *SERIES_ATTRS])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))
    assert state.import_stage == "preview"
    assert state.import_added_count == 0

    before = _db_row_count(session)
    state.confirm_import()

    assert _db_row_count(session) == before
    assert state.import_stage == "done"
    assert state.import_result_text == "Import complete: 0 rows added."


def test_confirm_import_calls_load_rows_so_rows_reflect_new_data(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    csv_bytes = _import_csv([_full_import_row("2026-04-01")])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))
    state.confirm_import()

    assert "2026-04-01" in [r.date for r in state.rows]


def test_confirm_import_result_count_derives_from_rows_not_parse_count(
    session, monkeypatch
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    csv_bytes = _import_csv(
        [_full_import_row("2026-05-01"), _full_import_row("2026-06-01")]
    )
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))
    before = len(state.rows)
    state.confirm_import()

    assert state.import_added_count == len(state.rows) - before


def test_confirm_import_twice_does_not_double_write(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    csv_bytes = _import_csv([_full_import_row("2026-07-01")])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))
    state.confirm_import()
    assert _db_row_count(session) == 1

    # Calling confirm_import again without a new upload must not re-insert
    # (staged rows were cleared after the first commit and stage is "done").
    state.confirm_import()
    assert _db_row_count(session) == 1


def test_cancel_import_writes_nothing_and_resets(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    csv_bytes = _import_csv([_full_import_row("2026-08-01")])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))
    assert state.import_stage == "preview"

    state.cancel_import()

    assert _db_row_count(session) == 0
    assert state.import_stage == "idle"
    assert state.import_added_count == 0
    assert state.import_duplicate_count == 0
    assert state.import_invalid_count == 0


def test_import_does_not_open_a_session_before_confirm(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()

    handler = DashboardState.__dict__["handle_csv_upload"]
    handler_fn = getattr(handler, "fn", handler)
    assert "rx.session" not in inspect.getsource(handler_fn)

    before = _db_row_count(session)
    csv_bytes = _import_csv([_full_import_row("2026-09-01")])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))

    assert _db_row_count(session) == before


# ---------------------------------------------------------------------------
# Theme mode (THEME-01/THEME-02/THEME-03, Phase 11 Plan 02)
# ---------------------------------------------------------------------------


def test_theme_mode_defaults_to_light():
    state = DashboardState()
    assert state.theme_mode == "light"


def test_toggle_theme_mode_flips_light_dark():
    state = DashboardState()
    state.toggle_theme_mode()
    assert state.theme_mode == "dark"
    state.toggle_theme_mode()
    assert state.theme_mode == "light"


def test_page_bg_resolves_per_mode():
    state = DashboardState()
    assert state.page_bg == theme.LIGHT["PAGE_BG"]
    state.theme_mode = "dark"
    assert state.page_bg == theme.DARK["PAGE_BG"]
    # End-to-end anchor proving the theme.py -> theme_mode -> computed var
    # chain is fully wired (11-02-PLAN.md Task 2).
    assert state.page_bg == "#101416"


def test_surface_resolves_per_mode():
    state = DashboardState()
    assert state.surface == theme.LIGHT["SURFACE"]
    state.theme_mode = "dark"
    assert state.surface == theme.DARK["SURFACE"]


def test_muted_text_resolves_per_mode():
    state = DashboardState()
    assert state.muted_text == theme.LIGHT["MUTED_TEXT"]
    state.theme_mode = "dark"
    assert state.muted_text == theme.DARK["MUTED_TEXT"]


def test_card_border_resolves_per_mode():
    state = DashboardState()
    assert state.card_border == f"1px solid {theme.LIGHT['BORDER']}"
    state.theme_mode = "dark"
    assert state.card_border == f"1px solid {theme.DARK['BORDER']}"


def test_up_down_destructive_colors_resolve_per_mode():
    state = DashboardState()
    assert state.up_color == theme.LIGHT["UP"]
    assert state.down_color == theme.LIGHT["DOWN"]
    assert state.destructive_color == theme.LIGHT["DESTRUCTIVE"]

    state.theme_mode = "dark"
    assert state.up_color == theme.DARK["UP"]
    assert state.down_color == theme.DARK["DOWN"]
    assert state.destructive_color == theme.DARK["DESTRUCTIVE"]


# ---------------------------------------------------------------------------
# Mode-aware Plotly figure builders (Phase 11 Plan 02 Task 3)
# ---------------------------------------------------------------------------


def test_historical_chart_figure_font_color_follows_theme_mode(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    figure = state.historical_chart_figure
    assert figure.layout.font.color == theme.LIGHT["MUTED_TEXT"]
    assert figure.layout.plot_bgcolor == "rgba(0,0,0,0)"

    state.theme_mode = "dark"
    figure = state.historical_chart_figure
    assert figure.layout.font.color == theme.DARK["MUTED_TEXT"]
    assert figure.layout.plot_bgcolor == "rgba(0,0,0,0)"


def test_forecast_chart_figure_font_color_follows_theme_mode(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure
    assert figure.layout.font.color == theme.LIGHT["MUTED_TEXT"]
    assert figure.layout.plot_bgcolor == "rgba(0,0,0,0)"

    state.theme_mode = "dark"
    figure = state.forecast_chart_figure
    assert figure.layout.font.color == theme.DARK["MUTED_TEXT"]
    assert figure.layout.plot_bgcolor == "rgba(0,0,0,0)"


def test_forecast_chart_band_fillcolor_follows_theme_mode(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4
    state.theme_mode = "dark"

    figure = state.forecast_chart_figure
    assert figure.data[2].fillcolor == theme.DARK["ACCENT_FILL"]


# ---------------------------------------------------------------------------
# Phase 12: fan chart legend / axis non-overlap (VIS-04)
# ---------------------------------------------------------------------------


def test_forecast_chart_legend_sits_below_plot_area(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure
    assert figure.layout.legend.orientation == "h"
    assert figure.layout.legend.y < 0
    assert figure.layout.legend.yanchor == "top"
    assert figure.layout.legend.x == 0.5
    assert figure.layout.legend.xanchor == "center"


def test_historical_chart_legend_layout_matches_forecast(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()

    figure = state.historical_chart_figure
    assert figure.layout.legend.orientation == "h"
    assert figure.layout.legend.y < 0
    assert figure.layout.legend.yanchor == "top"
    assert figure.layout.legend.x == 0.5
    assert figure.layout.legend.xanchor == "center"
    assert figure.layout.showlegend is False


def test_chart_bottom_margin_accommodates_legend(session, monkeypatch, synthetic_history):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.add(PriceRow(date="2026-02-01", hdan=2.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    populated_hist_state = DashboardState()
    populated_hist_state.load_rows()
    populated_hist_figure = populated_hist_state.historical_chart_figure

    populated_forecast_state = DashboardState()
    populated_forecast_state.rows = _rows_from_synthetic_history(synthetic_history)
    populated_forecast_state.horizon_months = 4
    populated_forecast_figure = populated_forecast_state.forecast_chart_figure

    empty_state = DashboardState()
    empty_state.rows = []
    empty_hist_figure = empty_state.historical_chart_figure
    empty_forecast_figure = empty_state.forecast_chart_figure

    for figure in (
        populated_hist_figure,
        populated_forecast_figure,
        empty_hist_figure,
        empty_forecast_figure,
    ):
        assert figure.layout.margin.b >= 130
        assert figure.layout.margin.l == 40
        assert figure.layout.margin.r == 16
        assert figure.layout.margin.t == 16


def test_empty_state_figures_also_carry_below_plot_legend():
    state = DashboardState()
    state.rows = []

    empty_hist_figure = state.historical_chart_figure
    empty_forecast_figure = state.forecast_chart_figure

    for figure in (empty_hist_figure, empty_forecast_figure):
        assert figure.layout.legend.y < 0
        assert figure.layout.legend.yanchor == "top"


def test_forecast_start_annotation_position_unchanged(session, monkeypatch, synthetic_history):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    figure = state.forecast_chart_figure
    annotation_texts = [a.text for a in figure.layout.annotations]
    assert "Forecast start" in annotation_texts


# Model provenance on summary_cards (VIS-05, Phase 13 plan 13-01 Task 2)


def test_summary_cards_model_label_and_text_present_populated(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    cards = {c["series_key"]: c for c in state.summary_cards}

    for key in ("hdan", "ppan", "diesel_mnt", "fx_rate"):
        assert cards[key]["model_label"] == "Model"
        assert cards[key]["model_text"] != ""


def test_summary_cards_model_label_and_text_present_empty(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = []

    cards = {c["series_key"]: c for c in state.summary_cards}

    for key in ("hdan", "ppan", "diesel_mnt", "fx_rate"):
        assert cards[key]["model_label"] == "Model"
        assert cards[key]["model_text"] != ""


def test_summary_cards_model_text_matches_model_info(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["hdan"]["model_text"] == "SARIMAX · 13.3% typical error"
    assert cards["ppan"]["model_text"] == "Direct-OLS VAR · 23.8% typical error"
    assert cards["fx_rate"]["model_text"] == "Naive · 1.7% typical error"


def test_summary_cards_diesel_mnt_model_text_has_no_percentage(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_from_synthetic_history(synthetic_history)
    state.horizon_months = 4

    cards = {c["series_key"]: c for c in state.summary_cards}

    assert cards["diesel_mnt"]["model_text"] == "Derived (Diesel USD × FX ÷ 1,136 L)"
    assert "%" not in cards["diesel_mnt"]["model_text"]
    assert "·" not in cards["diesel_mnt"]["model_text"]


def test_summary_cards_model_text_identical_across_data_branches(
    session, monkeypatch, synthetic_history
):
    monkeypatch.setattr("reflex.session", lambda: session)
    populated_state = DashboardState()
    populated_state.rows = _rows_from_synthetic_history(synthetic_history)
    populated_state.horizon_months = 4
    populated_cards = {c["series_key"]: c for c in populated_state.summary_cards}

    empty_state = DashboardState()
    empty_state.rows = []
    empty_cards = {c["series_key"]: c for c in empty_state.summary_cards}

    for key in ("hdan", "ppan", "diesel_mnt", "fx_rate"):
        assert populated_cards[key]["model_text"] == empty_cards[key]["model_text"]


def test_active_section_defaults_to_summary():
    state = DashboardState()
    assert state.active_section == "summary"


def test_set_active_section_preserves_mid_edit_state(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.add_row()
    state.start_edit(":hdan", "")
    state.update_draft("7")

    editing_key = state.editing_key
    draft_value = state.draft_value
    edit_error = state.edit_error
    pending_delete = state.pending_delete
    draft_rows = list(state.draft_rows)

    state.set_active_section("summary")
    state.set_active_section("data_entry")

    assert state.active_section == "data_entry"
    assert state.editing_key == editing_key
    assert state.draft_value == draft_value
    assert state.edit_error == edit_error
    assert state.pending_delete == pending_delete
    assert state.draft_rows == draft_rows


def test_set_active_section_preserves_import_preview_state(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.import_stage = "preview"
    state._staged_import_rows = [{"date": "2026-01-01", "hdan": 1.0}]

    staged_rows = list(state._staged_import_rows)

    state.set_active_section("data_entry")
    state.set_active_section("summary")

    assert state.import_stage == "preview"
    assert state._staged_import_rows == staged_rows


def test_set_active_section_does_not_reload_data():
    src = inspect.getsource(DashboardState.set_active_section.fn)
    assert "load_rows" not in src
    assert "load_markup_pct" not in src
