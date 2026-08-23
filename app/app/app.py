"""Prediction Dashboard Reflex app entrypoint."""

import reflex as rx

from app.models import AppSetting, PriceRow  # noqa: F401  (registers tables for reflex db migrate)
from app.state import (
    FORECAST_SERIES_LABELS,
    FORECAST_TABLE_COLUMNS,
    SERIES_ATTRS,
    SERIES_LABELS,
    DashboardState,
)
from app.theme import (
    CARD_BORDER,
    CARD_PADDING,
    CARD_RADIUS,
    DOWN,
    FONT_SIZE_DISPLAY,
    FONT_WEIGHT_SEMIBOLD,
    MUTED_TEXT,
    PAGE_BG,
    RADIX_SIZE_BODY,
    RADIX_SIZE_HEADING,
    RADIX_SIZE_LABEL,
    SPACE_LG,
    SPACE_XXL,
    SURFACE,
    UP,
)

# Header labels in display order, paired with the PriceRow attribute they render.
# Order and labels follow the D-05b/D-05c 17-column contract (Date + 16 series).
# Built from state.SERIES_LABELS so labels exist in exactly one place.
_COLUMNS: list[tuple[str, str]] = [("Date", "date")] + [
    (SERIES_LABELS[attr], attr) for attr in SERIES_ATTRS
]


def _editable_cell(row: PriceRow, attr: str) -> rx.Component:
    """Render a click-to-edit table cell bound to DashboardState's edit machine.

    Cell key is built as a Var-level concatenation inside the rx.foreach
    callback (row.date is only known at render time per row) so identity
    always matches the clicked row (RESEARCH Pitfall 2 / T-04-09).
    """
    value = getattr(row, attr)
    key = row.date + ":" + attr
    display_value = rx.cond(value != None, value, "")  # noqa: E711  (Var-level comparison)

    display = rx.text(
        display_value,
        on_click=DashboardState.start_edit(key, display_value),
        cursor="pointer",
        size="2",
    )

    editor = rx.vstack(
        rx.input(
            value=DashboardState.draft_value,
            on_change=DashboardState.update_draft,
            on_blur=DashboardState.commit_edit,
            on_key_down=DashboardState.handle_key_down,
            auto_focus=True,
            size="1",
            border_color=rx.cond(
                DashboardState.edit_error != "", "red", None
            ),
        ),
        rx.cond(
            DashboardState.edit_error != "",
            rx.text(DashboardState.edit_error, color_scheme="red", size="1"),
            rx.fragment(),
        ),
        spacing="1",
    )

    return rx.table.cell(
        rx.cond(DashboardState.editing_key == key, editor, display)
    )


def _delete_cell(row: PriceRow) -> rx.Component:
    """Render the per-row two-click delete control (armed -> confirm)."""
    confirm = rx.button(
        "Confirm delete?",
        color_scheme="red",
        variant="solid",
        size="1",
        on_click=DashboardState.request_delete(row.date),
        on_blur=DashboardState.cancel_pending_delete,
    )
    arm = rx.icon_button(
        rx.icon("trash-2", size=16),
        variant="ghost",
        color_scheme="red",
        size="1",
        on_click=DashboardState.request_delete(row.date),
        min_width="32px",
        min_height="32px",
    )
    return rx.table.cell(
        rx.cond(DashboardState.pending_delete == row.date, confirm, arm)
    )


def data_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                *[rx.table.column_header_cell(label) for label, _ in _COLUMNS],
                rx.table.column_header_cell(""),
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.rows,
                lambda row: rx.table.row(
                    *[_editable_cell(row, attr) for _, attr in _COLUMNS],
                    _delete_cell(row),
                ),
            ),
            rx.foreach(
                DashboardState.draft_rows,
                lambda row: rx.table.row(
                    *[_editable_cell(row, attr) for _, attr in _COLUMNS],
                    rx.table.cell(),
                ),
            ),
        ),
    )


def add_row_button() -> rx.Component:
    return rx.button(
        "Add row",
        on_click=DashboardState.add_row,
        disabled=~DashboardState.can_add_row,
        size="2",
    )


