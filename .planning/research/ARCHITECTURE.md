# Architecture Research

**Domain:** Adding weekly-cadence forecasting to an existing Reflex single-process monolith
**Researched:** 2026-09-01
**Confidence:** HIGH (all findings verified by reading the actual `app/` and `backend_research/` source, not inferred)

## Standard Architecture (as it exists today)

### System Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                        app/app/app.py (UI)                            │
│  Data Entry tab | Summary cards | Historical chart | Forecast section │
│  rx.slider(horizon_months) -> DashboardState.set_horizon              │
├───────────────────────────────┬───────────────────────────────────────┤
│   app/app/state.py            │  SOLE rx.session() call site           │
│   DashboardState(rx.State)    │  - forecast_results (@rx.var, wraps    │
│   - rows: list[PriceRow]      │    forecast_all())                     │
│   - horizon_months: int       │  - summary_cards / forecast_chart_     │
│   - forecast_series: str      │    figure / forecast_table_rows        │
│   - SERIES_ATTRS/SERIES_LABELS│    (all derived from forecast_results) │
│     (16-col PriceRow schema)  │  - _history_df(): PriceRow rows ->     │
│                                │    plain pd.DataFrame (Reflex/ORM      │
│                                │    boundary crossing point)            │
├───────────────────────────────┴───────────────────────────────────────┤
│         app/app/forecasting.py  (ZERO `import reflex`, D-08)          │
│  forecast_all(history_df, horizon, markup_pct) -> dict[5 keys]        │
│  dispatches to: forecast_hdan / forecast_ppan_var_system /            │
│  forecast_diesel_usd / forecast_fx / diesel_mnt_forecast (derived)    │
│  All models HARD-CODED from backend_research/02-MODEL-DECISIONS.md    │
│  MODEL_INFO{} = single source of truth for displayed model name+MAPE  │
├─────────────────────────────────────────────────────────────────────┤
│           app/app/models.py — rx.Model / SQLModel / SQLite            │
│  PriceRow(table=True): date UNIQUE + 16 series columns, ONE ROW       │
│  PER MONTH (monthly grain only, enforced by seed.py's collapse step)  │
│  AppSetting(table=True): key/value (markup_pct)                       │
├─────────────────────────────────────────────────────────────────────┤
│  app/app/seed.py (standalone script, never run at app startup)        │
│  Reads AN Data.csv (COLLAPSED monthly via mean), AN price weekly.csv  │
│  (COLLAPSED monthly), Diesel Data.csv (already monthly) -> upserts     │
│  PriceRow by date                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `DashboardState` | Sole DB session site; sole `forecast_all()` call site (`forecast_results` `@rx.var`); owns all UI-reactive vars | `app/app/state.py` |
| `forecasting.py` | Framework-independent, hard-coded, unit-testable forecast primitives; one function per series + one dispatcher | `app/app/forecasting.py` |
| `PriceRow` / `AppSetting` | Wide monthly table (16 series columns, `date` unique) + global settings | `app/app/models.py` |
| `seed.py` | One-shot CSV → SQLite loader, monthly-collapsed, run manually (`python -m app.seed ...`), never wired into app startup | `app/app/seed.py` |
| `backend_research/weekly/run_weekly_sarimax_ets.py` + `results/weekly_sarimax_ets.json` | Already-frozen, validated weekly HDAN/PPAN model choice (Phase 17) — research-only, not imported by `app/` today | `backend_research/weekly/` |
| `backend_research/data_loader.py` | Confirms **native weekly HDAN/PPAN/Baltic AN already exist in `AN Data.csv`** (no resampling needed) — this is the source `app/`'s new weekly seed path should reuse | `backend_research/data_loader.py` |

## Concrete Integration Points for v2.1

### (a) Extending `forecasting.py`'s hard-coded-model pattern for monthly + weekly

Do **not** parametrize the existing monthly functions with a cadence flag — the winning weekly models are structurally different (SARIMAX+BalticAN-exog univariate at weekly cadence, no VAR system, no HDAN→PPAN cross-dependency) and mixing cadence into one function would violate the module's own documented no-branching-model-selection discipline (`D-08`, "no runtime order-selection search," "each transcribed from a named Phase 2 [or 17] output file").

Concretely add, in the same file, following the exact existing pattern (frozen constants block → one function per series → dispatcher):

- New frozen constants transcribed from `backend_research/results/weekly_sarimax_ets.json` (the file already has these — do not re-search):
  - `WEEKLY_HDAN_SARIMAX_ORDER = (0, 1, 0)`, `WEEKLY_HDAN_EXOG = ["baltic_an"]` (verdict=`duplicate`, prefers `AN Data.csv`'s own Baltic AN column, per `backend_research/weekly/data_loader.py::merged_weekly`'s dedup choice — **not** `AN price weekly.csv`'s `BalticAN_wk`)
  - `WEEKLY_PPAN_SARIMAX_ORDER = (0, 1, 0)`, `WEEKLY_PPAN_EXOG = ["baltic_an"]`
  - `MIN_TRAIN_WEEKLY = 104`, `MAX_HORIZON_WEEKLY` (recommend 8–12 weeks; Phase 17 only backtested to h=5, see Gaps below)
  - `WEEKLY_MODEL_INFO: dict[str, tuple[str, float | None]]` mirroring `MODEL_INFO`'s shape (`hdan`: `("SARIMAX(0,1,0)+BalticAN", 7.25)`, `ppan`: `("SARIMAX(0,1,0)+BalticAN", 6.96)`) — the summary-card/model-provenance display code already reads `MODEL_INFO` generically by key; a second dict keyed the same way slots into that pattern without new branching logic in `state.py`.
  - No weekly SE/spread source is proven yet for the exog-SARIMAX variant — Phase 17's JSON has no `.se_mean`-equivalent artifact recorded, only MAPE. `forecast_weekly_hdan`/`forecast_weekly_ppan` will need their own `_arima_forecast_se`-style call on an auxiliary ARIMA fit (mirroring `ARIMA_SE_ORDER`'s pattern) since GARCH sigma (`HDAN_GARCH_SIGMA_PCT`) is monthly-only and cannot be reused at weekly cadence without re-deriving it — **flag for phase research**, this is new work, not already validated.
- New functions: `forecast_weekly_hdan(history, horizon)`, `forecast_weekly_ppan(history, horizon)`, `forecast_weekly_fx(history, horizon)` (the FX weekly model is not yet chosen — this milestone's own backtest task, see below) — each takes a **separate weekly-grain `pd.DataFrame`** (not the monthly `history` frame `forecast_all` already receives) since a weekly SARIMAX fit needs true weekly rows, not a resample of monthly rows.
- New dispatcher `forecast_all_weekly(weekly_history, horizon)` parallel to `forecast_all`, **not a branch inside `forecast_all`** — same reasoning: mixing two structurally different data shapes (monthly `history` vs. weekly `weekly_history`) into one function signature would force conditional logic `forecast_all` deliberately avoids today (it currently takes exactly one shape, always monthly-grain, always all 4 series). Diesel-USD/Diesel-MNT are simply absent from `forecast_all_weekly`'s output — no monthly/weekly duplication of code for series that don't change, and no dead code path in the weekly dispatcher for series it will never serve.
- Reuse (do not duplicate) shared low-level helpers: `_arima_forecast_se`, `_apply_se_spread`, `_naive_forecast`, `InsufficientHistoryError` all already take a generic `pd.Series` + `horizon`/`order` and have no monthly-specific assumption baked in — the weekly functions call these directly.

This keeps `forecast_all`'s existing contract (`Caller contract... converts them to a plain date-indexed pd.DataFrame`) completely untouched — zero risk of regressing the already-shipped monthly forecast — while extending the same file's established pattern (constants → per-series function → dispatcher) for the new cadence.

### (b) Data flow: new weekly table + new ingestion path required — cannot reuse `PriceRow` at a different resampling

Verified in code, not assumed: `PriceRow` is monthly-grain by construction — `date: str = sqlmodel.Field(unique=True, ...)` and `seed.py::_collapse_monthly` averages every source down to one row per calendar month before upsert. Reading `self.rows` "at a different resampling" is not possible because the finer-grained data was already discarded at seed time — a monthly `PriceRow` history literally does not contain the true weekly observations the validated weekly SARIMAX models were backtested on (`MIN_TRAIN_WEEKLY = 104` weekly rows, `n_origins = 102` in `weekly_sarimax_ets.json`).

However, per `backend_research/data_loader.py::load_an_weekly`, the true weekly HDAN/PPAN/Baltic AN observations **already exist** in `AN Data.csv` (it's genuinely weekly-cadence source data — `seed.py::parse_an_data` just happens to throw the within-month resolution away via `_collapse_monthly`). So:

- **New table**: `WeeklyPriceRow(rx.Model, table=True)` with `date: str` (unique, index) + `hdan`, `ppan`, `baltic_an`, `fx_rate` — 4 series columns only (no diesel/urals/brent/etc., since only HDAN/PPAN/FX get weekly forecasts). Add via a new Alembic migration (`reflex db migrate`), same mechanism the existing `alembic/versions/5becaaefd322_initial_schema.py` used.
- **New ingestion path**: a new `app/app/seed_weekly.py` (mirroring `seed.py`'s standalone-script pattern, never wired into app startup), with two source-specific parsers:
  - `parse_an_data_weekly(path)` — reads `AN Data.csv` **without** the `_collapse_monthly` step (i.e., a native-weekly variant of the existing `parse_an_data`), extracting `date, hdan, ppan, baltic_an` — reuses `_clean_numeric` from `seed.py` (import, don't duplicate).
  - `parse_fx_weekly(path)` — new parser for `FX Data.csv`'s `Weekly`/`Date` column-pair (this file has never been imported before — its 3-cadence, comma-separated-blank-column layout, confirmed by inspection: `Date,Daily,,Date,Weekly,,Date,Monthly`, is genuinely a new CSV shape `seed.py` has no precedent for; do not try to force it through `parse_diesel_data`'s or `parse_an_weekly`'s existing shape assumptions).
  - Since `AN Data.csv` and `FX Data.csv` have independent native cadences/week-ending conventions, follow `backend_research/data_loader.py::merged_weekly`'s already-proven pattern: `pd.merge_asof(..., direction="nearest", tolerance=pd.Timedelta(days=3))` rather than a hard date-equality join — this exact tolerance-join approach is precedented in `backend_research/`, not a new invention.
- `DashboardState` gains a **second** rows var, e.g. `weekly_rows: list[WeeklyPriceRow] = []`, loaded by a new `load_weekly_rows()` method that is the same one-more `rx.session()` read pattern `load_rows()` already uses (still funnels through the one state class — does not violate "DashboardState is the only DB session site").
- Diesel-USD/Diesel-MNT correctly have **no** weekly column anywhere — per PROJECT.md this milestone leaves them monthly-only by design, so `WeeklyPriceRow` should not carry `diesel_usd_ton` or any diesel-related field at all (avoids a schema that implies a weekly diesel forecast is coming when it structurally cannot be, given no weekly diesel source data exists per PROJECT.md's Context section).

### (c) Reflex state/UI for the granularity toggle + horizon control

- **New state var**: `granularity: str = "monthly"` (two values, `"monthly"` | `"weekly"`) on `DashboardState`, analogous in shape to the existing `active_section`/`theme_mode` string-enum pattern already used in the file — not a boolean, so a future third cadence (e.g. daily) doesn't require a breaking rename.
- **Horizon control: do NOT reuse `horizon_months` relabeled.** `set_horizon`'s existing clamp is `max(1, min(MAX_HORIZON, ...))` where `MAX_HORIZON = 12` is a **months** constant imported from `forecasting.py`; silently reinterpreting the same integer as "weeks" when `granularity == "weekly"` would corrupt `forecast_chart_figure`'s date-axis math, which explicitly does `last_hist_date + pd.DateOffset(months=entry["month"])` — a literal monthly offset baked into the chart-building code. Add a **separate** `horizon_weeks: int` state var + its own `set_horizon_weeks(value)` handler (mirroring `set_horizon`'s exact clamp-and-guard shape) and its own `MAX_HORIZON_WEEKLY` constant in `forecasting.py`. The UI should render only one of the two slider components at a time, switched by `rx.cond(DashboardState.granularity == "weekly", weekly_slider, monthly_slider)`, not one slider whose label text changes underneath the same underlying var.
- **`forecast_results` (`@rx.var`) must branch on `granularity`**, calling `forecast_all(...)` (monthly) or the new `forecast_all_weekly(...)` (weekly) and returning shapes with different key sets (5 monthly keys vs. 3 weekly keys: `hdan`, `ppan`, `fx_rate` only). Downstream vars that already iterate `FORECAST_SERIES_LABELS` (`summary_cards`, `forecast_table_rows`) need a parallel weekly-scoped label dict, e.g. `WEEKLY_FORECAST_SERIES_LABELS = {"hdan": "HDAN", "ppan": "PPAN", "fx_rate": "FX Rate"}`, and the vars that render them need a `granularity`-conditioned series-key list rather than an unconditional `FORECAST_SERIES_LABELS` iteration — this is a real, non-trivial UI-layer change, not just adding a toggle widget.
- **Diesel/Diesel-MNT under weekly granularity**: PROJECT.md is explicit these stay monthly-only and must be "shown honestly as such... rather than hidden or faked." Concretely: when `granularity == "weekly"`, the Diesel-USD/Diesel-MNT summary cards should render with a distinct "monthly only" badge/caption rather than disappearing — reuse the existing `has_data: "no"` card-shape branch in `summary_cards` as the template for a new `has_data: "monthly_only"` state with its own caption text, not a silent omission from the card list (which would look like a bug, not a deliberate scope boundary).
- **Series selector dropdowns** (`select_forecast_series`/`FORECAST_LABEL_TO_ATTR`, and the historical-chart's `select_series`/`SERIES_LABELS`) both need their option lists filtered by `granularity` too — `select_forecast_series` today unconditionally maps against the full `FORECAST_SERIES_LABELS` (5 entries); under weekly mode it must offer only HDAN/PPAN/FX rate, or `forecast_results` will be asked for a `diesel_usd_ton` key its weekly branch never returns, silently falling through to `[]` today's shape guarantees don't cover.

### (d) Safest build order given real dependencies found in code

The dependency chain is strictly: **schema/DB → ingestion/seed → forecasting-module weekly functions → state.py wiring → UI**. This mirrors the app's own existing phase history (models.py/seed.py preceded forecasting.py's Phase 3, which preceded state.py's Phase 4/5, which preceded app.py's UI phases) — no reason to deviate.

1. **Wave 1 — Schema + migration**: add `WeeklyPriceRow` to `app/app/models.py`, generate/apply the Alembic migration. Zero risk to existing monthly path (`PriceRow` untouched).
2. **Wave 2 — Weekly ingestion**: `app/app/seed_weekly.py` (parses `AN Data.csv` natively + new `FX Data.csv` Weekly-column parser, `merge_asof` join, upsert into `WeeklyPriceRow`). Testable standalone (mirrors `tests/test_seed.py`'s existing pattern) with zero Reflex/state dependency — can be fully verified before any UI work starts.
3. **Wave 3 — FX weekly backtest (this milestone's own research task, not yet done)**: run a `backend_research/weekly/`-style walk-forward backtest of candidate models against `FX Data.csv`'s `Weekly` column, following the exact harness (`walk_forward_backtest`, `mape_by_horizon`) Phase 17 already used for HDAN/PPAN, producing a frozen `results/weekly_fx.json` + go/no-go verdict — **must complete before Wave 4** touches `forecast_weekly_fx`, since the model choice/order is not yet known (unlike HDAN/PPAN, which Phase 17 already froze).
4. **Wave 4 — `forecasting.py` weekly functions**: add `forecast_weekly_hdan`/`forecast_weekly_ppan` (constants transcribed from `weekly_sarimax_ets.json`, no new research needed) + `forecast_weekly_fx` (constants transcribed from Wave 3's output) + `forecast_all_weekly` dispatcher + `WEEKLY_MODEL_INFO`. Fully unit-testable in isolation (`tests/test_forecasting.py`'s existing pattern), no Reflex dependency, can be developed/reviewed independently of Wave 5.
5. **Wave 5 — `state.py` wiring**: `granularity` var, `weekly_rows`/`load_weekly_rows()`, `horizon_weeks`/`set_horizon_weeks`, `forecast_results` branching, `WEEKLY_FORECAST_SERIES_LABELS`, series-selector filtering, Diesel "monthly only" card variant. Depends on Wave 4's function signatures being final.
6. **Wave 6 — UI**: granularity toggle component, conditional slider rendering, weekly-scoped summary cards/chart/table rendering, Diesel "monthly only" badge. Depends on Wave 5's vars existing.

Waves 1–2 and Wave 3 can run in parallel (independent files, no shared state). Waves 4–6 are strictly sequential because each wave's code directly imports/depends on the previous wave's finished interface (`forecasting.py` functions must exist with final signatures before `state.py` can call them; `state.py` vars must exist before `app.py` can bind to them) — this mirrors the same phase-boundary discipline already visible in the codebase's own docstrings (e.g. `forecasting.py`'s "Caller contract (Phase 4/5, NOT built in this phase)").

## Anti-Patterns to Avoid

### Anti-Pattern 1: Branching cadence inside the existing monthly functions/vars
**What people might do:** Add an `if cadence == "weekly"` branch inside `forecast_hdan`, `forecast_all`, or `horizon_months`/`set_horizon`.
**Why it's wrong:** The monthly functions' docstrings encode load-bearing assumptions (fixed GARCH sigma array, `pd.DateOffset(months=...)` chart math, `MAX_HORIZON=12` months) that are simply false for weekly data — branching would either silently misapply monthly constants to weekly data or require threading a cadence flag through every downstream call site, contradicting the module's own "no runtime search / hard-coded per series" discipline.
**Do this instead:** Fully parallel functions/vars (`forecast_all_weekly`, `horizon_weeks`), sharing only the genuinely cadence-agnostic low-level helpers (`_arima_forecast_se`, `_apply_se_spread`, `InsufficientHistoryError`).

### Anti-Pattern 2: Deriving "weekly" data by resampling/interpolating the monthly `PriceRow` table
**What people might do:** Forward-fill or linearly interpolate monthly `PriceRow` values to synthesize a weekly-looking series, avoiding a new table.
**Why it's wrong:** Phase 17's validated MAPE figures (7.25%/6.96%) were backtested against **real** weekly observations (`AN Data.csv`'s native ~206 rows) — a synthesized weekly series would not carry the same statistical properties the SARIMAX/exog model was fit and validated against, silently invalidating the "no un-backtested model ships" project discipline even though the *code* would still say "SARIMAX(0,1,0)+BalticAN, 7.25% MAPE."
**Do this instead:** Seed a genuine weekly table from the genuinely weekly source files (`AN Data.csv` native rows, `FX Data.csv`'s `Weekly` column).

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `state.py` ↔ `forecasting.py` (existing, monthly) | `forecast_all(history_df, horizon, markup_pct)` — plain `pd.DataFrame` in, dict out | Contract untouched by this milestone |
| `state.py` ↔ `forecasting.py` (new, weekly) | `forecast_all_weekly(weekly_history_df, horizon)` — same calling convention, no `markup_pct` (no derived series at weekly cadence) | New function, same file, same pattern |
| `state.py` ↔ `models.py` (new) | `rx.session()` reads/writes against `WeeklyPriceRow`, funneled through `load_weekly_rows()` | Second table, same single-session-site discipline |
| `seed_weekly.py` ↔ `AN Data.csv` / `FX Data.csv` | Standalone script, run manually, never at app startup | Mirrors `seed.py`'s existing pattern exactly |
| `backend_research/weekly/` ↔ `app/` | One-directional: frozen JSON results (`weekly_sarimax_ets.json`) are *read* (by a human transcribing constants) into `forecasting.py`; `app/` never imports `backend_research/` code at runtime | Matches existing monthly precedent (`02-MODEL-DECISIONS.md` → `forecasting.py` constants) |

## Sources

- `app/app/state.py`, `app/app/forecasting.py`, `app/app/models.py`, `app/app/seed.py`, `app/app/app.py` (read in full/via grep) — HIGH confidence, primary source
- `backend_research/weekly/run_weekly_sarimax_ets.py`, `backend_research/results/weekly_sarimax_ets.json`, `backend_research/data_loader.py` — HIGH confidence, primary source, confirms weekly HDAN/PPAN model choice and that native weekly data already exists in `AN Data.csv`
- `FX Data.csv` (first 20 lines inspected) — HIGH confidence, confirms 3-cadence blank-column-separated layout, never-before-imported shape
- `.planning/PROJECT.md` — HIGH confidence, milestone scope/constraints

---
*Architecture research for: Reflex weekly-forecast-UI integration (v2.1 milestone)*
*Researched: 2026-09-01*
