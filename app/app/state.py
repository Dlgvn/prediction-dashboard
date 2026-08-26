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

from app.csv_import import parse_import_csv
from app.forecasting import (
    MAX_HORIZON,
    MODEL_INFO,
    InsufficientHistoryError,
    forecast_all,
)
from app.models import AppSetting, PriceRow
from app.theme import (
    ARROW_DOWN,
    ARROW_FLAT,
    ARROW_UP,
    NUMBER_FORMAT,
    PLOTLY_HOVER_NUMBER,
    tokens,
)
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

# FCST-09: month-abbreviation lookup for YoY captions, avoiding a datetime
# import just to format "Jul 2025" (D-02 calendar-month comparator caption).
MONTH_ABBR = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

# D-01: exactly four forecast-summary cards, in display order. Deliberately
# excludes diesel_usd_ton from FORECAST_SERIES_LABELS' five keys because the
# user tracks the MNT purchasing price (diesel_mnt), not the raw USD/ton
# input.
SUMMARY_CARD_SERIES: tuple[str, ...] = ("hdan", "ppan", "diesel_mnt", "fx_rate")

# Derived programmatically (not a hand-written 15-entry literal) so headers
# and forecast_table_rows' composite keys can never drift apart (FCST-06).
FORECAST_TABLE_COLUMNS: list[tuple[str, str]] = [
    (f"{series_key}_{scenario}", f"{label} {scenario}")
    for series_key, label in FORECAST_SERIES_LABELS.items()
    for scenario in ("base", "bull", "bear")
]

# D-01 (Phase 7): the Data Entry table's default display window is the most
# recent 12 rows. Data is monthly cadence, so 12 rows == 12 months.
TABLE_WINDOW_ROWS: int = 12


