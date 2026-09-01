# Stack Research

**Domain:** Weekly-cadence FX forecasting + granularity toggle for an existing Reflex/statsmodels dashboard (v2.1 "Weekly Forecast UI")
**Researched:** 2026-09-01
**Confidence:** HIGH

## Headline Finding

**No new stack additions are needed for this milestone.** Both new-feature questions —
(1) backtesting/forecasting weekly FX from `FX Data.csv`'s Weekly column, and (2) adding a
Monthly/Weekly granularity toggle to the dashboard — are fully covered by technology already
installed and already used in this exact pattern elsewhere in the repo. This was confirmed by
reading the actual code (`backend_research/weekly/run_weekly_sarimax_ets.py`,
`backend_research/data_loader.py`, `app/app/app.py`), not assumed from the milestone framing.

## Recommended Stack

### Core Technologies (already installed — reuse as-is)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| statsmodels | 0.14.6 (already pinned in `app/`) | SARIMAX + Exponential Smoothing (Holt-damped) weekly FX candidates | Phase 17 (`backend_research/weekly/run_weekly_sarimax_ets.py`) already validated this exact SARIMAX(order, seasonal=None)/`ExponentialSmoothing(trend="add", seasonal=None, damped_trend=True)` pairing for weekly HDAN/PPAN, beating the monthly VAR benchmark. FX is a third series through the identical fit/forecast interface — no reason to introduce a different model family. |
| pandas | 3.0.5 (already pinned) | Parsing `FX Data.csv`'s three-cadence layout (Daily/Weekly/Monthly as separate comma-separated column blocks with `Date,Value,,Date,Value,,Date,Value` structure, thousands-comma-formatted numeric strings) | Confirmed by reading the raw CSV header: identical shape to the comma-formatted numeric strings already handled in `load_diesel_monthly()`/`load_an_weekly()` in `backend_research/data_loader.py` (`.astype(str).str.replace(',', '').astype(float)` / `pd.to_numeric(..., errors="coerce")`). A new `load_fx_weekly()` function following that exact pattern is all that's needed — no new parsing library. |
| Reflex | 0.9.8 (post1, already pinned) | Granularity toggle UI (Monthly/Weekly) | `app/app/app.py` already uses `rx.tabs.root`/`rx.tabs.list`/`rx.tabs.trigger` (Radix-backed, built into Reflex core) for the existing tab/nav bar, and `rx.select` (lines 236, 390) for other dropdown controls. A Monthly/Weekly toggle is the same shape of UI control — either `rx.select` (two options) or `rx.tabs`/`rx.segmented_control` (Reflex 0.9.x ships `rx.radix.segmented_control` too) — both already part of the installed component set, no new package. |
| plotly (`rx.plotly`) | 6.9.0 (already pinned) | Rendering weekly-cadence forecast fan charts alongside the existing monthly ones | Same chart component already used for monthly bull/base/bear charts; weekly is just a different x-axis cadence/dataset fed to the same `rx.plotly(figure=...)` call — no chart-library change needed. |

### Supporting Libraries — none new

No new supporting libraries are required. `walk_forward_backtest` (`backend_research/walk_forward.py`) is model-agnostic (never imports a fitting library directly) and is reused unmodified — the same function Phase 17 called for weekly HDAN/PPAN backtests is called again for weekly FX with a different `fit_fn`/series/`min_train`/`horizon`.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Unit test the new `load_fx_weekly()` loader and weekly-FX forecasting/toggle logic | Already the project's test tool (`app/tests/`); no new tool needed. |
| ruff | Lint the new loader/UI code | Already the project's linter; no config change needed. |

## Installation

