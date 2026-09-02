"""Component-tree smoke tests for app.app.

These tests compile the Reflex Var expression tree for index() without
booting a browser, catching invalid Var operations (bad .to_string(),
bad ~ negation, bad dict indexing) at test time.
"""

import inspect
import re

import pytest
import reflex as rx

import app.app as app_module
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


def test_editable_cell_date_column_renders_native_date_picker():
    """D-01/DATA-10: the date column's editor input carries type="date"."""
    row = PriceRow(date="2026-08-01")
    rendered = _start_edit_arg_source(row, "date")
    assert 'type:"date"' in rendered


def test_editable_cell_non_date_column_has_no_date_type():
    """Regression guard: non-date columns keep the plain free-text input."""
    row = PriceRow(date="2026-08-01", hdan=123.45)
    rendered = _start_edit_arg_source(row, "hdan")
    assert 'type:"date"' not in rendered


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
    # Phase 11: UP/DOWN/DESTRUCTIVE are no longer literal hex constants --
    # they resolve from DashboardState's mode-aware computed vars, so this
    # now proves both cond branches are wired to those state var names in
    # the compiled render tree instead of asserting on hex literals.
    rendered = str(app_module.forecast_summary_cards().render())
    assert "up_color" in rendered
    assert "down_color" in rendered


def test_forecast_summary_cards_has_no_forbidden_copy():
    rendered = str(app_module.forecast_summary_cards().render()).lower()
    assert "confidence" not in rendered
    assert "guaranteed" not in rendered


def test_forecast_summary_cards_wires_model_line():
    rendered = str(app_module.forecast_summary_cards().render())
    assert "model_label" in rendered
    assert "model_text" in rendered


def test_forecast_summary_cards_aria_label_includes_model_text():
    source = inspect.getsource(app_module._summary_card)
    assert 'card["model_text"]' in source
    # aria_label expression must be a single chained concatenation ending
    # with the model_text term appended after yoy_text.
    aria_start = source.rfind("aria_label=")
    aria_expr = source[aria_start:]
    assert aria_expr.find('card["yoy_text"]') < aria_expr.find('card["model_text"]')


def test_historical_section_compiles_to_component():
    component = app_module.historical_section()
    assert isinstance(component, rx.Component)


def test_data_entry_section_compiles_to_component():
    component = app_module.data_entry_section()
    assert isinstance(component, rx.Component)


def test_index_heading_order_matches_locked_layout():
    # Phase 14: sections now live behind an rx.match on active_section rather
    # than a single flat top-to-bottom stack, so DOM order across tab panels
    # is no longer a meaningful layout guarantee (only one panel is visible
    # to the user at a time; the compiled tree still contains all match
    # arms). This test is narrowed to presence-only -- the strict ordering
    # assertion it used to make no longer corresponds to any user-facing
    # property once sections are tab-scoped instead of stacked.
    rendered = str(app_module.index().render())
    assert rendered.find("Forecast Summary") != -1
    # The em dash is JSON-escaped (—) in the compiled render tree, so
    # anchor on the surrounding literal text rather than the raw glyph.
    assert rendered.find("u2014 base / bull / bear") != -1
    assert rendered.find("Historical") != -1
    assert rendered.find("Data Entry") != -1


def test_index_has_theme_toggle():
    # Phase 11: a header toggle now flips both color-mode mechanisms.
    # Supersedes the old test_index_has_no_theme_toggle (Phase 6 predated
    # the toggle). rx.color_mode.icon()/rx.toggle_color_mode compile to
    # "resolvedColorMode"/"toggleColorMode" in the render tree, not the
    # literal string "color_mode".
    rendered = str(app_module.index().render())
    assert "toggleColorMode" in rendered
    assert "resolvedColorMode" in rendered


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
    # Phase 11: MUTED_TEXT is now DashboardState.muted_text (mode-resolved).
    assert "DashboardState.muted_text" in source
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
    # Phase 11: UP/DOWN/MUTED_TEXT are now DashboardState's mode-resolved
    # computed vars (up_color/down_color/muted_text), not flat constants.
    assert "DashboardState.up_color" in source
    assert "DashboardState.down_color" in source
    assert "DashboardState.muted_text" in source
    assert "ACCENT" not in source
    assert "DashboardState.destructive_color" not in source


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


