# Phase 8: Forecast Context Enrichment — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add historical high/low and year-over-year (YoY) percentage change to the existing four forecast summary cards (HDAN, PPAN, Diesel MNT, FX). Purely additive presentational enrichment — no forecasting logic changes, no new state beyond new computed vars, no changes to the fan chart, forecast table, or Data Entry table (Phase 7's work).

In scope: two new computed values per summary card, rendered as new lines appended to `_summary_card()`.
Out of scope: "drivers"/attribution text (deferred per v1.2 REQUIREMENTS.md Out of Scope), changes to forecast models or bands, weekly-mode stats.
</domain>

<decisions>
## Implementation Decisions

### Historical high/low
- **D-01:** All-time high/low — the highest and lowest value ever recorded for that series across the full stored history (`self.rows`, unaffected by Phase 7's `visible_rows` windowing — this must read full history, never the windowed view).

### Year-over-year % change
- **D-02:** YoY compares the latest actual to the actual from the same calendar month, one year prior (e.g. latest = Jul 2026 → compare against Jul 2025's actual for that series). Not "12 rows back" — must match by calendar month/year, tolerating any data gaps.
- **D-03 (edge case, Claude's discretion resolved):** If no actual exists for the same month one year prior (data gap or history <12 months), YoY is not computable — render as empty/absent (`""`) rather than falling back to a different comparison, consistent with the existing `direction == "flat"` + empty `delta_text` pattern already used for the vs.-latest-actual case in `summary_cards`.

### Card layout
- **D-04:** High/low and YoY are appended as two additional compact lines below the existing card content (label → big number → expected range → vs.-latest-actual direction → **NEW: high/low line → NEW: YoY line**), not a replacement of any existing line. Style matches the existing muted-label + value line pattern already used for "Expected range".

### Claude's Discretion
- Exact copy wording for the two new lines (e.g. "All-time range:" / "YoY:") — follow the existing card copy pattern ("Expected range:") for consistency; should not collide with the existing D-13 "range" wording rule from Phase 6 (this is a different range — historical, not forecast — so wording must clearly distinguish it, e.g. "All-time high/low" not "Expected range").
- Whether high/low is one combined line ("High: $X · Low: $Y") or two separate lines — pick whichever reads cleanest against the existing card width/UI-SPEC spacing tokens.
- diesel_mnt derivation reuse: `.planning/research/PITFALLS.md` flags that the `diesel_usd_ton * fx_rate * (1 + markup_pct/100)` formula is already duplicated in 2-3 places in `state.py`. This phase MUST NOT add a third/fourth duplication — extract or reuse a single shared helper for computing the diesel_mnt series from `self.rows` before adding high/low/YoY logic for that series specifically.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/state.py` — `SUMMARY_CARD_SERIES` (line ~102), `summary_cards` computed var (line ~376), `_latest_actual_for` helper (line ~455) — the pattern to extend, NOT reimplement from scratch
- `app/app/app.py` — `_summary_card()` render function — where the two new lines get added
- `app/app/theme.py` — design tokens (muted text color, label sizing) already used for the "Expected range" line — reuse for visual consistency

### v1.2 milestone research (MANDATORY)
- `.planning/research/PITFALLS.md` — the `diesel_mnt` derivation duplication warning (2-3 existing occurrences); this phase must not add a 3rd/4th copy of `diesel_usd_ton * fx_rate * (1 + markup_pct/100)` — extract a shared helper first
- `.planning/research/ARCHITECTURE.md` — confirms high/low and YoY are "cheap additive `@rx.var`s following the existing `freshness_chips`/`summary_cards` flat-dict pattern — no forecasting.py changes needed"
- `.planning/research/STACK.md` — confirms pure pandas (`.min()/.max()/.pct_change()`) is sufficient, no new library

### Prior phase precedent
- `.planning/phases/07-table-pagination-windowing/07-CONTEXT.md` — establishes that `self.rows` must stay the untouched full-history source; this phase's high/low/YoY computations must read `self.rows`, never `visible_rows` (which only exists for the Data Entry table's display)
- `.planning/phases/06-ux-ui-redesign/06-CONTEXT.md` D-13 — "Expected range" wording is reserved for the FORECAST bull/bear range; this phase's historical high/low needs distinctly different wording to avoid ambiguity with that existing term

### Project-level
- `.planning/REQUIREMENTS.md` — FCST-08, FCST-09
- `.planning/ROADMAP.md` — Phase 8 entry

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_latest_actual_for(key)` — existing helper already scans `self.rows` for the latest non-None value per series, including the diesel_mnt derivation. High/low and YoY logic should follow/extend this same scanning pattern rather than introducing a new one.
- `summary_cards`'s flat-string-dict-per-card shape — the two new fields (high/low text, YoY text) should be added as new keys on the same dict, not a separate computed var, to keep one card = one dict = one `rx.foreach` item.

### Established Patterns
- All derived per-series values are computed inside the single `summary_cards` `@rx.var`, iterating `SUMMARY_CARD_SERIES` — new stats should be computed inside this same loop, not a new parallel var, to avoid duplicating the "how do I get diesel_mnt as a full series" logic a third time.
- Empty/uncomputable values render as `""` (empty string), never `null`/`None`, per the existing `has_data == "no"` and flat-string-dict discipline established in Phase 6.

### Integration Points
- `_summary_card()` in app.py needs two new `rx.text`/`rx.hstack` lines reading two new dict keys from the `summary_cards` var.

</code_context>

<specifics>
## Specific Ideas

No new visual references — this phase extends the existing Phase 6 card design, not a new pattern.

</specifics>

<deferred>
## Deferred Ideas

- "Drivers"/forecast-attribution explanation — explicitly out of scope per REQUIREMENTS.md Out of Scope (would require either a low-value static caption or real model-coefficient attribution, a forecasting research question).

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 8-forecast-context-enrichment*
*Context gathered: 2026-08-24*
