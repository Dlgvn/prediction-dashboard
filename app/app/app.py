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
    CARD_PADDING,
    CARD_RADIUS,
    FONT_SIZE_BODY,
    FONT_SIZE_DISPLAY,
    FONT_WEIGHT_REGULAR,
    FONT_WEIGHT_SEMIBOLD,
    RADIX_SIZE_BODY,
    RADIX_SIZE_HEADING,
    RADIX_SIZE_LABEL,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
)

# Header labels in display order, paired with the PriceRow attribute they render.
# Order and labels follow the D-05b/D-05c 17-column contract (Date + 16 series).
# Built from state.SERIES_LABELS so labels exist in exactly one place.
_COLUMNS: list[tuple[str, str]] = [("Date", "date")] + [
    (SERIES_LABELS[attr], attr) for attr in SERIES_ATTRS
]


def _editable_cell(row: PriceRow, attr: str, cell_style: dict | None = None) -> rx.Component:
    """Render a click-to-edit table cell bound to DashboardState's edit machine.

    Cell key is built as a Var-level concatenation inside the rx.foreach
    callback (row.date is only known at render time per row) so identity
    always matches the clicked row (RESEARCH Pitfall 2 / T-04-09).
    """
    value = getattr(row, attr)
    key = row.date + ":" + attr
    # `edit_value` seeds start_edit's draft (unrounded — must round-trip
    # exactly on a no-op edit, or committing without changing anything would
    # silently truncate the stored precision). `shown_text` is display-only:
    # numeric columns are stored as raw source floats (e.g.
    # 2.9299999999999997 from CSV import) and are rounded to 2dp so the
    # table is readable; the date column is untouched either way.
    edit_value = rx.cond(value != None, value, "")  # noqa: E711  (Var-level comparison)
    shown_text = (
        edit_value
        if attr == "date"
        else rx.cond(value != None, round(value, 2), "")  # noqa: E711
    )

    display = rx.text(
        shown_text,
        on_click=DashboardState.start_edit(key, edit_value),
        cursor="pointer",
        size="2",
        font_family="'IBM Plex Mono', monospace",
    )

    # Date column uses a native HTML5 date picker (D-01/DATA-10) so the user
    # never has to type/recall an exact ISO date string; every other column
    # keeps the plain free-text input. rx.input's `type` prop passes straight
    # through to the underlying TextField.Root -> <input> element, and its
    # on_change fires with the raw ISO YYYY-MM-DD string (or "") the browser's
    # native date control emits, so update_draft/commit_edit are unchanged.
    input_kwargs = dict(
        value=DashboardState.draft_value,
        on_change=DashboardState.update_draft,
        on_blur=DashboardState.commit_edit,
        on_key_down=DashboardState.handle_key_down,
        auto_focus=True,
        size="1",
        border_color=rx.cond(DashboardState.edit_error != "", "red", None),
    )
    if attr == "date":
        input_kwargs["type"] = "date"

    editor = rx.vstack(
        rx.input(**input_kwargs),
        rx.cond(
            DashboardState.edit_error != "",
            rx.text(DashboardState.edit_error, color_scheme="red", size="1"),
            rx.fragment(),
        ),
        spacing="1",
    )

    return rx.table.cell(
        rx.cond(DashboardState.editing_key == key, editor, display),
        **(cell_style or {}),
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
    header_cell_style = {
        "position": "sticky",
        "top": "0",
        "background": DashboardState.surface,
        "z_index": "1",
    }
    date_cell_style = {
        "position": "sticky",
        "left": "0",
        "background": DashboardState.surface,
        "z_index": "1",
    }
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                *[
                    rx.table.column_header_cell(label, **header_cell_style)
                    for label, _ in _COLUMNS
                ],
                rx.table.column_header_cell("", **header_cell_style),
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.visible_rows,
                lambda row: rx.table.row(
                    _editable_cell(row, "date", cell_style=date_cell_style),
                    *[_editable_cell(row, attr) for _, attr in _COLUMNS[1:]],
                    _delete_cell(row),
                ),
            ),
        ),
    )


