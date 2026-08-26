# Precision Instrument Visual Redesign — Design

*2026-08-26. A full visual-identity redesign of the Reflex dashboard's
existing three tabs (Summary, Forecast, Data Entry) — no information
architecture changes, no new features. Supersedes `theme.py`'s current
token values (from the Phase 6 UX/UI redesign and Phase 11 dark-mode
pass) with a new, more distinctive palette/type/signature system. Per
`theme.py`'s own header comment, changing these constants is a
design-contract change — this doc is that re-verification.*

## 1. Direction

**Precision instrument**: dense, data-forward, quiet confidence — the
visual language of a well-made technical instrument (an oscilloscope
readout, a lab scale, a trading terminal), not a generic SaaS dashboard.
Justification: this app's one job is showing a single person numbers they
need to trust before spending money — the design should read as
*measured* rather than *friendly*.

## 2. Color

Named tokens replacing the current `LIGHT`/`DARK` dicts in
`app/app/theme.py`. Light values first, dark values in parens; both
contrast-checked below.

| Token | Light | Dark | Role |
|---|---|---|---|
| `GRAPHITE` (was implicit body text) | `#14181B` | `#EDEFF0` | Primary text/ink |
| `INSTRUMENT` (was `PAGE_BG`) | `#EEF1F3` | `#101416` | Page canvas |
| `SURFACE` | `#FFFFFF` | `#1B2124` | Card/table background (unchanged role) |
| `STEEL` (was `BORDER`) | `#7B838B` | `#828B92` | Structural borders/rules |
| `INDICATOR` (was `ACCENT`) | `#0E7C86` | `#3FC3CE` | Interactive/brand accent |
| `INDICATOR_FILL` (was `ACCENT_FILL`) | `rgba(14,124,134,0.15)` | `rgba(63,195,206,0.15)` | Accent fill/highlight |
| `SIGNAL_UP` (was `UP`) | `#15803D` | `#4ADE80` | Positive delta (unchanged — already correct) |
| `SIGNAL_DOWN` / `DESTRUCTIVE` (was `DOWN`/`DESTRUCTIVE`) | `#DC2626` | `#F87171` | Negative delta / destructive action (unchanged) |
| `MUTED_TEXT` | `#5B6167` | `#9BA1A6` | Secondary/caption text |

**Why replace `ACCENT`'s blue with `INDICATOR`'s teal-cyan:** the old
`#2563EB` is a stock SaaS blue (Tailwind `blue-600`) that reads as
"generic dashboard template," not as a deliberate choice. Teal-cyan reads
closer to oscilloscope/terminal phosphor without going all the way to the
"black background, acid-green accent" AI-design cliché this project's own
`web-artifacts-builder` guidance already flags to avoid.

**Contrast verification** (WCAG formula, computed directly — not
estimated):

Light mode:
- `GRAPHITE` on `INSTRUMENT`: 15.74:1 (need 4.5:1 normal text) ✅
- `GRAPHITE` on `SURFACE`: 17.85:1 ✅
- `INDICATOR` on `SURFACE`: 4.95:1 ✅
- `INDICATOR` on `INSTRUMENT`: 4.36:1 — borderline for *normal* text but
  clears 3:1 for large/bold text and non-text use; `INDICATOR` is only
  used for large numerals, icons, and borders in this design, never
  normal-weight body text on the canvas color, so this is acceptable
  (same reasoning `theme.py` already uses elsewhere).
- `STEEL` on `SURFACE` (non-text, need 3:1): 3.85:1 ✅
- `STEEL` on `INSTRUMENT` (non-text, need 3:1): 3.39:1 ✅ (the original
  proposed `#8A9199` failed this at 2.81:1 — darkened to `#7B838B`,
  mirroring how the existing `theme.py` already darkened `BORDER` once
  before for the same reason, per its own changelog comments)
- `SIGNAL_UP` on `SURFACE`: 5.02:1 ✅ (unchanged from current)
- `SIGNAL_DOWN` on `SURFACE`: 4.83:1 ✅ (unchanged from current)

Dark mode:
- Text on `SURFACE`/`INSTRUMENT`: 14.12:1 / 16.06:1 ✅
- `INDICATOR` on `SURFACE`: 7.68:1 ✅
- `STEEL` on `SURFACE`/`INSTRUMENT` (non-text, need 3:1): 4.70:1 / 5.34:1 ✅
- `SIGNAL_UP`/`SIGNAL_DOWN` on `SURFACE`: 9.34:1 / 5.89:1 ✅ (unchanged)

All pass. `DESTRUCTIVE`/`SIGNAL_DOWN` and `SIGNAL_UP` values are carried
over unchanged from the current tokens — they were already
contrast-verified and already carry real meaning (direction), not
decoration, so there's no reason to touch them.

