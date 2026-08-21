# Project Research Summary

**Project:** Prediction Dashboard (Reflex forecasting dashboard)
**Domain:** Single-user commodity/FX price forecasting dashboard (procurement/budgeting tool) — Reflex full-stack Python + SQLite + statsmodels
**Researched:** 2026-08-21
**Confidence:** HIGH

## Executive Summary

This project replaces an existing Excel workbook with a single-process, single-user Reflex web application that lets a procurement/budgeting user manually enter monthly price data (HDAN, PPAN, Diesel, FX), forecast an adjustable 1-12 month horizon, and view bull/base/bear scenario ranges instead of the workbook's fixed next-month point forecast. The stack is fully settled: Reflex 0.9.8 as the single deployable process (UI + FastAPI backend + state), SQLite via `rx.Model`/SQLModel for persistence, statsmodels 0.14.6 for ARIMA/SARIMAX/VAR forecasting, pandas/openpyxl for Excel export, and Plotly for scenario charting. No external services, auth, or multi-user concerns are in scope.

The recommended approach is a strict architectural separation between a framework-free forecasting core (`forecasting.py`, plain Python types in/out, no `reflex` imports), a data layer (`models.py`/`seed.py` via `rx.Model`), and a single `rx.State` class that is the sole integration point bridging DB, model, and UI. Model selection itself is a separate offline research/backtest activity (`research/`) that must complete — with genuine holdout backtesting — before any model is wired into the shipped app; this "no un-backtested model ships" discipline is a hard project constraint, not a nice-to-have.

The key risks are all about false precision: fitting VAR/ARIMA on too little history (HDAN/PPAN has only ~48 monthly points) and getting confident-looking but overfit results; shipping bull/bear bands that don't scale with horizon or differ per series' actual backtested error; and prematurely shipping "weekly mode" using interpolated or unvalidated proxy data. All three are mitigated by keeping model research/backtesting as an explicit, gated phase with real holdout validation, computing scenario spread per-series and per-horizon (not a flat global percentage), and refusing to expose weekly mode in the UI until its data-gap problem is separately researched and backtested. A secondary but concrete risk is Reflex-specific: forecast results or table edits must write through to SQLite immediately (State reflects DB, not the reverse), and model fitting should happen once per data change rather than synchronously on every horizon-change click, or the UI will feel broken/slow.

## Key Findings

### Recommended Stack

