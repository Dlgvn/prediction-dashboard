# Pitfalls Research

**Domain:** Adding weekly-cadence forecasting (HDAN, PPAN, FX) to an existing monthly-only Reflex forecasting dashboard
**Researched:** 2026-09-01
**Confidence:** HIGH (grounded in this repo's own frozen artifacts, code, and CSV files — not generic advice)

## Critical Pitfalls

### Pitfall 1: Re-deriving weekly HDAN/PPAN model results instead of transcribing Phase 17's frozen numbers

**What goes wrong:**
A builder re-runs `backend_research/weekly/run_weekly_sarimax_ets.py`-style logic (or "improves" it) while wiring the weekly forecasting module into `app/`, producing SARIMAX orders, MAPE, or coefficients that quietly differ from what `backend_research/results/weekly_sarimax_ets.json` and `REPORT-WEEKLY.md` actually froze (SARIMAX(0,1,0) univariate/exog and ETS-HoltDamped, HDAN 7.25–7.72% MAPE, PPAN 6.96–7.95% MAPE, h=4).

**Why it happens:**
`forecast_hdan`/`forecast_ppan_var_system` in `app/app/forecasting.py` already establish the pattern of literally re-fitting a statsmodels model at request time using hard-coded orders/predictors "transcribed from a named Phase 2 output file" — not re-searched. It's tempting for weekly mode to instead call a convenience function that re-runs order selection (`select_arima_order`'s AIC grid search) live, since that logic already exists in `run_weekly_sarimax_ets.py`. That re-introduces exactly the "no runtime order-selection search" violation Phase 3's `forecasting.py` docstring explicitly forbids for monthly models (D-08 in that file) — the same discipline must extend to weekly.

