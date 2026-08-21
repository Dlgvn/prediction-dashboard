"""Prediction Dashboard Reflex app entrypoint."""

import reflex as rx


def index() -> rx.Component:
    return rx.container(
        rx.heading("Prediction Dashboard", size="9"),
    )


app = rx.App()
app.add_page(index, route="/")
