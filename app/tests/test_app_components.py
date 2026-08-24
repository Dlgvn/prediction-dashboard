"""Component-tree smoke tests for app.app.

These tests compile the Reflex Var expression tree for index() without
booting a browser, catching invalid Var operations (bad .to_string(),
bad ~ negation, bad dict indexing) at test time.
"""

import inspect
import re

import app.app as app_module
import reflex as rx

from app import state, theme
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
    # Amended in Task 06-03: UP darkened from #16A34A to #15803D to meet
    # WCAG AA contrast against SURFACE.
    rendered = str(app_module.forecast_summary_cards().render())
    assert "#15803D" in rendered
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


def test_app_py_source_uses_only_theme_hex_literals():
    # Scan app.py's own source (not the fully rendered page) for hardcoded
    # hex literals — the rendered index() page also embeds Plotly's own
    # default colorway/template hexes inside forecast/historical figure
    # JSON, which are unrelated to this plan's component styling and are
    # out of scope (figure builders live in state.py, restyled in 06-01).
    import inspect

    source = inspect.getsource(app_module)
    theme_hexes = {
        value
        for name, value in vars(theme).items()
        if isinstance(value, str) and value.upper().startswith("#")
    }
    found = set(re.findall(r"#[0-9A-Fa-f]{6}", source))
    assert found - theme_hexes == set()


def test_index_preserves_locked_copy_strings():
    rendered = str(app_module.index().render())
    for copy in [
        "No price data yet",
        "Add a row to start tracking monthly actuals.",
        "Export to Excel",
        "Add row",
        "Confirm delete?",
    ]:
        assert copy in rendered


def test_empty_state_compiles_to_component():
    component = app_module.empty_state()
    assert isinstance(component, rx.Component)


def test_export_button_still_compiles_with_theme_colors():
    component = app_module.export_button()
    assert isinstance(component, rx.Component)


def test_historical_chart_still_compiles_with_theme_colors():
    component = app_module.historical_chart()
    assert isinstance(component, rx.Component)


# --- Phase 6 Plan 03: responsive reflow + accessibility -----------------------


