# Project Research Summary

**Project:** Prediction Dashboard — v2.1 "Weekly Forecast UI" milestone
**Domain:** Mixed-cadence (weekly + monthly) commodity/FX forecast dashboard, adding a granularity toggle to an existing Reflex single-process monolith
**Researched:** 2026-09-01
**Confidence:** HIGH

## Executive Summary

This milestone adds a Monthly/Weekly granularity toggle to an already-shipped Reflex forecast dashboard, extending weekly-cadence forecasting to HDAN and PPAN (already validated in Phase 17, 7.25%/6.96% MAPE vs. 9.49%/10.08% monthly benchmarks) and to FX (net-new this milestone — the model has not yet been backtested). Diesel-USD and derived Diesel-MNT have no weekly source data and stay permanently monthly-only. No new technology is required: Reflex, statsmodels, pandas, and Plotly are already installed and already used in this exact pattern elsewhere in the codebase; this is purely an extension of established patterns, not a new stack decision.

The recommended approach is strict parallelism, not branching: new weekly functions (`forecast_all_weekly`, `forecast_weekly_hdan/ppan/fx`), a new `WeeklyPriceRow` table, a new `granularity` state var, and a separate `horizon_weeks` control — all living alongside, not inside, the existing monthly code paths. This mirrors the codebase's own established discipline (frozen, hard-coded model constants; no runtime order search; one function per series). The build order is dependency-strict: schema → weekly ingestion → FX weekly backtest → forecasting-module functions → state wiring → UI, with the FX backtest as a hard blocker before FX can appear in the toggle.

The dominant risk cluster is data-integrity, not framework risk: `FX Data.csv`'s three-cadence single-file layout (Date/Value pairs concatenated column-wise, not row-aligned) is a genuinely new CSV shape with real potential for silent misalignment or truncation; AN-family weekly data (Friday-based) and FX weekly data (Monday-based) use different week-ending conventions that must not be naively joined; and the two monthly-only series (Diesel) must be shown honestly-disabled, never hidden or faked, when weekly mode is selected — a discipline already established in this project's "no un-backtested model ships" precedent (the v2.0 Phase 16 sentiment no-go).

## Key Findings

### Recommended Stack

No new dependencies. Reuse statsmodels 0.14.6 (SARIMAX + Exponential Smoothing, same pattern Phase 17 validated for weekly HDAN/PPAN), pandas 3.0.5 (same comma-formatted-numeric parsing idiom already used for other loaders), Reflex 0.9.8.post1 (`rx.select`/`rx.tabs`/`rx.radix.segmented_control` already used elsewhere for toggle-shaped controls), and `rx.plotly` 6.9.0 (same chart component, different cadence of data). The existing `walk_forward_backtest` harness is model-agnostic and should be reused verbatim for the new FX weekly backtest rather than hand-rolled — a hand-rolled walk-forward loop is explicitly flagged in the codebase as the highest-risk bug class (leakage).

**Core technologies:**
- statsmodels 0.14.6 — weekly SARIMAX/ETS fitting — same interface already proven for weekly HDAN/PPAN
- pandas 3.0.5 — CSV parsing incl. new `FX Data.csv` three-cadence shape — same cleanup idiom (`.astype(str).str.replace(',', '').astype(float)`) as existing loaders
- Reflex 0.9.8.post1 — granularity toggle UI — same tab/select components already shipped
- plotly (`rx.plotly`) 6.9.0 — weekly fan charts — same component, different x-axis cadence

### Expected Features

**Must have (table stakes):**
- Single global Monthly/Weekly toggle driving both the Forecast tab chart and Summary cards together (not two independent settings)
- Toggle state persisted across session/reload (reuse existing dark/light-theme persistence pattern)
- Explicit, always-visible "monthly only" disabled/muted state for Diesel-USD and Diesel-MNT cards when Weekly is selected — never hidden, never faked/interpolated
- Granularity-aware model provenance line (model name + MAPE) per series, reflecting the currently selected cadence, not a stale monthly figure
- Horizon control denominated in weeks (not a relabeled month slider) when Weekly is selected, capped to the validated ~4-5 week backtested range
- True weekly-dated x-axis/date labels in Weekly mode (real week-ending dates, not relabeled monthly ticks)