**How to avoid:**
Transcribe the frozen weekly constants (SARIMAX order `(0,1,0)`, `seasonal=None`, ETS `trend=add, damped_trend=True`, and which driver variant — univariate vs `baltic_an_exog_duplicate` — actually won) into `forecasting.py` as new module-level frozen constants, exactly mirroring `HDAN_SARIMAX_ORDER`/`HDAN_PREDICTORS`. The runtime weekly-forecast function may still call `sm.tsa.SARIMAX(...).fit()` on live history (that's expected — the coefficients change as new rows are entered) but the **order/spec** must come from the frozen JSON, never from a live AIC grid search inside `app/`.

**Warning signs:**
Any weekly forecasting code path that imports `itertools` to build an order grid, or that calls something equivalent to `select_arima_order` at request time — that's the tell that order selection leaked into production.

**Phase to address:**
Weekly forecasting-module phase (the `app/app/forecasting.py` extension phase, analogous to Phase 3).

---

### Pitfall 2: FX Data.csv's three-cadence single-file layout silently corrupting the parse

**What goes wrong:**
`FX Data.csv` is one file with three independent Date/Value column pairs side by side (`Date,Daily,,Date,Weekly,,Date,Monthly`), separated by blank spacer columns, each with its own row count and its own date range (Daily is by far the longest, descending to 2010; Weekly is 865 rows also to 2010-01-04; Monthly is shorter). A naive `pd.read_csv("FX Data.csv")` produces a single DataFrame where pandas auto-names the duplicate `Date`/blank columns `Date.1`, `Unnamed: 2`, `Date.2`, etc., and — critically — rows past the shortest column's length are `NaN`, not absent, so a groupby/dropna on the whole frame silently truncates all three series to the shortest one's length, or (worse) misaligns Weekly row N with whatever Daily/Monthly value happens to sit on that same physical CSV row (they are NOT date-aligned row-for-row; Daily has ~5900 rows, Weekly 865, Monthly far fewer, and they're just concatenated column-wise).

**Why it happens:**
Every existing loader in `backend_research/data_loader.py` (`load_an_monthly`, `load_diesel_monthly`, `load_an_weekly`, `load_weekly_drivers`) assumes one Date column per CSV — this file layout has no precedent in the codebase, so there's no existing pattern to copy from. It's easy to write `pd.read_csv(FX_CSV)` and select `df["Weekly"]` without noticing the row you get back was aligned by physical CSV row position, not by the `Date` column three columns to its left after `Unnamed: 2`.

**How to avoid:**
Read each cadence as its own two-column slice, drop rows where that slice's Value is NaN, and treat the three cadences as three fully independent DataFrames — never assume matching row-index alignment across them:
```python
df = pd.read_csv(FX_CSV)
weekly = df.iloc[:, 3:5].rename(columns={df.columns[3]: "Date", df.columns[4]: "Weekly"}).dropna()
```
(pandas will name columns `Date`, `Daily`, `Unnamed: 2`, `Date.1`, `Weekly`, `Unnamed: 5`, `Date.2`, `Monthly` — use positional `.iloc` slicing, not name lookup, since the duplicate `Date` names are fragile to reorder/typos.) Confirm shape (865 rows for Weekly, per PROJECT.md) and date range (2010-01-04 to 2026-07-27) right after load, mirroring `data_loader.py`'s `if __name__ == '__main__':` assert-shape pattern.

**Warning signs:**
Row counts under 865 for the weekly slice, or a weekly date range that doesn't independently span 2010–2026 (a sign rows got truncated to the shortest column's length); any FX weekly value that looks suspiciously like a Daily or Monthly value from an adjacent column (unit/scale confusion from misaligned columns).

**Phase to address:**
FX weekly data-loader / backtest phase (the new `backend_research`-style research spike for FX, before any app wiring).

---

### Pitfall 3: Thousands-separator parsing on FX Data.csv's Value columns

**What goes wrong:**
FX values are quoted strings like `"3,592.73"` — `pd.read_csv` without cleanup either leaves these as `object`/string dtype (breaking any downstream `.astype(float)` or arithmetic with a `ValueError: could not convert string to float`) or, if `thousands=","` is passed to `read_csv` globally, it can misparse the `Date` columns' literal commas if any exist, or silently misinterpret the blank spacer columns.

**Why it happens:**
This exact issue was "already observed" per the task brief, and existing loaders (`load_an_monthly`, `load_diesel_monthly`) already have the fix pattern: `.astype(str).str.replace(',', '').astype(float)` per-column, not a `read_csv(thousands=...)` kwarg. A new FX loader written without consulting `data_loader.py`'s established pattern could reintroduce the bug that pattern already solved once.

**How to avoid:**
Reuse the exact `.astype(str).str.replace(',', '').astype(float)` idiom (or `pd.to_numeric(..., errors='coerce')` as `load_diesel_monthly` does) per value column, applied only to the Value columns identified via positional slicing (Pitfall 2), never via a blanket `read_csv(thousands=',')` that could interact unpredictably with the file's spacer/duplicate-Date-column layout.

**Warning signs:**
`TypeError`/`ValueError` on the first arithmetic operation on the FX weekly series; or, more dangerously, values silently truncated (e.g. `"3,592.73"` parsed as `3` because a partial numeric coercion succeeded on only the leading digits) — always check `.dtype == float64` and spot-check a few known values after load, not just that the load "succeeded" without error.

**Phase to address:**
FX weekly data-loader / backtest phase (same phase as Pitfall 2 — same loader function).

---

### Pitfall 4: Assuming FX Data.csv's weekly week-ending convention matches AN Data.csv's (Phase 17's) weekly convention

**What goes wrong:**
Phase 17's weekly HDAN/PPAN work used `AN Data.csv`'s native weekly rows, whose sampled dates in 2026 are `7/10, 7/3, 6/26, 6/19` — all **Fridays**. `FX Data.csv`'s Weekly column samples `2026-07-27, 07-20, 07-13, 07-06` — all **Mondays**. These are two different week-ending (or week-starting) conventions, roughly 3 days apart. If a builder joins HDAN/PPAN weekly series to FX weekly series by naive index alignment (e.g. `pd.concat(axis=1)` or a plain merge on Date) assuming "both are weekly, so rows line up," every joined row actually pairs a Friday AN observation with a Monday-ish FX observation from a different calendar week — introducing several days of look-ahead or lookback leakage into any exog/combined-view logic, and silently misaligning what the mixed-cadence UI displays side-by-side.

**Why it happens:**
`data_loader.py`'s own `merged_weekly()` function already anticipated this exact problem for AN Data.csv vs AN price weekly.csv ("the two files' week-ending conventions aren't guaranteed to align") and used `pd.merge_asof(..., direction='nearest', tolerance=pd.Timedelta(days=3))` to fix it — but that fix was scoped to those two files. Nothing currently checks or fixes the AN-vs-FX weekly offset, and because FX is being backtested as its own univariate series (no cross-series exog per PROJECT.md's plan), it's easy to assume this alignment problem doesn't apply — until the UI needs to show HDAN, PPAN, and FX on the same weekly x-axis/chart.

