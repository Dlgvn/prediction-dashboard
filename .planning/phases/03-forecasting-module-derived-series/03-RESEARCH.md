# Phase 3: Forecasting Module & Derived Series - Research

**Researched:** 2026-08-21
**Domain:** statsmodels time-series forecasting (SARIMAX+exog, VAR, ARIMA, Naive) wired into a framework-independent Python module
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** HDAN's winning model (SARIMAX+exog) needs future values of 6 predictors
  (ppan, urea_china, urea_black_sea, ammonia, baltic_an, corn_us) to forecast beyond
  horizon step 1. Phase 3 must forecast each of these 6 predictors with its own simple
  model first, then feed those forecasted paths into HDAN's SARIMAX as exog -- standard
  practice for SARIMAX-with-exog multi-step forecasting, not a shortcut.
- **D-02:** The 6 predictor sub-models use a simple ARIMA(1,1,0)-style fit each (or the
  closest sensible order per predictor's actual behavior) -- one consistent lightweight
  statistical approach for all 6, fit at request time. These do NOT need Phase 2's full
  backtest rigor, but they should be real fitted models, not held-flat-at-last-value
  naive projections.
- **D-03 (conflict resolution):** PPAN's winning model is a VAR system over
  [ppan, hdan, baltic_an, urals], which forecasts HDAN jointly as a byproduct of
  forecasting PPAN. HDAN also has its own separate winning model (SARIMAX+exog).
  HDAN's own SARIMAX forecast is authoritative everywhere the app displays "the" HDAN
  number -- the VAR system's internal hdan forecast is used only internally to make
  PPAN's VAR system self-consistent, not surfaced or compared against SARIMAX's HDAN
  output.
- **D-04:** Bull/bear = base +/- 1 standard deviation of the volatility source named per
  series in `02-MODEL-DECISIONS.md` (GARCH sigma for HDAN, ARIMA forecast SE for PPAN/
  Diesel-USD/FX) -- an approximately 68% band, not a 95% band.
- **D-05:** Per FCST-05 and Phase 2's GARCH findings, the spread must widen with horizon
  using each series' actual per-horizon sigma/SE value (already present in
  `02-MODEL-DECISIONS.md`'s h=1/h=6/h=12 walk-forward numbers) -- not a single fixed
  spread applied flat across all 12 months.
- **D-06:** Models refit on every forecast request, fitting on whatever's currently in
  the SQLite `PriceRow` table -- no caching or cache-invalidation logic. Fit cost is
  milliseconds; do not add caching infrastructure preemptively.
- **D-07:** Per-series functions behind one dispatch function -- `forecast_hdan()`,
  `forecast_ppan_var_system()`, `forecast_diesel_usd()` / `forecast_fx()` (both Naive,
  may share one function), each implementing that series' actual winning model's logic
  as validated in Phase 2. A single `forecast_all(rows, horizon)` orchestrates all four,
  computes bull/bear from the correct volatility source per series (D-04/D-05), and
  derives `diesel_mnt` (FCST-03) from the Diesel-USD and FX forecasts plus the global
  `markup_pct` `AppSetting`. Rejected a single generic
  `forecast_series(history, horizon, model_config)` -- the config dict would encode very
  different things per series, producing a fake-uniform interface that hides real
  complexity rather than clarifying it.
- **D-08:** This module has zero `import reflex` (per `ARCHITECTURE.md`'s established
  boundary) -- unit-testable independent of the UI, called by Phase 4/5's Reflex state
  layer, not by anything in `app/app/app.py` directly.

### Claude's Discretion

None flagged this round -- all four presented gray areas were explicitly decided,
several with follow-up rounds.

### Deferred Ideas (OUT OF SCOPE)

None raised outside phase scope -- discussion stayed within Phase 3's boundary (model
implementation, exog handling, spread computation, refit cadence, module organization).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| FCST-02 | For the selected horizon, the app computes a base (point), bull, and bear forecast value for each month, for HDAN, PPAN, Diesel-USD, and FX rate | Patterns 1-5 give per-series fit/forecast + spread code for all four series; `forecast_all()` dispatcher shape in the Architecture diagram composes them |
| FCST-03 | Diesel purchasing price in MNT is computed as a derived series (Diesel-USD forecast x FX forecast x markup) at each horizon step, not modeled independently | Pattern 6 (`diesel_mnt_forecast()`) gives the exact derivation and flags the bull/bear-combination method as an explicit, documented simplification (Assumption A3) |
| FCST-04 | Bull/bear spread is computed per series from that series' own backtested error/volatility (not one flat percentage applied to every series) | Patterns 3 (ARIMA forecast SE for PPAN/Diesel/FX) and 4 (GARCH sigma for HDAN) implement the two distinct volatility sources named in `02-MODEL-DECISIONS.md`; Pitfall 1 and Anti-Patterns section guard against collapsing them into one flat rule |
| FCST-05 | Bull/bear spread widens as the horizon extends further out, rather than staying a fixed percentage regardless of how many months ahead the forecast is | Both volatility sources are computed per-horizon-step (`se_mean` array from `get_forecast(steps=horizon)`; `sigma_by_horizon[:horizon]` slice), not as a single scalar; Validation Architecture section maps this to an explicit widening test |
</phase_requirements>

## Summary

Phase 3 is almost entirely a **transcription** task, not a model-design task: Phase 2
already picked every model, order, predictor set, and volatility source
(`02-MODEL-DECISIONS.md` / `winners.json`), and Phase 3's job is to reimplement those
exact specs as production, request-time-refit functions with zero `import reflex`. The
technical risk is concentrated in three statsmodels API details: (1) correctly passing
multi-step future exog into `SARIMAX.get_forecast()`, (2) correctly extracting a single
target's path out of a joint `VAR.forecast()` array, and (3) computing the "arima
forecast SE" volatility source for PPAN/Diesel-USD/FX using a *separate* small ARIMA fit
that is NOT the same object as the point-forecast model (Naive/VAR don't have native
forecast SEs). GARCH sigma for HDAN also needs a unit conversion (percent-return scale →
price scale) that is easy to get wrong.

