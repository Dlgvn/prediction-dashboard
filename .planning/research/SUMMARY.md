# Project Research Summary

**Project:** Prediction Dashboard — v1.2 (Data Entry Fix & Forecast Enrichment)
**Domain:** Single-user Reflex (Python) commodity/FX forecasting dashboard — retrofit milestone
**Researched:** 2026-08-24
**Confidence:** HIGH

## Executive Summary

This milestone retrofits four capabilities onto an already-shipped, well-structured Reflex dashboard: table pagination/windowing (fixing a real bug — 2,950+ DOM nodes hanging the browser at 167 rows), CSV bulk import, richer forecast context (historical high/low, YoY % change, "drivers" text), and general performance hygiene. No new third-party dependencies are needed — `rx.upload`, `@rx.var(cache=True)`, and the already-pinned pandas/openpyxl/plotly cover every new capability. The existing architecture (`DashboardState` as sole DB-access boundary, flat list-of-dict computed vars, `forecast_all()` single-call-site rule) is sound and should be extended, not replaced.

The dominant risk is not technology selection but retrofit correctness: `self.rows` is currently overloaded as both "what the table displays" and "the full-history source every derived computation (forecasts, charts, freshness chips, export) depends on." Naively slicing `self.rows` for pagination — the fastest-looking implementation — would silently corrupt forecasts, charts, and freshness data across the entire app. Every research stream (architecture and pitfalls) converges on the same fix: add a new, purely additive `visible_rows` computed var for display, and never touch `self.rows` itself. CSV import carries the second-largest risk: it must reuse the exact same `validate_numeric`/`validate_date` functions as manual entry (not a forked path) and must not open a second `rx.session()` outside `state.py`, or it will violate the app's single-DB-path architecture rule and let imported data silently bypass the correctness rules manual entry enforces.

The recommended approach is to build pagination first (self-contained, fixes the reported bug, zero dependency on other features), then low-risk additive forecast-context stats (reusing existing `_latest_actual_for`/`diesel_mnt` derivation to avoid drift), then export polish (independent, low risk), and CSV import last as its own phase — it is the only feature requiring a genuinely new component type, a new validation-at-scale path, and an unresolved product decision (upsert semantics for duplicate months).

## Key Findings

### Recommended Stack

No new packages required. The existing stack (Reflex 0.9.8.post1, SQLite via `rx.Model`, statsmodels 0.14.6, pandas 3.0.5, openpyxl 3.1.5, `rx.plotly` 6.9.0) already covers all four new capabilities via built-in Reflex components and library features not yet used.

**Core technologies (all already installed):**
- `rx.upload` + `rx.upload_files`: CSV bulk-import UI — built-in Reflex component, backend handler reads bytes via `await file.read()`
- `@rx.var(cache=True)` (computed vars, default in Reflex): the correct mechanism for windowed table pagination and new stats — only recomputes when its actual dependencies change
- pandas `.min()/.max()/.pct_change()/.rolling()`: historical high/low and % change stats, no new stats library needed
- openpyxl multi-sheet/formatting API: richer Excel export UX (column widths, number formats, native Excel charts via `openpyxl.chart.LineChart`) without adding `xlsxwriter`

### Expected Features

