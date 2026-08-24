"""Key-parity and WCAG contrast coverage for app/app/theme.py's DARK tokens.

Contrast ratios are computed locally (not imported from theme.py, which
must stay function-light and dependency-free) using the WCAG 2.1
relative-luminance formula, and cross-checked against the exact figures
recorded in 11-UI-SPEC.md.
"""

import pytest

from app import theme

EXPECTED_KEYS = frozenset(
    {
        "PAGE_BG",
        "SURFACE",
        "BORDER",
        "ACCENT",
        "ACCENT_FILL",
        "DESTRUCTIVE",
        "NEUTRAL_LINE",
        "UP",
        "DOWN",
        "MUTED_TEXT",
    }
)


def _srgb_channel_to_linear(channel: float) -> float:
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    r_lin, g_lin, b_lin = (_srgb_channel_to_linear(c) for c in (r, g, b))
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    lum_a = _relative_luminance(hex_a)
    lum_b = _relative_luminance(hex_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# (a) Key parity
# ---------------------------------------------------------------------------


def test_dark_and_light_tokens_have_identical_key_sets():
    assert set(theme.tokens("light")) == set(theme.tokens("dark"))


def test_token_key_set_matches_locked_10_key_frozenset():
    assert set(theme.tokens("light")) == EXPECTED_KEYS
    assert set(theme.tokens("dark")) == EXPECTED_KEYS


# ---------------------------------------------------------------------------
# (b) Contrast table — each dark text/boundary token vs DARK["SURFACE"],
# reproducing the exact ratios recorded in 11-UI-SPEC.md within 0.05.
# ---------------------------------------------------------------------------

CONTRAST_TABLE = [
    ("BORDER", 3.08, 3.0),
    ("ACCENT", 5.86, 4.5),
    ("DESTRUCTIVE", 5.39, 4.5),
    ("UP", 8.55, 4.5),
    ("DOWN", 5.39, 4.5),
    ("MUTED_TEXT", 5.82, 4.5),
]


@pytest.mark.parametrize("token_key,expected_ratio,threshold", CONTRAST_TABLE)
def test_dark_token_meets_contrast_threshold_and_matches_spec(
    token_key, expected_ratio, threshold
):
    surface_dark = theme.DARK["SURFACE"]
    token_value = theme.DARK[token_key]
    measured = contrast_ratio(token_value, surface_dark)

    assert measured >= threshold
    assert measured == pytest.approx(expected_ratio, abs=0.05)


# ---------------------------------------------------------------------------
# (c) Regression guard — rejected BORDER candidate must stay rejected.
# ---------------------------------------------------------------------------


def test_rejected_border_candidate_stays_below_threshold():
    rejected_candidate = "#52525B"
    measured = contrast_ratio(rejected_candidate, theme.DARK["SURFACE"])
    assert measured < 3.0


# ---------------------------------------------------------------------------
# (d) DOWN mirrors DESTRUCTIVE reuse in dark mode too.
# ---------------------------------------------------------------------------


def test_dark_down_equals_dark_destructive():
    assert theme.tokens("dark")["DOWN"] == theme.tokens("dark")["DESTRUCTIVE"]


# ---------------------------------------------------------------------------
# (e) Unrecognized mode falls back to LIGHT (D-02 safe default).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["", "system", "unrecognized-mode"])
def test_tokens_falls_back_to_light_for_unrecognized_mode(mode):
    assert theme.tokens(mode) == theme.LIGHT