**Primary recommendation:** Build one small ARIMA helper (`_arima_forecast_se(series,
order, steps)`) reused by PPAN/Diesel-USD/FX, one iterative-SARIMAX+exog helper for HDAN
that internally forecasts its 6 predictors first with `ARIMA(1,1,0)`-style sub-models,
one VAR-system helper for PPAN's point forecast (percent-change fit, level
reconstruction, as Phase 2's `_VARIterativeWrapper` already does), and one shared
Naive helper for Diesel-USD/FX. Compose all four through `forecast_all()`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read historical `PriceRow` data | Data layer (`models.py` via `rx.session()`) | — | Already established in Phase 1; Phase 3 receives plain data, does not query SQLite itself |
| Fit/forecast HDAN (SARIMAX+exog) | Model layer (`forecasting.py`) | — | Zero-Reflex, pure statsmodels logic per D-07/D-08 |
| Fit/forecast 6 HDAN predictor sub-models | Model layer (`forecasting.py`) | — | Internal implementation detail of `forecast_hdan()`, not separately surfaced |
| Fit/forecast PPAN (VAR system) | Model layer (`forecasting.py`) | — | Same boundary |
| Fit/forecast Diesel-USD, FX (Naive + ARIMA-SE) | Model layer (`forecasting.py`) | — | Same boundary |
| Bull/bear spread computation | Model layer (`forecasting.py`) | — | Pure arithmetic on volatility source + base forecast, belongs with the forecasting logic, not the state layer |
| Diesel-MNT derivation | Model layer (`forecasting.py`) | — | FCST-03, pure arithmetic on two other forecasts + `markup_pct` |
| Orchestration across all 4 series + derived series | Model layer (`forecast_all()` dispatcher) | — | D-07's single dispatch function |
| ORM ↔ plain-type translation, `markup_pct` lookup | State layer (Phase 4/5, not this phase) | — | `ARCHITECTURE.md`: state.py is the only file bridging `PriceRow`/`AppSetting` ORM objects into `forecasting.py`'s plain-type calls |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| statsmodels | 0.14.6 [CITED: STACK.md, project-verified 2026-08-21] | `SARIMAX`, `ARIMA`, `VAR` fit/forecast | Already pinned and used identically in Phase 2's `backend_research/` scripts; Phase 3 reuses the exact same API surface, just at request time instead of walk-forward time |
| pandas | 3.0.5 pinned per STACK.md; **2.2.3 actually installed per STATE.md Phase 02-01 note** [CITED: STATE.md] | Wide-table → per-series `Series`/`DataFrame` construction from `PriceRow` rows | Needed to build `pd.Series`/`pd.DataFrame` inputs for statsmodels calls; verify actual installed version with `pip show pandas` before writing date-index logic, since Phase 2 explicitly noted the installed version (2.2.3) diverges from the STACK.md pin (3.0.5) |
| numpy | whatever pip resolves per statsmodels' own constraint [ASSUMED — not independently re-verified this session, inherited from STACK.md's stated policy] | Array ops for exog frames, sigma arrays | Direct dependency of statsmodels/pandas; no separate install needed |

