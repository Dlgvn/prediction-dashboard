"""Unit coverage for app/app/theme.py's locked design tokens."""

import re

from app import theme


def test_accent_is_locked_hex():
    assert theme.ACCENT == "#3B82F6"


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
    for hex_value in (
        "#FAFAFA",
        "#FFFFFF",
        "#E4E4E7",
        "#3B82F6",
        "#DC2626",
        "#16A34A",
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


def test_no_dark_mode_or_theme_toggle_token():
    with open(theme.__file__) as fh:
        lines = fh.readlines()
    code_lines = [line for line in lines if not line.strip().startswith("#")]
    joined = "".join(code_lines)
    assert re.search(r"dark|toggle", joined, re.IGNORECASE) is None


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
