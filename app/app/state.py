"""App state: the sole database read and write path.

Per ARCHITECTURE.md Pattern 2, DashboardState is the only place in the app
that opens an rx.session() or touches the ORM. Components must read
DashboardState vars and never query the DB directly. This now covers both
reads (load_rows) and writes (cell edit, add-row-with-deferred-persist,
two-click delete) — DATA-01 through DATA-05.
"""

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import reflex as rx

from app.forecasting import MAX_HORIZON, InsufficientHistoryError, forecast_all
from app.models import AppSetting, PriceRow
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

# Single source of truth for series display labels, shared by app.py's
# _COLUMNS (table headers) and the chart's Series selector. Order matches
# the historical _COLUMNS ordering so the dropdown matches table columns.
SERIES_LABELS: dict[str, str] = {
    "hdan": "HDAN",
    "ppan": "PPAN",
    "baltic_an": "Baltic AN",
    "ammonia": "Ammonia",
    "urea_black_sea": "Urea Black Sea",
    "urea_china": "Urea China",
    "natural_gas_jkm": "NG JKM",
    "natural_gas_henry_hub": "NG Henry Hub",
    "natural_gas_uk": "NG UK",
    "natural_gas_netherlands": "NG Netherlands",
    "corn_us": "Corn US",
    "corn_china": "Corn China",
    "diesel_usd_ton": "Diesel USD/t",
    "urals": "Urals",
    "fx_rate": "FX Rate",
    "brent": "Brent",
}

LABEL_TO_ATTR: dict[str, str] = {label: attr for attr, label in SERIES_LABELS.items()}

# Phase 5's forecast-series selector triad (D-03/Pattern 3) — independent of
# SERIES_LABELS/LABEL_TO_ATTR above, scoped to forecast_all()'s exact 5
# output keys, in that order.
FORECAST_SERIES_LABELS: dict[str, str] = {
    "hdan": "HDAN",
    "ppan": "PPAN",
    "diesel_usd_ton": "Diesel USD/t",
    "diesel_mnt": "Diesel MNT",
    "fx_rate": "FX Rate",
}

FORECAST_LABEL_TO_ATTR: dict[str, str] = {
    label: attr for attr, label in FORECAST_SERIES_LABELS.items()
}

# D-07: freshness "as of" dates apply only to independently-modeled series;
# diesel_mnt is derived (diesel_usd * fx * markup) and has no own date.
FRESHNESS_SERIES: tuple[str, ...] = ("hdan", "ppan", "diesel_usd_ton", "fx_rate")


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

    selected_series: str = "hdan"

    # Phase 5 forecast state (FCST-01/EXPORT-01) — independent of the
    # historical-chart selector above (D-06: two separate chart sections).
    horizon_months: int = 3
    forecast_series: str = "hdan"
    markup_pct: float = 0.0
    forecast_error: str = ""
    export_message: str = ""
    export_failed: bool = False

    @rx.var
    def can_add_row(self) -> bool:
        """False while an unsaved draft exists (D-06b)."""
        return len(self.draft_rows) == 0

    @rx.var
    def series_label(self) -> str:
        """Human label for selected_series; rx.select's value prop needs the label."""
        return SERIES_LABELS[self.selected_series]

    @rx.var
    def historical_chart_figure(self) -> go.Figure:
        """Actuals-only line chart for the currently selected series (VIS-01).

        Built entirely from self.rows/self.selected_series (in-memory) so
        switching series never touches the database — RESEARCH Pattern 4.
        """
        attr = self.selected_series
        dates = []
        values = []
        for row in self.rows:
            value = getattr(row, attr)
            if value is not None:
                dates.append(row.date)
                values.append(value)

        if not values:
            figure = go.Figure()
            figure.update_layout(
                xaxis_title="Date",
                yaxis_title=SERIES_LABELS[attr],
                showlegend=False,
                margin=dict(l=40, r=16, t=16, b=40),
                annotations=[
                    dict(
                        text="No data for this series yet.",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                    )
                ],
            )
            return figure

        figure = px.line(x=dates, y=values, markers=True)
        figure.update_layout(
            xaxis_title="Date",
            yaxis_title=SERIES_LABELS[attr],
            showlegend=False,
            margin=dict(l=40, r=16, t=16, b=40),
        )
        figure.update_traces(line_color="#697177")
        return figure

    @rx.var
    def forecast_results(self) -> dict:
        """Single computed var wrapping forecast_all() (Pitfall 2 guard —
        exactly one call site app-wide). Empty-result shape is always the
        5-key P-02 shape with empty lists, so downstream chart/table vars
        (plan 05-02) can index keys unconditionally without branching on
        error state.
        """
        empty_result = {key: [] for key in FORECAST_SERIES_LABELS}

        if not self.rows:
            self.forecast_error = (
                "Not enough historical data to forecast yet. Add at least "
                "one month of actuals above."
            )
            return empty_result

        history = self._history_df()
        try:
            result = forecast_all(history, self.horizon_months, self.markup_pct)
        except (InsufficientHistoryError, ValueError):
            self.forecast_error = (
                "Not enough historical data to forecast yet. Add at least "
                "one month of actuals above."
            )
            return empty_result

        self.forecast_error = ""
        return result

    def select_series(self, label: str) -> None:
        """Handle the Series dropdown; ignores unknown labels (T-04-12)."""
        attr = LABEL_TO_ATTR.get(label)
        if attr is not None:
            self.selected_series = attr

    def set_horizon(self, value: list[int]) -> None:
        """on_change fires on every drag tick per D-02; value arrives as a
        single-element list (Radix Slider's array-value convention).
        Clamped server-side per T-05-01 — never trust the raw client
        payload, even though Radix also enforces min/max client-side.
        """
        if not value:
            return
        self.horizon_months = max(1, min(MAX_HORIZON, int(value[0])))

    def select_forecast_series(self, label: str) -> None:
        """Handle the forecast-series dropdown; ignores unknown labels."""
        attr = FORECAST_LABEL_TO_ATTR.get(label)
        if attr is not None:
            self.forecast_series = attr

    @rx.var
    def forecast_series_label(self) -> str:
        """Human label for forecast_series; rx.select's value prop needs the label."""
        return FORECAST_SERIES_LABELS[self.forecast_series]

    def load_markup_pct(self) -> None:
        """Read the live markup_pct AppSetting (D-04). Confirmed seeded by
        Phase 1 (id=1, value=0.0); the None branch is defence-in-depth
        only, not a seeding path — do NOT insert a row here.
        """
        with rx.session() as session:
            setting = session.exec(
                AppSetting.select().where(AppSetting.key == "markup_pct")
            ).first()
            self.markup_pct = setting.value if setting is not None else 0.0

    def _history_df(self) -> pd.DataFrame:
        """Build the plain date-indexed DataFrame forecast_all()'s caller
        contract requires — no ORM object crosses into forecasting.py.
        """
        if not self.rows:
            return pd.DataFrame()

        records = [
            {attr: getattr(row, attr) for attr in SERIES_ATTRS} for row in self.rows
        ]
        index = pd.DatetimeIndex(pd.to_datetime([row.date for row in self.rows]))
        frame = pd.DataFrame(records, index=index)
        return frame.sort_index()

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
