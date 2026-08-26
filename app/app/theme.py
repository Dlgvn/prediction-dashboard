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

PAGE_BG = "#EEF1F3"
SURFACE = "#FFFFFF"
# 2026-08-26 precision-instrument redesign: darkened from #8E9096 to
# #7B838B (a cooler blue-gray) to clear WCAG 3:1 non-text-boundary
# contrast against the new PAGE_BG (#EEF1F3, 3.39:1) as well as SURFACE
# (3.85:1) — the redesign's lighter/cooler PAGE_BG made the prior value
# fail against PAGE_BG specifically (2.81:1 measured).
BORDER = "#7B838B"
# 2026-08-26 precision-instrument redesign: teal-cyan accent (was generic
# blue #2563EB) — 4.95:1 against SURFACE white (WCAG AA 4.5:1 threshold).
ACCENT = "#0E7C86"
ACCENT_FILL = "rgba(14,124,134,0.15)"
DESTRUCTIVE = "#DC2626"
NEUTRAL_LINE = "#697177"
UP = "#15803D"
DOWN = "#DC2626"
# 2026-08-26 precision-instrument redesign: darkened from #71717A to
# #5B6167 within the same neutral hue — 6.27:1 against SURFACE (was
# already passing; kept comfortably above threshold after the palette's
# other tones shifted cooler, for visual consistency of the neutral family).
MUTED_TEXT = "#5B6167"

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
    # 2026-08-26 precision-instrument redesign: darkened from #18181B to
    # #101416 (cooler near-black) to match the light mode's cooler
    # PAGE_BG shift. No contrast pairing (background reference only).
    "PAGE_BG": "#101416",
    # 2026-08-26 precision-instrument redesign: #1B2124 (was #27272A) —
    # cooler card layer matching the new PAGE_BG hue family. No contrast
    # pairing (background reference only).
    "SURFACE": "#1B2124",
    # 2026-08-26 precision-instrument redesign: #828B92 (was #71717A) —
    # 4.70:1 against the new SURFACE dark (threshold 3:1 non-text).
    "BORDER": "#828B92",
    # 2026-08-26 precision-instrument redesign: brightened teal-cyan (was
    # #60A5FA blue) — 7.68:1 against SURFACE dark (threshold 4.5:1).
    "ACCENT": "#3FC3CE",
    "ACCENT_FILL": "rgba(63,195,206,0.15)",
    # Unchanged hex from before the redesign, but ratio vs the new
    # SURFACE dark recalculated: 5.89:1 (was 5.39:1 vs the old SURFACE).
    "DESTRUCTIVE": "#F87171",
    "NEUTRAL_LINE": "#A1A1AA",
    # Unchanged hex; ratio vs new SURFACE dark recalculated: 9.34:1.
    "UP": "#4ADE80",
    # Same value as DESTRUCTIVE dark, reused — mirrors light mode's
    # DOWN == DESTRUCTIVE reuse. Ratio vs new SURFACE dark: 5.89:1.
    "DOWN": "#F87171",
    # 2026-08-26 precision-instrument redesign: #9BA1A6 (was #A1A1AA) —
    # 6.24:1 against SURFACE dark (threshold 4.5:1).
    "MUTED_TEXT": "#9BA1A6",
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

CARD_RADIUS = "4px"
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