def history_toggle() -> rx.Component:
    """Show all history switch: reveals the full table beyond the 12-month window."""
    return rx.hstack(
        rx.switch(
            checked=DashboardState.show_all_history,
            on_change=DashboardState.toggle_show_all_history,
            color_scheme="blue",
            aria_label="Show all history",
        ),
        rx.text("Show all history", size=RADIX_SIZE_BODY),
        rx.text(
            DashboardState.history_window_caption,
            size=RADIX_SIZE_LABEL,
            color=DashboardState.muted_text,
        ),
        spacing="2",
        align="center",
    )


def historical_chart() -> rx.Component:
    """Actuals-only historical chart (VIS-01) with a Series selector (D-03/D-04)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    "Series",
                    font_weight=FONT_WEIGHT_SEMIBOLD,
                    size=RADIX_SIZE_BODY,
                ),
                rx.select(
                    list(SERIES_LABELS.values()),
                    value=DashboardState.series_label,
                    on_change=DashboardState.select_series,
                    size="2",
                    color_scheme="blue",
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
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding="1.5rem",
        width="100%",
        aria_label="Historical actual prices for the selected series",
    )


def empty_state() -> rx.Component:
    return rx.vstack(
        rx.heading("No price data yet", size=RADIX_SIZE_HEADING),
        rx.text(
            "Add a row to start tracking monthly actuals.",
            size=RADIX_SIZE_BODY,
            color=DashboardState.muted_text,
        ),
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
    )


def horizon_control() -> rx.Component:
    """Forecast horizon slider with a live numeric readout (D-01/D-02).

    Uses on_change (not on_value_commit) so the fan chart and table recompute
    live during drag, per D-02 — no Forecast button, no debounce.
    """
    return rx.hstack(
        rx.text(
            "Forecast horizon",
            font_weight=FONT_WEIGHT_SEMIBOLD,
            size=RADIX_SIZE_BODY,
        ),
        rx.slider(
            value=[DashboardState.horizon_months],
            min=1,
            max=12,
            step=1,
            on_change=DashboardState.set_horizon,
            size="2",
            width="100%",
            max_width="15rem",
            color_scheme="blue",
        ),
        rx.text(
            DashboardState.horizon_months.to_string()
            + rx.cond(DashboardState.horizon_months != 1, " months", " month"),
            size=RADIX_SIZE_BODY,
        ),
        align="center",
        spacing="2",
        wrap="wrap",
    )


def _freshness_chip(chip: rx.Var) -> rx.Component:
    """Render one freshness chip from a foreach item Var (DATA-06/D-07)."""
    return rx.box(
        rx.vstack(
            rx.text(
                chip["label"],
                size=RADIX_SIZE_LABEL,
                color_scheme="gray",
                text_transform="uppercase",
            ),
            rx.cond(
                chip["has_data"] == "yes",
                rx.text(
                    chip["date"],
                    size=RADIX_SIZE_BODY,
                    font_weight=FONT_WEIGHT_SEMIBOLD,
                    font_family="'IBM Plex Mono', monospace",
                ),
                rx.text("no data yet", size=RADIX_SIZE_BODY, color=DashboardState.muted_text),
            ),
            spacing="2",
        ),
        border=DashboardState.card_border,
        border_top=f"2px solid {DashboardState.accent_color}",
        border_style=rx.cond(chip["has_data"] == "yes", "solid", "dashed"),
        border_radius=CARD_RADIUS,
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
            color_scheme="blue",
        ),
        rx.cond(
            DashboardState.export_message != "",
            rx.text(
                DashboardState.export_message,
                size=RADIX_SIZE_LABEL,
                color=rx.cond(
                    DashboardState.export_failed,
                    DashboardState.destructive_color,
                    DashboardState.muted_text,
                ),
            ),
            rx.fragment(),
        ),
        spacing="2",
    )


def forecast_chart() -> rx.Component:
    """Fan chart with its own Series selector, independent of Phase 4's
    historical chart (VIS-02/D-03/D-04/D-05/D-06).
    """
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    "Series",
                    font_weight=FONT_WEIGHT_SEMIBOLD,
                    size=RADIX_SIZE_BODY,
                ),
                rx.select(
                    list(FORECAST_SERIES_LABELS.values()),
                    value=DashboardState.forecast_series_label,
                    on_change=DashboardState.select_forecast_series,
                    size="2",
                    color_scheme="blue",
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
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding="1.5rem",
        width="100%",
        aria_label="Fan chart of forecast base value with expected range",
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
                    rx.table.cell(row["month"], font_family="'IBM Plex Mono', monospace"),
                    *[
                        rx.table.cell(row[key], font_family="'IBM Plex Mono', monospace")
                        for key, _ in FORECAST_TABLE_COLUMNS
                    ],
                ),
            )
        ),
    )
    warning_banner = rx.cond(
        DashboardState.forecast_warning != "",
        rx.hstack(
            rx.icon("triangle-alert", size=16, color="amber"),
            rx.text(
                DashboardState.forecast_warning,
                size=RADIX_SIZE_BODY,
                color="amber",
            ),
            spacing="2",
            align="center",
            margin_bottom="0.75rem",
        ),
        rx.fragment(),
    )
    return rx.box(
        warning_banner,
        rx.cond(
            DashboardState.forecast_table_rows.length() > 0,
            table,
            rx.text(
                DashboardState.forecast_error,
                size=RADIX_SIZE_BODY,
                color=DashboardState.muted_text,
            ),
        ),
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
        overflow_x="auto",
        width="100%",
        min_width="0",
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
                        font_family="'IBM Plex Mono', monospace",
                    ),
                    rx.hstack(
                        rx.text(
                            card["range_label"] + ":",
                            size=RADIX_SIZE_LABEL,
                            color=DashboardState.muted_text,
                        ),
                        rx.text(card["range_text"], size=RADIX_SIZE_BODY),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text(
                            card["arrow"] + " " + card["delta_text"],
                            color=rx.cond(
                                card["direction"] == "up",
                                DashboardState.up_color,
                                rx.cond(card["direction"] == "down", DashboardState.down_color, DashboardState.muted_text),
                                ),
                            font_weight=FONT_WEIGHT_SEMIBOLD,
                            size=RADIX_SIZE_BODY,
                        ),
                        rx.text(card["caption"], size=RADIX_SIZE_LABEL, color=DashboardState.muted_text),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text(
                            card["hilo_label"] + ":",
                            size=RADIX_SIZE_LABEL,
                            color=DashboardState.muted_text,
                        ),
                        rx.text(card["hilo_text"], size=RADIX_SIZE_BODY),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text(
                            card["yoy_label"] + ":",
                            size=RADIX_SIZE_LABEL,
                            color=DashboardState.muted_text,
                        ),
                        rx.text(
                            card["yoy_arrow"] + " " + card["yoy_text"],
                            color=rx.cond(
                                card["yoy_direction"] == "up",
                                DashboardState.up_color,
                                rx.cond(card["yoy_direction"] == "down", DashboardState.down_color, DashboardState.muted_text),
                                ),
                            font_weight=FONT_WEIGHT_SEMIBOLD,
                            size=RADIX_SIZE_BODY,
                        ),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text(
                            card["model_label"] + ":",
                            size=RADIX_SIZE_LABEL,
                            color=DashboardState.muted_text,
                        ),
                        rx.text(card["model_text"], size=RADIX_SIZE_BODY),
                        spacing="2",
                    ),
                ),
                rx.text(card["no_data_text"], size=RADIX_SIZE_BODY, color=DashboardState.muted_text),
            ),
            spacing="2",
            align="start",
        ),
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_top=f"2px solid {DashboardState.accent_color}",
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
        min_width="200px",
        flex="1 1 200px",
        aria_label=card["label"]
        + " "
        + card["base"]
        + " "
        + card["delta_text"]
        + " "
        + card["hilo_text"]
        + " "
        + card["yoy_text"]
        + " "
        + card["model_text"],
    )


def forecast_summary_cards() -> rx.Component:
    """Four-card forecast summary row, all series visible at once (D-01)."""
    return rx.vstack(
        rx.heading("Forecast Summary", size=RADIX_SIZE_HEADING, as_="h2"),
        rx.hstack(
            rx.foreach(DashboardState.summary_cards, _summary_card),
            spacing="3",
            wrap="wrap",
            width="100%",
            align="stretch",
        ),
        spacing="3",
        aria_label="Forecast summary",
        role="region",
    )


def forecast_section() -> rx.Component:
    """Phase 5's forecast UI block, in the exact order the UI-SPEC locks (D-06).

    Freshness chips and the export button move to the end of the block
    (D-04) — they describe forecast provenance/export, not the forecast
    itself, so they trail the chart and table rather than leading them.
    """
    return rx.vstack(
        rx.heading("Forecast", size=RADIX_SIZE_HEADING, as_="h2"),
        horizon_control(),
        forecast_chart(),
        rx.heading(
            "Forecast — base / bull / bear", size=RADIX_SIZE_HEADING, as_="h3"
        ),
        forecast_table(),
        freshness_chips_row(),
        export_button(),
        spacing="3",
        aria_label="Forecast",
        role="region",
    )


def historical_section() -> rx.Component:
    """Historical chart under its own heading, trailing forecast content (D-02/D-03)."""
    return rx.vstack(
        rx.heading("Historical", size=RADIX_SIZE_HEADING, as_="h2"),
        historical_chart(),
        spacing="3",
        width="100%",
        aria_label="Historical prices",
        role="region",
    )


def csv_import_control() -> rx.Component:
    """CSV bulk-import control: dropzone, preview, error, and done states (D-04/D-05/D-06).

    Branches on DashboardState.import_stage using nested rx.cond, matching the
    string-Var branching style already established by _summary_card /
    _freshness_chip in this file (Reflex has no match on string Vars here).
    """
    error_state = rx.hstack(
        rx.icon("circle-alert", size=16, color=DashboardState.destructive_color),
        rx.text(
            DashboardState.import_error,
            size=RADIX_SIZE_BODY,
            color=DashboardState.destructive_color,
        ),
        rx.button(
            "Try again",
            variant="ghost",
            color_scheme="blue",
            on_click=DashboardState.cancel_import,
        ),
        spacing="2",
        align="center",
        padding=SPACE_MD,
        border=f"1px solid {DashboardState.destructive_color}",
        border_radius=CARD_RADIUS,
    )

    preview_state = rx.box(
        rx.vstack(
            rx.text(
                "Import preview",
                size=RADIX_SIZE_BODY,
                font_weight=FONT_WEIGHT_SEMIBOLD,
            ),
            rx.text(DashboardState.import_added_text, size=RADIX_SIZE_BODY),
            rx.text(
                DashboardState.import_duplicate_text,
                size=RADIX_SIZE_BODY,
                color=DashboardState.destructive_color,
            ),
            rx.text(
                DashboardState.import_invalid_text,
                size=RADIX_SIZE_BODY,
                color=DashboardState.destructive_color,
            ),
            rx.hstack(
                rx.button(
                    "Confirm import",
                    on_click=DashboardState.confirm_import,
                    disabled=~DashboardState.can_confirm_import,
                    size="2",
                    color_scheme="blue",
                ),
                rx.button(
                    "Cancel",
                    on_click=DashboardState.cancel_import,
                    size="2",
                    color_scheme="gray",
                    variant="soft",
                ),
                spacing="2",
            ),
            spacing="2",
        ),
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
    )

    done_state = rx.box(
        rx.vstack(
            rx.text(DashboardState.import_result_text, size=RADIX_SIZE_BODY),
            rx.button(
                "Done",
                variant="ghost",
                color_scheme="blue",
                on_click=DashboardState.dismiss_import,
            ),
            spacing="2",
        ),
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
    )

    idle_state = rx.upload(
        rx.vstack(
            rx.icon("upload", size=20, color=DashboardState.muted_text),
            rx.text(
                "Drag and drop a CSV file here, or click to browse.",
                size=RADIX_SIZE_BODY,
                color=DashboardState.muted_text,
            ),
            spacing="1",
            align="center",
        ),
        id="csv_upload",
        accept={"text/csv": [".csv"]},
        max_files=1,
        multiple=False,
        on_drop=DashboardState.handle_csv_upload(
            rx.upload_files(upload_id="csv_upload")
        ),
        border=DashboardState.card_border,
        border_style="dashed",
        border_radius=CARD_RADIUS,
        background=DashboardState.surface,
        padding=SPACE_MD,
        width="100%",
    )

    return rx.box(
        rx.cond(
            DashboardState.import_stage == "error",
            error_state,
            rx.cond(
                DashboardState.import_stage == "preview",
                preview_state,
                rx.cond(
                    DashboardState.import_stage == "done",
                    done_state,
                    idle_state,
                ),
            ),
        ),
        aria_label="CSV bulk import",
    )


def _quick_add_field(attr: str, label: str, required: bool = False) -> rx.Component:
    return rx.vstack(
        rx.text(
            label + (" *" if required else ""),
            size=RADIX_SIZE_LABEL,
            font_weight=FONT_WEIGHT_SEMIBOLD if required else FONT_WEIGHT_REGULAR,
            color_scheme="gray",
        ),
        rx.input(
            value=DashboardState.quick_add_values[attr].to(str),
            on_change=lambda value: DashboardState.update_quick_add_field(attr, value),
            type="date" if attr == "date" else "text",
            size="2",
            font_family="'IBM Plex Mono', monospace",
        ),
        spacing="1",
        align="start",
    )


def quick_add_form() -> rx.Component:
    """Compact form for entering one full month's actuals at once (replaces
    the old add-row-then-click-each-cell draft flow).
    """
    return rx.box(
        rx.cond(
            DashboardState.quick_add_error != "",
            rx.hstack(
                rx.icon("circle-alert", size=16, color=DashboardState.destructive_color),
                rx.text(
                    DashboardState.quick_add_error,
                    size=RADIX_SIZE_BODY,
                    color=DashboardState.destructive_color,
                ),
                spacing="2",
                align="center",
                margin_bottom=SPACE_SM,
            ),
            rx.fragment(),
        ),
        rx.flex(
            _quick_add_field("date", "Date", required=True),
            *[
                _quick_add_field(attr, SERIES_LABELS[attr])
                for attr in SERIES_ATTRS
            ],
            wrap="wrap",
            spacing="3",
            align="end",
        ),
        rx.button(
            "Save row",
            on_click=DashboardState.submit_quick_add,
            size="2",
            color_scheme="blue",
            margin_top=SPACE_SM,
        ),
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
        width="100%",
        aria_label="Add a month's actuals",
    )


def data_entry_section() -> rx.Component:
    """Data-entry table under its own heading, at the bottom of the page (D-02/D-03)."""
    return rx.vstack(
        rx.heading("Data Entry", size=RADIX_SIZE_HEADING, as_="h2"),
        rx.text("Click any cell to edit a month's actuals.", size=RADIX_SIZE_BODY),
        history_toggle(),
        rx.cond(
            DashboardState.rows.length() > 0,
            rx.box(
                data_table(),
                background=DashboardState.surface,
                border=DashboardState.card_border,
                border_radius=CARD_RADIUS,
                padding=CARD_PADDING,
                overflow_x="auto",
                overflow_y="auto",
                max_height="80vh",
                width="100%",
                min_width="0",
            ),
            empty_state(),
        ),
        quick_add_form(),
        rx.text(
            "Import CSV",
            size=RADIX_SIZE_BODY,
            font_weight=FONT_WEIGHT_SEMIBOLD,
        ),
        csv_import_control(),
        spacing="3",
        aria_label="Data entry",
        role="region",
    )


def theme_toggle() -> rx.Component:
    """Header toggle flipping both Radix chrome and app tokens (THEME-02)."""
    return rx.icon_button(
        rx.color_mode.icon(),
        on_click=[DashboardState.toggle_theme_mode, rx.toggle_color_mode],
        aria_label="Toggle dark mode",
    )


def nav_bar() -> rx.Component:
    """Sticky, controlled tab bar switching between the three dashboard sections (NAV-01, D-02).

    Built on rx.tabs so the tablist/tab/aria-selected/keyboard-navigation wiring comes for
    free from Radix rather than being hand-rolled. Only rx.tabs.list is placed here; the
    corresponding rx.tabs.content panels live in _data_entry_tab()/index() so index() can
    keep calling each section factory exactly once.
    """
    def _trigger(label: str, value: str) -> rx.Component:
        is_active = DashboardState.active_section == value
        return rx.tabs.trigger(
            label,
            value=value,
            padding_left=SPACE_MD,
            padding_right=SPACE_MD,
            font_size=FONT_SIZE_BODY,
            color=rx.cond(is_active, DashboardState.accent_color, DashboardState.muted_text),
            font_weight=rx.cond(is_active, FONT_WEIGHT_SEMIBOLD, FONT_WEIGHT_REGULAR),
            border_bottom=rx.cond(
                is_active,
                f"2px solid {DashboardState.accent_color}",
                "2px solid transparent",
            ),
        )

    return rx.tabs.root(
        rx.tabs.list(
            _trigger("Summary", "summary"),
            _trigger("Forecast", "forecast"),
            _trigger("Data Entry", "data_entry"),
            border_bottom=f"1px solid {DashboardState.border_color}",
            width="100%",
        ),
        value=DashboardState.active_section,
        on_change=DashboardState.set_active_section,
        position="sticky",
        top="0",
        background=DashboardState.page_bg,
        z_index="10",
        width="100%",
    )


def _data_entry_tab() -> rx.Component:
    """Historical chart and data-entry table, grouped as one unit (D-01)."""
    return rx.vstack(
        historical_section(),
        data_entry_section(),
        spacing="6",
        width="100%",
    )


def index() -> rx.Component:
    return rx.container(
        # THEME-01: html/body background must be mode-aware and Var-driven
        # (11-RESEARCH.md Pitfall 4). rx.App(style={"html, body": {...}})
        # cannot carry a reactive Var here — that style dict compiles into
        # a plain top-level JS module (utils/theme.js) evaluated outside
        # any React component, so the state-context hook the Var needs
        # never gets injected (verified: build fails with
        # "reflex___state____state...dashboard_state is not defined").
        # A <style> element rendered inside the component tree instead
        # gets the hook injected normally, and a <style> tag's CSS still
        # cascades globally regardless of where it sits in the DOM.
        rx.el.style(
            "html, body { background: " + DashboardState.page_bg + "; }"
        ),
        rx.hstack(
            rx.heading("Prediction Dashboard", size="9", as_="h1"),
            theme_toggle(),
            align="center",
            justify="between",
            width="100%",
            spacing="2",
        ),
        nav_bar(),
        rx.text(
            "Forecasts and actuals for ammonium nitrate, diesel, and the FX rate.",
            size=RADIX_SIZE_BODY,
        ),
        rx.match(
            DashboardState.active_section,
            ("summary", forecast_summary_cards()),
            ("forecast", forecast_section()),
            ("data_entry", _data_entry_tab()),
            rx.text(
                "Unknown section — try switching tabs again.",
                size=RADIX_SIZE_BODY,
                color=DashboardState.muted_text,
            ),
        ),
        background=DashboardState.page_bg,
        min_height="100vh",
        width="100%",
        spacing="6",
        padding_y=SPACE_LG,
        padding_x=SPACE_MD,
        on_mount=[DashboardState.load_rows, DashboardState.load_markup_pct],
    )


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap",
    ],
    style={
        "font_family": "'IBM Plex Sans', sans-serif",
    },
)
app.add_page(index, route="/")