# --- Phase 10 — CSV import control ------------------------------------------


def test_csv_import_control_compiles_to_component():
    component = app_module.csv_import_control()
    assert isinstance(component, rx.Component)


def test_csv_import_control_uses_rx_upload_with_csv_accept_and_single_file():
    source = inspect.getsource(app_module.csv_import_control)
    assert "rx.upload(" in source
    assert 'accept={"text/csv": [".csv"]}' in source
    assert "max_files=1" in source
    assert "multiple=False" in source
    assert 'id="csv_upload"' in source


def test_csv_import_control_binds_upload_files_to_handle_csv_upload():
    source = inspect.getsource(app_module.csv_import_control)
    assert "on_drop=DashboardState.handle_csv_upload(" in source
    assert 'rx.upload_files(upload_id="csv_upload")' in source


@pytest.mark.parametrize(
    "copy",
    [
        "Drag and drop a CSV file here, or click to browse.",
        "Import preview",
        "Confirm import",
        "Cancel",
        "Done",
    ],
)
def test_csv_import_control_renders_uispec_copy_verbatim(copy):
    source = inspect.getsource(app_module.csv_import_control)
    assert copy in source


def test_confirm_import_button_is_accent_not_destructive():
    source = inspect.getsource(app_module.csv_import_control)
    idx = source.index("Confirm import")
    block = source[idx : idx + 300]
    assert 'color_scheme="blue"' in block
    assert 'color_scheme="red"' not in block
    assert "DESTRUCTIVE" not in block


def test_confirm_import_button_disabled_binding_uses_can_confirm_import():
    source = inspect.getsource(app_module.csv_import_control)
    idx = source.index("Confirm import")
    block = source[idx : idx + 300]
    assert "disabled=~DashboardState.can_confirm_import" in block


def test_cancel_button_is_neutral_gray():
    source = inspect.getsource(app_module.csv_import_control)
    idx = source.index('"Cancel"')
    block = source[idx : idx + 200]
    assert 'color_scheme="gray"' in block


def test_data_entry_section_places_import_control_after_add_row():
    source = inspect.getsource(app_module.data_entry_section)
    assert source.index("add_row_button()") < source.index("csv_import_control()")


def test_csv_import_control_introduces_no_new_hex_or_px_literals():
    source = inspect.getsource(app_module.csv_import_control)
    assert re.findall(r"#[0-9A-Fa-f]{6}", source) == []
    assert re.findall(r'"\d+px"', source) == []


def test_app_py_has_no_session_calls():
    assert "rx.session" not in inspect.getsource(app_module)


# --- Phase 11 — background fix + theme toggle --------------------------------


def test_index_compiles_in_both_theme_modes():
    # index() itself does not branch on theme_mode (colors resolve via
    # DashboardState computed vars at render time), so simply confirming
    # it constructs without raising covers both modes here.
    component = app_module.index()
    assert isinstance(component, rx.Component)


def test_index_renders_html_body_style_bound_to_page_bg():
    # rx.App(style={"html, body": ...}) cannot carry a reactive backend Var
    # (it compiles into a plain module-level JS object with no React
    # context to read from -- verified via a failed `reflex export` build:
    # "reflex___state____state...dashboard_state is not defined"). Instead
    # a <style> element is rendered inside index()'s component tree, where
    # the state-context hook gets injected normally.
    rendered = str(app_module.index().render())
    assert "html, body { background: " in rendered
    assert "page_bg" in rendered


def test_header_has_exactly_one_theme_toggle_button():
    source = inspect.getsource(app_module.theme_toggle)
    assert "rx.icon_button" in source
    assert 'aria_label="Toggle dark mode"' in source
    assert source.count("rx.icon_button") == 1


def test_theme_toggle_on_click_is_two_event_chain():
    source = inspect.getsource(app_module.theme_toggle)
    assert (
        "on_click=[DashboardState.toggle_theme_mode, rx.toggle_color_mode]"
        in source
    )


