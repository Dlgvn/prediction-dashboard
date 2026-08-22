"""App state: the sole database read and write path.

Per ARCHITECTURE.md Pattern 2, DashboardState is the only place in the app
that opens an rx.session() or touches the ORM. Components must read
DashboardState vars and never query the DB directly. This now covers both
reads (load_rows) and writes (cell edit, add-row-with-deferred-persist,
two-click delete) — DATA-01 through DATA-05.
"""

import reflex as rx

from app.models import PriceRow
from app.validators import validate_date, validate_numeric

# The 16 series columns on PriceRow, defined once so both the draft-row
# copy loop here and Plan 04-04's chart selector share a single source of
# truth for the column list.
SERIES_ATTRS = (
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
)


class DashboardState(rx.State):
    """Holds the price table for display, reflecting the DB as source of truth."""

    rows: list[PriceRow] = []
    draft_rows: list[PriceRow] = []

    # editing_key format: f"{row_date}:{column}"; "" means no cell is in
    # edit mode. The single draft row always has date == "", so its keys
    # look like ":hdan" / ":date" — unambiguous against persisted rows,
    # whose dates are non-empty ISO strings.
    editing_key: str = ""
    draft_value: str = ""

    # edit_error is a plain scalar, NOT a dict keyed by cell, because
    # editing_key already guarantees at most one cell is in edit mode at a
    # time (D-05). This sidesteps the unverified dict_var[key] / .contains()
    # Var-indexing syntax entirely — no dict Var is rendered.
    edit_error: str = ""

    pending_delete: str = ""

    @rx.var
    def can_add_row(self) -> bool:
        """False while an unsaved draft exists (D-06b)."""
        return len(self.draft_rows) == 0

    def load_rows(self) -> None:
        """Re-read all PriceRow records from SQLite, ordered ascending by date.

        Assigns (does not append) to self.rows so repeated calls always match
        the current DB contents rather than drifting/accumulating.
        """
        with rx.session() as session:
            self.rows = session.exec(
                PriceRow.select().order_by(PriceRow.date)
            ).all()

    def start_edit(self, key: str, current: str) -> None:
        self.editing_key = key
        self.draft_value = current or ""
        self.edit_error = ""
        # Opening an editor disarms any pending delete.
        self.pending_delete = ""

    def update_draft(self, value: str) -> None:
        # Fires on every keystroke — never touch the DB or reload here.
        self.draft_value = value

    def cancel_edit(self) -> None:
        self.editing_key = ""
        self.draft_value = ""
        self.edit_error = ""

    def commit_edit(self) -> None:
        if self.editing_key == "":
            return

        row_date, column = self.editing_key.split(":", 1)

        if row_date == "":
            self._commit_draft_cell(column)
            return

        if column == "date":
            ok, value, error = validate_date(
                self.draft_value,
                [r.date for r in self.rows],
                own_original_date=row_date,
            )
            if not ok:
                self.edit_error = error
                return
        else:
            ok, value, error = validate_numeric(self.draft_value)
            if not ok:
                self.edit_error = error
                return

        with rx.session() as session:
            db_row = session.exec(
                PriceRow.select().where(PriceRow.date == row_date)
            ).first()
            if db_row is None:
                # Row was deleted concurrently; nothing to write.
                return
            setattr(db_row, column, value)
            session.add(db_row)
            session.commit()

        self.edit_error = ""
        self.editing_key = ""
        self.draft_value = ""
        self.load_rows()

    def _commit_draft_cell(self, column: str) -> None:
        if len(self.draft_rows) == 0:
            self.editing_key = ""
            return

        draft = self.draft_rows[0]

        if column != "date":
            ok, value, error = validate_numeric(self.draft_value)
            if not ok:
                self.edit_error = error
                return
            setattr(draft, column, value)
            # Whole-list assignment, not .append, so Reflex reliably
            # detects the mutation.
            self.draft_rows = [draft]
            self.editing_key = ""
            self.draft_value = ""
            self.edit_error = ""
            # D-06 forbids persisting a row that has no valid date.
            return

        ok, iso_date, error = validate_date(
            self.draft_value,
            [r.date for r in self.rows],
            own_original_date=None,
        )
        if not ok:
            self.edit_error = error
            return

        new_row_kwargs = {"date": iso_date}
        for attr in SERIES_ATTRS:
            new_row_kwargs[attr] = getattr(draft, attr)

        with rx.session() as session:
            session.add(PriceRow(**new_row_kwargs))
            session.commit()

        self.draft_rows = []
        self.editing_key = ""
        self.draft_value = ""
        self.edit_error = ""
        self.load_rows()

    def handle_key_down(self, key: str) -> None:
        if key == "Enter":
            self.commit_edit()
        elif key == "Escape":
            self.cancel_edit()

    def add_row(self) -> None:
        if len(self.draft_rows) > 0:
            return
        self.draft_rows = [PriceRow(date="")]
        self.editing_key = ""
        self.edit_error = ""

    def request_delete(self, row_date: str) -> None:
        if self.pending_delete == row_date:
            with rx.session() as session:
                db_row = session.exec(
                    PriceRow.select().where(PriceRow.date == row_date)
                ).first()
                if db_row is not None:
                    session.delete(db_row)
                    session.commit()
            self.pending_delete = ""
            self.load_rows()
        else:
            self.pending_delete = row_date

    def cancel_pending_delete(self) -> None:
        self.pending_delete = ""