class DashboardState(rx.State):
    """Holds the price table for display, reflecting the DB as source of truth."""

    rows: list[PriceRow] = []

    # editing_key format: f"{row_date}:{column}"; "" means no cell is in
    # edit mode. Only persisted rows are ever edited this way, so row_date
    # is always a non-empty ISO date string.
    editing_key: str = ""
    draft_value: str = ""

    # edit_error is a plain scalar, NOT a dict keyed by cell, because
    # editing_key already guarantees at most one cell is in edit mode at a
    # time (D-05). This sidesteps the unverified dict_var[key] / .contains()
    # Var-indexing syntax entirely — no dict Var is rendered.
    edit_error: str = ""

    pending_delete: str = ""

    quick_add_values: dict[str, str] = {}
    quick_add_error: str = ""

    # D-01/D-02 (Phase 7): controls the Data Entry table's rendered window
    # ONLY (see visible_rows below) — never affects self.rows, which stays
    # the full-history source of truth for every other computed var.
    show_all_history: bool = False

    selected_series: str = "hdan"

    # Phase 5 forecast state (FCST-01/EXPORT-01) — independent of the
    # historical-chart selector above (D-06: two separate chart sections).
    horizon_months: int = 3
    forecast_series: str = "hdan"
    markup_pct: float = 0.0
    forecast_error: str = ""
    # Non-fatal data-quality signal from forecast_all's `warning` key (e.g.
    # PPAN's stale-feature-anchor check) -- distinct from forecast_error,
    # which means "no forecast was produced at all". A forecast can be
    # valid AND carry a warning simultaneously.
    forecast_warning: str = ""
    export_message: str = ""
    export_failed: bool = False
    # Backend-only var (leading underscore, EXPORT-02 follow-up): set by
    # _export_bytes when forecast computation raises an *unexpected*
    # exception (not the already-handled InsufficientHistoryError/ValueError
    # "no history yet" case, which forecast_results resolves internally to
    # an empty-list result with no exception at all). Read by
    # export_to_excel immediately afterward to decide whether to surface a
    # partial-failure banner without blocking the actuals-only download.
    _last_export_forecast_failed: bool = False

    # Phase 10 (CSV bulk import) state — deliberately NOT reusing edit_error
    # (PITFALLS.md): edit_error is a single scalar sized for one in-edit
    # cell, while a multi-row import needs counts plus a stage, not one
    # message.
    import_stage: str = "idle"          # "idle" | "preview" | "error" | "done"
    # D-03 audit (15-CONTEXT.md/Plan 15-01): import_error is only ever set by
    # handle_csv_upload's explicit failure branches and cleared only by
    # _reset_import() (called from handle_csv_upload's start, cancel_import,
    # dismiss_import) — all single-shot, user-initiated actions with no
    # analogue of start_edit's "open a different thing mid-flight" trigger.
    # No clobber-race bug exists here; no fix needed.
    import_error: str = ""              # D-06 malformed/rejected-file message only
    import_filename: str = ""           # for the "Parsing {filename}…" copy
    import_added_count: int = 0         # rows that WILL be added (preview) / WERE added (done)
    import_duplicate_count: int = 0
    import_invalid_count: int = 0
    # Backend-only var (leading underscore): parsed rows are never
    # serialized to the frontend, per STACK.md's warning against putting a
    # whole parsed CSV into reactive state.
    _staged_import_rows: list[dict] = []

    # Phase 11 (background/theme fix): backend-readable, localStorage-
    # persisted theme mode (THEME-01/THEME-02/THEME-03). Deliberately uses
    # its OWN localStorage key ("pd_theme_mode"), NOT Reflex's built-in
    # "theme" key, so the two mechanisms never fight over one value's
    # format. Both keys must always move together via the toggle's
    # two-item on_click chain in app.py (Plan 11-03) — "simplifying" by
    # deleting one reintroduces the Radix-chrome-vs-custom-surface
    # mismatch bug documented in 11-RESEARCH.md Pattern 2.
    theme_mode: str = rx.LocalStorage("light", name="pd_theme_mode")

    # Phase 14 (tab/nav bar): which of the 3 tab groups (D-01) is currently
    # rendered. Deliberately a plain var, NOT persisted like theme_mode
    # above — D-03 is explicit that "Summary" is always the landing tab on
    # a fresh page load, so this must reset every reload.
    active_section: str = "summary"

    def toggle_theme_mode(self) -> None:
        """Flip theme_mode between "light" and "dark" (THEME-02).

        Any unrecognized stored value resolves to "light" on the next
        toggle (D-02: light is always the safe default).
        """
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"

    # PITFALLS.md Pitfall 3: set_active_section below must do exactly two
    # things — assign active_section and scroll to top — and NOTHING else.
    # It must never touch any field of the in-progress edit/delete/draft-
    # row/CSV-import state machine (the scalar and list vars declared
    # above this point), and it must never re-trigger the on_mount data
    # load (that fires exactly once, from the root container).
    def set_active_section(self, value: str):
        """Switch the active tab and scroll to top (D-02).

        Uses rx.call_script rather than rx.scroll_to: the installed
        Reflex version's rx.scroll_to requires a specific elem_id target,
        whereas a tab switch needs an unconditional scroll to the very
        top of the page regardless of which section is now showing.
        """
        self.active_section = value
        return rx.call_script("window.scrollTo({top: 0, behavior: 'instant'})")

    @rx.var
    def page_bg(self) -> str:
        return tokens(self.theme_mode)["PAGE_BG"]

    @rx.var
    def surface(self) -> str:
        return tokens(self.theme_mode)["SURFACE"]

    @rx.var
    def muted_text(self) -> str:
        return tokens(self.theme_mode)["MUTED_TEXT"]

    @rx.var
    def destructive_color(self) -> str:
        return tokens(self.theme_mode)["DESTRUCTIVE"]

    @rx.var
    def up_color(self) -> str:
        return tokens(self.theme_mode)["UP"]

    @rx.var
    def down_color(self) -> str:
        return tokens(self.theme_mode)["DOWN"]

    @rx.var
    def card_border(self) -> str:
        return f"1px solid {tokens(self.theme_mode)['BORDER']}"

    @rx.var
    def accent_color(self) -> str:
        return tokens(self.theme_mode)["ACCENT"]

    @rx.var
    def border_color(self) -> str:
        """Bare hex border color (distinct from card_border's "1px solid
        ..." shorthand) — the tab bar composes both 1px and 2px rules from
        the bare hex.
        """
        return tokens(self.theme_mode)["BORDER"]

    @rx.var
    def visible_rows(self) -> list[PriceRow]:
        """Display-only windowed slice of self.rows for the Data Entry table.

        Per PITFALLS.md Pitfall 1 (self.rows is overloaded): this is a pure
        read that never assigns to self.rows and never calls load_rows.
        self.rows remains the full-history source for forecast_results,
        _history_df, historical_chart_figure, freshness_chips,
        summary_cards, and _export_bytes — none of those read this var.
        """
        if self.show_all_history:
            return self.rows
        return self.rows[-TABLE_WINDOW_ROWS:]

    @rx.var
    def history_window_caption(self) -> str:
        """Muted caption describing the current table window (07-UI-SPEC.md
        Copywriting Contract, verbatim strings).
        """
        if self.show_all_history:
            return f"Showing full history ({len(self.rows)} rows)."
        return f"Showing the most recent {TABLE_WINDOW_ROWS} months."

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
        t = tokens(self.theme_mode)
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
                legend=dict(orientation="h", y=-0.55, yanchor="top", x=0.5, xanchor="center"),
                margin=dict(l=40, r=16, t=16, b=140),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(tickformat=NUMBER_FORMAT),
                font=dict(size=14, color=t["MUTED_TEXT"]),
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
            legend=dict(orientation="h", y=-0.55, yanchor="top", x=0.5, xanchor="center"),
            margin=dict(l=40, r=16, t=16, b=140),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(tickformat=NUMBER_FORMAT),
            font=dict(size=14, color=t["MUTED_TEXT"]),
        )
        figure.update_traces(
            line_color=t["NEUTRAL_LINE"],
            hovertemplate=f"%{{x}}<br>{PLOTLY_HOVER_NUMBER}<extra></extra>",
        )
        return figure

    def _forecast_export_records(self) -> list[dict]:
        """Build Forecast-sheet row dicts from the already-computed
        forecast_table_rows var (EXPORT-02, D-02). Deliberately reads
        self.forecast_table_rows rather than calling forecast_all or
        re-deriving from forecast_results — reusing the same values the
        dashboard renders is what keeps export/screen parity structural
        rather than coincidental.
        """
        records: list[dict] = []
        for row in self.forecast_table_rows:
            record: dict = {"Month": int(row["month"])}
            for key, label in FORECAST_TABLE_COLUMNS:
                raw = row[key]
                record[label] = float(raw.replace(",", "")) if raw else None
            records.append(record)
        return records

    def _export_bytes(self) -> bytes:
        """Build the .xlsx bytes for the two-sheet export workbook.

        EXPORT-02 (Phase 9, D-01/D-02/D-03) deliberately supersedes the
        prior D-08 actuals-only behavior: the workbook now carries a second
        "Forecast" sheet capturing base/bull/bear values for the horizon
        selected at the moment Export was clicked, built by reusing
        forecast_table_rows rather than adding a second forecast_all call
        site. Plain method (not an event handler) so it's unit-testable
        without Reflex's event machinery. Never writes to disk — BytesIO
        buffer only.
        """
        records = []
        for row in self.rows:
            # row.model_dump() misbehaves on this SQLModel/rx.Model instance
            # (returns non-dict values for some fields) — build the record
            # manually from date + SERIES_ATTRS, mirroring the proven
            # pattern used elsewhere in this file rather than trusting .model_dump().
            record = {"date": row.date}
            for attr in SERIES_ATTRS:
                record[attr] = getattr(row, attr)
            records.append(record)

        actuals_df = pd.DataFrame(records, columns=["date", *SERIES_ATTRS])

        # forecast_table_rows (via forecast_results) already converts the
        # legitimate "not enough history yet" case into an empty list with
        # no exception raised (InsufficientHistoryError/ValueError are
        # caught there). So if _forecast_export_records DOES raise here,
        # it's a genuine unexpected failure (e.g. a statsmodels/VAR bug),
        # not the routine empty-forecast case -- track that distinction so
        # export_to_excel can surface it instead of silently swallowing it.
        try:
            forecast_records = self._forecast_export_records()
            self._last_export_forecast_failed = False
        except Exception:
            forecast_records = []
            self._last_export_forecast_failed = True

        forecast_columns = ["Month", *[label for _, label in FORECAST_TABLE_COLUMNS]]
        forecast_df = pd.DataFrame(forecast_records, columns=forecast_columns)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            actuals_df.to_excel(writer, sheet_name="Actuals", index=False)
            forecast_df.to_excel(writer, sheet_name="Forecast", index=False)
        buffer.seek(0)
        return buffer.getvalue()

    def export_to_excel(self):
        """Event handler for the export button (EXPORT-01)."""
        try:
            data = self._export_bytes()
        except Exception:
            self.export_failed = True
            self.export_message = (
                "Export failed. Check that the app has write access and try again."
            )
            return None

        if self._last_export_forecast_failed:
            self.export_failed = True
            self.export_message = (
                "Downloaded prediction_dashboard_prices.xlsx, but the "
                "Forecast sheet is empty because forecast computation "
                "failed unexpectedly. Actuals data was exported."
            )
        else:
            self.export_failed = False
            self.export_message = "Downloaded prediction_dashboard_prices.xlsx"
        return rx.download(
            data=data, filename="prediction_dashboard_prices.xlsx"
        )

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
            self.forecast_warning = ""
            return empty_result

        history = self._history_df()
        try:
            result = forecast_all(history, self.horizon_months, self.markup_pct)
        except (InsufficientHistoryError, ValueError):
            self.forecast_error = (
                "Not enough historical data to forecast yet. Add at least "
                "one month of actuals above."
            )
            self.forecast_warning = ""
            return empty_result

        self.forecast_error = ""
        self.forecast_warning = result.get("warning", "")
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

    @rx.var
    def freshness_chips(self) -> list[dict[str, str]]:
        """Four ordered as-of-date chips (DATA-06/D-07), pure over self.rows.

        Returns a LIST of flat dicts (not a dict[str, str]) so app.py can
        render it with rx.foreach without dict-Var indexing.
        """
        chips: list[dict[str, str]] = []
        for attr in FRESHNESS_SERIES:
            dates = [
                row.date
                for row in self.rows
                if getattr(row, attr) is not None
            ]
            if dates:
                chips.append(
                    {
                        "label": SERIES_LABELS[attr],
                        "date": max(dates),
                        "has_data": "yes",
                    }
                )
            else:
                chips.append(
                    {
                        "label": SERIES_LABELS[attr],
                        "date": "",
                        "has_data": "no",
                    }
                )
        return chips

    @rx.var
    def summary_cards(self) -> list[dict[str, str]]:
        """Four horizon-reactive forecast-summary cards (D-10..D-13).

        Returns a LIST of flat ALL-STRING dicts, one per SUMMARY_CARD_SERIES
        entry in order, always length 4 — mirrors freshness_chips' shape
        discipline so app.py can rx.foreach without dict-Var indexing.
        Reads self.forecast_results only; never re-invokes forecast_all
        (Pitfall 2 guard, T-06-02).
        """
        results = self.forecast_results
        cards: list[dict[str, str]] = []

        for key in SUMMARY_CARD_SERIES:
            label = FORECAST_SERIES_LABELS[key]
            series = results.get(key, [])

            # D-01/D-04: full-history high/low + YoY, computed before the
            # no-data early return so both branches carry the same keys
            # (Phase 6 flat all-string dict discipline). Reuses ONE
            # self._actual_series_for(key) call (never re-scans self.rows,
            # never reads visible_rows) for both high/low and YoY.
            actual_pairs = self._actual_series_for(key)
            actual_values = [v for _, v in actual_pairs]
            hilo_label = "All-time high/low"
            hilo_text = (
                f"{max(actual_values):{NUMBER_FORMAT}} / {min(actual_values):{NUMBER_FORMAT}}"
                if actual_values
                else ""
            )

            # FCST-09/D-02: calendar-month match (YYYY-MM prefix), never a
            # 12-row offset — history gaps or non-day-01 dates must still
            # compare the correct prior-year month.
            yoy_label = "YoY"
            yoy_text = ""
            yoy_arrow = ""
            yoy_direction = "flat"
            if actual_pairs:
                latest_date, latest_value = actual_pairs[-1]
                year, month = int(latest_date[:4]), int(latest_date[5:7])
                target_month = f"{year - 1:04d}-{month:02d}"
                prior_value = None
                for pair_date, pair_value in actual_pairs:
                    if pair_date[:7] == target_month:
                        prior_value = pair_value
                        break
                if prior_value is not None and prior_value != 0:
                    pct = (latest_value - prior_value) / prior_value * 100
                    # D-03: yoy_arrow stays "" (not ARROW_FLAT) whenever not
                    # computable so app.py's "arrow + text" concatenation
                    # never renders a stray glyph next to empty text; here
                    # it IS computable, so mirror the existing delta
                    # three-way branch exactly.
                    if pct > 0:
                        yoy_arrow, yoy_direction = ARROW_UP, "up"
                    elif pct < 0:
                        yoy_arrow, yoy_direction = ARROW_DOWN, "down"
                    else:
                        yoy_arrow, yoy_direction = ARROW_FLAT, "flat"
                    yoy_text = f"{abs(pct):.1f}% vs. {MONTH_ABBR[month - 1]} {year - 1}"

            # VIS-05: model provenance, computed before the no-data early
            # return so both branches carry the same keys (model selection
            # is frozen, not data-dependent). Every value flows from
            # MODEL_INFO — never hand-type a model name or percentage here.
            model_label = "Model"
            model_name, model_mape = MODEL_INFO[key]
            if model_mape is None:
                model_text = model_name
            else:
                model_text = f"{model_name} · {model_mape:.1f}% typical error"

            if not series:
                cards.append(
                    {
                        "series_key": key,
                        "label": label,
                        "has_data": "no",
                        "base": "",
                        "range_text": "",
                        "range_label": "Expected range",
                        "arrow": ARROW_FLAT,
                        "direction": "flat",
                        "delta_text": "",
                        "caption": "vs. latest actual",
                        "hilo_label": hilo_label,
                        "hilo_text": hilo_text,
                        "yoy_label": yoy_label,
                        "yoy_text": "",
                        "yoy_arrow": "",
                        "yoy_direction": "flat",
                        "model_label": model_label,
                        "model_text": model_text,
                        "no_data_text": "Add pricing data to see a forecast",
                    }
                )
                continue

            # T-06-01: index the LAST entry rather than assuming length
            # equals horizon_months, so a client-driven horizon can never
            # index out of range.
            entry = series[-1]
            base_value = entry["base"]
            bull_value = entry["bull"]
            bear_value = entry["bear"]

            latest_actual = self._latest_actual_for(key)

            if latest_actual is None or latest_actual == 0:
                arrow = ARROW_FLAT
                direction = "flat"
                delta_text = ""
            elif base_value > latest_actual:
                arrow = ARROW_UP
                direction = "up"
                delta_text = f"{abs((base_value - latest_actual) / latest_actual * 100):.1f}%"
            elif base_value < latest_actual:
                arrow = ARROW_DOWN
                direction = "down"
                delta_text = f"{abs((base_value - latest_actual) / latest_actual * 100):.1f}%"
            else:
                arrow = ARROW_FLAT
                direction = "flat"
                delta_text = ""

            cards.append(
                {
                    "series_key": key,
                    "label": label,
                    "has_data": "yes",
                    "base": f"{base_value:{NUMBER_FORMAT}}",
                    "range_text": f"{bear_value:{NUMBER_FORMAT}} – {bull_value:{NUMBER_FORMAT}}",
                    "range_label": "Expected range",
                    "arrow": arrow,
                    "direction": direction,
                    "delta_text": delta_text,
                    "caption": "vs. latest actual",
                    "hilo_label": hilo_label,
                    "hilo_text": hilo_text,
                    "yoy_label": yoy_label,
                    "yoy_text": yoy_text,
                    "yoy_arrow": yoy_arrow,
                    "yoy_direction": yoy_direction,
                    "model_label": model_label,
                    "model_text": model_text,
                    "no_data_text": "Add pricing data to see a forecast",
                }
            )

        return cards

    def _actual_series_for(self, key: str) -> list[tuple[str, float]]:
        """Full-history (date, value) pairs for a series key, skipping None.

        This is the SOLE derivation site for diesel_mnt (PITFALLS.md
        Pitfall 6): diesel_usd_ton * fx_rate * (1 + markup_pct/100). Always
        iterates self.rows (never visible_rows) in existing date-ascending
        order, so every caller (_latest_actual_for, forecast_chart_figure,
        summary_cards high/low and YoY) shares one formula and one
        full-history read.
        """
        pairs: list[tuple[str, float]] = []
        for row in self.rows:
            if key == "diesel_mnt":
                if row.diesel_usd_ton is None or row.fx_rate is None:
                    continue
                value = row.diesel_usd_ton * row.fx_rate * (1 + self.markup_pct / 100.0)
            else:
                value = getattr(row, key)
                if value is None:
                    continue
            pairs.append((row.date, value))
        return pairs

    def _latest_actual_for(self, key: str) -> float | None:
        """Last non-None actual value for a SUMMARY_CARD_SERIES key."""
        series = self._actual_series_for(key)
        return series[-1][1] if series else None

    @rx.var
    def forecast_chart_figure(self) -> go.Figure:
        """Fan chart for the selected forecast series (VIS-02/D-04/D-05).

        Reads self.forecast_results (never re-invokes forecast_all -- Pitfall
        2 guard) and builds a single continuous date axis: 12 trailing
        historical months feeding into a shaded bull/bear band with a solid
        base line drawn on top.
        """
        t = tokens(self.theme_mode)
        attr = self.forecast_series
        results = self.forecast_results
        series = results.get(attr, [])

        # Historical segment (D-05): last 12 non-null observations for the
        # selected series, diesel_mnt derived per diesel_mnt_forecast's
        # exact multiplier convention.
        hist_pairs = self._actual_series_for(attr)[-12:]
        hist_dates: list = [d for d, _ in hist_pairs]
        hist_values: list = [v for _, v in hist_pairs]

        if not series or not hist_dates:
            figure = go.Figure()
            figure.update_layout(
                xaxis_title="Month",
                yaxis_title=FORECAST_SERIES_LABELS[attr],
                showlegend=False,
                legend=dict(orientation="h", y=-0.55, yanchor="top", x=0.5, xanchor="center"),
                margin=dict(l=40, r=16, t=16, b=140),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(tickformat=NUMBER_FORMAT),
                font=dict(size=14, color=t["MUTED_TEXT"]),
                annotations=[
                    dict(
                        text="No forecast available for this series yet.",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                    )
                ],
            )
            return figure

        hist_dates_dt = pd.to_datetime(hist_dates).tolist()
        last_hist_date = hist_dates_dt[-1]
        last_hist_value = hist_values[-1]

        fc_dates = [
            last_hist_date + pd.DateOffset(months=entry["month"]) for entry in series
        ]
        fc_base = [entry["base"] for entry in series]
        fc_bull = [entry["bull"] for entry in series]
        fc_bear = [entry["bear"] for entry in series]

        # Bridge the visual seam: prepend the last historical point to each
        # forecast trace so the band/base line starts at the last actual.
        bridge_dates = [last_hist_date, *fc_dates]
        bear_y = [last_hist_value, *fc_bear]
        bull_y = [last_hist_value, *fc_bull]
        base_y = [last_hist_value, *fc_base]

        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=hist_dates_dt,
                y=hist_values,
                mode="lines",
                line=dict(color=t["NEUTRAL_LINE"], dash="solid"),
                name="Historical",
                hovertemplate=f"%{{x}}<br>{PLOTLY_HOVER_NUMBER}<extra>Historical</extra>",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=bridge_dates,
                y=bear_y,
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                name="Bear",
                hoverinfo="skip",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=bridge_dates,
                y=bull_y,
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=t["ACCENT_FILL"],
                name="Expected range",
                hovertemplate=f"%{{x}}<br>{PLOTLY_HOVER_NUMBER}<extra>Expected range</extra>",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=bridge_dates,
                y=base_y,
                mode="lines",
                line=dict(color=t["ACCENT"], width=2, dash="dash"),
                name="Base forecast",
                hovertemplate=f"%{{x}}<br>{PLOTLY_HOVER_NUMBER}<extra>Base forecast</extra>",
            )
        )
        figure.add_vline(
            x=last_hist_date,
            line=dict(color=t["BORDER"], dash="dash"),
            annotation_text="Forecast start",
            annotation_position="top left",
        )
        figure.update_layout(
            xaxis_title="Month",
            yaxis_title=FORECAST_SERIES_LABELS[attr],
            margin=dict(l=40, r=16, t=16, b=140),
            legend=dict(orientation="h", y=-0.55, yanchor="top", x=0.5, xanchor="center"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(tickformat=NUMBER_FORMAT),
            font=dict(size=14, color=t["MUTED_TEXT"]),
            hovermode="x unified",
        )
        return figure

    @rx.var
    def forecast_table_rows(self) -> list[dict[str, str]]:
        """Month-major all-series forecast table data (FCST-06/VIS-03).

        Transposes self.forecast_results (series-major) into one flat row
        per horizon month, carrying all five series' base/bull/bear values
        simultaneously, preformatted to strings.
        """
        results = self.forecast_results
        if not any(results.get(key) for key in FORECAST_SERIES_LABELS):
            return []

        rows: list[dict[str, str]] = []
        for month in range(1, self.horizon_months + 1):
            row: dict[str, str] = {"month": str(month)}
            for series_key in FORECAST_SERIES_LABELS:
                series = results.get(series_key, [])
                entry = series[month - 1] if month - 1 < len(series) else None
                for scenario in ("base", "bull", "bear"):
                    value = entry[scenario] if entry is not None else None
                    row[f"{series_key}_{scenario}"] = (
                        f"{value:,.2f}" if value is not None else ""
                    )
            rows.append(row)
        return rows

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

    # State-transition table (15-CONTEXT.md D-02) — for each trigger, what
    # happens to editing_key / draft_value / edit_error / pending_delete:
    #
    # | Trigger                        | editing_key      | draft_value | edit_error | pending_delete |
    # |---------------------------------|-------------------|-------------|------------|----------------|
    # | Normal cell edit (start_edit,   | -> key            | -> current  | -> ""      | -> ""          |
    # | no pending error elsewhere)     |                   |             |            |                |
    # | Escape (cancel_edit)            | -> "" (always)    | -> ""       | -> ""      | unchanged      |
    # | Blur/commit success             | -> ""              | -> ""       | -> ""      | unchanged      |
    # | Blur/commit failure             | UNCHANGED (stays  | unchanged   | -> error   | unchanged      |
    # |                                  | open on failing   |             | message    |                |
    # |                                  | cell)              |             |            |                |
    # | Window toggle                    | -> "" (always,    | -> ""       | -> ""      | -> ""          |
    # | (toggle_show_all_history)       | via cancel_edit)  |             |            |                |
    # | Delete-arm (request_delete)     | unchanged          | unchanged   | unchanged  | -> row_date    |
    #
    # The row above this comment ("Blur/commit failure") is why start_edit
    # cannot unconditionally clear edit_error: a failure leaves editing_key
    # pointing at the failing cell so its error can render, but a
    # near-simultaneous click that opens a DIFFERENT cell would otherwise
    # wipe that still-unrendered error before the user ever sees it. Guard
    # below: ignore the click-away while a real error is pending on a
    # different cell; re-opening the SAME errored cell (retry) or opening
    # any cell when no error is pending both behave exactly as before.
    def start_edit(self, key: str, current: str | float | None) -> None:
        if self.edit_error != "" and self.editing_key != "" and key != self.editing_key:
            return
        self.editing_key = key
        # `current` arrives from a numeric cell as a raw JS number, not a
        # string — Reflex's Var-level string casting (.to_string()/f-string
        # interpolation) either JSON-quotes it or is a no-op depending on
        # the value's underlying type, so coerce here instead of trying to
        # force a particular Var cast in app.py's click handler.
        if current is None or current == "":
            self.draft_value = ""
        else:
            self.draft_value = str(current)
        self.edit_error = ""
        # Opening an editor disarms any pending delete.
        self.pending_delete = ""

    def update_draft(self, value: str) -> None:
        # Fires on every keystroke — never touch the DB or reload here.
        self.draft_value = value

    def update_quick_add_field(self, attr: str, value: str) -> None:
        # Whole-dict reassignment, not in-place mutation, so Reflex reliably
        # detects the change.
        self.quick_add_values = {**self.quick_add_values, attr: value}

    def submit_quick_add(self) -> None:
        raw_date = self.quick_add_values.get("date", "")
        ok, iso_date, error = validate_date(
            raw_date, [r.date for r in self.rows], own_original_date=None
        )
        if not ok:
            self.quick_add_error = error
            return

        parsed_values: dict[str, float | None] = {}
        for attr in SERIES_ATTRS:
            raw = self.quick_add_values.get(attr, "")
            ok, value, error = validate_numeric(raw)
            if not ok:
                self.quick_add_error = f"{SERIES_LABELS[attr]}: {error}"
                return
            parsed_values[attr] = value

        with rx.session() as session:
            session.add(PriceRow(date=iso_date, **parsed_values))
            session.commit()

        self.quick_add_values = {}
        self.quick_add_error = ""
        self.load_rows()

    def cancel_edit(self) -> None:
        self.editing_key = ""
        self.draft_value = ""
        self.edit_error = ""

    def toggle_show_all_history(self, value: bool) -> None:
        """rx.switch's on_change handler (D-02/D-03, Phase 7).

        Assigns the boolean emitted by the switch directly — the switch is
        the source of truth for the new value, not a negation of the prior
        field, so this stays correct even if events ever coalesce.

        Per D-03, also cancels any in-progress cell edit and any armed
        two-click delete confirmation, since a row can leave the visible
        window mid-edit/mid-delete-arm. The quick-add form is intentionally
        left untouched — an in-progress unsaved entry is unrelated to
        windowing and must survive the toggle (PITFALLS.md). This is a pure
        in-memory re-slice; it never calls load_rows() or opens a DB
        session.
        """
        self.show_all_history = value
        self.cancel_edit()
        self.cancel_pending_delete()

    def commit_edit(self) -> None:
        if self.editing_key == "":
            return

        row_date, column = self.editing_key.split(":", 1)

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

    def handle_key_down(self, key: str) -> None:
        if key == "Enter":
            self.commit_edit()
        elif key == "Escape":
            self.cancel_edit()

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

    # -------------------------------------------------------------------
    # CSV bulk import (IMPORT-01, IMPORT-02, Phase 10)
    # -------------------------------------------------------------------

    @rx.var
    def import_added_text(self) -> str:
        return f"{self.import_added_count} rows will be added"

    @rx.var
    def import_duplicate_text(self) -> str:
        return f"{self.import_duplicate_count} rows skipped (duplicate date)"

    @rx.var
    def import_invalid_text(self) -> str:
        return f"{self.import_invalid_count} rows skipped (invalid value)"

    @rx.var
    def import_result_text(self) -> str:
        return f"Import complete: {self.import_added_count} rows added."

    @rx.var
    def can_confirm_import(self) -> bool:
        return self.import_stage == "preview" and self.import_added_count > 0

    def _reset_import(self) -> None:
        self.import_stage = "idle"
        self.import_error = ""
        self.import_filename = ""
        self.import_added_count = 0
        self.import_duplicate_count = 0
        self.import_invalid_count = 0
        self._staged_import_rows = []

    @rx.event
    async def handle_csv_upload(self, files: list[rx.UploadFile]) -> None:
        self._reset_import()

        if not files:
            return

        # rx.upload is configured max_files=1 (plan 10-03); only the first
        # file is relevant.
        file = files[0]
        self.import_filename = getattr(file, "name", None) or getattr(
            file, "filename", ""
        )

        try:
            contents = await file.read()
            result = parse_import_csv(
                contents, SERIES_ATTRS, [r.date for r in self.rows]
            )
        except Exception:
            self.import_error = (
                "This file couldn't be read as a CSV. Save it as .csv and try again."
            )
            self.import_stage = "error"
            return

        if not result.ok:
            self.import_error = result.error
            self.import_stage = "error"
            return

        self._staged_import_rows = result.rows
        self.import_added_count = result.added_count
        self.import_duplicate_count = result.duplicate_count
        self.import_invalid_count = result.invalid_count
        self.import_stage = "preview"

    def confirm_import(self) -> None:
        if self.import_stage != "preview":
            return

        before = len(self.rows)

        with rx.session() as session:
            for record in self._staged_import_rows:
                session.add(PriceRow(**record))
            session.commit()

        self._staged_import_rows = []
        self.load_rows()
        self.import_added_count = len(self.rows) - before
        self.import_stage = "done"

    def cancel_import(self) -> None:
        self._reset_import()

    def dismiss_import(self) -> None:
        self._reset_import()
