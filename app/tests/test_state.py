"""Tests for DashboardState.load_rows — the app's sole DB read path."""

from app import validators
from app.models import PriceRow
from app.state import DashboardState


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