## 3. Typography

Two-face pairing, both from the IBM Plex family (chosen because Plex was
designed for IBM's own technical/engineering documentation — a direct,
justifiable fit for "instrument readout," not an arbitrary swap away from
the current Radix default):

- **IBM Plex Mono** — every number that matters: summary-card figures,
  freshness-chip dates, all table cells (both Data Entry's price table and
  the Forecast table), forecast chart hover values. Monospace + tabular
  figures make columns of numbers scannable, which generic proportional
  fonts don't.
- **IBM Plex Sans** — headings, labels, body copy, button text. Replaces
  the current Radix-default font stack (effectively Inter) app-wide.

Both load via Google Fonts — the only external font source a Reflex app
(and, separately, a Claude artifact) can safely reference. Reflex's
`rx.App` accepts a `stylesheets` list for exactly this.

Existing 4-size / 2-weight type scale (`FONT_SIZE_LABEL/BODY/HEADING/DISPLAY`,
`FONT_WEIGHT_REGULAR/SEMIBOLD`) is kept as-is — the redesign changes *which
typeface* renders at each size, not the scale itself.

## 4. Layout & shared chrome

- **Radius**: `CARD_RADIUS` goes from `8px` to `4px`, and the app-level
  Radix theme radius (`rxconfig.py`'s `rx.theme(...)`) moves from its
  current default ("medium") to `"small"`. Sharper corners read as
  precise rather than soft/friendly — consistent with the direction.
- **Accent**: `rxconfig.py`'s `rx.theme(accent_color="blue")` becomes
  `accent_color="cyan"` — the closest built-in Radix palette name to the
  new `INDICATOR` hex, so Radix-native components (buttons, switches,
  focus rings) and our own hand-drawn elements (chart lines, chip
  borders) read as one consistent accent rather than two different blues.
- **Tabular numbers**: every numeric cell/figure gets Plex Mono, which is
  itself close to tabular by design; where Radix's `rx.text` renders
  inside a table cell we additionally do not need a separate
  `font-variant-numeric: tabular-nums` override, since Plex Mono glyphs
  are already fixed-width.
- No IA/structural layout changes — same three tabs, same section order
  within each tab.

## 5. Signature element: the gauge-bezel summary card

The four Forecast Summary cards (`_summary_card` in `app/app/app.py`) and
the freshness chips (`_freshness_chip`) get a distinct "instrument gauge"
treatment, replacing today's plain bordered box:

```
┌─ HDAN ──────────────┐
│ 417.85               │
│ ↓ 9.8%  vs latest     │
│ range 365 – 470       │
└──────────────────────┘
```

- A thin top rule in `STEEL`, with two small corner ticks (4px each) at
  the top-left and top-right — evoking a gauge bezel or panel-mount
  instrument frame, drawn with plain CSS borders (no images/SVG needed).
- The label (`HDAN`) sits inline with the top rule, uppercase, Plex Sans,
  small size — like an engraved panel label.
- The big figure is Plex Mono at `FONT_SIZE_DISPLAY`.
- The delta line uses `SIGNAL_UP`/`SIGNAL_DOWN` color + the existing
  arrow glyphs (`ARROW_UP`/`ARROW_DOWN`/`ARROW_FLAT` — unchanged, already
  good: direction is never color-only).
- This is the one place carrying decorative weight in the whole redesign;
  everything else (tables, forms, CSV import) stays plain and quiet per
  the "spend your boldness in one place" principle.

## 6. What's explicitly unchanged

- Both light and dark modes remain fully supported (existing toggle
  behavior untouched).
- `SIGNAL_UP`/`SIGNAL_DOWN`/`DESTRUCTIVE` hex values (already correct,
  already contrast-verified, already carry real meaning).
- Arrow glyphs (`ARROW_UP`/`ARROW_DOWN`/`ARROW_FLAT`).
- Spacing scale (`SPACE_XS` .. `SPACE_XXL`).
- Number formatting (`NUMBER_FORMAT`, `PLOTLY_HOVER_NUMBER`).
- All IA/behavior: tabs, forms, table interactions, CSV import states,
  forecast/export flows — this is a skin change, not a feature change.

## 7. Testing

- `app/tests/test_theme.py` / `test_theme_tokens.py` assert on the
  current token *values* in places — these need updating to the new
  values, not just re-running (the whole point of the change is the
  values are different). Any test asserting a specific contrast ratio
  gets the newly-computed ratio.
- Visual verification in the running app (light + dark, all three tabs)
  is required before considering this done — token changes alone don't
  prove out how Plex Mono actually reads in a real Radix table at
  `FONT_SIZE_BODY`.