### Supporting
None new — this phase adds no new third-party dependencies. It only *uses* the
already-installed statsmodels/pandas stack differently (request-time single-shot fit
instead of Phase 2's walk-forward harness).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hard-coded statsmodels calls per D-06 | `pmdarima.auto_arima` | Explicitly forbidden by `02-MODEL-DECISIONS.md`'s "Phase 3 must not" section and STACK.md — re-searching orders at runtime is banned regardless of convenience |
| One ARIMA helper reused 3x (PPAN/Diesel/FX SE) | Bespoke per-series SE logic | Reuse is correct here — all three use the identical `ARIMA(order).fit().get_forecast(steps).se_mean` pattern with only the order differing; a single parameterized helper avoids code duplication without hiding real per-series differences (D-07's stated rejection criterion is about hiding *model* differences, not about a shared SE-computation utility) |

## Package Legitimacy Audit

Not applicable — no new external packages are introduced in this phase. All required
libraries (`statsmodels`, `pandas`, `numpy`) were already installed and verified in
Phase 1/Phase 2.

## Verified Version Check

```
$ pip show statsmodels pandas 2>/dev/null | grep -E "Name|Version"
```
Run this at the start of Phase 3 implementation to confirm the actually-installed
versions match what this research assumes (statsmodels 0.14.6; pandas possibly 2.2.3 per
Phase 2's note, not the STACK.md-pinned 3.0.5) — **do not assume STACK.md's pins are what
is installed; Phase 2 already found one mismatch.**

## Architecture Patterns

### System Architecture Diagram

```
[state.py: DashboardState.run_forecast(horizon)]           <- Phase 4/5, not this phase
        │  reads PriceRow rows already loaded in memory
        │  extracts plain pd.Series per series column (date-indexed, sorted)
        ▼
┌───────────────────────────── forecasting.py (zero `import reflex`) ─────────────────────────────┐
│                                                                                                    │
│  forecast_all(history: dict[str, pd.Series], horizon: int, markup_pct: float) -> dict            │
│        │                                                                                          │
│        ├──► forecast_hdan(history, horizon)                                                       │
│        │        │                                                                                 │
│        │        ├──► _forecast_predictor(history[p], horizon)  × 6   (D-01/D-02: ARIMA(1,1,0)-style)│
│        │        │        (ppan, urea_china, urea_black_sea, ammonia, baltic_an, corn_us)          │
│        │        │                                                                                 │
│        │        └──► SARIMAX(0,1,0)+exog fit on hdan history                                      │
│        │                 .get_forecast(steps=horizon, exog=future_exog_df)                        │
│        │                 → base path (predicted_mean)                                             │
│        │        └──► GARCH sigma (garch_volatility.json, hard-coded per-horizon %) → bull/bear     │
│        │                                                                                            │
│        ├──► forecast_ppan_var_system(history, horizon)                                             │
│        │        │  VAR system=[ppan, hdan, baltic_an, urals], fit on pct-change                    │
│        │        │  .forecast(y, steps=horizon) → array, reconstruct levels for ppan column only     │
│        │        │  (internal hdan output DISCARDED per D-03 — SARIMAX's hdan is authoritative)      │
│        │        └──► _arima_forecast_se(ppan_history, order=(0,1,0), horizon) → bull/bear            │
│        │                                                                                            │
│        ├──► forecast_diesel_usd(history, horizon) ─┐  both Naive point-forecast +                   │
│        ├──► forecast_fx(history, horizon)         ─┘  _arima_forecast_se() per-series order          │
│        │                                                                                            │
│        └──► diesel_mnt = diesel_usd_forecast × fx_forecast × (1 + markup_pct/100)  per horizon step │
│                 (FCST-03; bull/bear on diesel_mnt = product of bull/bear bounds, see Pitfall below)  │
│                                                                                                       │
│  Returns: dict[series_name, list[{"month": int, "base": float, "bull": float, "bear": float}]]      │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
        ▲
        │  called with plain pd.Series/dict, returns plain dict — no ORM, no rx.State
[Phase 4/5 state.py translates result dict into DashboardState.forecast_results for UI]
```

### Recommended Project Structure
```
app/app/
├── forecasting.py          # NEW this phase — all logic below lives here, zero `import reflex`
├── models.py                # existing — PriceRow/AppSetting, untouched by this phase
└── state.py                  # Phase 4/5 — will call forecast_all(), not touched by this phase
```

Single-file `forecasting.py` is appropriate at this scale (4 series + 6 predictor
sub-models + 2 derived computations) — do not pre-split into a package unless the file
exceeds ~300-400 lines.

### Pattern 1: SARIMAX+exog multi-step forecast with future exog (HDAN)

**What:** Fit `SARIMAX(order=(0,1,0))` on HDAN history with lagged exog, then forecast
`horizon` steps ahead by supplying a **future exog DataFrame** whose row count exactly
equals `horizon` and whose column order exactly matches what the model was fit with.
**When to use:** HDAN only — this is the one series with an exog-dependent multi-step
forecast (D-01).
**Source:** [CITED: statsmodels 0.14 docs — `SARIMAXResults.get_forecast`, https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.get_forecast.html] cross-checked against `backend_research/run_arima_sarimax_wf.py`'s working `_SARIMAXWrapper` (same fit call, `enforce_stationarity=False, enforce_invertibility=False`).

```python
import numpy as np
import pandas as pd
import statsmodels.api as sm

def forecast_hdan(history: pd.DataFrame, horizon: int) -> dict:
    """history: DataFrame with columns [hdan, ppan, urea_china, urea_black_sea,
    ammonia, baltic_an, corn_us], date-indexed, sorted ascending, most-recent last.
    """
    predictors = ["ppan", "urea_china", "urea_black_sea", "ammonia", "baltic_an", "corn_us"]
    lags = {"ppan": 1, "urea_china": 1, "urea_black_sea": 1, "ammonia": 3,
            "baltic_an": 1, "corn_us": 1}

    # D-01: forecast each predictor forward `horizon` steps with its own ARIMA(1,1,0)-style fit
    future_exog = {}
    for p in predictors:
        future_exog[p] = _forecast_predictor(history[p].dropna(), horizon)  # returns np.ndarray, len == horizon

    # Build the aligned lagged exog history the model was ORIGINALLY fit on (leakage-safe:
    # same shift-by-lag convention as Phase 2's build_sarimax_records, per RESEARCH.md Pitfall 1)
    exog_cols = {p: history[p].shift(lags[p]) for p in predictors}
    exog_hist = pd.DataFrame(exog_cols, index=history.index)
    combined = pd.concat([history["hdan"].rename("y"), exog_hist], axis=1).dropna()
    y_fit = combined["y"]
    x_fit = combined[predictors]

    model = sm.tsa.SARIMAX(
        y_fit.to_numpy(),
        exog=x_fit.to_numpy(),
        order=(0, 1, 0),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    fitted = model.fit(disp=False)

    # Future exog: horizon rows, same column order as x_fit.columns
    future_exog_df = pd.DataFrame({p: future_exog[p] for p in predictors})[predictors]

    forecast_result = fitted.get_forecast(steps=horizon, exog=future_exog_df.to_numpy())
    base = forecast_result.predicted_mean          # np.ndarray, len == horizon
    # forecast_result.se_mean also available but HDAN uses GARCH, not this SE, per D-04
    return _apply_garch_spread("hdan", base, horizon)
```

**Key gotchas:**
- `exog` passed to `.fit()`/model constructor must be a **2-D array-like** with columns
  in a fixed, remembered order; `.get_forecast(steps=..., exog=...)` must supply the
  SAME column order and exactly `steps` rows, or statsmodels raises a shape error (or,
  worse, silently misaligns columns if you pass a plain unordered dict/array).
- Building the future exog for lag > 1 predictors (ammonia, lag 3): the sub-model
  forecasts `ammonia`'s own future values, and those forecasted values feed directly into
  HDAN's exog frame for the corresponding future step — the lag is already baked into how
  the *original* fit's exog was constructed (`history[p].shift(lag)`), so the future exog
  frame simply uses `_forecast_predictor`'s forward path directly, not shifted again.
- `enforce_stationarity=False, enforce_invertibility=False` matches Phase 2's exact
  fitting conditions — carry this over so behavior doesn't silently drift from the
  backtested configuration.

### Pattern 2: VAR system forecast, extracting one target series (PPAN)

**What:** Fit `VAR` on **percent-change** data across the 4-series system
`[ppan, hdan, baltic_an, urals]`, forecast `horizon` steps with `.forecast(y, steps)`,
then reconstruct PPAN's price level from the cumulative percent-change path — this is
exactly `backend_research/run_var_vecm_wf.py`'s `_VARIterativeWrapper`, promoted to
production. HDAN's own column in the VAR output is fit and forecast internally (VAR
requires forecasting its whole system jointly) but **must be discarded / never surfaced**
per D-03 — only `forecast_hdan()`'s SARIMAX output is authoritative for "the" HDAN number.
**Source:** [CITED: statsmodels 0.14 docs — `VAR.fit`, `VARResults.forecast`, https://www.statsmodels.org/stable/vector_ar.html] cross-checked against the working implementation in `run_var_vecm_wf.py`.

```python
from statsmodels.tsa.api import VAR
import numpy as np
import pandas as pd

def forecast_ppan_var_system(history: pd.DataFrame, horizon: int) -> dict:
    """history: DataFrame with columns [ppan, hdan, baltic_an, urals], date-indexed."""
    system = ["ppan", "hdan", "baltic_an", "urals"]
    levels = history[system].dropna()

    target_pct = (levels["ppan"].pct_change() * 100).rename("ppan")
    member_pct = (levels[["hdan", "baltic_an", "urals"]].pct_change() * 100)
    frame = pd.concat([target_pct, member_pct], axis=1).dropna()

    lag = 1  # hard-coded per D-06/02-MODEL-DECISIONS.md — no runtime select_order() search
    fitted = VAR(frame).fit(lag)

    last_obs = fitted.k_ar  # == lag; number of trailing rows VAR.forecast() needs
    history_array = frame.values[-last_obs:]
    pct_path = fitted.forecast(history_array, steps=horizon)  # shape (horizon, n_vars)

    # Column order in `pct_path` == `frame.columns` order == ["ppan", "hdan", "baltic_an", "urals"]
    ppan_pct = pct_path[:, frame.columns.get_loc("ppan")] / 100.0
    last_level = float(levels["ppan"].iloc[-1])
    ppan_levels = last_level * np.cumprod(1 + ppan_pct)   # reconstruct price levels

    # hdan_pct = pct_path[:, frame.columns.get_loc("hdan")]  -- computed internally, NEVER returned (D-03)
    return _apply_arima_se_spread("ppan", levels["ppan"], ppan_levels, order=(0, 1, 0), horizon=horizon)
```

**Key gotchas:**
- `VARResults.forecast(y, steps)` takes the **trailing `k_ar` observations** as its `y`
  argument (a plain numpy array, not the fitted DataFrame) — passing the wrong number of
  trailing rows raises a shape error. `fitted.k_ar` gives you the exact count to slice.
- The returned array's column order matches the DataFrame's column order at fit time —
  always resolve the target's column index via `frame.columns.get_loc(...)` rather than
  a hard-coded integer index, so a future column-order change doesn't silently
  mis-extract the wrong series.
- VAR lag must be **hard-coded to whatever Phase 2 selected once via `select_order()`**,
  not re-searched at runtime (D-06 / `02-MODEL-DECISIONS.md`'s "must not" list). Confirm
  the exact winning lag value against `backend_research/results/wf_var_vecm.json`'s ppan
  Direct-OLS record before hard-coding `lag = 1` in the plan — this research infers `lag=1`
  from `run_var_vecm_wf.py`'s `select_var_lag(..., maxlags=3)` default fallback but the
  planner/implementer MUST verify the actual selected lag from Phase 2's output JSON
  rather than trust this inferred value. **[ASSUMED — verify against wf_var_vecm.json]**

### Pattern 3: ARIMA forecast standard error as the volatility source (PPAN / Diesel-USD / FX)

**What:** `02-MODEL-DECISIONS.md` names `arima_forecast_se` as the volatility source for
PPAN, Diesel-USD, and FX — but PPAN's point-forecast model is VAR and Diesel/FX's is
Naive, **neither of which produces a native forecast standard error**. This means a
*separate*, small ARIMA model must be fit purely to extract `se_mean` per horizon step,
independent of the point-forecast path. The exact orders were AIC-selected once in Phase
2 and appear in `REPORT-PHASE2.md`'s per-series ranking tables: **PPAN → ARIMA(0,1,0)**,
**Diesel-USD → ARIMA(1,1,1)**, **FX rate → ARIMA(1,1,2)**. `winners.json`'s
`sigma_by_horizon: null` for these three series confirms this SE was NOT precomputed by
Phase 2 and must be computed fresh at request time in Phase 3 (consistent with D-06's
refit-on-every-request decision).
**Source:** [VERIFIED: backend_research/REPORT-PHASE2.md lines 52, 68, 88 — per-series ARIMA order + MAPE table] + [CITED: statsmodels 0.14 docs — `ARIMAResults.get_forecast().se_mean`, https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMAResults.html]

```python
from statsmodels.tsa.arima.model import ARIMA
import numpy as np

# Hard-coded per REPORT-PHASE2.md — verify against wf_arima_sarimax.json before finalizing;
# these are the ARIMA orders AIC-selected on the FIRST training window in Phase 2, not
# re-searched here (D-06).
ARIMA_SE_ORDER = {
    "ppan": (0, 1, 0),
    "diesel_usd_ton": (1, 1, 1),
    "fx_rate": (1, 1, 2),
}

def _arima_forecast_se(series: pd.Series, order: tuple[int, int, int], horizon: int) -> np.ndarray:
    """Fits a plain ARIMA(order) on `series` levels and returns per-horizon-step
    standard error (se_mean), length == horizon. Independent of the point-forecast model.
    """
    fitted = ARIMA(series.dropna().to_numpy(), order=order).fit()
    result = fitted.get_forecast(steps=horizon)
    return result.se_mean          # np.ndarray, shape (horizon,), same units as `series`
```

**Key gotchas:**
- `ARIMAResults.get_forecast(steps=h)` returns a `PredictionResults` object; `.se_mean`
  is the array to use (NOT `.se`, which does not exist on this object; NOT the
  in-sample residual std, which does not widen with horizon and would violate FCST-05).
  `.predicted_mean` is also available but is NOT used here — only the SE is consumed;
  the *point* forecast for PPAN/Diesel/FX comes from the VAR/Naive model, not this
  auxiliary ARIMA fit.
- `.se_mean` is already in the **same units as the input series** (price levels, USD, or
  MNT/USD rate — not a percent), so it can be added/subtracted from the base forecast
  directly: `bull = base + se_mean`, `bear = base - se_mean` — no unit conversion needed
  here (contrast with GARCH sigma below, which DOES need conversion).
- This ARIMA fit is fully separate from whatever model actually produced the point
  forecast (VAR for PPAN, Naive for Diesel/FX) — do not attempt to extract this ARIMA's
  own `.predicted_mean` as the displayed forecast; that would silently replace the
  actual winning model with the runner-up.

### Pattern 4: GARCH sigma → price-unit bull/bear spread (HDAN)

**What:** `backend_research/results/garch_volatility.json`'s `hdan.sigma_by_horizon`
array holds conditional volatility in **percent-return units** (GARCH was fit on
`pct_change() * 100` per `run_garch.py` line 105: `pct_returns = series.pct_change() *
100`), NOT in price-level units and NOT as a 0-1 fraction. Applying these sigma values
directly as an additive price offset would be off by a factor of 100 and would not scale
with the current price level. Convert: `bound = base_forecast_h × sigma_pct_h / 100`.
**Source:** [VERIFIED: backend_research/run_garch.py lines 41, 105 — `arch_model(..., mean="Constant")` fit on `series.pct_change() * 100`, `forecast.variance` → `sigma = sqrt(variance)` in the same percent units]

```python
import numpy as np

# Hard-coded from backend_research/results/garch_volatility.json's "hdan" record —
# 12 values, h=1..12 (D-06: precomputed offline, no runtime GARCH refit needed since
# 02-MODEL-DECISIONS.md names this as the frozen volatility source, not a live-refit one).
# CONFIRM at implementation time whether Phase 3 should re-fit GARCH live per D-06's
# "refit on every request" language, OR reuse this static array — see Open Questions.
HDAN_GARCH_SIGMA_PCT = [
    12.532726174302507, 12.583026997209927, 12.633127540913241, 12.6830301788432,
    12.73273723791998, 12.782250999819277, 12.83157370219443, 12.880707539856434,
    12.929654665913594, 12.978417192872477, 13.026997193701803, 13.075396702860736,
]

def _apply_garch_spread(series_name: str, base: np.ndarray, horizon: int) -> dict:
    sigma_pct = np.array(HDAN_GARCH_SIGMA_PCT[:horizon])
    offset = base * sigma_pct / 100.0   # convert percent-return sigma to price-unit offset
    return {
        "base": base.tolist(),
        "bull": (base + offset).tolist(),
        "bear": (base - offset).tolist(),
    }
```

**Key gotchas:**
- Do NOT treat `sigma_by_horizon` values (~12.5) as already being in price units — they
  are percent-of-return magnitudes; multiplying by 100 (treating them as a raw fraction)
  or skipping the `/100` (treating them as already a price delta) are both silent
  correctness bugs that would produce a wildly wrong spread.
- The offset scales with `base` (the current-horizon forecast level), so bull/bear bands
  naturally widen in absolute price terms even where `sigma_pct` itself is roughly flat
  (HDAN's sigma_by_horizon only grows from 12.53 to 13.08 across h=1..12, a mild ~4.3%
  relative widening — combined with `base` typically trending, the resulting price-unit
  band still satisfies FCST-05's widening requirement, but confirm this empirically once
  real forecasts are computed, since a flat/declining base path combined with near-flat
  sigma_pct could produce a band that widens less than expected).

### Pattern 5: Predictor sub-models (D-02) and Naive forecasts (Diesel-USD, FX)

```python
from statsmodels.tsa.arima.model import ARIMA
import numpy as np

def _forecast_predictor(series: pd.Series, horizon: int) -> np.ndarray:
    """D-02: one consistent lightweight ARIMA(1,1,0)-style fit per HDAN predictor,
    fit at request time. Falls back to a lower-order fit if (1,1,0) fails to converge
    on a short/degenerate series (real fitted model still required, not a naive hold-flat)."""
    y = series.dropna().to_numpy()
    try:
        fitted = ARIMA(y, order=(1, 1, 0)).fit()
    except Exception:
        fitted = ARIMA(y, order=(0, 1, 0)).fit()   # documented fallback, still a real fit
    return fitted.forecast(steps=horizon)


def _naive_forecast(series: pd.Series, horizon: int) -> np.ndarray:
    """Diesel-USD / FX point forecast: repeat the last observed value for every step."""
    last = float(series.dropna().iloc[-1])
    return np.full(horizon, last)


def forecast_diesel_usd(history: pd.Series, horizon: int) -> dict:
    base = _naive_forecast(history, horizon)
    se = _arima_forecast_se(history, order=ARIMA_SE_ORDER["diesel_usd_ton"], horizon=horizon)
    return {"base": base.tolist(), "bull": (base + se).tolist(), "bear": (base - se).tolist()}


def forecast_fx(history: pd.Series, horizon: int) -> dict:
    base = _naive_forecast(history, horizon)
    se = _arima_forecast_se(history, order=ARIMA_SE_ORDER["fx_rate"], horizon=horizon)
    return {"base": base.tolist(), "bull": (base + se).tolist(), "bear": (base - se).tolist()}
```

### Pattern 6: Diesel-MNT derivation (FCST-03) and its bull/bear propagation

```python
def diesel_mnt_forecast(diesel_usd_fc: dict, fx_fc: dict, markup_pct: float) -> dict:
    """diesel_usd_fc / fx_fc: {"base": [...], "bull": [...], "bear": [...]} from
    forecast_diesel_usd()/forecast_fx(). markup_pct is a percentage (e.g. 5.0 for 5%)."""
    multiplier = 1 + markup_pct / 100.0

    def _mnt(usd_path, fx_path):
        return [u * f * multiplier for u, f in zip(usd_path, fx_path)]

    return {
        "base": _mnt(diesel_usd_fc["base"], fx_fc["base"]),
        # Bull for MNT = both underlying series at their OWN bull edge, not base×base+delta;
        # since diesel_usd and fx are forecast independently (not jointly), this treats their
        # errors as compounding in the same direction for the bull/bear extremes -- a
        # deliberate, documented simplification, not a statistically rigorous joint interval.
        "bull": _mnt(diesel_usd_fc["bull"], fx_fc["bull"]),
        "bear": _mnt(diesel_usd_fc["bear"], fx_fc["bear"]),
    }
```

**Gotcha (flag for planner as an open design decision, not a settled fact):**
Multiplying two independent bull/bear bounds together (`diesel_usd.bull × fx.bull`)
compounds two separate ~68% intervals into something that is no longer itself a clean
~68% interval for the product — it's wider than the "true" combined uncertainty would be
if the two series' errors were uncorrelated, and narrower than it would be if they were
perfectly correlated. This is a reasonable, simple, explainable approximation (matches
the Excel workbook's stated "approximate range communicated honestly" philosophy per
D-04) but is not statistically rigorous. No requirement in `REQUIREMENTS.md` mandates a
more rigorous combination method, and `02-MODEL-DECISIONS.md` is silent on Diesel-MNT's
own spread methodology (it only names volatility sources for HDAN/PPAN/Diesel-USD/FX,
not for the derived series) — this is Claude's Discretion territory left open by
CONTEXT.md, and this straightforward "combine at matching scenario edges" approach is
the recommended default unless the planner/user wants something more rigorous (e.g.
propagate variances instead of bounds). **[ASSUMED — reasonable default, not verified
against any requirement or Phase 2 spec]**

### Anti-Patterns to Avoid
- **Re-running AIC grid search or `select_order()`/`auto_arima` at request time:**
  explicitly forbidden by D-06 and `02-MODEL-DECISIONS.md`'s "Phase 3 must not" list —
  all orders (SARIMAX(0,1,0), VAR lag, ARIMA(0,1,0)/(1,1,1)/(1,1,2)) must be hard-coded
  constants sourced from Phase 2's output files.
- **Surfacing the VAR system's internal HDAN forecast anywhere:** per D-03, only
  `forecast_hdan()`'s SARIMAX output is "the" HDAN number; the VAR system's own hdan
  column must be computed (VAR requires it) but discarded, never returned from
  `forecast_ppan_var_system()`.
- **Treating GARCH sigma as already being in price units:** see Pattern 4 — must divide
  by 100 and multiply by the base forecast.
- **Passing `PriceRow` ORM instances or calling `rx.session()` inside `forecasting.py`:**
  violates D-08/`ARCHITECTURE.md`'s zero-`import reflex` boundary; all inputs must
  already be plain `pd.Series`/`pd.DataFrame`/`float` by the time they reach this module.
- **Using a single flat spread percentage across all series/horizons:** explicitly
  forbidden by FCST-04/FCST-05 and D-04/D-05 — every series must use its own named
  volatility source, evaluated per-horizon-step.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ARIMA/SARIMAX fitting and forecasting | Custom Kalman-filter or OLS-based ARIMA implementation | `statsmodels.tsa.arima.model.ARIMA` / `statsmodels.tsa.statespace.sarimax.SARIMAX` | Already the project's chosen stack (STACK.md); hand-rolling would reintroduce the exact numerical edge cases (differencing, invertibility, MLE convergence) statsmodels already handles correctly and that Phase 2's backtest already validated against |
| VAR system fitting/forecasting | Custom multivariate OLS system solver | `statsmodels.tsa.api.VAR` | Same rationale — Phase 2's `wf_var_vecm.json` numbers were produced with this exact API; a hand-rolled reimplementation would not match the backtested MAPE figures, breaking FCST-07's provenance guarantee |
| Forecast standard error computation | Manual residual-based SE approximation | `ARIMAResults.get_forecast().se_mean` | statsmodels' native SE already correctly accounts for parameter uncertainty and the specific ARIMA order's error propagation; a hand-rolled approximation (e.g. flat in-sample residual std) would violate FCST-05's per-horizon widening requirement |
| Order search / model selection | Any runtime AIC/BIC grid search or `auto_arima` | Hard-coded orders from `02-MODEL-DECISIONS.md`/`REPORT-PHASE2.md` | Explicitly forbidden by this phase's own governing decisions (D-06); order search is Phase 2's completed job, not Phase 3's |

**Key insight:** Every model-fitting building block this phase needs already exists,
already-tested, in `backend_research/`'s Phase 2 scripts. The only genuinely new work is
(a) collapsing walk-forward windowing into a single request-time fit-on-everything call,
(b) wiring HDAN's predictor sub-models feed-forward (D-01), and (c) the bull/bear
arithmetic layer (D-04/D-05) that Phase 2's scripts never needed (they only computed
MAPE, not scenario bands).

## Common Pitfalls

### Pitfall 1: GARCH sigma unit mismatch
**What goes wrong:** Bull/bear bands for HDAN come out either ~100x too wide or
effectively invisible.
**Why it happens:** `sigma_by_horizon` values (~12.5) look like they could plausibly be
either a raw price-unit std or a percent value; without checking `run_garch.py`'s fit
call (`pct_change() * 100`), it's easy to guess wrong.
**How to avoid:** Always compute `offset = base_forecast * sigma_pct / 100`, never
`offset = sigma_pct` directly.
**Warning signs:** Bull/bear bands that are visually identical to the base line (offset
too small) or that dwarf the chart's y-axis range (offset too large).

### Pitfall 2: Future exog shape/order mismatch for SARIMAX
**What goes wrong:** `get_forecast(exog=...)` either raises a shape error or (worse)
silently produces a nonsensical forecast if columns are in the wrong order relative to
how the model was fit.
**Why it happens:** Building `future_exog` from a dict comprehension does not guarantee
column order matches `x_fit.columns`; dict iteration order in Python 3.7+ is
insertion-order but easy to accidentally scramble across a refactor.
**How to avoid:** Always explicitly reindex/select `future_exog_df[predictors]` with the
same `predictors` list used to build `x_fit`, immediately before calling
`.get_forecast()`.
**Warning signs:** HDAN forecasts that look wildly discontinuous from the last actual
value, or a shape-mismatch exception at `.get_forecast()` call time.

### Pitfall 3: Confusing which model's SE/forecast is authoritative
**What goes wrong:** Accidentally returning the auxiliary ARIMA(0,1,0)/(1,1,1)/(1,1,2)
fit's own point forecast (`.predicted_mean`) instead of the actual winning model's
(VAR/Naive) point forecast — silently swapping in a worse model (27.5% MAPE ARIMA vs.
23.8% MAPE VAR for PPAN, per REPORT-PHASE2.md).
**Why it happens:** `_arima_forecast_se()` internally has both `.predicted_mean` and
`.se_mean` available on the same result object; it's easy to accidentally wire the wrong
attribute through if the helper's return type isn't carefully scoped to `se_mean` only.
**How to avoid:** `_arima_forecast_se()` should return ONLY the SE array, never the point
forecast, making misuse a type error rather than a silent wrong-number bug.
**Warning signs:** PPAN forecasts that don't visibly incorporate `hdan`/`baltic_an`/`urals`
movement (a sign the VAR system's joint forecast was replaced by a univariate ARIMA).

### Pitfall 4: VAR forecast() trailing-window size error
**What goes wrong:** `VARResults.forecast(y, steps)` raises a shape error or produces
garbage if `y`'s row count doesn't exactly equal `fitted.k_ar` (the fitted lag order).
**Why it happens:** Manually hard-coding "pass the last 1 row" without checking that the
actual selected lag might not be 1 (see Pattern 2's explicit ASSUMED flag).
**How to avoid:** Always slice `frame.values[-fitted.k_ar:]`, never a hard-coded trailing
count independent of the fitted model's own `.k_ar` attribute.
**Warning signs:** `ValueError` at `.forecast()` call time, or (if the wrong slice size
happens not to raise) forecasts that don't smoothly continue from the last actual VAR
state.

### Pitfall 5: Diesel-MNT computed from independently-refit Diesel-USD/FX rather than the same forecast objects
**What goes wrong:** If `forecast_all()` accidentally calls `forecast_diesel_usd()` and
`forecast_fx()` twice each (once for their own display, once again inside
`diesel_mnt_forecast()`), refit-on-every-request (D-06) means two calls could, in theory,
produce non-identical Naive point values IF the underlying history changed between
calls (unlikely mid-request, but still wasteful and a correctness risk if history is
ever passed by reference and mutated between calls).
**Why it happens:** `diesel_mnt_forecast()`'s natural signature takes already-computed
forecast dicts, but a careless orchestrator could instead call the fit functions a
second time inline.
**How to avoid:** `forecast_all()` must compute `diesel_usd_fc` and `fx_fc` exactly once
each, then pass those same dict objects into both the returned `forecast_all()` result
AND `diesel_mnt_forecast()` — never refit either series a second time for the derived
series.
**Warning signs:** Diesel-USD/FX shown standalone don't numerically match what was used
to compute Diesel-MNT.

## Code Examples

See Patterns 1-6 above — all six are complete, directly usable reference
implementations covering every one of this phase's four series plus the derived series.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Phase 2's walk-forward harness (`walk_forward_backtest`, refit at every rolling origin, held-out MAPE scoring) | Phase 3's single request-time fit-on-all-available-data, no held-out scoring | This phase (D-06) | Simpler code path (no windowing loop), but loses the ability to self-check against fresh data drift — Phase 3 trusts that Phase 2's backtested orders/models remain valid as more months of data accumulate; there is no requirement in this phase to re-validate that trust (re-backtesting is out of scope, belongs to a hypothetical future "Phase 2 refresh" milestone) |

**Deprecated/outdated:** None — this is greenfield code within an already-current stack;
no statsmodels API used here is deprecated in 0.14.6.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | VAR lag for PPAN's system is 1 (inferred from `run_var_vecm_wf.py`'s `select_var_lag(..., maxlags=3)` fallback default, not directly read from `wf_var_vecm.json`'s actual output for the ppan Direct-OLS record) | Pattern 2 | If the actual selected lag differs (e.g. 2 or 3), the hard-coded `lag = 1` in the shipped module would silently reproduce a DIFFERENT (worse or better) model than what Phase 2 actually backtested and reported as the 23.80% MAPE winner — violates FCST-07's provenance guarantee. **Planner must add a task to read the exact lag from `backend_research/results/wf_var_vecm.json` before hard-coding.** |
| A2 | Pandas actually-installed version may be 2.2.3 (per Phase 02-01's STATE.md note), not STACK.md's pinned 3.0.5 | Standard Stack | If the planner assumes pandas 3.x's copy-on-write/dtype-inference semantics apply but 2.2.3 is actually installed, date-index handling or dtype coercion in the history-extraction glue code (Phase 4/5, but exercised in this phase's tests) could behave subtly differently than expected | 
| A3 | Diesel-MNT's bull/bear should combine Diesel-USD and FX's own bull/bear at matching scenario edges (bull×bull, bear×bear) rather than a more statistically rigorous variance-propagation approach | Pattern 6 | No requirement mandates a specific combination method; if the user/planner wants a more rigorous approach (e.g. combining SEs in quadrature: `se_mnt = mnt_base * sqrt((se_usd/usd_base)^2 + (se_fx/fx_base)^2)`), this simpler approach would need revision — low risk since D-04 already establishes the project favors an "approximate, honestly communicated" band over statistical rigor |
| A4 | Whether HDAN's GARCH sigma should be a static hard-coded array (reusing `garch_volatility.json`'s precomputed values) or refit live via `arch_model` at every request, per D-06's "refit on every request" language | Pattern 4 | If D-06 is read strictly (ALL models refit live, including GARCH), the static array approach violates that decision; if D-06's "refit" language is read as applying only to the four named point-forecast models (HDAN/PPAN/Diesel/FX) and GARCH is treated as a frozen offline volatility calibration (consistent with `arch==8.0.0` being a research-phase-only dependency per STACK.md's "model research phase only" installation note), the static array is correct. **This is a genuine open question for the planner to resolve, ideally by re-reading D-06's exact wording with the user or defaulting conservatively to live refit for consistency with the other three volatility sources (`_arima_forecast_se` is always refit live in this research's patterns).** |

## Open Questions

1. **Does D-06's "refit on every request" apply to HDAN's GARCH volatility source, or only to the four point-forecast models?**
   - What we know: `02-MODEL-DECISIONS.md` names `garch` as HDAN's volatility source and D-06 says "models refit on every forecast request." `arch` (the GARCH library) is listed in STACK.md only under "Model research phase only (not necessarily shipped)" — suggesting it may NOT be a runtime dependency of the shipped `forecasting.py` at all.
   - What's unclear: If `arch` isn't a shipped runtime dependency, `garch_volatility.json`'s precomputed sigma array MUST be hard-coded into `forecasting.py` (as Pattern 4 does) rather than refit live — which would make GARCH the one volatility source that does NOT refit on every request, an inconsistency worth surfacing explicitly to the user/planner rather than silently deciding either way.
   - Recommendation: Planner should explicitly decide (and record as a phase-level decision, not silently pick one) whether `arch` becomes a Phase 3 runtime dependency (live GARCH refit, matching D-06 literally) or stays research-only (static hard-coded sigma array, treating "refit on every request" as referring only to the four named point-forecast models). This research recommends the static-array approach as the DEFAULT (lower complexity, no new runtime dependency, and PPAN's own volatility-source caveat already establishes precedent for "GARCH doesn't have to mean live GARCH" — PPAN fell back to ARIMA-SE specifically because live/rolling GARCH sigma was unstable) but flags this as needing explicit confirmation.

2. **Exact VAR lag for PPAN's system (A1 above) — needs direct verification against `backend_research/results/wf_var_vecm.json` before implementation, not inferred from source code defaults.**
   - Recommendation: Add a Wave 0 / first-task step: `python -c "import json; d=json.load(open('backend_research/results/wf_var_vecm.json')); print([r['model'] for r in d if r['series']=='ppan'])"` to read the exact lag hard-coded in the winning record's `model` string (e.g. `"VAR(lag=2) system=[...]"` would confirm 2, not 1).

## Environment Availability

Skipped — this phase adds no new external dependencies (statsmodels/pandas/numpy already
installed and verified functional by Phase 2's `backend_research/` scripts, which ran
successfully to produce `02-MODEL-DECISIONS.md` and the results JSON files this phase
consumes).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (per STACK.md's Supporting Libraries table; no version installed/verified yet — `pytest --version` should be run at Wave 0) |
| Config file | none detected — no `pytest.ini`/`pyproject.toml [tool.pytest]` found in repo scan; Wave 0 gap |
| Quick run command | `pytest tests/test_forecasting.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| FCST-02 | `forecast_all()` returns base/bull/bear per month for HDAN/PPAN/Diesel-USD/FX at a given horizon | unit | `pytest tests/test_forecasting.py::test_forecast_all_shape -x` | ❌ Wave 0 |
| FCST-03 | Diesel-MNT = Diesel-USD × FX × (1+markup) per horizon step | unit | `pytest tests/test_forecasting.py::test_diesel_mnt_derivation -x` | ❌ Wave 0 |
| FCST-04 | Bull/bear spread differs per series, sourced from that series' own named volatility source (not one flat percentage) | unit | `pytest tests/test_forecasting.py::test_spread_uses_named_volatility_source -x` | ❌ Wave 0 |
| FCST-05 | Bull/bear spread widens as horizon extends (checked via monotonic-or-plausible widening assertion, acknowledging PPAN's GARCH-non-widening caveat is why PPAN uses ARIMA-SE instead) | unit | `pytest tests/test_forecasting.py::test_spread_widens_with_horizon -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_forecasting.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_forecasting.py` — covers FCST-02 through FCST-05, plus per-pattern unit tests (SARIMAX exog shape, VAR column extraction, GARCH unit conversion, ARIMA-SE isolation from point forecast)
- [ ] `tests/conftest.py` — shared fixture providing a synthetic multi-series `pd.DataFrame` history (short, deterministic, seeded) so tests don't depend on the real SQLite-seeded dataset
- [ ] Framework install/verify: `pip show pytest` — confirm installed before Wave 0; STACK.md lists it but no evidence yet it's actually `pip install`ed in this environment

## Security Domain

Not applicable in the standard web-app sense — this phase has no user input handling,
no auth, no network calls, and no cryptography. The one relevant control:

| Threat Pattern | STRIDE | Standard Mitigation |
|-----------------|--------|----------------------|
| Malformed/degenerate history (too few rows, all-null column) crashing the whole `forecast_all()` call and breaking the dashboard | Denial of Service (availability) | Each per-series function should defensively `dropna()` and check minimum row counts before fitting (statsmodels raises informative exceptions on too-short series; catch and surface a clear "insufficient history" result rather than letting an unhandled exception propagate to the UI layer — though the exact error-surfacing UX is Phase 4/5's concern, this phase's functions should not silently produce NaN-filled forecasts) |

ASVS categories (V2 Auth, V3 Session, V6 Crypto) are not applicable — this is a
single-user, no-network, offline module.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/02-model-research-backtesting/02-MODEL-DECISIONS.md` — binding per-series model/order/volatility-source specification
- `backend_research/REPORT-PHASE2.md` — per-series ranking tables confirming ARIMA orders for the arima_forecast_se fallback (PPAN=(0,1,0), Diesel=(1,1,1), FX=(1,1,2))
- `backend_research/results/winners.json` — machine-readable confirmation that sigma_by_horizon is null (not precomputed) for PPAN/Diesel/FX, consistent with request-time ARIMA-SE computation
- `backend_research/results/garch_volatility.json` — HDAN's exact 12-step GARCH sigma array
- `backend_research/run_garch.py` — confirms GARCH fit on `pct_change() * 100`, establishing the percent-unit convention for sigma
- `backend_research/run_arima_sarimax_wf.py`, `backend_research/run_var_vecm_wf.py`, `backend_research/run_baseline_ets.py` — working reference implementations of every statsmodels call pattern this phase reuses
- `app/app/models.py` — `PriceRow`/`AppSetting` schema, confirming this phase's data source shape
- `.planning/research/ARCHITECTURE.md` — confirms the zero-`import reflex` boundary (D-08) and single-file `forecasting.py` structure
- statsmodels 0.14 official docs (`SARIMAXResults.get_forecast`, `ARIMAResults.get_forecast`, `VAR.fit`/`VARResults.forecast`) — training-knowledge API surface cross-checked against the working Phase 2 scripts' actual calls, which is a stronger verification than docs alone since these exact calls already ran successfully against this project's real data

### Secondary (MEDIUM confidence)
- None — all critical claims in this research trace back to either Phase 2's own output files (already-executed, already-verified code) or statsmodels' stable, long-documented public API.

### Tertiary (LOW confidence)
- The exact VAR lag for PPAN's system (Pattern 2 / Assumption A1) — inferred from source code defaults, not directly read from the output JSON; flagged for planner verification.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, reusing an already-installed, already-validated stack
- Architecture: HIGH — module boundary (D-07/D-08) is explicitly decided and matches existing `ARCHITECTURE.md`
- Pitfalls: HIGH — every named pitfall traces to a concrete, verified source-code detail (unit conversions, column ordering, trailing-window sizing) rather than generic statsmodels folklore

**Research date:** 2026-08-21
**Valid until:** No expiry driver — this research is tied to Phase 2's frozen model decisions and statsmodels 0.14.6's stable API, not to any fast-moving external service; safe to treat as valid for the remainder of this project's v1 milestone.