def _srgb_channel_to_linear(channel_255: float) -> float:
    """Convert one 0-255 sRGB channel to a linearized value per WCAG 2.1."""
    c = channel_255 / 255
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance (1.4.3 / 1.4.11) for a `#RRGGBB` hex string."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r_lin, g_lin, b_lin = (_srgb_channel_to_linear(v) for v in (r, g, b))
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2.1 contrast ratio between two `#RRGGBB` hex colors."""
    l_a, l_b = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = max(l_a, l_b), min(l_a, l_b)
    return (lighter + 0.05) / (darker + 0.05)


def test_theme_contrast_pairings_meet_wcag_aa():
    # Normal-text pairings require 4.5:1; the border/surface pairing is a
    # non-text UI boundary and requires 3:1 (WCAG 1.4.3 / 1.4.11).
    normal_text_pairs = [
        ("MUTED_TEXT/SURFACE", theme.MUTED_TEXT, theme.SURFACE),
        ("UP/SURFACE", theme.UP, theme.SURFACE),
        ("DOWN/SURFACE", theme.DOWN, theme.SURFACE),
        ("ACCENT/white-label", theme.ACCENT, "#FFFFFF"),
    ]
    for name, fg, bg in normal_text_pairs:
        ratio = _contrast_ratio(fg, bg)
        assert ratio >= 4.5, f"{name} contrast {ratio:.2f} below WCAG AA 4.5:1"

    border_ratio = _contrast_ratio(theme.BORDER, theme.SURFACE)
    assert border_ratio >= 3.0, (
        f"BORDER/SURFACE contrast {border_ratio:.2f} below WCAG AA 3:1"
    )


def test_index_has_section_landmarks_and_chart_labels():
    rendered = str(app_module.index().render())
    for label in ["Forecast summary", "Forecast", "Historical prices", "Data entry"]:
        assert f'aria-label:"{label}"' in rendered or label in rendered
    assert "Fan chart of forecast base value with expected range" in rendered
    assert "Historical actual prices for the selected series" in rendered


def test_summary_card_row_wraps_with_flex_basis():
    rendered = str(app_module.forecast_summary_cards().render())
    assert 'wrap:"wrap"' in rendered or "wrap" in rendered
    assert "flex" in rendered
    assert "200px" in rendered


def test_no_fixed_pixel_width_on_horizon_slider():
    source_path = app_module.__file__
    with open(source_path) as f:
        source = f.read()
    assert 'width="240px"' not in source


# --- Phase 7 Plan 02: table windowing + history toggle ------------------------


def test_history_toggle_compiles_to_component():
    component = app_module.history_toggle()
    assert isinstance(component, rx.Component)


def test_data_table_iterates_visible_rows_not_rows():
    source = inspect.getsource(app_module.data_table)
    assert "DashboardState.visible_rows" in source
    assert "DashboardState.rows" not in source


def test_draft_rows_foreach_unchanged():
    source = inspect.getsource(app_module.data_table)
    assert "DashboardState.draft_rows" in source


def test_data_entry_section_empty_state_uses_full_rows():
    source = inspect.getsource(app_module.data_entry_section)
    assert "DashboardState.rows.length()" in source
    assert "visible_rows" not in source


def test_history_toggle_wiring():
    source = inspect.getsource(app_module.history_toggle)
    assert "rx.switch" in source
    assert "checked=DashboardState.show_all_history" in source
    assert "on_change=DashboardState.toggle_show_all_history" in source
    assert "Show all history" in source
    assert "rx.button" not in source
    assert "rx.cond" not in source


def test_history_toggle_uses_theme_tokens_not_literals():
    source = inspect.getsource(app_module.history_toggle)
    assert "MUTED_TEXT" in source
    assert "RADIX_SIZE_LABEL" in source
    assert re.findall(r"#[0-9A-Fa-f]{6}", source) == []


def test_state_rows_still_assigned_once():
    import app.state as state_module

    source_path = state_module.__file__
    with open(source_path) as f:
        lines = f.readlines()
    non_comment_lines = [line for line in lines if not line.strip().startswith("#")]
    joined = "".join(non_comment_lines)
    assert joined.count("self.rows = ") == 1


def test_summary_card_renders_hilo_and_yoy_keys():
    source = inspect.getsource(app_module._summary_card)
    for key in (
        "hilo_label",
        "hilo_text",
        "yoy_label",
        "yoy_text",
        "yoy_arrow",
        "yoy_direction",
    ):
        assert f'card["{key}"]' in source


def test_summary_card_line_order_matches_ui_spec():
    source = inspect.getsource(app_module._summary_card)
    delta_idx = source.index('card["delta_text"]')
    hilo_idx = source.index('card["hilo_label"]')
    yoy_idx = source.index('card["yoy_label"]')
    assert delta_idx < hilo_idx < yoy_idx


def test_summary_card_yoy_reuses_direction_colors():
    source = inspect.getsource(app_module._summary_card)
    assert 'card["yoy_direction"] == "up"' in source
    assert 'card["yoy_direction"] == "down"' in source
    assert "UP" in source
    assert "DOWN" in source
    assert "MUTED_TEXT" in source
    assert "ACCENT" not in source
    assert "DESTRUCTIVE" not in source


def test_summary_card_hilo_has_no_direction_color():
    source = inspect.getsource(app_module._summary_card)
    hilo_line = source[source.index('card["hilo_text"]') : source.index('card["hilo_text"]') + 60]
    assert "UP" not in hilo_line
    assert "DOWN" not in hilo_line


def test_summary_card_no_hex_literals():
    source = inspect.getsource(app_module._summary_card)
    assert "#" not in source


def test_summary_card_aria_label_includes_new_figures():
    source = inspect.getsource(app_module._summary_card)
    aria_label_expr = source[source.index("aria_label=") :]
    assert 'card["hilo_text"]' in aria_label_expr
    assert 'card["yoy_text"]' in aria_label_expr


def test_summary_card_yoy_row_not_conditionally_hidden():
    source = inspect.getsource(app_module._summary_card)
    yoy_idx = source.index('card["yoy_label"]')
    preceding = source[:yoy_idx]
    # The last rx.cond before the YoY row's own hstack must be the shared
    # has_data == "yes" branch, not a new cond keyed on yoy_text emptiness.
    assert 'card["yoy_text"] == ""' not in source


def test_card_copy_literals_match_ui_spec():
    source = inspect.getsource(state)
    assert "All-time high/low" in source
    assert "YoY" in source
    app_source = inspect.getsource(app_module)
    assert "confidence interval" not in source.lower()
    assert "confidence interval" not in app_source.lower()
    assert "guaranteed" not in source.lower()
    assert "guaranteed" not in app_source.lower()
