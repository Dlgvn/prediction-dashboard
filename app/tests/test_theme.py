"""Unit coverage for app/app/theme.py's locked design tokens."""

from app import theme


def test_accent_is_locked_hex():
    # 2026-08-26 precision-instrument redesign: teal-cyan INDICATOR accent
    # (#0E7C86) replaces the prior generic blue (#2563EB). 4.95:1 against
    # SURFACE white, meets WCAG AA 4.5:1 normal-text threshold.
    assert theme.ACCENT == "#0E7C86"


def test_spacing_values_are_multiples_of_four():
    spacing_tokens = [
        theme.SPACE_XS,
        theme.SPACE_SM,
        theme.SPACE_MD,
        theme.SPACE_LG,
        theme.SPACE_XL,
        theme.SPACE_XXL,
    ]
    for value in spacing_tokens:
        assert value.endswith("px")
        px = int(value[:-2])
        assert px % 4 == 0


def test_exactly_four_font_size_constants_with_locked_values():
    sizes = {
        theme.FONT_SIZE_LABEL,
        theme.FONT_SIZE_BODY,
        theme.FONT_SIZE_HEADING,
        theme.FONT_SIZE_DISPLAY,
    }
    assert sizes == {"12px", "14px", "20px", "28px"}
    assert len(sizes) == 4


def test_only_two_font_weights_declared():
    weights = {theme.FONT_WEIGHT_REGULAR, theme.FONT_WEIGHT_SEMIBOLD}
    assert weights == {"400", "600"}
    assert len(weights) == 2


def test_all_locked_color_hex_values_present():
    # 2026-08-26 precision-instrument redesign: PAGE_BG, BORDER, ACCENT,
    # and MUTED_TEXT were retuned to the new palette; SURFACE, DESTRUCTIVE,
    # and UP are unchanged (already correct/contrast-verified).
    for hex_value in (
        "#EEF1F3",
        "#FFFFFF",
        "#7B838B",
        "#0E7C86",
        "#DC2626",
        "#15803D",
    ):
        assert hex_value in (
            theme.PAGE_BG,
            theme.SURFACE,
            theme.BORDER,
            theme.ACCENT,
            theme.DESTRUCTIVE,
            theme.UP,
            theme.DOWN,
        )


def test_theme_module_imports_with_no_third_party_dependency():
    # Module already imported above without error; assert it declares no
    # import statements at all (zero third-party imports requirement),
    # via AST parsing so docstring prose mentioning "import" is ignored.
    import ast

    with open(theme.__file__) as fh:
        tree = ast.parse(fh.read())

    import_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    assert import_nodes == []
