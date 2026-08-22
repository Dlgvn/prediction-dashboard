"""Prediction Dashboard Reflex app entrypoint."""

import reflex as rx

from app.models import AppSetting, PriceRow  # noqa: F401  (registers tables for reflex db migrate)
from app.state import DashboardState

# Header labels in display order, paired with the PriceRow attribute they render.
# Order and labels follow the D-05b/D-05c 17-column contract (Date + 16 series).
_COLUMNS: list[tuple[str, str]] = [
    ("Date", "date"),
    ("HDAN", "hdan"),
    ("PPAN", "ppan"),
    ("Baltic AN", "baltic_an"),
    ("Ammonia", "ammonia"),
    ("Urea Black Sea", "urea_black_sea"),
    ("Urea China", "urea_china"),
    ("NG JKM", "natural_gas_jkm"),
    ("NG Henry Hub", "natural_gas_henry_hub"),
    ("NG UK", "natural_gas_uk"),
    ("NG Netherlands", "natural_gas_netherlands"),
    ("Corn US", "corn_us"),
    ("Corn China", "corn_china"),
    ("Diesel USD/t", "diesel_usd_ton"),
    ("Urals", "urals"),
    ("FX Rate", "fx_rate"),
    ("Brent", "brent"),
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
        on_click=DashboardState.start_edit(key, value.to_string()),
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


def empty_state() -> rx.Component:
    return rx.vstack(
        rx.heading("No price data yet", size="4"),
        rx.text("Add a row to start tracking monthly actuals."),
    )


def index() -> rx.Component:
    return rx.container(
        rx.heading("Prediction Dashboard", size="9"),
        rx.text("Click any cell to edit a month's actuals."),
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
        rx.box(height="2rem"),
        spacing="4",
        on_mount=DashboardState.load_rows,
    )


app = rx.App()
app.add_page(index, route="/")