**How to avoid:**
(1) For backtesting FX standalone, no join is needed — this pitfall doesn't block WKLY-FX modeling itself. (2) For the mixed-cadence UI (Pitfall 6 below), when plotting/aligning weekly HDAN/PPAN forecast dates against weekly FX forecast dates on one chart or table, either normalize both to the same week-ending weekday before display, or use `pd.merge_asof` with an explicit tolerance (mirroring `merged_weekly()`'s `tolerance_days=3` pattern) rather than assuming index equality — and document which convention (Friday vs Monday week-ending) the UI's weekly x-axis actually uses, so labels aren't misleading.

**Warning signs:**
Any `pd.concat`/`.join()` of AN-family weekly series and FX weekly series that doesn't go through `merge_asof` or an explicit date-tolerance join; a chart where weekly gridlines/x-axis ticks don't consistently land on the same weekday across series.

**Phase to address:**
Mixed-cadence UI wiring phase (whichever phase builds the weekly chart/table that shows HDAN+PPAN+FX together).

---

### Pitfall 5: Mixed-cadence UI silently showing stale or misleading data for Diesel-USD/Diesel-MNT when the user is in "weekly" mode

**What goes wrong:**
Diesel-USD and derived Diesel-MNT have no weekly source data and remain monthly-only per PROJECT.md's explicit scope. If the granularity toggle is implemented as a single global "mode" flag that the whole page reads (the natural first implementation), the two monthly-only series either (a) silently disappear from the weekly view with no explanation, (b) show their last monthly forecast row repeated/stretched across weekly x-axis positions in a way that looks like a real weekly forecast, or (c) throw an unhandled exception when the weekly-mode code path tries to call a weekly forecast function that doesn't exist for `diesel_usd_ton`/`diesel_mnt`.

**Why it happens:**
`forecast_all()` in `forecasting.py` is currently a single dispatcher returning exactly five keys (`hdan`, `ppan`, `diesel_usd_ton`, `fx_rate`, `diesel_mnt`) for one implicit cadence (monthly). There is no existing `granularity` parameter anywhere in `app/app/state.py` or `forecasting.py` — this is genuinely new plumbing, not an extension of an existing pattern, so there's no established "how do we degrade a series that isn't available at the requested cadence" convention to fall back on. The most natural naive implementation is a global toggle that assumes all series can render the same way, because that's true today (all four series are monthly).

**How to avoid:**
Make cadence-availability an explicit, queryable property per series, not an implicit assumption. Concretely: extend `forecast_all`'s return contract (or a new `forecast_all_weekly`) so each series result carries its own cadence, and have the UI layer branch per-series, not per-page: `hdan`/`ppan`/`fx_rate` render on the weekly x-axis when weekly mode is on; `diesel_usd_ton`/`diesel_mnt` continue to render their monthly forecast (with an explicit "monthly — no weekly data available" label/badge) in the same view, rather than being hidden or resampled to look weekly. This matches the milestone's own stated principle: "shown honestly as such in the mixed-cadence UI rather than hidden or faked." Never resample/interpolate a monthly forecast into fake weekly points to fill the chart.

**Warning signs:**
Any chart or table row for Diesel-USD/Diesel-MNT in weekly mode that has more than ~1 data point per month, or that has no visible cadence label; any code path that reuses the same x-axis tick array for all five series without checking which series actually has data at that cadence.

**Phase to address:**
Mixed-cadence UI wiring phase; this is the single most consequential pitfall for this milestone and should get explicit acceptance-criteria coverage ("Diesel-USD/Diesel-MNT visibly labeled monthly-only when weekly mode is selected") in that phase's plan.

