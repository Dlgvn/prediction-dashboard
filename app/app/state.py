"""App state: the sole database read path (Phase 1 scope is read-only).

Per ARCHITECTURE.md Pattern 2, DashboardState is the only place in the app
that opens an rx.session() or touches the ORM. Components must read
DashboardState vars and never query the DB directly.

No write path (add_row/delete_row) exists yet — that is Phase 4 (DATA-01
through DATA-05) scope.
"""

import reflex as rx

from app.models import PriceRow


class DashboardState(rx.State):
    """Holds the price table for display, reflecting the DB as source of truth."""

    rows: list[PriceRow] = []

    def load_rows(self) -> None:
        """Re-read all PriceRow records from SQLite, ordered ascending by date.

        Assigns (does not append) to self.rows so repeated calls always match
        the current DB contents rather than drifting/accumulating.
        """
        with rx.session() as session:
            self.rows = session.exec(
                PriceRow.select().order_by(PriceRow.date)
            ).all()