```bash
# Nothing to install — this milestone adds zero new dependencies.
# All required packages (statsmodels 0.14.6, pandas 3.0.5, reflex 0.9.8.post1,
# plotly 6.9.0) are already in app/requirements (or equivalent) from prior milestones.
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| Reuse `walk_forward_backtest` + SARIMAX/ExponentialSmoothing wrappers verbatim for weekly FX | Write a new/bespoke backtest loop or try a different model family (e.g. VAR, ML baseline) for FX specifically | Only if a first pass of the existing SARIMAX/ETS candidates fails to beat the current monthly FX benchmark (0.25% MAPE, AR(1)) at weekly cadence during the backtest step — in which case broaden the candidate set the same way Phase 17 did for HDAN/PPAN (it is a modeling decision, not a stack decision, and doesn't require new libraries either way). |
| `rx.select` for the granularity toggle (two options: Monthly/Weekly) | `rx.tabs` or `rx.radix.segmented_control` | Use `rx.tabs` if the toggle should visually match the existing top-level tab/nav bar convention already in `app/app/app.py`; use `segmented_control` if a more compact, inline "pill" toggle fits the chart-header layout better. All three are equally available in the installed Reflex version — this is a UI/UX choice, not a stack constraint. |
| New `load_fx_weekly()` function in `data_loader.py`-equivalent module | Extending the existing monthly FX loader to optionally return the Weekly column | Prefer a separate function (matching the existing `load_an_monthly()` / `load_an_weekly()` split pattern already in the codebase) — keeps monthly and weekly loading independently testable and mirrors the established convention rather than introducing a cadence parameter into one function. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| A new charting library or a second `rx.*` chart component for the weekly view | The dashboard already has one proven charting path (`rx.plotly`); introducing a second chart library for one more cadence of the same series type would fragment the UI and add a dependency for zero benefit. | `rx.plotly`, same as monthly charts. |
| A hand-rolled walk-forward loop for the weekly FX backtest | `walk_forward.py`'s docstring explicitly flags hand-rolled walk-forward slicing as "the single most dangerous bug class in this phase" — re-implementing it for FX risks reintroducing leakage bugs already solved once. | Import and call the existing `walk_forward_backtest()` from `backend_research/walk_forward.py`. |
| `pmdarima`/`auto_arima` as a runtime dependency for weekly FX order selection | Already ruled out project-wide in the prior STACK research (CLAUDE.md) — fine for exploratory order search during backtesting only, never wired into the shipped app. The weekly HDAN/PPAN precedent (Phase 17) used a manual AIC grid search (`select_arima_order`) instead, which weekly FX should also reuse. | Reuse `select_arima_order()`'s AIC-grid-search pattern from `run_weekly_sarimax_ets.py`, or hard-code the winning order once backtested. |
| Building a new "generic cadence" abstraction layer before backtesting FX | Premature engineering — the milestone's own framing (`FX Data.csv` already has all three cadences in one file, no new ingestion pattern needed) and PROJECT.md's "model provenance" constraint say backtest first, generalize later if a pattern actually repeats a third time. | Copy Phase 17's per-series script pattern for FX; only abstract if a fourth weekly series appears in a future milestone. |

## Stack Patterns by Variant

**If the weekly FX backtest (using `walk_forward_backtest` + SARIMAX/ETS) beats the existing monthly FX benchmark (0.25% MAPE, AR(1)):**
- Add a `load_fx_weekly()` function (mirrors `load_an_weekly()`) to the data-loading module used by `app/`.
- Add a granularity toggle (`rx.select` or `rx.tabs`) to state (`app/app/state.py`) that switches which forecast function/series is queried and re-renders the same `rx.plotly` chart component with weekly-cadence data.
- Diesel-USD/Diesel-MNT stay monthly-only in the toggle — either disable/hide the toggle for those series' cards, or show them with a static "monthly only" label when Weekly is selected (an honesty-in-UI decision already flagged in PROJECT.md, not a stack decision).

**If the weekly FX backtest is a no-go:**
- No `app/` changes ship for FX granularity (mirrors the Phase 17 precedent: a no-go is a valid, complete research outcome, not a blocker requiring more stack investigation). The HDAN/PPAN weekly toggle can still ship on its own from Phase 17's go result if that's independently in scope.

## Version Compatibility

No new compatibility surface — this milestone doesn't touch any package versions. Existing pins carry forward unchanged: `reflex==0.9.8.post1`, `statsmodels==0.14.6`, `pandas==3.0.5`, `plotly==6.9.0` (all confirmed already in use via `app/app/*.py` and `backend_research/*.py`).

## Sources

- `backend_research/weekly/run_weekly_sarimax_ets.py` — read directly, HIGH confidence: confirms the exact SARIMAX/ExponentialSmoothing + `walk_forward_backtest` pattern already validated for weekly HDAN/PPAN, the pattern this research recommends reusing verbatim for weekly FX.
- `backend_research/data_loader.py` — read directly, HIGH confidence: confirms the existing comma-formatted-numeric-string parsing pattern (`load_an_monthly`, `load_diesel_monthly`, `load_an_weekly`) that a new `load_fx_weekly()` should mirror.
- `FX Data.csv` (raw file, first rows read directly) — HIGH confidence: confirms the three-cadence column-block layout (`Date,Daily,,Date,Weekly,,Date,Monthly`) parses with the same pandas technique already in use, no new library needed.
- `app/app/app.py` (grep for `rx.tabs`/`rx.select`) — read directly, HIGH confidence: confirms `rx.tabs.root`/`rx.tabs.list`/`rx.tabs.trigger` and `rx.select` are already used in the shipped UI, both suitable for a granularity toggle with zero new components.
- `.planning/PROJECT.md` — read directly, HIGH confidence: source of the "no un-backtested model ships," "Diesel stays monthly-only," and "existing Reflex+SQLite+statsmodels stack" constraints this research confirms rather than second-guesses.
- Prior `CLAUDE.md`-embedded STACK research (this same repo, dated 2026-08-21) — HIGH confidence: confirms current pinned versions (statsmodels 0.14.6, pandas 3.0.5, reflex 0.9.8.post1, plotly 6.9.0) are unchanged and still current as of this milestone; no re-verification against PyPI was needed since no version change is proposed.

---
*Stack research for: weekly-cadence FX forecasting + Monthly/Weekly granularity toggle (v2.1 milestone)*
*Researched: 2026-09-01*
