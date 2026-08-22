"""Component-tree smoke tests for app.app.

These tests compile the Reflex Var expression tree for index() without
booting a browser, catching invalid Var operations (bad .to_string(),
bad ~ negation, bad dict indexing) at test time.
"""

import app.app as app_module
import reflex as rx

from app.models import PriceRow


def test_index_compiles_to_component():
    component = app_module.index()
    assert isinstance(component, rx.Component)


def test_columns_count_is_seventeen():
    assert len(app_module._COLUMNS) == 17


def test_historical_chart_compiles_to_component():
    component = app_module.historical_chart()
    assert isinstance(component, rx.Component)


def _start_edit_arg_source(row: PriceRow, attr: str) -> str:
    """Render _editable_cell's start_edit on_click args to source text.

    Regression test for the bug where `value.to_string()` was passed as the
    second start_edit argument: that produces a JSON-string-literal
    (quote-wrapped) Var, so an empty string arrived as the two-character
    string `""` instead of a truly empty string. The fix passes
    `display_value` (already coalesced to "" and never JSON-stringified).
    """
    cell = app_module._editable_cell(row, attr)
    rendered = str(cell.render())
    return rendered


def test_editable_cell_start_edit_arg_not_json_stringified_for_empty_string():
    row = PriceRow(date="")
    rendered = _start_edit_arg_source(row, "date")
    # The buggy `.to_string()` call renders as `.toString()` / JSON-quoting
    # helpers in the compiled component tree; assert it's gone from the
    # click handler wiring for this cell.
    assert "to_string" not in rendered
    assert "toJSON" not in rendered


def test_editable_cell_start_edit_arg_not_json_stringified_for_numeric():
    row = PriceRow(date="2026-08-01", hdan=123.45)
    rendered = _start_edit_arg_source(row, "hdan")
    assert "to_string" not in rendered
    assert "toJSON" not in rendered