def test_theme_toggle_does_not_use_color_mode_button_or_switch():
    source = inspect.getsource(app_module.theme_toggle)
    assert "rx.color_mode.button" not in source
    assert "rx.color_mode.switch" not in source
    assert "allow_system" not in source


def test_app_py_imports_no_flat_theme_color_names():
    # AST-based guard (mirrors tests/test_theme.py's approach) so the check
    # can't be fooled by these names appearing in comments/docstrings.
    import ast

    source_path = app_module.__file__
    tree = ast.parse(open(source_path).read())
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "app.theme"
        for alias in node.names
    }
    forbidden = {
        "PAGE_BG",
        "SURFACE",
        "CARD_BORDER",
        "MUTED_TEXT",
        "DESTRUCTIVE",
        "UP",
        "DOWN",
    }
    assert imported_names & forbidden == set()


def test_app_py_uses_mode_resolved_vars_for_surfaces_and_borders():
    source = inspect.getsource(app_module)
    assert "background=SURFACE" not in source
    assert "background=PAGE_BG" not in source
    assert "border=CARD_BORDER" not in source
    assert "color=MUTED_TEXT" not in source
    assert "DashboardState.surface" in source
    assert "DashboardState.card_border" in source
    assert "DashboardState.muted_text" in source
    assert "DashboardState.destructive_color" in source
    assert "DashboardState.up_color" in source
    assert "DashboardState.down_color" in source


# --- Phase 14 Plan 02: tab bar structure -------------------------------------


def test_nav_bar_compiles_to_component():
    component = app_module.nav_bar()
    assert isinstance(component, rx.Component)


def test_nav_bar_uses_controlled_radix_tabs():
    source = inspect.getsource(app_module.nav_bar)
    assert "rx.tabs.root" in source
    assert "value=DashboardState.active_section" in source
    assert "on_change=DashboardState.set_active_section" in source
    # Radix supplies role/aria-selected wiring for free; no hand-rolled
    # accessibility attributes should be added on top of it.
    assert 'role="tab' not in source
    assert "aria_selected" not in source


def test_nav_bar_has_three_verbatim_tab_labels():
    source = inspect.getsource(app_module.nav_bar)
    for label in ["Summary", "Forecast", "Data Entry"]:
        assert f'"{label}"' in source
    for value in ["summary", "forecast", "data_entry"]:
        assert f'"{value}"' in source
    # nav_bar() defines a single _trigger() helper (one rx.tabs.trigger call
    # site) invoked three times -- one per tab -- rather than three separate
    # literal rx.tabs.trigger(...) call sites.
    assert source.count("rx.tabs.trigger") == 1
    assert source.count("_trigger(") == 4  # 1 def + 3 call sites


def test_index_declares_on_mount_exactly_once():
    source_path = app_module.__file__
    with open(source_path) as f:
        lines = f.readlines()
    non_comment_lines = [line for line in lines if not line.strip().startswith("#")]
    joined = "".join(non_comment_lines)
    assert joined.count("on_mount") == 1
    normalized = " ".join(joined.split())
    assert (
        "on_mount=[ DashboardState.load_rows, DashboardState.load_markup_pct, "
        "DashboardState.load_weekly_rows, ],"
    ) in normalized


def test_data_entry_tab_groups_historical_and_data_entry():
    source = inspect.getsource(app_module._data_entry_tab)
    assert "historical_section()" in source
    assert "data_entry_section()" in source
    # Both calls must live inside the same helper, proving they mount and
    # unmount together (D-01) rather than being reachable from separate
    # branches of the tab match.
    index_source = inspect.getsource(app_module.index)
    assert "_data_entry_tab()" in index_source
    assert "historical_section()" not in index_source
    assert "data_entry_section()" not in index_source


def test_index_renders_each_section_once():
    combined_source = inspect.getsource(app_module.index) + inspect.getsource(
        app_module._data_entry_tab
    )
    for call in [
        "forecast_summary_cards()",
        "forecast_section()",
        "historical_section()",
        "data_entry_section()",
    ]:
        assert combined_source.count(call) == 1


def test_index_does_not_css_hide_sections():
    source_path = app_module.__file__
    with open(source_path) as f:
        source = f.read()
    assert re.search(r"display[^,\n]*none", source) is None
