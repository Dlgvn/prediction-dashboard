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


def _cell(row: PriceRow, attr: str) -> rx.Component:
    """Render a table cell, resolving None to an empty string rather than 'None'/'nan'."""
    value = getattr(row, attr)
    return rx.table.cell(rx.cond(value != None, value, ""))  # noqa: E711  (Var-level comparison)


def data_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                *[rx.table.column_header_cell(label) for label, _ in _COLUMNS]
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.rows,
                lambda row: rx.table.row(
                    *[_cell(row, attr) for _, attr in _COLUMNS]
                ),
            )
        ),
    )


def index() -> rx.Component:
    return rx.container(
        rx.heading("Prediction Dashboard", size="9"),
        rx.text("Seeded historical monthly price data."),
        rx.box(
            data_table(),
            overflow_x="auto",
            overflow_y="auto",
            max_height="80vh",
            width="100%",
        ),
        on_mount=DashboardState.load_rows,
    )


app = rx.App()
app.add_page(index, route="/")