---

### Pitfall 6: Reusing `walk_forward_backtest`'s `min_train`/`horizon` monthly intuition for a fresh FX weekly backtest

**What goes wrong:**
Phase 17 chose `MIN_TRAIN_WEEKLY=104` (~2 years) and `HORIZON_WEEKLY=5` deliberately for HDAN/PPAN's ~206-row native weekly series, leaving ~102 backtest origins — explicitly sized to that series' short history. FX Data.csv's Weekly column has 865 rows (2010–2026), a much longer history. Copy-pasting `MIN_TRAIN_WEEKLY=104`/`HORIZON_WEEKLY=5` verbatim for FX isn't wrong, but leaving it unexamined risks two separate mistakes: (a) not revisiting whether 104 is still a sensible "burn-in" fraction now that ~760 origins would be available (a much larger backtest sample is possible and arguably should be used to strengthen confidence, since FX has 4x the history HDAN/PPAN had), and (b) accidentally reusing `BENCHMARK_MAPE = {"HDAN": 9.49, "PPAN": 10.08}` style hard-coded dict logic that has no FX entry, causing a `KeyError` at runtime if the script is cloned rather than rewritten per-series.

**Why it happens:**
`run_weekly_sarimax_ets.py` is the obvious, only prior-art template for "how do we weekly-backtest a series in this repo," and its `beats_benchmark()` function's `BENCHMARK_MAPE[series_name]` lookup is written as if the dict will always contain the queried key — cloning the file wholesale without adding an `"FX"` entry (and without deciding what FX's benchmark even is — the existing monthly FX model's Naive/1.72% MAPE, transcribed from `forecasting.py`'s `MODEL_INFO`) will crash or silently compare against the wrong number if a stray dict key collides.

**How to avoid:**
Write a dedicated FX weekly backtest script (not a live edit of `run_weekly_sarimax_ets.py`) that: (1) explicitly sets `BENCHMARK_MAPE = {"FX": 1.72}` sourced from `forecasting.py`'s `MODEL_INFO["fx_rate"]` (transcribed, not re-derived, per Pitfall 1's discipline), (2) re-evaluates `MIN_TRAIN_WEEKLY` given FX's 865-row history rather than copying 104 unexamined — document the choice with a comment the way `run_weekly_sarimax_ets.py` did ("Pitfall 2 budget" comment), and (3) reuses the shared `walk_forward.py` harness exactly as Phase 17 did (never a hand-rolled loop), consistent with the project's established discipline.

**Warning signs:**
A backtest script for FX where `BENCHMARK_MAPE` still contains `"HDAN"`/`"PPAN"` keys, or where `MIN_TRAIN_WEEKLY=104` appears without any comment justifying it against FX's actual row count.

**Phase to address:**
FX weekly backtest/research phase (before any app wiring — mirrors Phase 17's research-first discipline that PROJECT.md's "no un-backtested model ships" constraint requires).

---

### Pitfall 7: FX weekly series' 2010–2026 span vs. the app's actual seeded `PriceRow` history creating a length mismatch at forecast time