**Should have (competitive):**
- Fold the weekly-vs-monthly MAPE accuracy delta directly into the provenance line (e.g. "7.25% MAPE weekly vs 9.49% monthly") rather than a separate comparison widget — the numbers already exist, this is a formatting decision
- URL query param deep-link for granularity state (low cost, optional)

**Defer (v2+):**
- Per-series granularity mixing/override (anti-feature — reintroduces "two reading speeds on one screen")
- Weekly Data Entry UI for manual weekly actuals (explicitly out of scope this milestone)
- Extended weekly horizon range beyond ~5 weeks (blocked on future backtesting)
- Auto-defaulting to Weekly mode "because it's more accurate" (removes user agency, default stays Monthly)

### Architecture Approach

Extend the existing `forecasting.py` frozen-constants-per-series pattern with a fully parallel weekly track rather than branching cadence into existing monthly functions — the monthly functions' fixed constants (GARCH sigma, `MAX_HORIZON=12` months, `pd.DateOffset(months=...)` chart math) are structurally false for weekly data. A new `WeeklyPriceRow` table (4 columns: hdan, ppan, baltic_an, fx_rate — no diesel) is required because the existing monthly `PriceRow` table already discarded within-month resolution at seed time; weekly history must come from genuinely weekly source rows (`AN Data.csv` native, `FX Data.csv`'s Weekly column), never resampled/interpolated from monthly data.

**Major components:**
1. `WeeklyPriceRow` (new table, `models.py`) — genuine weekly-grain storage for HDAN/PPAN/Baltic AN/FX, separate from monthly `PriceRow`
2. `seed_weekly.py` (new, standalone script) — parses `AN Data.csv` natively + new `FX Data.csv` Weekly-column parser, joined via `merge_asof` tolerance (not naive row alignment)
3. `forecasting.py` extensions — `forecast_weekly_hdan/ppan/fx` + `forecast_all_weekly` dispatcher, frozen constants transcribed from Phase 17's JSON (HDAN/PPAN) and this milestone's own FX backtest output
4. `state.py` extensions — `granularity` string-enum var, `weekly_rows`/`load_weekly_rows()`, separate `horizon_weeks`/`set_horizon_weeks`, `forecast_results` branching by granularity, granularity-filtered series selectors
5. `app.py` UI — conditional slider rendering, weekly-scoped summary cards/chart, explicit "monthly only" badge for Diesel cards

### Critical Pitfalls

