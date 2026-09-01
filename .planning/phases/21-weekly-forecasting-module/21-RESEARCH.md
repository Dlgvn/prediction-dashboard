# Phase 21: Weekly Forecasting Module - Research

**Researched:** 2026-09-01
**Domain:** statsmodels SARIMAX/ETS transcription into a Reflex-independent forecasting module
**Confidence:** HIGH

## Summary

This phase transcribes three already-frozen, already-backtested weekly models into
`app/app/forecasting.py`: HDAN and PPAN via `SARIMAX(0,1,0)+BalticAN(exog, duplicate)`
(7.25% / 6.96% MAPE h=4), and FX via `ETS-HoltDamped` (0.86% MAPE h=4). The HDAN/PPAN
SARIMAX call is a near-verbatim copy of the existing `forecast_hdan`'s SARIMAX pattern,
simplified to a single exog column with no lag-shifting (Baltic AN is used at its
concurrent, unlagged value in the backtest script — confirmed by reading
`run_weekly_sarimax_ets.py`'s `build_exog_sarimax_record`, which builds exog via
`mg[exog_cols]` with no `.shift()` anywhere). The FX ETS model is new ground: statsmodels'
`ExponentialSmoothing`/`HoltWintersResults` has no `.get_forecast()`/`.se_mean` the way
ARIMA does, so `_arima_forecast_se` cannot be reused for FX. Live verification in
`app/.venv` (pandas 3.0.5, statsmodels 0.14.6) confirms `HoltWintersResults.simulate()` is
available and exposes a `random_state` parameter for deterministic reruns, producing a
per-horizon standard deviation array that is a legitimate, model-native, backtest-fit
spread source (not an arbitrary flat percentage) — the recommended solution to the
CONTEXT.md discretion point on ETS spread generation.

No pandas 2.x -> 3.x porting risk was found: none of the three fitting paths (SARIMAX,
ETS, exog construction) touch any pandas-3.0-changed behavior (copy-on-write, dtype
inference) in a way that differs from what `forecast_hdan` already does successfully in
this exact `app/.venv` today. The backtest scripts under `backend_research/` ran on system
Python (pandas 2.2.3) but their `.to_numpy()`-first calling convention into
`sm.tsa.SARIMAX`/`ExponentialSmoothing` sidesteps pandas-version-sensitive DataFrame
behavior entirely — the fitted objects only ever see raw numpy arrays.

**Primary recommendation:** Add three new `forecast_weekly_*` functions plus
`WEEKLY_MODEL_INFO`/`MAX_HORIZON_WEEKLY`/`forecast_all_weekly` in a clearly-delineated
weekly section of `forecasting.py`, reusing `_arima_forecast_se`/`_apply_se_spread`
verbatim for HDAN/PPAN, and adding one new small helper (`_ets_forecast_spread` or
similar) for FX's ETS-native `.simulate()`-derived band.

## User Constraints

### Locked Decisions

- **HDAN**: `SARIMAX(0,1,0)+BalticAN(exog, duplicate)` — 7.25% MAPE (h=4), from
  `backend_research/results/weekly_sarimax_ets.json`. Uses `Baltic AN` as an exogenous
  driver (from `AN Data.csv`, already present in `WeeklyPriceRow.baltic_an` per Phase 19's
  ingestion — no new data needed).
- **PPAN**: `SARIMAX(0,1,0)+BalticAN(exog, duplicate)` — 6.96% MAPE (h=4), same source file,
  same exog driver.
- **FX rate**: `ETS-HoltDamped` (trend=add, seasonal=None, damped_trend=True) — 0.86% MAPE
  (h=4), from `backend_research/results/weekly_fx.json`. Note this is a **univariate**
  model — no exog driver, unlike HDAN/PPAN.
- Benchmark figures for `WEEKLY_MODEL_INFO`: HDAN 7.25%, PPAN 6.96%, FX 0.86% — read the
  exact figures from the frozen JSON at implementation time rather than trusting this
  document's transcription.