**What goes wrong:**
`FX Data.csv`'s Weekly column goes back to 2010, but the app's SQLite `PriceRow` table (seeded per `app/app/seed.py` from `Diesel Data.csv`, monthly since 2020-02) has no comparable weekly FX history loaded yet — nothing in `app/app/models.py`/`seed.py` currently seeds anything from `FX Data.csv` at all. If the weekly forecast module is wired to read weekly FX history from `PriceRow` (the existing pattern `forecast_fx` uses for monthly — reading from the app's own DB, not re-reading CSVs at request time), a naive implementation might assume the DB already has ~16 years of weekly FX rows when it will actually have zero until a new seed step is added, causing `InsufficientHistoryError`-style failures (per `MIN_HISTORY_ROWS=24` in `forecasting.py`) or, worse, a seed script that dumps all 865 weekly rows into the same `PriceRow` table/columns the monthly UI reads, corrupting the monthly Data Entry view's row count/history window (12-month default + "show all history" toggle from v1.2).

**Why it happens:**
`forecast_hdan`/`forecast_ppan_var_system`/`forecast_fx` all take a `history: pd.DataFrame` parameter that Phase 4/5's state layer builds directly from `PriceRow` query results — there is exactly one `PriceRow` table today, storing one row per (implicitly monthly) date. Weekly FX data needs either a new table/column, or a clearly separated in-memory path that doesn't route through `PriceRow` at all — but nothing in the current schema distinguishes cadence, so it's easy to reach for "just add more rows to `PriceRow`" as the path of least resistance.

**How to avoid:**
Decide explicitly (in the phase that wires weekly FX into `app/`) whether weekly history is (a) a new `rx.Model` table (e.g. `WeeklyPriceRow`) seeded once from `FX Data.csv`'s Weekly column, separate from the monthly `PriceRow` table the Data Entry tab reads/writes, or (b) read directly from `FX Data.csv` at forecast time without going through SQLite at all (acceptable since this milestone is "forecast-viewing only... no new weekly data-entry UI" — there's no user-editable weekly data to persist yet). Either is defensible, but it must be a deliberate choice, not an accidental commingling with the existing monthly `PriceRow` table that the Data Entry UI and CSV-import feature already depend on.

**Warning signs:**
Any migration/seed script that inserts rows into the existing `PriceRow` table with a weekly cadence; any code path where the monthly Data Entry table's row count or "12-month default window" suddenly includes weekly-cadence rows.

**Phase to address:**
Weekly FX data-loading/seeding phase (should be decided before or alongside the mixed-cadence UI phase, since it determines what `history` the weekly forecast functions receive).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|--------------------|-----------------|------------------|
| Cloning `run_weekly_sarimax_ets.py` in place for FX instead of writing a fresh script | Faster to start | Stale `BENCHMARK_MAPE`/`MIN_TRAIN_WEEKLY` constants copied unexamined (Pitfall 6), report determinism logic (`write_report`) hard-codes `series_list = ["HDAN", "PPAN"]` and would need surgery to not silently omit FX | Never — write a new script per series family, reusing only the shared `walk_forward.py` harness import |
| Global page-level `granularity` toggle instead of per-series cadence-awareness | Simpler first implementation | Diesel-USD/Diesel-MNT silently mis-rendered in weekly mode (Pitfall 5) | Never for this milestone — PROJECT.md explicitly requires honest per-series cadence display |
| Reading `FX Data.csv` directly at forecast-request time instead of seeding a table | Avoids new migration/seed work this milestone | Re-parses/re-cleans the CSV (Pitfall 2/3 risk) on every request; no persisted weekly FX history for future data-entry milestones | Acceptable for this milestone specifically, since it's "forecast-viewing only" — revisit once weekly data entry is in scope |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|------------------|-------------------|
| `FX Data.csv` (three-cadence single file) | `pd.read_csv` + name-based column selection, silently misaligning Weekly values with Daily/Monthly rows on the same physical CSV line (Pitfall 2) | Positional `.iloc` column slicing per cadence, independent `.dropna()` per slice, verify row count (865) and date range (2010-01-04..2026-07-27) after load |
| `backend_research/results/weekly_sarimax_ets.json` (Phase 17's frozen weekly HDAN/PPAN results) | Re-deriving/re-fitting order selection at runtime in `app/` instead of transcribing frozen constants (Pitfall 1) | Copy frozen order/spec into `forecasting.py` module constants, exactly mirroring `HDAN_SARIMAX_ORDER`; live refit is fine, live *order search* is not |
| AN Data.csv weekly cadence vs. FX Data.csv weekly cadence (different week-ending weekday) | Assuming both "weekly" series share row alignment; joining via plain `concat`/`merge` (Pitfall 4) | `pd.merge_asof(..., direction='nearest', tolerance=pd.Timedelta(days=3))`, mirroring `data_loader.py`'s existing `merged_weekly()` pattern, whenever HDAN/PPAN and FX weekly series need to appear aligned |
| Existing monthly `PriceRow` SQLite table | Seeding weekly FX rows into the same table/columns the monthly Data Entry UI reads (Pitfall 7) | New dedicated weekly table, or CSV-direct read with no DB persistence this milestone — never commingle cadences in one table |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Re-fitting SARIMAX/ETS on FX's full 865-row weekly history on every forecast request (mirrors existing monthly `forecast_fx`'s "D-06 forbids caching" refit-every-call design) | Slightly slower page load in weekly mode than monthly mode | Acceptable at this project's single-user/occasional-use scale per PROJECT.md's own constraints — do not add caching purely for this milestone; only reconsider if perceived latency becomes a real user complaint | Not expected to break at this project's scale (single user, occasional use); would only matter if usage pattern changed significantly |
| Walk-forward backtesting FX's full 865-row history with `refit_every=1` (refit at every one of ~760 possible origins) during the research phase | Backtest script research phase runs noticeably slower than Phase 17's ~102-origin HDAN/PPAN runs | Cap origins similarly to Phase 17's ~100-origin scale (e.g. don't start `min_train` unnecessarily small) or accept the longer one-time research run — this is a research-script cost, not a runtime app cost, so it's a one-time tradeoff | Only a research-phase inconvenience, not a shipped-app issue |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| No visible cadence label per series in mixed-cadence weekly view | User can't tell if Diesel-USD/Diesel-MNT numbers are "this week's forecast" or "still this month's, unchanged" — could misread a stale-looking number as a fresh weekly forecast | Explicit "Monthly" badge/label next to Diesel-USD/Diesel-MNT whenever the page is in weekly mode, reusing the existing per-series model-name+MAPE display pattern (`MODEL_INFO`) that Phase 3/5 already established for provenance transparency |
| Weekly x-axis gridlines silently using a different week-ending weekday for FX vs. HDAN/PPAN (Pitfall 4) | Chart looks aligned but isn't — user could misread which week a crossing/value belongs to | Pick and document one canonical weekly x-axis convention for the whole chart, normalizing or clearly footnoting the ~3-day AN-vs-FX week-ending offset |
| Granularity toggle framed as an all-or-nothing page mode | Reinforces the false impression that all 5 series behave identically in weekly mode | Frame the toggle as "preferred cadence" with clear fallback behavior communicated in the UI copy itself, not just in code comments |

