"""Design token module for the Phase 6 UX/UI redesign, extended in Phase 11
with dark-mode tokens.

Every color, spacing, and typography value used by the redesign resolves
out of this single Python module — no scattered literals in state.py or
app.py. Light-mode values are transcribed VERBATIM from
.planning/phases/06-ux-ui-redesign/06-UI-SPEC.md; dark-mode values are
transcribed VERBATIM from
.planning/phases/11-background-fix-theme-toggle/11-UI-SPEC.md. Those
documents are the source of truth. Changing a constant here is a
design-contract change, not a routine code edit — re-verify against the
relevant UI-SPEC first.

Dependency-free by design (no Reflex import) so both state.py's figure
builders and app.py's components can import these constants without
pulling in the Reflex runtime. `tokens(mode)` is the mode-resolution
entry point: it returns the DARK dict when `mode == "dark"` and the
LIGHT dict otherwise (light is always the safe default, per D-02).
"""

# ---------------------------------------------------------------------------
# Color (06-UI-SPEC.md "Color" section)
# ---------------------------------------------------------------------------

PAGE_BG = "#FAFAFA"
SURFACE = "#FFFFFF"
# Amended in Task 06-03 (responsive/a11y pass): #E4E4E7 measured 1.27:1
# against SURFACE, below the WCAG 3:1 non-text-boundary threshold.
# Darkened within the same neutral-gray hue to #8E9096 (3.19:1 measured).
BORDER = "#8E9096"
# Amended in Task 06-03: #3B82F6 measured 3.68:1 with a white label,
# below the WCAG 4.5:1 normal-text threshold. Darkened within the same
# blue hue to #2563EB (5.17:1 measured).
ACCENT = "#2563EB"
ACCENT_FILL = "rgba(37,99,235,0.15)"
DESTRUCTIVE = "#DC2626"
NEUTRAL_LINE = "#697177"
# Amended in Task 06-03: #16A34A measured 3.30:1 against SURFACE, below
# the WCAG 4.5:1 normal-text threshold. Darkened within the same green
# hue to #15803D (5.02:1 measured).
UP = "#15803D"
DOWN = "#DC2626"
# Radix gray.11-equivalent neutral gray for muted/secondary text.
MUTED_TEXT = "#71717A"

# LIGHT dict: same 10 light-mode literals above, referenced (not
# re-typed) so there is exactly one literal per light color.
LIGHT: dict[str, str] = {
    "PAGE_BG": PAGE_BG,
    "SURFACE": SURFACE,
    "BORDER": BORDER,
    "ACCENT": ACCENT,
    "ACCENT_FILL": ACCENT_FILL,
    "DESTRUCTIVE": DESTRUCTIVE,
    "NEUTRAL_LINE": NEUTRAL_LINE,
    "UP": UP,
    "DOWN": DOWN,
    "MUTED_TEXT": MUTED_TEXT,
}

# ---------------------------------------------------------------------------
# Dark tokens (11-UI-SPEC.md "Color" section — bespoke, hand-picked per
# D-03, NOT a mechanical invert of LIGHT). All ratios measured against
# SURFACE dark (#27272A), the dark-mode card/chart-figure background —
# same pairing basis Phase 6 used for LIGHT (measuring against SURFACE).
# ---------------------------------------------------------------------------

DARK: dict[str, str] = {
    # Darkest layer — page canvas beneath cards. No contrast pairing
    # (background reference, not text/boundary).
    "PAGE_BG": "#18181B",
    # Card layer — one step lighter than PAGE_BG, mirrors the light-mode
    # PAGE_BG -> SURFACE step direction. No contrast pairing.
    "SURFACE": "#27272A",
    # Amended in Task 11-01: #52525B measured 1.92:1 against SURFACE dark,
    # below the WCAG 3:1 non-text-boundary threshold. Lightened within the
    # same neutral-gray hue to #71717A (3.08:1 measured, threshold 3:1).
    "BORDER": "#71717A",
    # Measured 5.86:1 against SURFACE dark (threshold 4.5:1 normal text).
    "ACCENT": "#60A5FA",
    # Fill only, not a contrast-tested pairing — matching rgba of ACCENT
    # dark, mirrors light mode's ACCENT_FILL derivation.
    "ACCENT_FILL": "rgba(96,165,250,0.15)",
    # Measured 5.39:1 against SURFACE dark (threshold 4.5:1 normal text).
    "DESTRUCTIVE": "#F87171",
    # Chart line color — reuses MUTED_TEXT dark's hue family. Not
    # independently re-measured (chart-line legibility is visual, not a
    # text-contrast pairing).
    "NEUTRAL_LINE": "#A1A1AA",
    # Measured 8.55:1 against SURFACE dark (threshold 4.5:1 normal text).
    "UP": "#4ADE80",
    # Same value as DESTRUCTIVE dark, reused — mirrors light mode's
    # DOWN == DESTRUCTIVE reuse.
    # Measured 5.39:1 against SURFACE dark (threshold 4.5:1 normal text).
    "DOWN": "#F87171",
    # Measured 5.82:1 against SURFACE dark (threshold 4.5:1 normal text).
    "MUTED_TEXT": "#A1A1AA",
}


def tokens(mode: str) -> dict[str, str]:
    """Resolve the color token dict for the given theme mode.

    Returns DARK when mode == "dark", else LIGHT (light is always the
    safe default per D-02 — no third "system" state is exposed).
    """
    if mode == "dark":
        return DARK
    return LIGHT


# ---------------------------------------------------------------------------
# Spacing scale (06-UI-SPEC.md "Spacing Scale" section)
# No 3xl token this phase — UI-SPEC declares it unused (single-column
# layout, no page-level multi-region spacing needed).
# ---------------------------------------------------------------------------

SPACE_XS = "4px"
SPACE_SM = "8px"
SPACE_MD = "16px"
SPACE_LG = "24px"
SPACE_XL = "32px"
SPACE_XXL = "48px"

# ---------------------------------------------------------------------------
# Typography (06-UI-SPEC.md "Typography" section)
# Exactly 4 sizes / 2 weights per contract.
# ---------------------------------------------------------------------------

FONT_SIZE_LABEL = "12px"
FONT_SIZE_BODY = "14px"
FONT_SIZE_HEADING = "20px"
FONT_SIZE_DISPLAY = "28px"

FONT_WEIGHT_REGULAR = "400"
FONT_WEIGHT_SEMIBOLD = "600"

# Radix Themes `size` prop equivalents, so app.py maps props without
# re-deriving the size->px mapping.
RADIX_SIZE_LABEL = "1"
RADIX_SIZE_BODY = "2"
RADIX_SIZE_HEADING = "4"

# ---------------------------------------------------------------------------
# Shared surface chrome
# ---------------------------------------------------------------------------

CARD_RADIUS = "8px"
CARD_BORDER = f"1px solid {BORDER}"
CARD_PADDING = SPACE_MD

# ---------------------------------------------------------------------------
# Direction glyphs (D-11: direction is never conveyed by color alone)
# ---------------------------------------------------------------------------

ARROW_UP = "↑"
ARROW_DOWN = "↓"
ARROW_FLAT = "→"

# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------

NUMBER_FORMAT = ",.2f"
PLOTLY_HOVER_NUMBER = "%{y:,.2f}"