1. **Re-deriving weekly HDAN/PPAN results instead of transcribing Phase 17's frozen constants** — any runtime order-selection search (`itertools`/`select_arima_order` at request time) violates the project's established "no runtime search" discipline; transcribe frozen SARIMAX/ETS specs from `weekly_sarimax_ets.json` into `forecasting.py` constants instead.
2. **`FX Data.csv`'s three-cadence single-file layout silently corrupting the parse** — the file's three Date/Value column pairs are concatenated column-wise, not row-aligned; naive `pd.read_csv` + name-based selection risks truncation to the shortest column or cross-cadence misalignment. Use positional `.iloc` slicing per cadence, independent `.dropna()`, and verify shape (865 rows, 2010-01-04..2026-07-27) after load.
3. **AN weekly (Friday-based) vs FX weekly (Monday-based) week-ending convention mismatch** — naive joining/co-display of these two "weekly" series without `merge_asof`(tolerance) introduces several days of misalignment; the codebase already has a precedented fix (`merged_weekly()`'s tolerance-join pattern) to reuse.
4. **Monthly-only series (Diesel) silently mis-rendered in weekly mode** — the single most consequential pitfall for this milestone; requires explicit per-series cadence-awareness in the UI, not a page-level all-or-nothing toggle, with acceptance criteria mandating a visible "monthly only" label.
5. **Copy-pasting HDAN/PPAN's backtest constants (`MIN_TRAIN_WEEKLY=104`, `BENCHMARK_MAPE` dict) unexamined for the new FX backtest** — FX has 865 rows vs. HDAN/PPAN's ~206, and lacks an FX entry in the benchmark dict; write a dedicated FX backtest script with its own examined constants rather than cloning Phase 17's script in place.

## Implications for Roadmap

Based on research, suggested phase structure (mirrors the architecture research's dependency-strict build order):

### Phase A: Weekly Schema + Ingestion
**Rationale:** Zero risk to the existing monthly path; must exist before any weekly model or UI work can be tested against real data.
**Delivers:** `WeeklyPriceRow` table + Alembic migration; `seed_weekly.py` parsing `AN Data.csv` natively and the new `FX Data.csv` Weekly column via positional slicing + `merge_asof` tolerance join.
**Addresses:** Foundational data layer for weekly HDAN/PPAN/FX display.
**Avoids:** Pitfall 2 (FX CSV misparse), Pitfall 3 (thousands-separator parsing), Pitfall 4 (AN/FX week-ending mismatch), Pitfall 7 (commingling weekly rows into the monthly `PriceRow` table).

### Phase B: FX Weekly Backtest (research spike)
**Rationale:** FX is the one genuinely new modeling question this milestone — HDAN/PPAN are already validated (Phase 17), FX is not. This is a hard blocker before FX can ship in the toggle; can run in parallel with Phase A.
**Delivers:** A dedicated FX weekly backtest script (not a clone of `run_weekly_sarimax_ets.py`) using the existing `walk_forward_backtest` harness, its own examined `MIN_TRAIN_WEEKLY` and `BENCHMARK_MAPE["FX"]` (transcribed from `MODEL_INFO["fx_rate"]`), producing a frozen `results/weekly_fx.json` + go/no-go verdict.
**Uses:** statsmodels SARIMAX/ETS candidates, shared `walk_forward.py` harness.
**Avoids:** Pitfall 1 (no live order search shipped), Pitfall 6 (unexamined constant reuse).

### Phase C: Weekly Forecasting Module
**Rationale:** Depends on Phase A (data) and Phase B (FX model spec) both being finalized; must complete before state/UI wiring since those layers call this module's functions by final signature.
**Delivers:** `forecast_weekly_hdan/ppan/fx` + `forecast_all_weekly` dispatcher + `WEEKLY_MODEL_INFO` in `forecasting.py`, fully unit-testable in isolation, zero Reflex dependency.
**Implements:** Frozen-constants-per-series pattern (Architecture component 3).
**Avoids:** Pitfall 1 (frozen HDAN/PPAN transcription), branching cadence logic inside monthly functions.

### Phase D: State + UI Wiring (Mixed-Cadence Toggle)
**Rationale:** Depends on Phase C's final function signatures; the highest-touch UI phase and the one most likely to introduce the Diesel mis-rendering pitfall if not treated with explicit acceptance criteria.
**Delivers:** `granularity` state var + persistence, separate `horizon_weeks` control, granularity-branched `forecast_results`, weekly-scoped summary cards/chart/table, series-selector filtering, explicit "monthly only" badge for Diesel-USD/Diesel-MNT, granularity-aware provenance line with weekly-vs-monthly MAPE contrast.
**Addresses:** All table-stakes features from FEATURES.md (toggle, persistence, honest Diesel state, provenance, weeks-denominated horizon, true weekly date labels).
**Avoids:** Pitfall 5 (mis-rendered monthly-only series) — the single most consequential pitfall for this milestone; Pitfall 4 (AN/FX chart alignment) if HDAN/PPAN/FX are ever shown together.

### Phase Ordering Rationale

- Schema/ingestion must precede modeling and UI because weekly forecast functions need real weekly-grain history to fit against, and the monthly `PriceRow` table structurally cannot supply it (within-month resolution was already discarded at monthly seed time).
- The FX backtest is sequenced as its own phase (not folded into "forecasting module") because, unlike HDAN/PPAN, its model choice is not yet known — treating it as underlying research work, not implementation, matches the project's "no un-backtested model ships" discipline and avoids conflating a research spike with a build task in the same phase's acceptance criteria.
- State/UI wiring is deliberately last and depends on the forecasting module's finished interface — this mirrors the codebase's own existing phase-boundary discipline (forecasting.py before state.py before app.py) documented directly in the source.
- Phases A and B have no shared state and can run in parallel; Phases C and D are strictly sequential.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase B (FX Weekly Backtest):** Genuinely open modeling question — model family/order not yet chosen, candidate set may need broadening if SARIMAX/ETS don't beat the 1.72% MAPE monthly Naive benchmark at weekly cadence.
- **Phase D (State + UI Wiring):** The "honest degradation" UX pattern for Diesel cards and the AN/FX week-ending alignment display convention are both genuinely new UI decisions with no existing precedent in this codebase to copy verbatim.

Phases with standard patterns (skip research-phase):
- **Phase A (Schema + Ingestion):** Precedented patterns exist for both the migration mechanism (`reflex db migrate`) and the CSV-cleanup/tolerance-join idioms (`merged_weekly()`), just applied to a new file shape.
- **Phase C (Forecasting Module):** Directly mirrors the existing monthly-forecasting module's established constants→function→dispatcher pattern; HDAN/PPAN constants are already frozen and just need transcription.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified by reading actual installed versions and existing usage in `app/app/*.py` and `backend_research/*.py` — zero new dependencies, no external doc research needed |
| Features | MEDIUM | Project-specific reasoning is HIGH (grounded in PROJECT.md, REPORT-WEEKLY.md); general mixed-cadence dashboard UX guidance is MEDIUM (thin authoritative literature, corroborated by one community forum thread and general dashboard-cadence blog posts) |
| Architecture | HIGH | All findings verified by reading actual `app/` and `backend_research/` source directly, not inferred from framework docs |
| Pitfalls | HIGH | Grounded in this repo's own frozen artifacts, code, and direct inspection of `FX Data.csv`'s raw layout — not generic advice |

**Overall confidence:** HIGH

### Gaps to Address

- **FX weekly model choice is unresolved:** research confirms the backtest methodology to use (reuse `walk_forward_backtest`, SARIMAX/ETS candidates) but not the winning order/spec — this is intentionally left as Phase B's own research output, not resolved in advance.
- **Weekly SE/spread source for HDAN/PPAN exog-SARIMAX is not yet proven:** Phase 17's frozen JSON has MAPE but no `.se_mean`-equivalent artifact; the weekly forecast functions will need their own auxiliary ARIMA SE-fit call, flagged in architecture research as new work requiring its own small research pass during Phase C planning.
- **Canonical weekly x-axis week-ending convention (Friday vs. Monday) for the mixed UI is undecided:** flagged in pitfalls research as a decision to make explicitly (and document in UI copy) during Phase D, not a solved problem yet.

## Sources

### Primary (HIGH confidence)
- `app/app/state.py`, `app/app/forecasting.py`, `app/app/models.py`, `app/app/seed.py`, `app/app/app.py` — read directly
- `backend_research/weekly/run_weekly_sarimax_ets.py`, `backend_research/results/weekly_sarimax_ets.json`, `backend_research/data_loader.py`, `backend_research/REPORT-WEEKLY.md` — read directly
- `FX Data.csv` (repo root) — inspected directly for layout, cadence, and date-range confirmation
- `.planning/PROJECT.md`, `.planning/milestones/v2.0-ROADMAP.md` — milestone scope and prior go/no-go precedent
- PyPI JSON API version lookups (statsmodels, pandas, reflex, plotly, sqlmodel) — dated 2026-08-21, confirmed still current

### Secondary (MEDIUM confidence)
- Forecast Cadence | Revspire — general B2B forecast-cadence guidance, not commodity-specific
- How do dashboards visualize forecasts? | Pedowitz Group
- community.qlik.com — monthly/weekly/daily dynamic views — concrete implementation precedent, community forum not official docs
- DataCult — Weekly Decision Cadence dashboards — source of "don't mix cadences on one screen" principle

---
*Research completed: 2026-09-01*
*Ready for roadmap: yes*