def historical_chart() -> rx.Component:
    """Actuals-only historical chart (VIS-01) with a Series selector (D-03/D-04)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text("Series", weight="bold", size="2"),
                rx.select(
                    list(SERIES_LABELS.values()),
                    value=DashboardState.series_label,
                    on_change=DashboardState.select_series,
                    size="2",
                ),
                spacing="2",
                align="center",
            ),
            rx.plotly(
                data=DashboardState.historical_chart_figure,
                width="100%",
                height="360px",
            ),
            spacing="3",
        ),
        padding="1.5rem",
        width="100%",
    )


def empty_state() -> rx.Component:
    return rx.vstack(
        rx.heading("No price data yet", size="4"),
        rx.text("Add a row to start tracking monthly actuals."),
    )


def horizon_control() -> rx.Component:
    """Forecast horizon slider with a live numeric readout (D-01/D-02).

    Uses on_change (not on_value_commit) so the fan chart and table recompute
    live during drag, per D-02 — no Forecast button, no debounce.
    """
    return rx.hstack(
        rx.text("Forecast horizon", weight="bold", size="2"),
        rx.slider(
            value=[DashboardState.horizon_months],
            min=1,
            max=12,
            step=1,
            on_change=DashboardState.set_horizon,
            size="2",
            width="240px",
        ),
        rx.text(
            DashboardState.horizon_months.to_string()
            + rx.cond(DashboardState.horizon_months != 1, " months", " month"),
            size="2",
        ),
        align="center",
        spacing="2",
    )


def _freshness_chip(chip: rx.Var) -> rx.Component:
    """Render one freshness chip from a foreach item Var (DATA-06/D-07)."""
    return rx.box(
        rx.vstack(
            rx.text(
                chip["label"],
                size="1",
                color_scheme="gray",
                text_transform="uppercase",
            ),
            rx.cond(
                chip["has_data"] == "yes",
                rx.text(chip["date"], size="2", weight="bold"),
                rx.text("no data yet", size="2", color_scheme="gray"),
            ),
            spacing="1",
        ),
        border="1px solid var(--gray-5)",
        border_style=rx.cond(chip["has_data"] == "yes", "solid", "dashed"),
        border_radius="8px",
        padding="8px 12px",
    )


def freshness_chips_row() -> rx.Component:
    """Row of four as-of-date chips, one per independently-modeled series."""
    return rx.hstack(
        rx.foreach(DashboardState.freshness_chips, _freshness_chip),
        spacing="2",
        wrap="wrap",
    )


def export_button() -> rx.Component:
    """Excel export trigger with inline result copy (D-08/EXPORT-01)."""
    return rx.vstack(
        rx.button(
            rx.icon("download", size=16),
            "Export to Excel",
            on_click=DashboardState.export_to_excel,
            size="2",
        ),
        rx.cond(
            DashboardState.export_message != "",
            rx.text(
                DashboardState.export_message,
                size="1",
                color_scheme=rx.cond(DashboardState.export_failed, "red", "gray"),
            ),
            rx.fragment(),
        ),
        spacing="1",
    )


def forecast_chart() -> rx.Component:
    """Fan chart with its own Series selector, independent of Phase 4's
    historical chart (VIS-02/D-03/D-04/D-05/D-06).
    """
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text("Series", weight="bold", size="2"),
                rx.select(
                    list(FORECAST_SERIES_LABELS.values()),
                    value=DashboardState.forecast_series_label,
                    on_change=DashboardState.select_forecast_series,
                    size="2",
                ),
                spacing="2",
                align="center",
            ),
            rx.plotly(
                data=DashboardState.forecast_chart_figure,
                width="100%",
                height="360px",
            ),
            spacing="3",
        ),
        padding="1.5rem",
        width="100%",
    )


def forecast_table() -> rx.Component:
    """Read-only all-series base/bull/bear table (FCST-06/VIS-03), with a
    graceful empty state fallback showing forecast_error copy.
    """
    table = rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Month"),
                *[
                    rx.table.column_header_cell(label)
                    for _, label in FORECAST_TABLE_COLUMNS
                ],
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.forecast_table_rows,
                lambda row: rx.table.row(
                    rx.table.cell(row["month"]),
                    *[
                        rx.table.cell(row[key])
                        for key, _ in FORECAST_TABLE_COLUMNS
                    ],
                ),
            )
        ),
    )
    return rx.box(
        rx.cond(
            DashboardState.forecast_table_rows.length() > 0,
            table,
            rx.text(DashboardState.forecast_error, size="2", color_scheme="gray"),
        ),
        overflow_x="auto",
        width="100%",
    )


def _summary_card(card: rx.Var) -> rx.Component:
    """Render one forecast summary card from a foreach item Var (D-01/D-10/D-11/D-13)."""
    return rx.box(
        rx.vstack(
            rx.text(
                card["label"],
                size=RADIX_SIZE_LABEL,
                color_scheme="gray",
                text_transform="uppercase",
                font_weight=FONT_WEIGHT_SEMIBOLD,
            ),
            rx.cond(
                card["has_data"] == "yes",
                rx.fragment(
                    rx.text(
                        card["base"],
                        font_size=FONT_SIZE_DISPLAY,
                        font_weight=FONT_WEIGHT_SEMIBOLD,
                        line_height="1.2",
                    ),
                    rx.hstack(
                        rx.text(
                            card["range_label"] + ":",
                            size=RADIX_SIZE_LABEL,
                            color=MUTED_TEXT,
                        ),
                        rx.text(card["range_text"], size=RADIX_SIZE_BODY),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.text(
                            card["arrow"] + " " + card["delta_text"],
                            color=rx.cond(
                                card["direction"] == "up",
                                UP,
                                rx.cond(card["direction"] == "down", DOWN, MUTED_TEXT),
                            ),
                            font_weight=FONT_WEIGHT_SEMIBOLD,
                            size=RADIX_SIZE_BODY,
                        ),
                        rx.text(card["caption"], size=RADIX_SIZE_LABEL, color=MUTED_TEXT),
                        spacing="1",
                    ),
                ),
                rx.text(card["no_data_text"], size=RADIX_SIZE_BODY, color=MUTED_TEXT),
            ),
            spacing="2",
            align="start",
        ),
        background=SURFACE,
        border=CARD_BORDER,
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
        min_width="200px",
        flex="1 1 200px",
        aria_label=card["label"] + " " + card["base"] + " " + card["delta_text"],
    )


def forecast_summary_cards() -> rx.Component:
    """Four-card forecast summary row, all series visible at once (D-01)."""
    return rx.vstack(
        rx.heading("Forecast Summary", size=RADIX_SIZE_HEADING),
        rx.hstack(
            rx.foreach(DashboardState.summary_cards, _summary_card),
            spacing="3",
            wrap="wrap",
            width="100%",
            align="stretch",
        ),
        spacing="3",
    )


def forecast_section() -> rx.Component:
    """Phase 5's forecast UI block, in the exact order the UI-SPEC locks (D-06).

    Freshness chips and the export button move to the end of the block
    (D-04) — they describe forecast provenance/export, not the forecast
    itself, so they trail the chart and table rather than leading them.
    """
    return rx.vstack(
        rx.heading("Forecast", size="6"),
        horizon_control(),
        forecast_chart(),
        rx.heading("Forecast — base / bull / bear", size=RADIX_SIZE_HEADING),
        forecast_table(),
        freshness_chips_row(),
        export_button(),
        spacing="3",
    )


def historical_section() -> rx.Component:
    """Historical chart under its own heading, trailing forecast content (D-02/D-03)."""
    return rx.vstack(
        rx.heading("Historical", size=RADIX_SIZE_HEADING),
        historical_chart(),
        spacing="3",
    )


def data_entry_section() -> rx.Component:
    """Data-entry table under its own heading, at the bottom of the page (D-02/D-03)."""
    return rx.vstack(
        rx.heading("Data Entry", size=RADIX_SIZE_HEADING),
        rx.text("Click any cell to edit a month's actuals.", size=RADIX_SIZE_BODY),
        rx.cond(
            (DashboardState.rows.length() + DashboardState.draft_rows.length()) > 0,
            rx.box(
                data_table(),
                overflow_x="auto",
                overflow_y="auto",
                max_height="80vh",
                width="100%",
            ),
            empty_state(),
        ),
        add_row_button(),
        spacing="3",
    )


def index() -> rx.Component:
    return rx.container(
        rx.heading("Prediction Dashboard", size="9"),
        rx.text(
            "Forecasts and actuals for ammonium nitrate, diesel, and the FX rate.",
            size=RADIX_SIZE_BODY,
        ),
        forecast_summary_cards(),
        forecast_section(),
        rx.box(height=SPACE_XXL),
        historical_section(),
        data_entry_section(),
        background=PAGE_BG,
        min_height="100vh",
        spacing="6",
        padding_y=SPACE_LG,
        on_mount=[DashboardState.load_rows, DashboardState.load_markup_pct],
    )


app = rx.App()
app.add_page(index, route="/")