The stack is fully specified and version-pinned via live PyPI lookups (HIGH confidence): Python 3.11/3.12, Reflex 0.9.8.post1, SQLite via SQLModel 0.0.39 (`rx.Model`), statsmodels 0.14.6 (pin explicitly — statsmodels' hosted docs default to unreleased 0.15.0 "devel" content), pandas 3.0.5, openpyxl 3.1.5, and Plotly 6.9.0 for charting (`rx.plotly`, chosen over `rx.recharts` for multi-series interactive scenario lines). scikit-learn 1.9.0 is a research-phase-only dependency for the mandated ML baseline comparison against statsmodels candidates — it should not become a shipped runtime dependency unless it wins the backtest. `pmdarima` (auto_arima) is similarly research-only, never a production dependency (re-searches on every call).

**Core technologies:**
- Reflex 0.9.8 — single-process Python full-stack framework — matches the explicit "Python-only, single-process" project constraint and gives reactive DB<->UI binding via `rx.Model`
- SQLite via `rx.Model`/SQLModel — persistence — zero-config, matches single-user/monthly-cadence scale; no reason to introduce Postgres
- statsmodels 0.14.6 — ARIMA/SARIMAX/VAR forecasting — explicit project requirement, continuation of existing `backend_research/` prototyping
- pandas 3.0.5 + openpyxl 3.1.5 — data wrangling and Excel export — standard, no native-dependency-free Excel round-trip
- plotly (`rx.plotly`) — scenario chart rendering — best fit for multi-series time-series lines with hover/zoom/export

### Expected Features

**Must have (table stakes):**
- View current/latest values per series; historical actuals chart
- Manual add/edit/delete of data rows (direct replacement for Excel's Input tab), with input validation to protect model integrity
- Data persists across sessions (SQLite)
- Excel export of stored data
- Forecast horizon selector (1-12 months) and per-horizon base/bull/bear values shown as both chart and table (procurement users need copyable numbers, not just a chart)
- Loading/empty states

**Should have (competitive differentiators):**
- Adjustable multi-month horizon with live recompute (the single named differentiator vs. the Excel workbook, which only forecasts one month ahead)
- Bull/base/bear scenario chart, ideally as a shaded confidence band (v1.x upgrade from 3 discrete lines)
- Inline in-row table editing (v1.x, upgrade from modal edit)
- Derived Diesel-MNT series computed automatically from Diesel-USD x FX x markup
- Multi-series single-page dashboard (all 4 series visible together, vs. Excel's tab-switching)
- "As of" / last-updated freshness indicator per series

**Defer (v2+, explicitly out of scope for v1):**
- Weekly forecast mode — blocked on resolving the AN-family vs. Diesel/FX weekly data-cadence gap; needs its own research pass
- Live news/sentiment-driven bull/bear adjustment — provider selection is an open research question
- Automatic API data-fetch from external price sources; bulk CSV upload UI
- Multi-user accounts/auth; configurable model-selection dropdown in the UI

### Architecture Approach

A four-layer single-process architecture: UI layer (`app.py`, declarative components only) -> State layer (`state.py`, the sole `rx.State` subclass and the only code allowed to touch `rx.session()` or call the forecasting module) -> parallel Data layer (`models.py`/`seed.py`, `rx.Model`/SQLModel CRUD) and Model layer (`forecasting.py`, pure Python functions with zero Reflex imports, unit-testable in isolation) -> SQLite storage. A separate top-level `research/` directory (never imported by the shipped app) holds exploratory ARIMA/SARIMAX/VAR/GBM candidate fitting and backtesting; only the winning model's minimal inference logic is hand-transcribed into `forecasting.py` once `research/REPORT.md` names a winner.

**Major components:**
1. Data layer (`models.py`, `seed.py`) — schema definition, one-time CSV seed import, raw CRUD via `rx.Model`
2. Model/forecasting layer (`forecasting.py`, `research/`) — pure prediction logic (fit/forecast, scenario spread, derived series), framework-independent and unit-testable
3. State layer (`state.py`) — bridges UI events to data and model layers, owns all mutable UI-visible state, sole integration point
4. UI layer (`app.py`) — declarative rendering only, no business logic or direct DB/model calls

Suggested build order (dependency-driven, confirmed by existing project design docs): app skeleton -> data layer schema -> seed script -> model research (can run in parallel with further app-layer work) -> forecasting module (scaffolded with placeholder, swapped once research lands) -> derived-series logic -> state layer -> UI layer last.

### Critical Pitfalls

1. **Overfit VAR/ARIMA/SARIMAX on too little history** (HDAN/PPAN ~48 monthly points) — avoid by capping model complexity to sample size, always backtesting on genuine holdout (not in-sample fit), and treating "the model ran" as no validation at all.
2. **Weekly-mode data gap silently produces misleading forecasts** — no weekly data exists for HDAN/PPAN/Diesel/FX except a different-commodity-family proxy (Baltic AN); never interpolate monthly data to fake weekly points or ship weekly mode until the proxy relationship is backtested and validated.
3. **Bull/bear bands presented as falsely precise** — must be computed per-series (each series has its own backtested MAPE, ranging 0.25%-10%) and widen with horizon (forecast uncertainty compounds); never a single flat global percentage applied uniformly.
4. **Reflex State/DB desync losing user edits** — State must be a thin reflection of SQLite, not the source of truth; write through to `rx.Model` immediately on submit, reload State from DB on session start.
5. **Synchronous model refit blocking the UI on every horizon change** — fit once when actuals change, cache the fitted model, and re-project cheaply per horizon change rather than re-fitting on every click.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: App Skeleton & Data Layer
**Rationale:** No dependencies; unblocks everything else. Data layer must exist before seed data, model research, or state layer can proceed.
**Delivers:** Reflex app scaffold, `models.py` (`PriceRow` schema via `rx.Model`), `reflex db init`/migrations wired up from the start, `seed.py` CSV import script, seeded SQLite database.
**Addresses:** Data persistence, manual entry foundation (table stakes)
**Avoids:** Pitfall 4 (Reflex State/DB desync) — establish "State reflects DB" pattern before any UI is built on top of it; avoid hand-editing `.db` files by using Reflex migrations from day one

### Phase 2: Model Research & Backtesting
**Rationale:** Can run in parallel with further app-layer work since it doesn't need a running Reflex app; its output (winning models per product, per-series MAPE) blocks real implementation of the forecasting module. Must happen before scenario/band math is built.
**Delivers:** `research/` directory with candidate fitting (ARIMA/SARIMAX/VAR/GBM), holdout backtest harness, weekly-gap proxy analysis, `REPORT.md` naming winning models and per-series backtested error.
**Addresses:** Backend for forecast horizon selector and bull/base/bear scenarios (differentiators)
**Avoids:** Pitfall 1 (overfitting on small samples) via genuine holdout backtesting; Pitfall 2 (weekly-mode data gap) by explicitly gating weekly mode behind its own validated research, separate from monthly models

### Phase 3: Forecasting Module & Derived Series
**Rationale:** Gated on Phase 2's findings but can be scaffolded earlier with a placeholder model (TDD'd against a shape-only contract) and swapped once the research report lands.
**Delivers:** `forecasting.py` (framework-free, `list[float] -> list[dict]` functions), per-series N-step-ahead forecasting, per-series/per-horizon scenario spread (bull/base/bear), derived Diesel-MNT computation.
**Uses:** statsmodels 0.14.6, plain-Python function boundary from STACK.md/ARCHITECTURE.md
**Implements:** Model layer component, Pattern 1 (framework-independent forecasting core)
**Avoids:** Pitfall 3 (flat, non-horizon-scaled bands) — compute spread per-series using actual backtested error and widen with horizon from the start, not as a retrofit

### Phase 4: State Layer & Manual Data Entry UI
**Rationale:** Depends on Phase 1 (data layer) and Phase 3 (forecasting interface being stable); should not start before both are stable or it requires rework.
**Delivers:** `state.py` (`DashboardState`), add/edit/delete row event handlers with write-through persistence and input validation, historical actuals chart, loading/empty states.
**Addresses:** Manual add/edit/delete, input validation, historical chart, persistence (table stakes)
**Avoids:** Pitfall 4 (state/DB desync) enforced in practice; basic validation prevents corrupt rows from poisoning future model fits

### Phase 5: Forecast UI, Scenario Chart & Excel Export
**Rationale:** Last phase — lowest research risk, standard Reflex CRUD/rendering and well-documented `to_excel()`/openpyxl patterns. UI churn is cheap; should follow stable state/model layers.
**Delivers:** Forecast horizon selector, bull/base/bear scenario chart (3-line minimum, shaded-band upgrade optional), forecast values table, "as of" freshness indicators, Excel export including base/bull/bear columns (not just point forecast).
**Addresses:** Forecast horizon selector, scenario chart, forecast table, Excel export, freshness indicator (table stakes + differentiators)
**Avoids:** Pitfall 5 (synchronous refit blocking UI) — fit once per actuals change, re-project cheaply on horizon change; Excel export mismatch pitfall — export exactly what's displayed/cached, not a fresh recompute

### Phase Ordering Rationale

- Data layer must precede everything since seed data feeds both model research and the running app.
- Model research is deliberately decoupled from and can run parallel to early app-layer work, but forecasting-module *implementation* is hard-gated on its output — no un-backtested model ships, per explicit project constraint.
- State layer is intentionally sequenced after both data and model layers stabilize, since it's the integration point that would need rework if either shifts underneath it.
- UI is last because it's the cheapest to iterate on and has the most standard, well-documented Reflex patterns — the inverse of model/data layers where getting the interface wrong is costly to unwind.
- This ordering directly avoids the two most severe pitfalls (overfitting, weekly-mode data gap) by forcing genuine backtest validation before any forecast reaches the UI, and avoids the Reflex-specific pitfalls (state desync, blocking UI) by establishing write-through persistence and fit-once caching as foundational patterns rather than retrofits.

### Research Flags

Needs research during planning:
- **Phase 2 (Model Research & Backtesting):** Model family selection (ARIMA vs SARIMAX vs VAR vs ML baseline), sample-size-appropriate complexity, weekly-mode proxy validation — sparse/domain-specific, needs its own deep dive per series
- **Phase 3 (Forecasting Module, scenario spread math):** Horizon-dependent, per-series confidence band computation is a design decision with real correctness risk, not a standard pattern

Standard patterns (skip research-phase):
- **Phase 1 (App Skeleton & Data Layer):** Well-documented official Reflex `rx.Model`/SQLModel/migration patterns
- **Phase 4 (State Layer & Manual Entry UI):** Standard Reflex CRUD/state conventions, confirmed by official docs
- **Phase 5 (Forecast UI & Excel Export):** Standard Reflex charting (`rx.plotly`) and pandas/openpyxl export patterns, well documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified via live PyPI version lookups and official Reflex/statsmodels docs; only MEDIUM sub-point is exact statsmodels 0.14.x API surface since hosted docs default to unreleased 0.15.0 |
| Features | MEDIUM | Grounded in project docs plus adjacent-category UX literature (no direct competitor combines manual entry + multi-horizon forecasting + scenario bands in one small tool) |
| Architecture | HIGH | Project's own design/implementation docs already encode this correctly; confirmed against official Reflex docs and community structure conventions |
| Pitfalls | MEDIUM | Reflex-specific findings are officially documented but sparsely covered for gotchas; statsmodels small-sample findings corroborated across multiple sources; scenario-band honesty findings are domain reasoning from the existing Excel workbook's own backtest approach |

**Overall confidence:** HIGH

### Gaps to Address

- **Weekly-mode data gap resolution:** No weekly HDAN/PPAN/Diesel/FX data exists; the Baltic AN proxy relationship is unvalidated. Must be resolved via its own dedicated research/backtest phase before weekly mode is even scoped, let alone built — do not let it slip into v1 scope.
- **Model family selection is genuinely open:** PROJECT.md and STACK.md leave the winning model (ARIMA/SARIMAX/VAR vs. an ML baseline) undecided pending backtest results — the roadmap should treat Phase 2's output as a real unknown that could affect Phase 3's implementation complexity, not a formality.
- **Confidence-band methodology:** No single source fully specifies how per-series, per-horizon spread should be computed (backtest MAPE vs. model-native forecast standard errors) — this needs a concrete design decision during Phase 3 planning, not just "make it dynamic."

## Sources

### Primary (HIGH confidence)
- PyPI JSON API — live version lookups for reflex, statsmodels, pandas, openpyxl, sqlmodel, plotly, pmdarima, scikit-learn, xgboost (2026-08-21)
- https://reflex.dev/docs/database/overview/ — `rx.Model`/SQLAlchemy/SQLModel architecture, State/session model, Alembic migration workflow
- https://reflex.dev/docs/library/graphing/other-charts/plotly/, https://reflex.dev/docs/library/graphing/charts/linechart/ — `rx.plotly`/`rx.recharts` confirmation
- https://reflex.dev/docs/advanced-onboarding/code-structure/, https://reflex.dev/docs/getting-started/project-structure/, https://reflex.dev/docs/getting-started/basics/ — project structure and state conventions
- https://www.statsmodels.org/devel/generated/statsmodels.tsa.arima.model.ARIMAResults.forecast.html — forecast/confidence interval API behavior
- Project files: `.planning/PROJECT.md`, `docs/plans/2026-08-21-reflex-dashboard-design.md`, `docs/plans/2026-08-21-reflex-dashboard-implementation.md`

### Secondary (MEDIUM confidence)
- https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables — enterprise data-table UX patterns
- https://uxdworld.com/inline-editing-in-tables-design/ — inline editing rationale
- https://reflex.dev/templates/data-table-editor/ — editable grid feasibility confirmation
- https://machinelearningmastery.com/make-sample-forecasts-arima-python/ — practitioner guidance on out-of-sample ARIMA forecasting
- WebSearch synthesis on small-sample time-series overfitting risk (sample-size-to-parameter ratio)
- Citigroup Commodities Market Outlook 4Q'25, CRU Group scenario/forecast framing — bull/base/bear as an institutional convention

### Tertiary (LOW confidence)
- Streamlit community discussions on editable data tables — adjacent-framework analogue only, used to confirm general expectation pattern

---
*Research completed: 2026-08-21*
*Ready for roadmap: yes*
