"""Design token module for the Phase 6 UX/UI redesign.

Every color, spacing, and typography value used by the redesign resolves
from this single Python module — no scattered literals in state.py or
app.py. Values are transcribed VERBATIM from
.planning/phases/06-ux-ui-redesign/06-UI-SPEC.md; that document is the
source of truth. Changing a constant here is a design-contract change,
not a routine code edit — re-verify against 06-UI-SPEC.md first.

Dependency-free by design (no Reflex import, no functions) so both
state.py's figure builders and app.py's components can import these
constants without pulling in the Reflex runtime.
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