This is a single-user, monthly-cadence app — most "enterprise CSV import" and "BI dashboard" patterns from generic research are explicitly downgraded to anti-features here (fuzzy column-mapping, streaming validation for large files, infinite scroll, real-time refresh, AI anomaly detection all solve problems this app doesn't have).

**Must have (table stakes, v1.2):**
- Excel export gains a second sheet with base/bull/bear forecast data, reusing existing forecast output
- Number formatting (units, decimals, thousands separators) on all exported columns
- Historical high/low and % change vs. same-period-last-year on forecast summary cards (where ≥12 months of history exists)
- Simple CSV bulk import: fixed expected column order, in-page preview + row-level validation errors, explicit confirm-to-commit step — no wizard, no fuzzy mapping

**Should have (differentiators, v1.x follow-up):**
- Native Excel line-chart embedded in the export's forecast sheet
- Templated "drivers" explanation text per series (static caption, not ML/LLM-generated — model families are fixed/known per PROJECT.md)

**Defer (v2+):**
- Column-mapping UI for CSV import (only if a second real import source with different layout materializes)
- Any anomaly detection or AI-generated forecast commentary (depends on explicitly-deferred LLM/news provider research)
- Weekly-cadence YoY/context stats (blocked on weekly data-cadence gap, PROJECT.md §6)

### Architecture Approach

`DashboardState(rx.State)` is the sole DB-access boundary; `app.py` holds pure render functions; `self.rows: list[PriceRow]` is fully reloaded (not incrementally patched) after every write and is the authoritative source for every derived var (charts, `forecast_results`, freshness chips, export). The actual reported bug is a rendering-scale problem (unwindowed `rx.foreach` generating O(rows × 17 cols) DOM nodes), not a DB or state-size problem — SQLite reads at this scale are sub-millisecond.

**Major components:**
1. `DashboardState` (state.py) — all DB access, computed vars (`rows`, `forecast_results`, `summary_cards`, `freshness_chips`), the single call site for `forecast_all()`
2. `app.py` — pure render/component functions, reads state vars via `rx.foreach`/`rx.cond`, never touches DB
3. `models.py` — `PriceRow` (17 cols) and `AppSetting` flat `rx.Model` tables
4. `forecasting.py` — `forecast_all()` dispatcher (VAR for HDAN/PPAN, AR-lag-2-on-Brent for Diesel, AR(1) for FX), called only from `forecast_results`
5. `validators.py` — dependency-free `validate_date`/`validate_numeric`, the single source of truth for cell validation, must be reused (not forked) by CSV import

**Build order (from architecture research):** (1) pagination/windowing — self-contained, ships first; (2) historical high/low & % change stats — independent, low risk; (3) export polish — independent, low risk; (4) "drivers" context — needs scope decision (static caption vs. real attribution) before estimation; (5) CSV bulk import — build last as its own phase, highest complexity and risk.

### Critical Pitfalls

1. **Pagination breaks full-history computed vars if `self.rows` itself is sliced** — `forecast_results`, `historical_chart_figure`, `freshness_chips`, `summary_cards`, and export all assume `self.rows` is complete history. Fix: add a new `visible_rows` computed var for display only; never mutate/slice `self.rows`.
2. **Stale edit/delete state across pagination boundary** — `editing_key`/`pending_delete` have no awareness of pagination; must be explicitly reset (`cancel_edit()`/`cancel_pending_delete()`) on every page-change/toggle event.
3. **CSV import validation drift from manual entry** — must reuse `validate_numeric`/`validate_date` exactly, not a forked/weaker path; must also catch batch-internal duplicate months (two rows in the same CSV for the same month), which the current single-row validator doesn't need to handle today.
4. **CSV import violating the single-DB-path architecture rule** — bulk import logic should be a pure, DB-free function (parse/validate), with only `DashboardState` opening the actual `rx.session()` bulk write.
5. **New forecast stats drifting from `summary_cards`** — `diesel_mnt` is a derived value (usd × fx × markup) computed in three places already; any new high/low/%-change stat must call a shared helper, not reimplement the loop, or numbers will silently disagree on-page.

## Implications for Roadmap

### Phase 1: Table Pagination / Windowing (also serves as the Performance phase)
**Rationale:** Fixes the actual reported bug (browser hang at 167 rows), is fully self-contained, and has zero dependency on the other three features — ship first.
**Delivers:** `show_all_history` bool + `visible_rows` computed var + repointed `rx.foreach`, with explicit edit/delete-state reset on page/toggle events.
**Addresses:** "Table shows recent history by default with a way to see everything" (FEATURES.md table stakes).
**Avoids:** Pitfall 1 (full-history computed vars silently broken), Pitfall 2 (stale edit/delete state), Pitfall 3 (`rx.foreach` key stability under list swaps).

### Phase 2: Forecast Context Enrichment (high/low, YoY % change)
**Rationale:** Independent of pagination; low risk; follows the exact same list-of-dict `@rx.var` pattern already established by `summary_cards`/`freshness_chips`.
**Delivers:** New computed vars for historical high/low and % change vs. same-period-last-year, rendered as additional summary-card-style components.
**Uses:** Hand-rolled Python loops (consistent with existing codebase style, not pandas-inside-computed-vars) over `self.rows`.
**Implements:** Reuse of a shared `_diesel_mnt_series`/`_latest_actual_for` helper to avoid drift (Pitfall 6); no second call site to `forecast_all()` (Pitfall 7).

### Phase 3: Excel Export Polish
**Rationale:** Independent of Phases 1-2; touches only `_export_bytes`/`export_to_excel`; low risk, can slot in anytime.
**Delivers:** Multi-sheet export (Data + Forecast base/bull/bear), number formatting, optionally an embedded native Excel line chart.
**Addresses:** "Excel export with a real multi-sheet workbook mirroring the existing forecast model structure" (FEATURES.md differentiator).
**Avoids:** Silently violating the documented D-08 "actuals table only" UI-spec constraint without an explicit scope decision to change it.

### Phase 4: CSV Bulk Import
**Rationale:** Highest complexity — new component type (`rx.upload`), new validation-at-scale path, and an unresolved product decision (upsert semantics for duplicate months). Sequence last so scope/risk is well understood.
**Delivers:** Fixed-schema CSV upload → preview/validate → explicit confirm → single batch commit + single `load_rows()` reload.
**Uses:** `rx.upload` (stack), reuses `validators.py` (architecture), pandas `read_csv` over `io.BytesIO`.
**Avoids:** Pitfall 4 (validation drift/forked path), Pitfall 5 (second `rx.session()` outside `state.py`), Pitfall 9 (re-render storms from row-by-row state updates during parse).

### Phase Ordering Rationale

- Pagination first because it fixes the actual reported bug and every other phase's UI sits on top of a working, non-hanging table.
- Forecast-context and export polish are ordered by risk/independence, not hard dependency — either could be swapped, but both are lower-risk than CSV import and should not be blocked waiting on it.
- CSV import is last because it is architecturally the riskiest (new session-boundary risk, new validation-at-scale risk, unresolved product decision) and benefits from the codebase patterns (windowing, shared helpers) established in earlier phases.
- "Drivers" explanation text is deliberately not its own phase — build the static-caption version inside Phase 2 only after the model family per series is confirmed; a real attribution/decomposition version would need its own backtest-style research phase per PROJECT.md's model-provenance constraint.

### Research Flags

Phases likely needing deeper research during planning:
- **CSV Import phase:** upsert semantics for duplicate-month rows (overwrite vs. reject) is an unresolved product decision, not yet scoped; also verify `rx.foreach` explicit-key behavior via Context7/official docs before combining with pagination.
- **"Drivers" context (if pursued beyond static caption):** any real contribution/attribution computation is a forecasting.py research topic requiring its own backtest-style validation, not assumed in scope.

Phases with standard patterns (skip research-phase):
- **Pagination/windowing phase:** well-documented Reflex computed-var pattern, already matches existing codebase conventions (`freshness_chips`, `summary_cards`).
- **Forecast-context stats phase:** standard derived-stat computation over existing SQLite data, no new library or pattern.
- **Export polish phase:** openpyxl API is well-documented and already in use.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | No new dependencies needed; recommendations verified against official Reflex/pandas docs (2026-08-24), some patterns (pagination-specific tutorials) are general-docs-inferred rather than literally copy-pasted |
| Features | MEDIUM | WebSearch-verified against multiple sources; no authoritative library docs apply (this is a UX/domain question), filtered hard against PROJECT.md's single-user constraint |
| Architecture | HIGH | Based on direct reading of the actual `state.py`, `app.py`, `models.py`, `forecasting.py` source files, not inference |
| Pitfalls | HIGH | Grounded directly in the same source files; two specific items (Reflex `rx.foreach` key-stability behavior, whole-state-per-event model) are flagged MEDIUM/LOW as inferred rather than doc-verified |

**Overall confidence:** HIGH

### Gaps to Address

- **CSV import upsert semantics** (overwrite vs. reject duplicate-month rows on import): not yet decided — must be resolved as an explicit product decision during Phase 4 planning, not assumed.
- **`rx.foreach` explicit-key requirement under pagination**: flagged as needing direct Context7/official-doc verification before the pagination phase ships (Pitfall 3) — do not assume positional keying is safe.
- **"Drivers" feature scope**: ambiguous between a cheap static caption (in scope, low risk) and a real magnitude-of-contribution computation (out of scope without further research) — must be explicitly scoped before estimation.
- **CSV import file size/row-count sanity cap**: no specific limit chosen yet; recommend a basic defense-in-depth cap even for single-user trusted context.

## Sources

### Primary (HIGH confidence)
- Direct reads: `app/app/state.py`, `app/app/app.py`, `app/app/models.py`, `app/app/forecasting.py`, `app/app/validators.py` — actual system being modified
- `.planning/PROJECT.md` — authoritative scope/constraints document
- https://reflex.dev/docs/library/forms/upload/ — `rx.upload` API, fetched 2026-08-24
- https://reflex.dev/docs/vars/computed-vars/ — cached computed var behavior, fetched 2026-08-24
- PyPI JSON API — live version lookups for reflex, statsmodels, pandas, openpyxl, sqlmodel, plotly

### Secondary (MEDIUM confidence)
- https://reflex.dev/docs/library/dynamic-rendering/foreach/ — general `rx.foreach` pattern, not pagination-specific
- CSV/bulk-import UX sources (CSVBox blog, Smart Interface Design Patterns, Dromo blog) — corroborated across multiple sources for preview/validate/confirm pattern; Dromo used as a negative reference (different scale problem)
- YoY calculation and financial-dashboard-structure sources (xelplus, oneadvanced, Excel Dashboard School) — standard, uncontroversial patterns
- Data-table UX sources (LogRocket, Setproduct) — corroborate pagination over infinite scroll for analytical/reference tables

### Tertiary (LOW confidence, flagged for validation)
- Reflex `rx.foreach` key-stability behavior under list reordering — inferred from general React/Reflex diffing conventions, not independently re-verified against current Reflex 0.9.8 docs; flagged explicitly in PITFALLS.md as needing Context7 verification before the pagination phase ships
- Reflex whole-state-per-event re-render model — consistent with documented architecture and existing in-code comments, but not independently re-verified via Context7 in this pass

---
*Research completed: 2026-08-24*
*Ready for roadmap: yes*