## "Looks Done But Isn't" Checklist

- [ ] **FX weekly backtest:** Often missing a genuinely FX-specific `BENCHMARK_MAPE` entry — verify the script doesn't reuse or silently omit a benchmark comparison for FX (unlike HDAN/PPAN, FX's monthly benchmark is Naive/1.72%, not VAR)
- [ ] **Frozen weekly HDAN/PPAN wiring:** Often missing the frozen-constant transcription step — verify `forecasting.py`'s weekly additions have no live `itertools.product`/AIC grid search anywhere in the `app/` runtime path
- [ ] **Mixed-cadence UI:** Often missing an explicit "why is Diesel-USD only showing monthly points" affordance — verify a first-time user in weekly mode isn't left to infer the cadence mismatch themselves
- [ ] **FX Data.csv parsing:** Often missing verification that all three cadence columns parsed to the expected row counts/date ranges independently — verify with an assert-shape check mirroring `data_loader.py`'s existing `if __name__ == '__main__':` pattern
- [ ] **AN-vs-FX weekly alignment:** Often missing any join-tolerance handling at all (the two sources were developed independently — Phase 17 for AN, this milestone for FX) — verify any code that displays AN-family and FX weekly series together uses `merge_asof`/tolerance logic, not row-position assumptions

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Re-derived (not transcribed) weekly HDAN/PPAN constants ship to `app/` | LOW | Replace with a direct read of `backend_research/results/weekly_sarimax_ets.json`'s frozen values; add a regression test comparing `forecasting.py`'s constants against the JSON file's values so this can't silently drift again |
| FX Data.csv column-misalignment bug ships (Pitfall 2) | MEDIUM | Add the assert-shape check retroactively, re-verify against known FX values for a few spot-check dates, re-run any backtest that used the corrupted load |
| Diesel-USD/Diesel-MNT silently mis-rendered in weekly mode (Pitfall 5) | LOW-MEDIUM | UI-only fix (add cadence badge/label, adjust chart data source per series) — doesn't require re-touching the forecasting module itself since the underlying monthly forecast values were never wrong, just mislabeled |
| PriceRow table commingled with weekly FX rows (Pitfall 7) | HIGH | Requires a data migration to split weekly rows into a new table, re-verify the monthly Data Entry tab's row counts/history window are back to monthly-only, re-test CSV import/export paths that assume one row = one month |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|----------------|
| 1: Re-deriving frozen weekly HDAN/PPAN results | Weekly forecasting-module phase | New weekly constants in `forecasting.py` byte-match `backend_research/results/weekly_sarimax_ets.json`'s chosen records; no order-search code imported into `app/` |
| 2: FX Data.csv three-cadence layout misparsed | FX weekly backtest/research phase | Loader's weekly slice has exactly 865 rows spanning 2010-01-04..2026-07-27, verified via an assert/test |
| 3: Thousands-separator parsing on FX values | FX weekly backtest/research phase | Loaded weekly FX series is `float64` dtype; spot-checked values match the raw CSV (e.g. `3592.90` for 2026-07-27) |
| 4: AN vs FX weekly week-ending convention mismatch | Mixed-cadence UI wiring phase | Any joined/co-displayed AN+FX weekly view uses `merge_asof` with documented tolerance; UI copy states which weekday convention is shown |
| 5: Monthly-only series mis-rendered in weekly mode | Mixed-cadence UI wiring phase | Diesel-USD/Diesel-MNT show an explicit "monthly" cadence label/badge when weekly mode is active; no interpolated/faked weekly points appear for them |
| 6: FX weekly backtest reusing HDAN/PPAN-scaled constants unexamined | FX weekly backtest/research phase | Dedicated FX backtest script has its own `BENCHMARK_MAPE["FX"]` (transcribed from `MODEL_INFO["fx_rate"]`) and a commented, deliberate `MIN_TRAIN_WEEKLY` choice given FX's 865-row history |
| 7: Weekly FX history storage commingled with monthly `PriceRow` | Weekly FX data-loading/seeding phase | Either a new dedicated weekly table exists, or weekly forecast functions read `FX Data.csv` directly with no writes to `PriceRow`; monthly Data Entry tab's row counts unaffected |