- New functions in `app/app/forecasting.py` (same file, not a new module):
  `forecast_weekly_hdan(history, horizon)`, `forecast_weekly_ppan(history, horizon)`,
  `forecast_weekly_fx(history, horizon)`, each returning the same
  `{"base": [...], "bull": [...], "bear": [...]}`-shaped dict the monthly functions
  already return.
- `forecast_all_weekly(history, horizon)` dispatcher, mirroring `forecast_all`'s shape —
  but weekly has only 3 series (HDAN, PPAN, FX), never Diesel-USD or Diesel-MNT. Key set
  must be exactly `{"hdan", "ppan", "fx_rate"}` — no stub/placeholder Diesel entries.
- `WEEKLY_MODEL_INFO: dict[str, tuple[str, float]]` constant, analogous to `MODEL_INFO`,
  3 keys only.
- Reuse existing low-level helpers wherever the pattern fits: `_arima_forecast_se` (for the
  SARIMAX-based HDAN/PPAN spread), `_apply_se_spread`, `_naive_forecast` if useful. Do NOT
  duplicate these helpers into new weekly-prefixed copies. For ETS (FX's winning model), a
  new spread-generation approach is needed since `_arima_forecast_se` is ARIMA-specific.
- `MAX_HORIZON` equivalent for weekly: the backtest only validated up to `horizon=5` weeks
  (`horizon: 5` field in the frozen JSON). A weekly `MAX_HORIZON_WEEKLY = 5` (or similar
  name) constant should cap what these functions will forecast.
- Weekly history comes from `WeeklyPriceRow` (Phase 19's table), queried the same way
  `PriceRow` already is — but this phase does NOT touch `state.py` or any Reflex code.
  Functions take a `history: pd.DataFrame` parameter and are fully testable without a
  Reflex session.

### Claude's Discretion

- Exact spread/confidence-band generation approach for the ETS-HoltDamped FX model — must
  be backtest-grounded, not an arbitrary flat percentage. (Resolved by this research: use
  `HoltWintersResults.simulate()`, see Pattern 3 below.)
- Exact module organization within `forecasting.py` — keep weekly and monthly clearly
  delineated (comment banner section, consistent naming prefix `_weekly`/`forecast_weekly_*`).
- Whether `forecast_all_weekly` takes a `markup_pct` parameter — likely not needed since
  there's no weekly Diesel-MNT derivation; confirm by checking Phase 22 need (executor's
  call). This research found no weekly Diesel derivation anywhere in scope, so the
  recommendation is: **no `markup_pct` parameter** on `forecast_all_weekly`.

### Deferred Ideas

None raised — this is a tightly-scoped, pre-specified infrastructure phase with no
scope-creep surface.

## Standard Stack

No new dependencies. Both `statsmodels.api.tsa.SARIMAX` and
`statsmodels.tsa.holtwinters.ExponentialSmoothing` are already imported/used elsewhere in
this codebase's research scripts and are already available via `app/.venv`'s pinned
`statsmodels==0.14.6` [VERIFIED: `app/.venv/Scripts/python.exe -c "import statsmodels; print(statsmodels.__version__)"` → `0.14.6`]. `forecasting.py` currently imports `statsmodels.api as sm`
and `from statsmodels.tsa.arima.model import ARIMA`; it will need one additional import:
`from statsmodels.tsa.holtwinters import ExponentialSmoothing` [VERIFIED: import + fit +
`.simulate()`/`.forecast()` smoke-tested successfully in `app/.venv`, see Code Examples].

**Version verification:**
```
app/.venv/Scripts/python.exe -c "import pandas, statsmodels; print(pandas.__version__, statsmodels.__version__)"
# -> pandas 3.0.5, statsmodels 0.14.6
```
[VERIFIED: ran live in this session, 2026-09-01]

## Architecture Patterns

### Recommended Project Structure

Single-file addition — no new files. Add a clearly-delineated section to
`app/app/forecasting.py`, after the existing monthly `forecast_all`/`_to_rows` block:

```python
# ---------------------------------------------------------------------------
# Weekly forecasting (Phase 21) -- mirrors the monthly section above exactly
# in return-contract shape, but is a wholly separate model set (frozen from
# backend_research/results/weekly_sarimax_ets.json and weekly_fx.json).
# Only 3 series exist at weekly cadence: hdan, ppan, fx_rate. No weekly
# Diesel-USD/Diesel-MNT -- no weekly source data exists for those.
# ---------------------------------------------------------------------------
```

### Pattern 1: HDAN/PPAN weekly SARIMAX(0,1,0)+BalticAN exog

**What:** A single-exog-column SARIMAX, using Baltic AN at its **concurrent** (unlagged)
value — this is the one structural difference from monthly `forecast_hdan`'s six-predictor,
per-predictor-lagged exog frame.

**Why unlagged:** Read `backend_research/weekly/run_weekly_sarimax_ets.py`'s
`build_exog_sarimax_record` closely — the exog frame is built as
`frame = pd.concat([mg[series_name].rename("y"), mg[exog_cols]], axis=1).dropna()` with
`exog_cols = ["Baltic AN"]` and **no `.shift()` call anywhere** in that function. This is
unlike `forecast_hdan`'s `_build_future_exog`, which shifts every predictor by a per-column
lag (`HDAN_PREDICTOR_LAGS`). The weekly backtest's `_SARIMAXWrapper.forecast(steps, exog=...)`
also receives raw future exog values with no lag adjustment
(`walk_forward_backtest`'s harness passes the test window's actual future exog directly).
**Transcribe this concurrent-value convention exactly — do not import `HDAN_PREDICTOR_LAGS`
or apply any lag to the weekly Baltic AN exog column.** Applying monthly's lag-1 convention
here would silently diverge from the backtested/frozen model and violate the "no
un-backtested model ships" constraint.

**Future exog for forecast steps:** Since Baltic AN's own value at each future weekly step
is unknown, it must itself be projected forward. The backtest's walk-forward harness always
supplies genuine held-out actuals as the "future exog" (that's what the harness validates
against) — it never itself forecasts Baltic AN forward, because during backtesting the
future values already exist in the historical dataset. In production, no such future data
exists, so `forecast_weekly_hdan`/`forecast_weekly_ppan` must project Baltic AN forward
themselves. **Reuse the existing `_forecast_predictor(series, horizon)` helper** (already
in `forecasting.py`, ARIMA(1,1,0) with (0,1,0) fallback) — it is generic (any series in,
array out) and already serves exactly this "project an exogenous driver forward" role for
monthly HDAN's six predictors. This is a reasonable, precedented choice given `_forecast_predictor`
already exists in the file and is not itself a "winning model" needing its own backtest
(the constant `PREDICTOR_ARIMA_ORDER`'s docstring already says "purely a helper for feeding
predictors").

**Exact statsmodels call** (mirrors `forecast_hdan`'s SARIMAX call, `enforce_stationarity`/
`enforce_invertibility=False` unchanged — verbatim from `_SARIMAXWrapper` in both weekly
backtest scripts):

```python
# Source: backend_research/weekly/run_weekly_sarimax_ets.py, _SARIMAXWrapper
# (fit-time call); transcribed order=(0, 1, 0) from
# backend_research/results/weekly_sarimax_ets.json records where
# model == "SARIMAX(0, 1, 0)+BalticAN(exog, duplicate)"
WEEKLY_SARIMAX_ORDER = (0, 1, 0)          # both HDAN and PPAN
WEEKLY_EXOG_COLUMN = "baltic_an"          # WeeklyPriceRow's column name (models.py)

fitted = sm.tsa.SARIMAX(
    y_fit.to_numpy(),
    exog=x_fit.to_numpy(),                # x_fit: single-column DataFrame [baltic_an]
    order=WEEKLY_SARIMAX_ORDER,
    enforce_stationarity=False,
    enforce_invertibility=False,
).fit(disp=False)

future_exog = _forecast_predictor(history[WEEKLY_EXOG_COLUMN], horizon)  # 1-D np.ndarray
result = fitted.get_forecast(steps=horizon, exog=future_exog.reshape(-1, 1))
base = np.asarray(result.predicted_mean, dtype=float)
```

**Spread:** reuse `_arima_forecast_se` + `_apply_se_spread` verbatim, exactly as
`forecast_ppan_var_system` already does — fit an auxiliary ARIMA on the raw `hdan`/`ppan`
series (not the SARIMAX+exog model) purely to obtain `.se_mean`. There is no existing
`ARIMA_SE_ORDER` entry for weekly hdan/ppan; a new small dict (e.g.
`WEEKLY_ARIMA_SE_ORDER = {"hdan": (0, 1, 0), "ppan": (0, 1, 0)}`, transcribed from the
`weekly_sarimax_ets.json` univariate SARIMAX records — the "SARIMAX(0, 1, 0)" order without
BalticAN, which is a valid ARIMA order for `_arima_forecast_se`'s purposes) should be added
following the existing `ARIMA_SE_ORDER` naming convention. [ASSUMED: using the univariate
SARIMAX(0,1,0) order as the SE-only auxiliary fit is a direct analogy of how monthly PPAN's
`ARIMA_SE_ORDER["ppan"] = (0, 1, 0)` is used purely for `.se_mean`, not point forecast — the
frozen JSON confirms `(0,1,0)` is also HDAN/PPAN weekly's own univariate winning order, so
this is a well-grounded but not separately re-verified choice; low risk given `_arima_forecast_se`
never uses this fit's point forecast.]

### Pattern 2: FX weekly ETS-HoltDamped

**Exact statsmodels call**, transcribed verbatim from `_HoltDampedWrapper` in
`run_fx_weekly_backtest.py` and `run_weekly_sarimax_ets.py` (byte-identical in both):

```python
# Source: backend_research/weekly/run_fx_weekly_backtest.py, _HoltDampedWrapper
from statsmodels.tsa.holtwinters import ExponentialSmoothing

fitted = ExponentialSmoothing(
    y_fit.to_numpy(),
    trend="add",
    seasonal=None,
    damped_trend=True,
    initialization_method="estimated",
).fit()

base = np.asarray(fitted.forecast(horizon), dtype=float)
```

No exog — FX weekly is univariate (confirmed: `weekly_fx.json`'s only two records are
`"driver_variant": "univariate"`, and `_SARIMAXWrapper`/`_HoltDampedWrapper` in
`run_fx_weekly_backtest.py` never call `sm.tsa.SARIMAX(..., exog=...)`).

### Pattern 3: ETS spread band via `.simulate()` — the new-ground piece

[VERIFIED live in `app/.venv`, 2026-09-01]: `HoltWintersResults` (the fitted object's type)
has **no** `.get_forecast()` and **no** `.se_mean` — confirmed by direct probe
(`AttributeError: 'HoltWintersResults' object has no attribute 'get_forecast'`). It does
have `.simulate(nsimulations, repetitions, error, random_state)`, confirmed present and
working:

```python
>>> fit.simulate(5, repetitions=200, error="add", random_state=0)
# returns np.ndarray shape (5, 200) -- 200 simulated paths per horizon step
```

`repetitions=200` simulated paths' per-horizon standard deviation naturally widens with
horizon (measured live: `[0.97, 1.51, 1.88, 2.11, 2.43]` for a 5-step synthetic random-walk
fixture) — satisfying FCST-05's "spread widens with horizon" precedent the monthly module
already establishes (GARCH sigma array, ARIMA SE). `random_state` accepts a plain int seed
for full reproducibility across calls (confirmed via `inspect.signature`), which matters
because D-06 (existing `forecast_all` docstring) forbids caching/memoization — every call
refits and re-derives the spread fresh, so the spread must be deterministic given identical
input data or repeated calls with the same history would jitter the displayed band.

**Recommended new helper** (parallel structure to `_apply_se_spread`, added near it):

```python
def _apply_ets_spread(fitted_ets, base, horizon: int, n_reps: int = 500) -> dict:
    """Apply an ETS-HoltDamped model's own simulated-path spread to a base forecast.

    `HoltWintersResults` has no `.get_forecast()`/`.se_mean` the way ARIMA does
    (verified: 0.14.6 raises AttributeError on `.get_forecast`), so `_arima_forecast_se`
    cannot be reused here. Instead, this uses the fitted ETS model's own `.simulate()`
    method to draw `n_reps` simulated future paths and takes their per-horizon standard
    deviation as the spread -- a model-native, backtest-fit uncertainty measure, not an
    arbitrary flat percentage. `random_state` is fixed so repeated calls against
    identical history produce an identical band (no un-memoized jitter between renders).
    """
    base_arr = np.asarray(base, dtype=float)
    sims = fitted_ets.simulate(horizon, repetitions=n_reps, error="add", random_state=0)
    spread = np.std(sims, axis=1)
    return {
        "base": base_arr.tolist(),
        "bull": (base_arr + spread).tolist(),
        "bear": (base_arr - spread).tolist(),
    }
```

This keeps `forecast_weekly_fx`'s return contract identical in shape to `forecast_fx`'s
(`{"base": [...], "bull": [...], "bear": [...]}`) while sourcing the band from the model
family actually used, matching CONTEXT.md's "backtest-grounded, not an arbitrary flat
percentage" requirement — the ETS model itself was the one walk-forward backtested and
frozen; its own simulated dispersion is a direct byproduct of that same fitted model, not a
second unrelated statistic.

**Alternative considered and rejected:** deriving spread from `mape_h4`/`mape_h5` in
`weekly_fx.json` (e.g. `base * mape_pct/100`, GARCH-style). Rejected because those are
aggregate scalars (one number per horizon-*bucket*, not per individual step 1..5) and the
JSON does not carry a full per-step SE array the way `HDAN_GARCH_SIGMA_PCT` does for
monthly HDAN — using it would require inventing an interpolation scheme not itself
backtest-derived. `.simulate()` is the more directly model-grounded choice and required no
new research artifact.

### Anti-Patterns to Avoid

- **Applying `HDAN_PREDICTOR_LAGS`-style lag-shifting to the weekly Baltic AN exog column.**
  The weekly backtest uses Baltic AN at its concurrent (unlagged) value — confirmed by
  reading `build_exog_sarimax_record`'s exog construction, which has no `.shift()` call.
  Lagging it would silently diverge from the frozen/backtested model.
- **Reusing `_apply_garch_spread` for weekly HDAN.** HDAN's monthly winner is SARIMAX+exog
  with a GARCH volatility band (`HDAN_GARCH_SIGMA_PCT`), but weekly HDAN's winner per the
  frozen JSON is SARIMAX+BalticAN with no GARCH refit in this phase's scope — CONTEXT.md's
  decisions section explicitly names `_arima_forecast_se`/`_apply_se_spread` as the intended
  reuse target for weekly HDAN/PPAN, not GARCH. No weekly GARCH sigma array exists in
  `backend_research/results/`.
  - [VERIFIED: no `weekly_garch*.json` file found in `backend_research/results/`]
- **Calling `fitted.get_forecast()` on an `ExponentialSmoothing` fit result.** Raises
  `AttributeError` — confirmed live. Only `ARIMA`/`SARIMAX` results expose `get_forecast()`.
- **Skipping `random_state` on `.simulate()`.** Without it, `forecast_weekly_fx`'s bull/bear
  band would silently jitter on every call with identical input, since D-06 forbids caching
  and every dashboard interaction refits fresh.
- **Forecasting beyond `MAX_HORIZON_WEEKLY = 5`.** The backtest only validated `horizon: 5`
  in both frozen JSONs; extrapolating further is un-backtested territory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Projecting Baltic AN forward as future exog | A new bespoke forecaster for the exog driver | `_forecast_predictor` (already in `forecasting.py`) | Generic, already-tested helper serving this exact "project an exog driver forward" role for monthly HDAN's six predictors; reuse avoids duplicated ARIMA-fitting logic. |
| ARIMA-derived SE for weekly HDAN/PPAN's SARIMAX+exog band | A new SE helper | `_arima_forecast_se` + `_apply_se_spread` (verbatim) | CONTEXT.md explicitly names these as the reuse target; the helper is already family-appropriate (ARIMA `.se_mean`) for a SARIMAX-family winning model. |
| ETS uncertainty | Hand-computed residual-std flat band | `HoltWintersResults.simulate()` | Model-native uncertainty propagation through the fitted damped-trend recursion, not a static in-sample residual std (which wouldn't widen with horizon and would repeat the class of bug `_apply_se_spread`'s docstring already warns against for `.se`). |

**Key insight:** every spread mechanism in this module (GARCH sigma, ARIMA SE, and now ETS
simulate-std) is deliberately model-family-specific because a flat single-percentage band
across all series/models was explicitly rejected earlier in this project (FCST-05's
"per-series, not one flat percentage" requirement, restated in `_apply_se_spread`'s own
docstring). The weekly ETS case is not an exception to that discipline — it's the same
discipline applied to a model family not previously present in this file.

## Common Pitfalls

### Pitfall 1: Reusing `HDAN_PREDICTOR_LAGS`/`_build_future_exog` for weekly HDAN/PPAN
**What goes wrong:** Silently applies monthly's per-predictor lag convention to a weekly
model whose backtest used the exog column unlagged.
**Why it happens:** `_build_future_exog` is the most visible existing "future exog" pattern
in the file, tempting direct reuse/generalization.
**How to avoid:** Write a small, weekly-specific exog-building step inline (or a tiny new
helper) using `_forecast_predictor` directly on the single `baltic_an` column with no shift,
rather than generalizing `_build_future_exog`.
**Warning signs:** If a new `WEEKLY_PREDICTOR_LAGS` dict appears anywhere, that's a sign the
concurrent-value convention was missed.

### Pitfall 2: Calling `.get_forecast()` on the ETS fit result
**What goes wrong:** `AttributeError` at runtime — `HoltWintersResults` has no such method
(confirmed live, 0.14.6).
**Why it happens:** Copy-pasting the SARIMAX call pattern (`fitted.get_forecast(steps=...)`)
without checking the ETS results object's actual API.
**How to avoid:** Use `.forecast(horizon)` for the point estimate (returns a plain
`np.ndarray`, not a results wrapper with `.predicted_mean`) and `.simulate(...)` separately
for spread.
**Warning signs:** `AttributeError: 'HoltWintersResults' object has no attribute 'get_forecast'`.

### Pitfall 3: Confusing weekly `WeeklyPriceRow.baltic_an` cadence with monthly's `PriceRow.baltic_an`
**What goes wrong:** Both tables have a same-named `baltic_an` column, but they are
different tables (`WeeklyPriceRow` vs `PriceRow`) at different cadences with different
underlying source rows (Phase 19: weekly is parsed natively, never resampled from monthly).
Passing a monthly-derived `history` DataFrame into a weekly forecast function would silently
fit on the wrong cadence.
**Why it happens:** Same column name across both tables invites accidental cross-wiring,
especially since this phase's functions all take a generic `history: pd.DataFrame`
parameter with no built-in cadence tag.
**How to avoid:** Document clearly in each `forecast_weekly_*` docstring that `history` must
be built from `WeeklyPriceRow` rows only; add a unit test constructing history explicitly
from weekly-shaped fixtures (206-row range per 19-02-SUMMARY.md) to catch drift.
**Warning signs:** Forecast horizon of "5" silently meaning 5 months instead of 5 weeks in
downstream Phase 22 UI would be a visible symptom of this being missed, though that surface
is out of scope for Phase 21 itself.

### Pitfall 4: Using `MIN_HISTORY_ROWS = 24` (monthly's constant) as a floor for weekly history
**What goes wrong:** Monthly's `MIN_HISTORY_ROWS = 24` was calibrated for monthly-cadence
data reaching a fitting-stability floor; the weekly backtest's own `MIN_TRAIN_WEEKLY = 104`
constant establishes a very different, weekly-appropriate floor (~2 years of weekly data).
Reusing 24 would let `forecast_weekly_*` attempt to fit SARIMAX/ETS on far too little weekly
history relative to what was actually validated.
**Why it happens:** `_require_series`'s existing `min_rows: int = MIN_HISTORY_ROWS` default
parameter is easy to call without overriding.
**How to avoid:** Introduce a weekly-appropriate minimum (e.g. `MIN_HISTORY_ROWS_WEEKLY`,
informed by `MIN_TRAIN_WEEKLY = 104` from both backtest scripts) and pass it explicitly as
`min_rows=` to every `_require_series` call inside the new weekly functions. Note
`WeeklyPriceRow` currently has only 206 rows total (19-02-SUMMARY.md) — 104 is a large
fraction of that, so this floor should be treated as a real, binding constraint worth
surfacing to the planner rather than silently choosing something smaller. [ASSUMED: the
exact weekly floor value — 104 vs. some smaller number — is Claude's Discretion per
CONTEXT.md's spirit, since CONTEXT.md doesn't name an exact constant; recommend using 104
to stay directly backtest-grounded, but this is not itself independently re-derived in this
research pass.]

### Pitfall 5: Treating `weekly_sarimax_ets.json`'s non-exog `"SARIMAX(0, 1, 0)"` records as the winning model
**What goes wrong:** Both files list multiple candidate records per series (univariate
SARIMAX, ETS-HoltDamped, SARIMAX+exog) — only the lowest-`mape_h4` record per series is the
winning, shippable model.
**Why it happens:** The JSON is a flat list of all candidates tried, not just winners; a
careless `json.load()` + first-match read could grab the wrong record.
**How to avoid:** At implementation time, explicitly select
`min(records_for_series, key=lambda r: r["mape_h4"])` (or hand-verify against the numbers
already locked in CONTEXT.md) rather than indexing by position.
**Warning signs:** Transcribed MAPE not matching 7.25%/6.96%/0.86% would indicate the wrong
record was read.

## Code Examples

### HDAN/PPAN weekly SARIMAX+exog fit and forecast
```python
# Source: backend_research/weekly/run_weekly_sarimax_ets.py, _SARIMAXWrapper +
# build_exog_sarimax_record (transcribed pattern, adapted to production single fit)
fitted = sm.tsa.SARIMAX(
    y_fit.to_numpy(),
    exog=x_fit.to_numpy(),
    order=(0, 1, 0),
    enforce_stationarity=False,
    enforce_invertibility=False,
).fit(disp=False)

result = fitted.get_forecast(steps=horizon, exog=future_exog.reshape(-1, 1))
base = np.asarray(result.predicted_mean, dtype=float)
```

### FX weekly ETS-HoltDamped fit, forecast, and simulated spread
```python
# Source: backend_research/weekly/run_fx_weekly_backtest.py, _HoltDampedWrapper
# (fit + forecast), extended here with .simulate() for the spread (new — not
# present in the backtest scripts, since backtests only needed point forecasts
# to score against holdout actuals)
fitted = ExponentialSmoothing(
    y_fit.to_numpy(),
    trend="add",
    seasonal=None,
    damped_trend=True,
    initialization_method="estimated",
).fit()

base = np.asarray(fitted.forecast(horizon), dtype=float)
sims = fitted.simulate(horizon, repetitions=500, error="add", random_state=0)
spread = np.std(sims, axis=1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Monthly-only forecasting.py, 4 series | Adds a weekly section, 3 series | Phase 21 (this phase) | Additive only — no monthly function/constant is touched (locked non-goal). |
| ARIMA-family spread only (`_arima_forecast_se`, GARCH) | Adds ETS-family spread (`.simulate()`-based) | Phase 21 (this phase) | First non-ARIMA-derived spread mechanism in this file. |

No deprecated/outdated statsmodels API surfaces were found in this investigation — both
`sm.tsa.SARIMAX` and `statsmodels.tsa.holtwinters.ExponentialSmoothing` are the current
stable 0.14.x APIs, matching CLAUDE.md's explicit pin and warning to avoid the "0.15.0 devel"
docs branch.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Using `weekly_sarimax_ets.json`'s univariate `SARIMAX(0,1,0)` order as the auxiliary SE-only fit order for weekly HDAN/PPAN (`WEEKLY_ARIMA_SE_ORDER`) is the correct analogy to monthly PPAN's `ARIMA_SE_ORDER["ppan"]` pattern | Pattern 1 | Low — `_arima_forecast_se` never uses this fit's point forecast, only `.se_mean`; a different order would only change band width, not correctness of the base forecast. Executor should sanity-check the resulting band isn't implausibly narrow/wide. |
| A2 | `MIN_HISTORY_ROWS_WEEKLY` should be set to 104 (matching `MIN_TRAIN_WEEKLY` from both backtest scripts) rather than some smaller value | Pitfall 4 | Medium — too low a floor risks fitting SARIMAX/ETS on statistically unstable weekly windows never validated by the backtest; too high (impossible here, since 206 total rows already barely exceeds 104) would make the function fail on the smallest real dataset. Planner/executor should treat 104 as a strong default, not gospel — confirm against actual `WeeklyPriceRow` row count (206) at implementation time. |

## Open Questions

1. **Exact `MIN_HISTORY_ROWS_WEEKLY` value and whether it should differ per series**
   - What we know: `MIN_TRAIN_WEEKLY = 104` was the backtest's burn-in floor for all three
     series (HDAN, PPAN, FX), and real seeded weekly data is 206 rows (HDAN/PPAN) / up to
     865 rows (FX, if a wider FX-only weekly source were ever joined — but `WeeklyPriceRow`
     itself currently only has the 206-row AN-joined range per 19-02-SUMMARY.md).
   - What's unclear: whether 104 is too conservative for a "does this function raise
     `InsufficientHistoryError` too eagerly on real data" standpoint, given only 206 rows
     exist for `WeeklyPriceRow` today (barely 2x the floor).
   - Recommendation: use 104 as documented above (backtest-grounded), but flag this
     explicitly to the planner as a value worth a first-pass sanity test against the real
     206-row seeded database rather than only synthetic test fixtures.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| statsmodels | SARIMAX + ExponentialSmoothing | ✓ | 0.14.6 | — |
| pandas | DataFrame history handling | ✓ | 3.0.5 | — |
| `app/.venv` interpreter | Correct interpreter for `forecasting.py`/tests | ✓ | confirmed matches CLAUDE.md's pinned versions | — |

No missing dependencies — everything needed is already installed in `app/.venv`.

## Security Domain

Not applicable — this phase adds pure numerical forecasting functions with no user input
parsing, no auth, no external network calls, and no new data-entry surface. `security_enforcement`
is not separately configured in `.planning/config.json`, but nothing in this phase's scope
(statsmodels fitting on already-validated `WeeklyPriceRow` data) introduces an ASVS-relevant
attack surface beyond what the existing monthly module already has.

## Sources

### Primary (HIGH confidence)
- `app/app/forecasting.py` (full file read) — existing monthly pattern, all helpers/constants
- `app/app/models.py` — `WeeklyPriceRow` schema
- `backend_research/results/weekly_sarimax_ets.json` — frozen HDAN/PPAN weekly candidates
- `backend_research/results/weekly_fx.json` — frozen FX weekly candidates
- `backend_research/weekly/run_weekly_sarimax_ets.py` — `_SARIMAXWrapper`, `_HoltDampedWrapper`, `build_exog_sarimax_record`
- `backend_research/weekly/run_fx_weekly_backtest.py` — `_SARIMAXWrapper`, `_HoltDampedWrapper` for FX
- Live probe in `app/.venv` (2026-09-01): confirmed `pandas==3.0.5`, `statsmodels==0.14.6`,
  `HoltWintersResults` API surface (no `get_forecast`, has `simulate(random_state=...)`),
  smoke-tested `ExponentialSmoothing(...).fit()`/`.forecast()`/`.simulate()` end to end
- `.planning/phases/19-weekly-schema-ingestion/19-02-SUMMARY.md` — real seeded row count (206), date range
- `.planning/config.json` — confirmed `workflow.nyquist_validation: false` (Validation
  Architecture section omitted per this research's own instructions)

### Secondary (MEDIUM confidence)
- None used beyond primary sources — no WebSearch was needed; every claim was verifiable
  directly against this repo's own frozen artifacts and a live interpreter probe.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, versions verified live
- Architecture (SARIMAX+exog pattern): HIGH — transcribed directly from backtest script + existing monthly precedent
- Architecture (ETS spread): HIGH — verified live against the actual pinned statsmodels version in `app/.venv`, not assumed from training knowledge
- Pitfalls: HIGH — each grounded in a specific file/line read this session, not general statsmodels folklore

**Research date:** 2026-09-01
**Valid until:** 30 days (stable statsmodels pin, no external API drift risk)
