---
phase: 13-model-provenance-display
plan: 02
subsystem: ui
tags: [reflex, ui, forecast-summary-cards, provenance]

# Dependency graph
requires:
  - phase: 13-model-provenance-display
    plan: 01
    provides: model_label/model_text keys on every summary_cards dict, sourced from MODEL_INFO
provides:
  - Visible "Model:" line on all 4 forecast summary cards, rendered from model_label/model_text
  - aria_label extended to include model_text for accessibility parity
affects: [ui-model-provenance-badge]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New card line follows the existing high/low hstack structure (muted label + regular-weight value, no arrow, no color/font-weight)"

key-files:
  created: []
  modified:
    - app/app/app.py
    - app/tests/test_app_components.py

key-decisions:
  - "Model hstack placed as the last child inside the has_data == 'yes' fragment, directly after the YoY hstack, per 13-CONTEXT.md D-02 card line order"
  - "No new rx.cond branch added — model_text is always non-empty when has_data == 'yes', so the line is unconditional within that branch"
  - "aria_label extended with a single additional ' ' + card[\"model_text\"] term, keeping the existing single-expression structure intact"

patterns-established:
  - "Provenance display line pattern: muted rx.text(label + ':') + regular rx.text(value), spacing='2', mirroring the high/low line exactly"

requirements-completed: [VIS-05]

# Metrics
duration: 15min
completed: 2026-08-25
---

# Phase 13 Plan 02: Model Provenance Display (Rendering) Summary

**Added the "Model:" line to all 4 forecast summary cards, sourced from the model_label/model_text state vars built in 13-01, and human-verified in a live browser in both light and dark mode**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 2

## Accomplishments
- Added a new `rx.hstack` model line to `_summary_card()` in `app/app/app.py`, structured identically to the existing high/low line (muted label, regular-weight value, no arrow, no color/font-weight)
- Placed as the last line inside the `has_data == "yes"` fragment, directly after the YoY hstack, per the locked card line order
- Extended the `aria_label` expression to append `card["model_text"]` after `card["yoy_text"]`
- Added 2 new component tests: one asserting `model_label`/`model_text` appear in the compiled render tree, one asserting the aria_label expression's ordering (yoy_text before model_text)
- No changes to `app/app/theme.py`; no new tokens, colors, or components introduced
- Human browser verification confirmed all four exact rendered strings, correct line ordering, correct styling (muted label/regular value, no bold/color), legibility in both light and dark mode, and no overflow at 390px mobile width

## Task Commits

1. **Task 1: Add the Model line to _summary_card and extend aria_label** - `396be10` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `app/app/app.py` - Added the model `rx.hstack` line to `_summary_card()`; extended `aria_label` expression
- `app/tests/test_app_components.py` - Added `test_forecast_summary_cards_wires_model_line` and `test_forecast_summary_cards_aria_label_includes_model_text`

## Decisions Made
- Model line placed last, after YoY, matching 13-CONTEXT.md D-02's locked card line order
- No arrow glyph, no icon, no `rx.cond` color branch on the model line — it is a plain informational line like high/low, not a directional value
- aria_label kept as a single chained expression rather than restructured

## Deviations from Plan

None - plan executed exactly as written.

## Human Verification (Task 2 Checkpoint)

Verified live in browser (`reflex run`, http://localhost:3000):
1. HDAN card: `Model: SARIMAX · 13.3% typical error` — confirmed exact match
2. PPAN card: `Model: Direct-OLS VAR · 23.8% typical error` — confirmed exact match
3. Diesel MNT card: `Model: Derived (Diesel USD × FX)` — confirmed no `%`, no "typical error", no "N/A"/dash
4. FX Rate card: `Model: Naive · 1.7% typical error` — confirmed exact match
5. Model line confirmed as the last line on all 4 cards, directly below YoY
6. Styling confirmed matching the high/low line: muted/small label, regular-weight value, no bold/color
7. Dark mode toggle confirmed legible with correct dark-mode text colors
8. Resized to 390px mobile width: confirmed no horizontal overflow (`document.body.scrollWidth === window.innerWidth === 390`), single-column reflow, no text clipping on any card

No discrepancies found. Approved by developer.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- VIS-05 fully satisfied — Phase 13 (model-provenance-display) is complete
- Full test suite green: 337 passed
- No theme.py changes; no new dependencies

---
*Phase: 13-model-provenance-display*
*Completed: 2026-08-25*

## Self-Check: PASSED