## Sources

- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\.planning\PROJECT.md` — milestone scope, prior weekly no-go/go history, key decisions — HIGH confidence (primary project record)
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\REPORT-WEEKLY.md` — Phase 17's frozen weekly HDAN/PPAN go/no-go, models, MAPE figures — HIGH confidence (frozen deliverable)
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\weekly\run_weekly_sarimax_ets.py` — weekly backtest methodology, `MIN_TRAIN_WEEKLY`/`HORIZON_WEEKLY` rationale, benchmark-lookup pattern — HIGH confidence (source code read directly)
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\results\weekly_sarimax_ets.json` — frozen per-record weekly results — HIGH confidence
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\data_loader.py` — existing CSV-cleanup and cross-file date-alignment patterns (`merged_weekly`'s `merge_asof` tolerance fix) — HIGH confidence
- `FX Data.csv` (repo root) — inspected directly: three Date/Value column pairs, comma-thousands-separated values, Weekly column dates observed as Mondays (2026-07-27, 07-20, 07-13, 07-06) vs. AN Data.csv's Friday-based weekly dates (7/10, 7/3, 6/26, 6/19 2026) — HIGH confidence (direct file inspection)
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\app\app\forecasting.py` — existing frozen-constant discipline, per-series cadence assumptions baked into `forecast_all`'s five-key contract, existing Pitfall 1-5 inline documentation this file already carries — HIGH confidence
- `git log` (this repo) — confirmed Phase 3's `forecasting.py` foundation had at least one explicit revert/correction (`docs: revert premature FCST-04/05 completion (foundation only, not full wiring)`), and Phase 17/16's research-first, frozen-artifact discipline pattern — HIGH confidence

---
*Pitfalls research for: weekly-cadence forecasting UI addition to an existing monthly-only Reflex dashboard*
*Researched: 2026-09-01*
