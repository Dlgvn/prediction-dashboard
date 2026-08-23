"""Component-tree smoke tests for app.app.

These tests compile the Reflex Var expression tree for index() without
booting a browser, catching invalid Var operations (bad .to_string(),
bad ~ negation, bad dict indexing) at test time.
"""

import app.app as app_module
import reflex as rx

from app import state
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


# --- Phase 5 ---------------------------------------------------------------


def test_horizon_control_compiles_to_component():
    component = app_module.horizon_control()
    assert isinstance(component, rx.Component)


def test_freshness_chips_row_compiles_to_component():
    component = app_module.freshness_chips_row()
    assert isinstance(component, rx.Component)


def test_forecast_chart_compiles_to_component():
    component = app_module.forecast_chart()
    assert isinstance(component, rx.Component)


def test_forecast_table_compiles_to_component():
    component = app_module.forecast_table()
    assert isinstance(component, rx.Component)


def test_export_button_compiles_to_component():
    component = app_module.export_button()
    assert isinstance(component, rx.Component)


def test_forecast_section_compiles_to_component():
    component = app_module.forecast_section()
    assert isinstance(component, rx.Component)


def test_index_still_compiles_with_forecast_section():
    component = app_module.index()
    assert isinstance(component, rx.Component)


def test_forecast_table_columns_count_is_fifteen():
    assert len(state.FORECAST_TABLE_COLUMNS) == 15


def test_forecast_chart_uses_its_own_selector():
    rendered = str(app_module.forecast_chart().render())
    assert "select_forecast_series" in rendered
    assert "select_series" not in rendered


def test_index_on_mount_loads_markup_pct():
    # component.render() does not surface the on_mount prop (it lives on the
    # rx.Container wrapper's event trigger dict, not the child render tree),
    # so this falls back to a source-level assertion per the plan's
    # substitution allowance.
    import inspect

    source = inspect.getsource(app_module.index)
    assert "load_markup_pct" in source


def test_forecast_table_has_no_edit_wiring():
    rendered = str(app_module.forecast_table().render())
    assert "start_edit" not in rendered
    assert "update_draft" not in rendered


# --- Phase 6 -----------------------------------------------------------------


def test_forecast_summary_cards_compiles_to_component():
    component = app_module.forecast_summary_cards()
    assert isinstance(component, rx.Component)


def test_forecast_summary_cards_references_state_var():
    rendered = str(app_module.forecast_summary_cards().render())
    assert "summary_cards" in rendered


def test_forecast_summary_cards_wires_direction_colors():
    # Arrow glyphs themselves come from DashboardState.summary_cards data
    # (Var-driven, not literal Python strings in app.py), so they never
    # appear in the compiled component tree's static render() output.
    # The UP/DOWN hex constants ARE literal in the rx.cond color branch,
    # so their presence proves both cond branches are wired.
    rendered = str(app_module.forecast_summary_cards().render())
    assert "#16A34A" in rendered
    assert "#DC2626" in rendered


def test_forecast_summary_cards_has_no_forbidden_copy():
    rendered = str(app_module.forecast_summary_cards().render()).lower()
    assert "confidence" not in rendered
    assert "guaranteed" not in rendered


def test_historical_section_compiles_to_component():
    component = app_module.historical_section()
    assert isinstance(component, rx.Component)


def test_data_entry_section_compiles_to_component():
    component = app_module.data_entry_section()
    assert isinstance(component, rx.Component)


def test_index_heading_order_matches_locked_layout():
    rendered = str(app_module.index().render())
    summary_idx = rendered.find("Forecast Summary")
    # The em dash is JSON-escaped (—) in the compiled render tree, so
    # anchor on the surrounding literal text rather than the raw glyph.
    forecast_idx = rendered.find("u2014 base / bull / bear")
    historical_idx = rendered.find("Historical")
    data_entry_idx = rendered.find("Data Entry")
    assert summary_idx != -1
    assert forecast_idx != -1
    assert historical_idx != -1
    assert data_entry_idx != -1
    assert summary_idx < forecast_idx < historical_idx < data_entry_idx


def test_index_has_no_theme_toggle():
    rendered = str(app_module.index().render())
    assert "color_mode" not in rendered
    assert "dark_mode" not in rendered
