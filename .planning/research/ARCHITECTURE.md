# Architecture Research

**Domain:** Single-process Python web dashboard (Reflex) with an embedded statsmodels forecasting module and SQLite persistence
**Researched:** 2026-08-21
**Confidence:** HIGH (project's own design/implementation docs already encode this correctly; confirmed against Reflex official docs and community structure conventions)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          UI Layer (app/app/app.py)                    │
│  ┌────────────┐  ┌───────────────┐  ┌────────────┐  ┌─────────────┐  │
│  │ data_table │  │ add_row_form  │  │  forecast_ │  │ export_btn  │  │
│  │ (rx.table) │  │  (rx.input)   │  │  chart     │  │ (rx.button) │  │
│  └─────┬──────┘  └──────┬────────┘  │(rx.recharts│  └──────┬──────┘  │
│        │                │           └─────┬──────┘         │         │
├────────┴────────────────┴─────────────────┴─────────────────┴────────┤
│                    State Layer (app/app/state.py)                     │
│         DashboardState(rx.State) — event handlers, UI-bound vars      │
│   rows, new_row_*, horizon_months, forecast_results                   │
│   load_rows() / add_row() / run_forecast() / export_to_excel()        │
├─────────────────────────┬───────────────────────────┬─────────────────┤
│   Model Layer            │   Data Layer               │  Forecasting   │
│  (app/app/forecasting.py)│  (app/app/models.py +      │  Module        │
│  forecast_series()       │   seed.py)                 │  boundary is   │
│  diesel_mnt_forecast()   │  PriceRow(rx.Model)         │  same file for │
│  — plain functions,      │  seed_database()            │  v1, but MUST  │
│  no Reflex/rx.* imports  │  rx.session() CRUD          │  stay import-  │
│  in the hot path         │                             │  free of rx.*  │
├─────────────────────────┴───────────────────────────┴─────────────────┤
│                     Storage: SQLite (reflex.db via rx.Model/SQLModel) │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Data layer (`models.py`, `seed.py`) | Schema definition, one-time CSV import, raw CRUD | `rx.Model(table=True)` subclass (SQLModel under the hood); `rx.session()` context manager for queries; pandas for CSV parsing/cleaning |
| Model/forecasting layer (`forecasting.py`, `research/`) | Pure prediction logic: fit/forecast, scenario spread, derived series | Plain Python functions taking primitives (`list[float]`, `int`) and returning primitives (`dict`/`TypedDict`) — statsmodels (ARIMA/SARIMAX/VAR) internally, **zero Reflex imports** |
| State layer (`state.py`) | Bridges UI events to data + model layers; owns all mutable UI-visible state | `rx.State` subclass; event handler methods call into `models.py` (via `rx.session()`) and `forecasting.py` (plain function calls); holds `forecast_results` as a plain dict for `rx.foreach`/recharts binding |
| UI layer (`app.py`, optionally split into `components/`) | Declarative rendering, wiring state vars/handlers to widgets | Functions returning `rx.Component`; no business logic, no direct DB access, no direct statsmodels calls |

## Recommended Project Structure

```
app/
├── rxconfig.py                 # Reflex app config
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── app.py                  # UI layer — page composition, app = rx.App()
│   ├── state.py                # State layer — DashboardState(rx.State)
│   ├── models.py                # Data layer — PriceRow(rx.Model)
│   ├── seed.py                  # Data layer — one-time CSV → SQLite import
│   └── forecasting.py           # Model layer — forecast_series, diesel_mnt_forecast
├── research/                    # NOT shipped in state/UI layers — exploratory only
│   ├── candidates.py            # ARIMA/SARIMAX/VAR/GBM candidate fitting
│   ├── backtest.py              # Holdout MAPE harness
│   ├── weekly_gap_analysis.py   # Baltic AN → HDAN/PPAN proxy test
│   └── REPORT.md                # Winning model per product + weekly-mode decision
└── tests/
    ├── test_models.py           # Data layer — no Reflex app running required
    ├── test_seed.py             # Data layer
    ├── test_forecasting.py      # Model layer — pure functions, no DB/no Reflex
    └── test_state.py            # State layer — instantiate rx.State subclass directly
```

### Structure Rationale

- **`app/app/forecasting.py` stays dependency-light on purpose:** it must never import `reflex`. This is what makes it unit-testable with plain pytest and swappable once `research/REPORT.md` names per-product winners, without touching `state.py`'s calling convention (`history: list[float], horizon: int -> list[dict]`). This boundary is already correctly specified in the implementation plan (Task 5) — confirm it's enforced, don't drift from it.
- **`research/` is a separate top-level directory from `app/app/`,** not a subpackage of the shipped app. It's exploratory, not production code, and its scripts/notebooks legitimately violate the "no exploration in shipped code" rule; only the winning model's *call shape* graduates into `forecasting.py`.
- **`state.py` is the only file allowed to import both `rx` and `models`/`forecasting`.** It's the integration point — this matches Reflex's own convention (state classes own the app's business-flow orchestration) and matches this project's existing implementation plan almost exactly (Tasks 7-8).
- **Single `models.py` file for the schema** — Reflex's official guidance recommends one file for all `rx.Model` definitions unless the schema is very large, to keep relationships and the full schema visible in one place. `PriceRow` alone justifies staying in one file at this project's scale.
- **UI split (`app.py` only, for v1):** at this scale (4 series, one page, no auth, no routing) a single `app.py` with a few component-returning functions (`data_table()`, `add_row_form()`, `forecast_chart()`) is appropriate. Split into `app/components/` only if the page grows past ~150-200 lines or a second page/route is added — don't do it preemptively.

## Architectural Patterns

### Pattern 1: Framework-independent forecasting core

**What:** `forecasting.py` (and eventually per-product functions) accepts and returns plain Python types only — no `rx.Model` instances, no `rx.State` references, no Reflex imports at all.
**When to use:** Always, for any Reflex app where the "hard" logic (ML/stats/business rules) is more complex than trivial CRUD. This is the single most important boundary for this project given "unit-testable independent of Reflex" is an explicit project requirement.
**Trade-offs:** Requires the state layer to do the translation from `PriceRow` ORM objects to `list[float]` and back — a small amount of glue code in `state.py`, in exchange for forecasting logic that can be tested, backtested, and swapped without spinning up Reflex or a DB at all.

**Example:**
```python
# forecasting.py — no `import reflex`
def forecast_series(history: list[float], horizon: int) -> list[ForecastPoint]:
    ...

# state.py — the only place that bridges ORM <-> plain types
def run_forecast(self):
    hdan_hist = [r.hdan for r in self.rows if r.hdan is not None]
    hdan_fc = forecast_series(hdan_hist, self.horizon_months)
    self.forecast_results = {"hdan": hdan_fc, ...}
```

### Pattern 2: State as the sole DB/model integration point

**What:** `rx.State` subclass methods are the only code that opens `rx.session()` for reads/writes triggered by UI events, and the only code that calls into `forecasting.py` in response to a user action.
**When to use:** Standard Reflex convention — UI components should never touch `rx.session()` or call model-layer functions directly; they only read state vars and call state event handlers via `on_click`/`on_change`.
**Trade-offs:** Centralizes DB access in one class, which is fine at this scale (one page, one state class); would need splitting into multiple `rx.State` subclasses only if the app grows multiple independent page/feature areas later.

### Pattern 3: One-time seed script decoupled from the running app

**What:** `seed.py` is a standalone script (`python -m app.seed <path1> <path2>`) invoked manually once, not wired into `app.py`'s startup or any UI action.
**When to use:** Any app bootstrapping historical/reference data from external files where re-running on every app start would risk duplicate rows or slow startup.
**Trade-offs:** Requires the operator (single user, so acceptable here) to remember to run it once; in exchange, avoids building idempotent-upsert or migration-guard logic into the app's runtime path for a one-time operation.

## Data Flow

### Request Flow — Add a row

```
[User types + clicks "Add row"]
    ↓
[add_row_form (rx.input on_change)] → [DashboardState.new_row_* vars]
    ↓ (on_click)
[DashboardState.add_row()] → [rx.session()] → [PriceRow insert] → [SQLite]
    ↓
[DashboardState.load_rows()] → [rx.session() query] → [DashboardState.rows]
    ↓
[data_table (rx.foreach over rows)] ← re-renders automatically (Reflex reactivity)
```

### Request Flow — Run forecast

```
[User sets horizon, clicks "Forecast"]
    ↓
[DashboardState.run_forecast()]
    ↓ reads DashboardState.rows (already-loaded ORM objects)
    ↓ extracts plain float lists per series
[forecasting.forecast_series(history, horizon)] × 4 series   (model layer, no DB/Reflex)
    ↓
[forecasting.diesel_mnt_forecast(diesel_fc, fx_fc, markup)]   (derived series)
    ↓
[DashboardState.forecast_results = {...}]   (plain dict, UI-bindable)
    ↓
[forecast_chart (rx.recharts, data=forecast_results["hdan"])] ← re-renders
```

### State Management

```
[SQLite via rx.Model]
    ↓ (rx.session() query, inside state event handlers only)
[DashboardState.rows / forecast_results]
    ↓ (reactive re-render on state var change — Reflex's built-in mechanism)
[UI components: data_table, forecast_chart]
    ↑ (on_click / on_change wiring)
[User interaction] → [DashboardState event handler methods]
```

### Key Data Flows

1. **Seed (one-time, offline):** CSV files → `seed.py` parse/clean functions → `PriceRow` rows → SQLite. Runs once via CLI, independent of the running app and independent of `research/`.
2. **Manual entry (ongoing, UI-triggered):** form inputs → `DashboardState` scratch vars → `add_row()` → SQLite insert → `load_rows()` refresh → table re-render. No file upload in this flow (explicitly out of scope for v1).
3. **Forecast (ongoing, UI-triggered):** `DashboardState.rows` (already in memory) → per-series plain-float extraction → `forecasting.py` functions → `forecast_results` dict → chart/table render. This flow never touches SQLite directly (uses already-loaded `rows`), keeping forecast runs fast for the single-user/occasional-use scale.
4. **Export (ongoing, UI-triggered):** `DashboardState.rows` → pandas `DataFrame` → `to_excel()` → file on disk. One-directional (DB → file); no re-import path in v1.
5. **Model research (offline, separate from app runtime):** seeded SQLite (or raw CSVs) → `research/candidates.py` + `backtest.py` → `research/REPORT.md` → manually transcribed into `forecasting.py`'s per-product implementation. This is a human-in-the-loop hop, not an automated pipeline — intentional, since "no un-backtested model ships" is a project constraint.

## Suggested Build Order (dependency-driven)

This matches the existing implementation plan's sequencing and is worth preserving as-is in the roadmap's phase structure:

1. **App skeleton + dependencies** — no dependencies; unblocks everything else.
2. **Data layer: `models.py`** (schema) — depends on (1) only.
3. **Data layer: `seed.py`** (CSV import) — depends on (2)'s schema; produces the historical data both the app and model research need.
4. **Model research (`research/`)** — depends on (3)'s seeded data (or can read raw CSVs directly); *can run in parallel* with further app-layer work since it doesn't need the running Reflex app, but its output (winning models) blocks the *real* implementation of (5).
5. **Model layer: `forecasting.py`** — can be scaffolded with a placeholder model before (4) completes (as the implementation plan does — momentum-model placeholder, TDD'd against a shape-only contract), then swapped for real models once (4)'s report lands. Depends structurally on (2) only (needs to know what a `PriceRow`-derived history list looks like), not on Reflex.
6. **Derived-series logic (Diesel-MNT)** — depends on (5)'s per-series output shape.
7. **State layer (`state.py`)** — depends on (2)+(3) for row CRUD, and (5)+(6) for forecast orchestration. This is the integration point and should not be started before both data and model layers have stable interfaces, or state.py will need rework when either shifts.
8. **UI layer (`app.py`)** — depends on (7)'s state vars/handlers being stable. Should be last; UI churn is cheap, state/model churn is not.

**Implication for roadmap phases:** phases 2-3 (data layer) and phase 4 (model research) can be scheduled as parallel-eligible or research-flagged phases; phases 5-6 (forecasting module) should be gated on phase 4's findings; phases 7-8 (state, UI) should be the last phases and are the lowest-research-risk (standard Reflex CRUD/rendering patterns, well-documented).

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (1 user, monthly use) | Single Reflex process, SQLite, in-memory `rows` list reloaded per session — no adjustment needed. This is explicitly the target scale per PROJECT.md. |
| If multi-user / concurrent access emerges | SQLite's single-writer lock becomes a real constraint; would need to reconsider Postgres + a proper migration path, and likely split `rx.State` per-user scoping (Reflex already isolates state per browser session by default, but concurrent *writes* to the same rows need review). |
| If cloud-hosted / always-on emerges | Consider splitting `research/`-style heavy statsmodels fitting out of the request path entirely (background job) if refitting-on-demand ever becomes part of the UX (currently it isn't — models are backtested offline and only inference happens in `forecast_series`, which is cheap). |

### Scaling Priorities

1. **First (and likely only) bottleneck at target scale:** none expected — single user, monthly cadence, SQLite, in-process inference on small history arrays. No premature optimization warranted.
2. **If it ever becomes a bottleneck:** it would be SQLite write concurrency (multi-user) before it would be forecast compute time (statsmodels ARIMA/VAR on <200-row histories is sub-second).

## Anti-Patterns

### Anti-Pattern 1: Reflex imports leaking into the forecasting module

**What people do:** Import `reflex as rx` or pass `PriceRow` ORM objects directly into forecasting functions "for convenience," instead of translating to plain lists in the state layer first.
**Why it's wrong:** Breaks the explicit project requirement that the forecasting module be independently unit-testable; couples model research/testing to a running Reflex app or DB session; makes swapping model families (a known upcoming need, per Task 4/5) touch more files than necessary.
**Do this instead:** Keep `forecasting.py`'s public functions typed as `list[float] -> list[dict]` (or `TypedDict`), with all ORM-to-primitive translation happening in `state.py`.

### Anti-Pattern 2: UI components calling `rx.session()` or forecasting functions directly

**What people do:** Put `with rx.session(): ...` or `forecast_series(...)` calls inside a component function (e.g., inside `data_table()` or `forecast_chart()`) instead of routing through state event handlers and state vars.
**Why it's wrong:** Component functions run at render/compile time in Reflex's model, not as isolated per-request handlers the way a typical web framework's view function does — DB/model calls there break Reflex's reactivity model and won't behave as expected (stale or repeated calls). It also makes UI code untestable without a live app + DB.
**Do this instead:** Components only read `DashboardState.*` vars and wire `on_click`/`on_change`/`on_mount` to state methods; state methods do all data/model-layer work.

### Anti-Pattern 3: Mixing research/exploratory scripts into the shipped `app/app/` package

**What people do:** Leave ARIMA/SARIMAX/VAR/GBM candidate-fitting and backtest scripts inside `app/app/forecasting.py` (or a nearby module that gets imported at app startup), rather than in a separate `research/` directory.
**Why it's wrong:** Exploratory model-selection code has different quality bars (no TDD requirement, throwaway experiments, heavier dependencies like scikit-learn possibly not needed at runtime) and shouldn't be imported by the running app or slow down app startup/tests.
**Do this instead:** Keep `research/` fully separate; only the *winning* model's minimal inference code graduates into `forecasting.py`, transcribed by hand once `research/REPORT.md` names a winner (per Task 5 Step 5 in the existing implementation plan).

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| None (v1) | — | v1 explicitly has no external API integration (no live data fetch, no news/sentiment API) — this is a fully offline, local-file/SQLite-only app. Revisit this table if/when the "connect to an API" future milestone is picked up. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| UI (`app.py`) ↔ State (`state.py`) | Reactive var binding (`DashboardState.rows`, etc.) + event handler wiring (`on_click=DashboardState.add_row`) | Standard Reflex pattern; one-directional trigger (UI → handler), reactive re-render (state → UI) |
| State (`state.py`) ↔ Data layer (`models.py`) | Direct Python calls inside `rx.session()` context managers | State is the only caller of `rx.session()`; models.py has no behavior beyond schema + (in `seed.py`) parsing helpers |
| State (`state.py`) ↔ Model layer (`forecasting.py`) | Direct Python function calls, plain-type in/out | No shared mutable state; forecasting functions are pure/stateless given their inputs |
| Model layer (`forecasting.py`) ↔ Research (`research/`) | One-way, offline, human-mediated | `research/` never imports from `app/app/`; findings flow via `REPORT.md` → manual code update in `forecasting.py`, not via a shared import |
| App (`app/`) ↔ Existing Excel workbook (project root) | None at runtime — shared only via source CSVs at seed time | Independent storage (workbook's `Input` tab vs. this app's SQLite); this app's `seed.py` reads the same-family raw CSVs the workbook's research phase used, but the two systems don't call each other |

## Sources

- [Reflex Docs — Code Structure (Advanced Onboarding)](https://reflex.dev/docs/advanced-onboarding/code-structure/) — HIGH confidence, official docs; confirms single-file model convention and module-splitting guidance used above
- [Reflex Docs — Project Structure (Getting Started)](https://reflex.dev/docs/getting-started/project-structure/) — HIGH confidence, official docs; confirms `rxconfig.py`/`assets/`/app package layout
- [Reflex Docs — Basics](https://reflex.dev/docs/getting-started/basics/) — HIGH confidence; confirms `rx.State` subclassing and var/handler conventions
- Project's own prior design work (treated as authoritative per PROJECT.md): `docs/plans/2026-08-21-reflex-dashboard-design.md`, `docs/plans/2026-08-21-reflex-dashboard-implementation.md` — HIGH confidence, already encodes the correct forecasting/UI separation; this research confirms and elaborates rather than contradicts it

---
*Architecture research for: Reflex + statsmodels commodity/FX forecasting dashboard*
*Researched: 2026-08-21*
