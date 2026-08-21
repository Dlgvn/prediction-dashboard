# Phase 2: Model Research & Backtesting - Research

**Researched:** 2026-08-21
**Domain:** Time-series/econometric/ML model selection via walk-forward backtesting (statsmodels + arch + scikit-learn), against a 4-series, 16-predictor monthly SQLite dataset
**Confidence:** HIGH on stack/API surface (verified via pip registry + prior codebase); MEDIUM on walk-forward implementation patterns (statsmodels docs are sparse on this specific pattern, corroborated across sources); MEDIUM on small-sample GARCH viability (data-availability risk, not API risk)

## Summary

This phase does not ship a UI feature — it produces a research report and a suite of
backtest scripts that decide, per series (HDAN, PPAN, Diesel-USD, FX), which model family,
which predictors, and which multi-step strategy (iterative vs. direct) Phase 3 will
implement. The existing `backend_research/` scripts already establish the right shape
(one shared `model_harness.py`-style backtest function, per-family runner scripts, JSON
results, causality-driven predictor selection) but used a **single fixed 12-month holdout**.
D-07 requires converting this to **walk-forward/rolling-origin validation**, which is the
central new engineering problem this phase must solve — everything else (which models,
which predictors) is largely an extension of code that already exists and runs.

The stack is already pinned in STACK.md (statsmodels 0.14.6, pandas 3.0.5, scikit-learn
1.9.0) and does NOT need a new pin for time-series methods — ARIMA/SARIMAX/VAR are all in
statsmodels. The one confirmed gap is **GARCH**: statsmodels does not ship a maintained
GARCH implementation (its `tsa.arima.model` and `tsa.statespace` modules cover
ARIMA/SARIMAX/VAR/state-space, not conditional heteroskedasticity); the `arch` package
(bashtage/arch, PyPI `arch==8.0.0`, confirmed current) is the standard tool and must be
added as a new research-phase-only dependency. `pmdarima` (already flagged in STACK.md as
research-only, not production) is optional convenience for ARIMA order search but not
required — the existing `run_sarimax_tuned.py` already does manual grid search successfully
and that pattern should be kept rather than adding a new dependency.

**Primary recommendation:** Extend the existing `backend_research/` harness pattern
(don't rewrite it) — add a `walk_forward.py` harness function parallel to
`model_harness.py`'s single-holdout functions, reuse `data_loader.py`/`causality_matrix.py`
patterns adapted to the new 16-column `PriceRow` schema read from SQLite (not CSV), and add
one new runner script per method family (naive/ETS baseline, ARIMA/SARIMAX, VAR+Granger+
cointegration, GARCH via `arch`, ML baseline) plus a final report script that assembles
per-series winners across both iterative and direct horizon strategies.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reading training data (164-row PriceRow table) | Database / Storage (SQLite via `rx.Model`) | Research scripts (plain Python, read-only `sqlmodel`/`sqlite3` query) | Phase 1 established SQLite as sole source of truth; research scripts must query it directly (via `sqlmodel.Session` or raw `sqlite3`), not re-parse CSVs, so results reflect any data entered since seeding |
| Model fitting / backtesting | Standalone research scripts (`backend_research/`) | — (no UI/State involvement) | This phase is explicitly research-only — no Reflex, no `rx.State`, no production wiring. Keeps forecasting logic UI-independent per PITFALLS.md pattern (testable outside Reflex) |
| Predictor selection (Granger/cointegration) | Standalone research scripts | — | Statistical decision made once, offline; not a runtime computation |
| Research report / winner selection | Research script output (JSON) + markdown report | Phase 3 consumes as input | Report is the hand-off artifact — Phase 3's forecasting module hard-codes whatever this phase names as winners (mirrors STACK.md's guidance not to keep `auto_arima`-style runtime search in production) |

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Test three method families — Time-series (naive/MA baseline, SES/Holt-Winters,
  ARIMA, GARCH for volatility feeding Phase 3's bull/bear spread), Causal/econometric
  (regression, VAR, Granger causality, cointegration — decide which predictors earn a
  place), Machine learning (random forest, gradient boosting — comparison point only,
  explicitly flag overfitting risk on ~48-164 rows, don't present ML results at face value
  against simpler models).
- **D-02 (exclusion):** Technical/market-based methods (momentum, support/resistance) NOT
  tested — poor fit for monthly fundamentals-driven data.
- **D-03 (exclusion):** Scenario planning / Delphi qualitative judgment explicitly OUT of
  scope — not backtestable; note the throughline to v2's live news/sentiment mechanism but
  build/test nothing for it this phase.
- **D-04:** For HDAN/PPAN — test the FULL predictor set (Baltic AN, Ammonia, both Urea
  series, all 4 gas benchmarks, Brent, both Corn series, own lagged values, other AN
  product's lagged value for VAR). Run Granger causality across the whole set; don't
  pre-filter by intuition.
- **D-05:** For Diesel-USD/FX — test Brent AND Urals (both crude benchmarks now available),
  plus natural gas and the full AN-family as candidate predictors, even without an obvious
  economic mechanism for AN-family → diesel/FX. Let backtesting decide.
- **D-06:** Test BOTH iterative/recursive (1-step model fed back in for steps 2-12) AND
  direct multi-step (separate model per horizon) — compare backtest accuracy per horizon,
  report which wins per series/horizon range; can differ by series.
- **D-07:** Use walk-forward/rolling-origin validation (train up to month N, forecast
  N+1..N+12, roll forward, repeat) — NOT a single fixed holdout. Still report the
  single-holdout MAPE too for comparability with `backend_research/REPORT.md`'s existing
  numbers (HDAN 9.4%, PPAN 10.0%, Diesel-USD 3.4%, FX 0.25%).
- **D-08:** Do NOT investigate weekly-mode Baltic AN → HDAN/PPAN proxy this phase — explicitly
  deferred; STATE.md confirms it's already a backtest no-go anyway (10.35%/16.01% vs.
  9.49%/10.08% MAPE monthly).

### Claude's Discretion
None flagged — all four presented gray areas were explicitly decided.

### Deferred Ideas (OUT OF SCOPE)
- Weekly-mode Baltic AN → HDAN/PPAN proxy research (D-08).
- Scenario planning / Delphi qualitative override mechanism (D-03) — reserved for v2 news/
  sentiment scenario adjustment.
- Technical/market-based methods (D-02).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FCST-07 | Forecasting models are selected via a research/backtest process before being used — no un-backtested model is used in the shipped app | This entire RESEARCH.md exists to satisfy FCST-07: it specifies the walk-forward backtest methodology, the model families/APIs to test, and the report structure that produces FCST-07's required "winning model per series with backtested error" artifact for Phase 3 to consume |

## Project Constraints (from CLAUDE.md)

- **Tech stack lock:** Reflex + SQLite + statsmodels + pandas/openpyxl — this phase adds
  `scikit-learn` (already pinned, research-phase-only per STACK.md) and `arch` (new, see
  Package Legitimacy Audit) as research-only dependencies; neither becomes a runtime
  dependency of the shipped app unless it wins a backtest AND Phase 3 explicitly re-adopts it.
- **No un-backtested model ships** — explicit project-level rule (mirrors FCST-07), enforced
  by this phase's entire existence.
- **GSD workflow enforcement:** file changes must go through `/gsd-execute-phase`, not ad hoc
  edits — applies when this research is acted on by the planner/executor, not to this
  research step itself.
- **Model provenance constraint (PROJECT.md):** forecasting models must go through this
  research/backtest step (mirroring `backend_research/`) before use in the app.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| statsmodels | 0.14.6 [VERIFIED: pip index, installed] | ARIMA/SARIMAX/VAR/ExponentialSmoothing, Granger causality, cointegration tests | Already the project's pinned forecasting library (STACK.md); covers every time-series and causal/econometric method D-01 requires except GARCH |
| pandas | 3.0.5 (STACK.md pin); 2.2.3 currently installed in this environment [VERIFIED: pip show] | Data wrangling, walk-forward window slicing | Already pinned; note the installed dev environment shows 2.2.3 not 3.0.5 — confirm the actual project virtualenv pin before running scripts, don't assume the STACK.md number matches what's installed everywhere |
| scikit-learn | 1.9.0 (STACK.md); 1.7.2 currently installed [VERIFIED: pip show] | RandomForestRegressor, GradientBoostingRegressor (ML comparison family) | Already pinned as research-phase-only per STACK.md — correct scope, this phase is exactly that research phase |
| arch | 8.0.0 [VERIFIED: pip index, PyPI] [ASSUMED: package identity — see Package Legitimacy Audit] | GARCH/ARCH volatility modeling (D-01's GARCH requirement) | statsmodels has no maintained GARCH model; `arch` (bashtage/arch on GitHub) is the de facto standard Python GARCH library, actively maintained, used throughout the econometrics community |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | resolved by statsmodels (installed: 1.16.2) | `scipy.stats.f` for Granger F-test (already used in `causality_matrix.py`) | Already a transitive dependency; no new pin needed |
| sqlmodel | 0.0.39 (Reflex-pinned) | Reading `PriceRow`/`AppSetting` tables directly from `reflex.db` for research scripts | Use `sqlmodel.Session` + `select(PriceRow)` (or a read-only raw `sqlite3` connection) instead of re-parsing CSVs — Phase 1 established SQLite as sole source of truth |
| pytest | 8.x (STACK.md) | Optional: smoke-test the walk-forward harness function itself (not the models) | If the walk-forward slicing logic has any off-by-one risk (very likely — see Pitfalls), a small pytest test asserting window boundaries never leak future data is worth the low cost even in a research-only phase |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `arch` for GARCH | Hand-rolled GARCH via statsmodels `tsa.arima.model` residual variance modeling | Not viable — statsmodels doesn't expose a GARCH fit; hand-rolling GARCH's MLE is exactly the kind of "don't hand-roll" case flagged below |
| Manual grid search for ARIMA/SARIMAX order (existing `run_sarimax_tuned.py` pattern) | `pmdarima.auto_arima` | STACK.md already flags `pmdarima` as research-convenience-only; the existing manual grid search in `run_sarimax_tuned.py` already works and keeps one fewer dependency — no strong reason to add `pmdarima` unless grid search becomes a bottleneck (unlikely at (p,d,q) ranges of 3×2×3=18 combos × 2 series) |
| Walk-forward via manual index slicing (recommended) | `sklearn.model_selection.TimeSeriesSplit` | `TimeSeriesSplit` gives expanding-window CV folds but doesn't natively support statsmodels' `.append()`/refit-per-step pattern or multi-horizon forecast evaluation per step — manual slicing (as shown in Code Examples below) gives more control over refit frequency and multi-step evaluation, which D-06/D-07 both require |

**Installation:**
```bash
pip install arch==8.0.0
```
(statsmodels, pandas, scikit-learn already installed per STACK.md's core pin — no new install needed for those.)

**Version verification:** Confirmed via `pip index versions <pkg>` against live PyPI on
2026-08-21: `statsmodels==0.14.6` (installed and current), `arch==8.0.0` (current, prior
releases 7.2.0/7.1.0/etc. also on registry — no gap/typosquat pattern in version history).
`pandas`/`scikit-learn` STACK.md pins (3.0.5/1.9.0) are ahead of what's actually installed in
this research environment (2.2.3/1.7.2) — the planner should have the executor confirm the
project's actual virtualenv versions before writing exact API calls that depend on
version-specific behavior (e.g., pandas 3.0's copy-on-write defaults).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| statsmodels | PyPI | 15+ yrs | very high | github.com/statsmodels/statsmodels | [OK] | Approved |
| pandas | PyPI | 15+ yrs | very high | github.com/pandas-dev/pandas | [OK] | Approved |
| scikit-learn | PyPI | 15+ yrs | very high | github.com/scikit-learn/scikit-learn | [OK] | Approved |
| arch | PyPI | 10+ yrs (v1.0 circa 2016) | high (widely used in econometrics/quant research) | github.com/bashtage/arch | [SUS] — flagged "suspiciously close to 'torch', could be a typosquat" | Flagged — planner must add `checkpoint:human-verify` before install, but note: this is a known false-positive pattern (name-similarity heuristic, not an actual typosquat signal). `arch` is a long-established, independently well-known package (Kevin Sheppard/bashtage, University of Oxford) predating and unrelated to PyTorch's naming. Verified via `pip index versions arch` showing a clean, continuous version history back to 1.0 with no suspicious gaps. |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `arch` — slopcheck's name-similarity heuristic
triggers on "arch" vs. "torch" edit-distance, not on any actual registry-abuse signal. The
planner should still insert a `checkpoint:human-verify` before the install task per protocol,
but the research finding is that this is very likely a false positive — cross-check the
GitHub org (`bashtage/arch`) and PyPI project page against `bashtage`'s other packages
(`arch`, `linearmodels`) before installing, rather than assuming malicious intent.

## Architecture Patterns

### System Architecture Diagram

```
reflex.db (SQLite, PriceRow table, 164 rows)
        │
        ▼
research/data_loader.py  ──► reads via sqlmodel/sqlite3, returns wide DataFrame
        │
        ▼
research/causality_matrix.py ──► Granger F-test + cointegration test, ALL predictor×target×lag
        │  (outputs: which predictors earn a place per D-04/D-05)
        ▼
research/walk_forward.py  ──► shared rolling-origin harness (the new core piece)
        │
        ├──► research/run_baseline_naive_ets.py     (naive/MA, SES, Holt-Winters)
        ├──► research/run_arima_sarimax.py           (ARIMA, SARIMAX w/ selected exog)
        ├──► research/run_var_candidates.py          (VAR w/ Granger-selected series)
        ├──► research/run_garch.py                   (arch package — volatility/spread)
        ├──► research/run_ml_baseline.py              (RandomForest/GradientBoosting)
        │        each tests BOTH iterative and direct multi-step (D-06)
        ▼
research/results/*.json  ──► per-model, per-series, per-horizon walk-forward MAPE
        │
        ▼
research/assemble_report.py ──► picks per-series winner, writes 02-REPORT.md
```

### Recommended Project Structure
```
backend_research/
├── data_loader.py           # NEW/adapted: read PriceRow from reflex.db (not CSV)
├── walk_forward.py          # NEW: shared rolling-origin harness (see Code Examples)
├── causality_matrix.py      # ADAPT: full 16-predictor set, add cointegration test
├── run_baseline_naive_ets.py    # NEW
├── run_arima_sarimax.py         # ADAPT from run_sarimax_tuned.py
├── run_var_candidates.py        # ADAPT: walk-forward instead of single holdout
├── run_garch.py                 # NEW
├── run_ml_baseline.py           # NEW: RandomForest/GradientBoosting w/ lag features
├── assemble_report.py           # NEW: collects all results/*.json → final report
└── results/
    ├── causality_matrix.json
    ├── walk_forward_*.json      # one per model family
    └── REPORT.md                # or write directly to 02-RESEARCH-REPORT.md in .planning/
```

### Pattern 1: Walk-Forward / Rolling-Origin Validation (the core new pattern)

**What:** Repeatedly train on data up to month N, forecast N+1..N+H (H up to 12), roll
forward by one step, repeat — collect per-horizon errors across all origins, not a single
train/test split.

**When to use:** Required by D-07 for every model family tested this phase.

**Example (statsmodels-compatible, refit-every-step — most correct but most expensive):**
```python
# Source: pattern synthesized from statsmodels forecasting docs +
# common walk-forward practice (MachineLearningMastery, cross-verified against
# statsmodels ARIMAResults.append() docs) — MEDIUM confidence, no single official
# "walk-forward" tutorial exists in statsmodels docs themselves.
import numpy as np
import pandas as pd

def walk_forward_backtest(series, exog, fit_fn, min_train=36, horizon=12, step=1, refit_every=1):
    """
    series: full price Series indexed by date, ascending.
    exog: optional DataFrame of exogenous predictors, aligned to series.index (or None).
    fit_fn: callable(train_series, train_exog) -> fitted statsmodels-like results object
            with .forecast(steps, exog=future_exog) or .get_forecast(...).
    min_train: minimum training window length before first origin.
    horizon: max steps ahead to forecast at each origin (1..horizon).
    refit_every: refit model every N origins (1 = refit every origin; >1 saves compute
                 but staler model — document which was used per PITFALLS.md Pitfall 5).

    Returns: DataFrame with columns [origin_date, horizon_step, forecast, actual].
    """
    n = len(series)
    records = []
    fitted = None
    for origin in range(min_train, n - 1, step):
        train_y = series.iloc[:origin]
        train_x = exog.iloc[:origin] if exog is not None else None
        if fitted is None or (origin - min_train) % refit_every == 0:
            fitted = fit_fn(train_y, train_x)
        max_h = min(horizon, n - origin)
        future_x = exog.iloc[origin:origin + max_h] if exog is not None else None
        preds = fitted.forecast(steps=max_h, exog=future_x) if future_x is not None \
            else fitted.forecast(steps=max_h)
        for h in range(1, max_h + 1):
            records.append({
                "origin_date": series.index[origin - 1],
                "horizon_step": h,
                "forecast": preds.iloc[h - 1] if hasattr(preds, "iloc") else preds[h - 1],
                "actual": series.iloc[origin + h - 1],
            })
    return pd.DataFrame(records)

def mape_by_horizon(results_df):
    results_df["ape"] = (results_df["forecast"] - results_df["actual"]).abs() / results_df["actual"].abs()
    return results_df.groupby("horizon_step")["ape"].mean() * 100
```

**Critical correctness notes (data leakage prevention):**
- `train_y = series.iloc[:origin]` must NEVER include index `origin` or later — off-by-one
  here silently leaks the target month's own value into training, producing implausibly
  good MAPE (ties directly to PITFALLS.md Pitfall 1's "confident-looking garbage" warning
  sign).
- Exogenous predictors for the FORECAST window (`future_x`) must be predictors' actual
  future values if testing "what if we knew future predictor values" (unrealistic for
  production) OR must be lagged so the predictor value used at forecast time was already
  known at the origin date (realistic — this is what D-04/D-05's lagged-predictor framing
  implies, and matches the existing `backend_research/` OLS pattern of `predictors_with_lags`
  shifting a predictor by 1-3 months so it's known before the target month).
- `min_train`: given PITFALLS.md's small-sample warning, don't start walk-forward origins
  before the model has enough data for its complexity (e.g., a VAR(3) on 4 series needs at
  least ~20-30 points before the first origin to avoid degenerate fits at early origins).

### Pattern 2: Iterative (Recursive) vs. Direct Multi-Step Forecasting (D-06)

**Iterative/recursive:** Fit ONE 1-step-ahead model. At forecast time, predict step 1,
feed that prediction back in as if it were an observed value, predict step 2, etc.
```python
# Iterative — works naturally with statsmodels' native multi-step .forecast(steps=H),
# which IS iterative internally for ARIMA/SARIMAX/VAR (this is what run_var_candidates.py
# already does implicitly via fitted.forecast(steps=1) in a loop, or steps=H directly).
fitted = sm.tsa.SARIMAX(train_y, exog=train_x, order=(1,1,1)).fit(disp=False)
iterative_forecast = fitted.forecast(steps=12, exog=future_x)  # errors compound step to step
```

**Direct multi-step:** Fit H SEPARATE models, one per horizon, each trained to predict
"value H months from now" directly from data known at the origin (not from its own
1-step forecasts).
```python
# Direct — requires reshaping the training data per horizon: target = y shifted -H,
# features = predictors known at time t (including y's own lags).
import statsmodels.api as sm

def fit_direct_horizon_model(train_df, target_col, feature_cols, h):
    d = train_df.copy()
    d["target_h"] = d[target_col].shift(-h)  # value h steps in the future
    d = d.dropna(subset=["target_h"] + feature_cols)
    X = sm.add_constant(d[feature_cols])
    return sm.OLS(d["target_h"], X).fit()

# One model per horizon 1..12 — each model directly targets its own horizon,
# avoiding iterative error compounding but requiring H separate fits and losing
# H rows of training data per horizon (worse for HDAN/PPAN's already-short history).
direct_models = {h: fit_direct_horizon_model(train_df, "HDAN", feature_cols, h) for h in range(1, 13)}
```
For ML models (RandomForest/GradientBoosting), direct is the natural fit (train H separate
regressors, or use `sklearn.multioutput.MultiOutputRegressor` with H target columns);
iterative for ML means feeding predicted `y` back into the lag-feature set at each step.

**Report requirement (D-06):** compare walk-forward MAPE by horizon-step for iterative vs.
direct per series — expect iterative to win at short horizons (1-3mo, less data loss) and
possibly direct to win at long horizons (10-12mo, avoids compounding) but let the data decide
per series as instructed.

### Pattern 3: Granger Causality + Cointegration for Predictor Selection (D-04/D-05)

**Granger causality** (already implemented in `causality_matrix.py` via manual F-test —
this is correct and can be extended, OR switched to the built-in statsmodels function for
convenience/cross-validation):
```python
# Source: statsmodels.tsa.stattools docs (0.14.x API, verified against installed version)
from statsmodels.tsa.stattools import grangercausalitytests

# data: 2-column DataFrame [target, candidate_predictor], stationary (differenced/pct-change)
result = grangercausalitytests(data[["target", "predictor"]], maxlag=3, verbose=False)
# result[lag][0] is a dict of test statistics; ssr_ftest p-value is directly comparable
# to the manual F-test already used in causality_matrix.py — use as a cross-check, not
# a replacement, since the existing manual implementation is already validated this session.
p_value_lag2 = result[2][0]["ssr_ftest"][1]
```
**Threshold interpretation:** the existing `causality_matrix.py` uses `p < 0.10` as
"significant" (looser than the conventional 0.05) — CONTEXT.md/D-04 doesn't override this,
and given the small-N warning in PITFALLS.md, a stricter p<0.05 threshold would likely
reject even real relationships due to low power. Recommend **keeping p<0.10** as the
"predictor earns a place" threshold, consistent with prior art, but explicitly reporting
both p<0.05 and p<0.10 tiers in the report so Phase 3 can see the confidence gradient
rather than a binary in/out cutoff.

**Cointegration** (new for this phase — D-01 explicitly adds it, not present in prior
`backend_research/` scripts):
```python
# Source: statsmodels.tsa.stattools docs — Engle-Granger two-step method
from statsmodels.tsa.stattools import coint

# Use on LEVELS (not pct-change/differenced series) — cointegration tests for a
# long-run equilibrium relationship between non-stationary series, which is the
# opposite framing from Granger causality on stationary differenced data.
t_stat, p_value, crit_values = coint(target_level_series, predictor_level_series)
# p_value < 0.05 suggests a cointegrating (long-run equilibrium) relationship exists —
# relevant for VAR-vs-VECM choice: if series are cointegrated, a Vector Error Correction
# Model (statsmodels.tsa.vector_ar.vecm.VECM) may outperform a plain VAR fit on differences.
```
**Note on VECM:** D-01 lists "VAR" not "VECM" explicitly, but cointegration testing's whole
purpose is to inform whether VECM should be tried instead of/alongside VAR. Recommend the
research report flag this explicitly if cointegration is found (e.g., HDAN/PPAN, which move
together) — testing `statsmodels.tsa.vector_ar.vecm.VECM` as a natural D-01 extension if
cointegration p<0.05 is found, since it directly serves D-01's "let the data decide" spirit
without expanding scope into a new untested family.

### Pattern 4: ExponentialSmoothing / Holt-Winters (D-01 time-series family)

```python
# Source: statsmodels.tsa.holtwinters docs, 0.14.x API
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# No seasonal component recommended for HDAN/PPAN (< 2 full annual cycles of monthly
# data — 48 months = 4 years is borderline; if seasonal=True is tried, cap seasonal_periods=12
# and flag results as exploratory per PITFALLS.md's "avoid seasonal terms with <2 full cycles"
# guidance for Diesel/FX which have even less history in some windows).
model = ExponentialSmoothing(train_y, trend="add", seasonal=None, damped_trend=True).fit()
forecast = model.forecast(steps=12)
```

### Pattern 5: GARCH via `arch` (D-01's volatility/spread requirement)

```python
# Source: arch package docs (bashtage/arch README + docstrings) — package not in
# Context7; verified via installed docstring inspection recommended before final use.
from arch import arch_model

# Fit on PERCENT RETURNS (pct_change * 100), consistent with existing pct-change framing
# in causality_matrix.py/model_harness.py — GARCH models conditional variance of returns,
# not price levels directly.
returns = train_y.pct_change().dropna() * 100
am = arch_model(returns, vol="Garch", p=1, q=1, mean="Constant", dist="normal")
res = am.fit(disp="off")
forecast = res.forecast(horizon=12)
conditional_variance = forecast.variance.values[-1]  # per-horizon variance, USE THIS
# to build horizon-widening bull/bear spreads (feeds PITFALLS.md Pitfall 3's fix:
# spread should widen with horizon and vary per series — GARCH's own multi-step variance
# forecast does this natively, better than a flat backtest MAPE).
```
**Small-sample caution specific to GARCH:** GARCH(1,1) needs enough data to estimate
volatility clustering reliably — with HDAN/PPAN's ~48-164 monthly points, GARCH fit may be
unstable or fail to converge. Recommend: try GARCH but explicitly report convergence
warnings/failures per series rather than silently falling back; if GARCH fails to converge
on HDAN/PPAN's shorter history, that's a valid, reportable research finding (use ARIMA's own
native forecast standard errors — which grow with horizon — as the fallback volatility
source for those series' bull/bear bands, per PITFALLS.md Pitfall 3's existing fallback
guidance).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GARCH / conditional volatility estimation | Custom EWMA or rolling-std volatility model | `arch.arch_model` | GARCH's MLE fitting (variance targeting, convergence handling) is well-tested in `arch`; a hand-rolled version would need to replicate significant numerical-optimization work for no benefit and higher bug risk |
| Granger F-test / cointegration test | Custom F-statistic or ADF-based cointegration logic | `statsmodels.tsa.stattools.grangercausalitytests` / `.coint` | Already available, already used correctly in `causality_matrix.py`'s manual version (which is itself a reasonable custom implementation, kept for continuity) — no need to invent a third approach |
| Walk-forward window slicing | Ad hoc for-loops per model family | ONE shared `walk_forward.py` harness function (Pattern 1) reused across all model families | Prevents subtly different off-by-one bugs per script (data leakage risk is the single most dangerous bug class this phase can introduce — see PITFALLS.md Pitfall 1) — the existing `model_harness.py` already establishes this "one shared function reused by every runner" pattern for the old single-holdout approach; extend it, don't duplicate |
| ARIMA/SARIMAX order search | Custom grid search loop (though `run_sarimax_tuned.py` already does this reasonably) | Keep the existing manual `itertools.product` grid search pattern; optionally cross-check with `pmdarima.auto_arima` if grid search is too slow | Existing pattern works and keeps dependency count down (STACK.md's explicit "not a production dependency" note for pmdarima); no reason to add it as a hard requirement |

**Key insight:** The biggest hand-roll risk in this specific phase is walk-forward slicing
logic — get the origin/train/forecast boundary wrong even once and every downstream MAPE
number becomes fiction (looks great, is actually leaking future data). Write it once as a
tested, shared function; don't let five runner scripts each reimplement their own loop.

## Common Pitfalls

### Pitfall 1: Data leakage in walk-forward slicing (train window bleeding into the forecast window)
**What goes wrong:** An off-by-one in `iloc[:origin]` vs `iloc[:origin+1]`, or including the
target month's own predictor value without confirming it was actually laggged/known at
forecast time, silently produces suspiciously good backtest MAPE.
**Why it happens:** pandas positional slicing (`iloc[:n]` excludes index `n`) is easy to get
subtly wrong when mixing with `.shift()`-based lag features, especially across the 4 different
runner scripts this phase needs (naive/ETS, ARIMA/SARIMAX, VAR, GARCH, ML).
**How to avoid:** Use the single shared `walk_forward.py` harness (Pattern 1) for every model
family rather than each script implementing its own loop; add an assertion in the harness
that `train_y.index.max() < forecast target date` at every origin.
**Warning signs:** Walk-forward MAPE is dramatically better than the existing single-holdout
MAPE for the same model/series (compare against `backend_research/REPORT.md`'s numbers as
the sanity baseline, exactly as PITFALLS.md Pitfall 1 already recommends).

### Pitfall 2: Refit-every-origin cost explosion for VAR/SARIMAX grid search under walk-forward
**What goes wrong:** D-07's walk-forward requires potentially dozens of origins per series;
combined with D-06's iterative+direct comparison and D-04/D-05's "test the full predictor
set," a naive full-refit-every-origin-every-model-every-predictor-combo approach can take
hours to run and become impractical to iterate on.
**Why it happens:** Walk-forward's correctness (D-07) and the broad predictor/model search
(D-01/D-04/D-05/D-06) pull in opposite directions computationally.
**How to avoid:** Use Granger causality/cointegration results (Pattern 3) to PRE-FILTER the
predictor search space before walk-forward backtesting — don't walk-forward every predictor
combination, only ones that passed the causality screen. Use `refit_every` > 1 (e.g., refit
every 3 origins) for the expensive model families (VAR order selection, GARCH) once initial
full-refit runs establish that staler refits don't meaningfully change results; document
which refit cadence was used.
**Warning signs:** A single runner script takes so long that iterating on it becomes
impractical — treat this as a design smell, not something to just wait out.

### Pitfall 3: GARCH convergence failures on short series (HDAN/PPAN, ~48 points)
**What goes wrong:** `arch_model(...).fit()` may raise convergence warnings or produce
unstable variance estimates on HDAN/PPAN's shorter history; silently accepting whatever
`.fit()` returns (even with a convergence warning) risks feeding garbage volatility into
Phase 3's bull/bear band logic.
**Why it happens:** GARCH(1,1) MLE typically wants 50+ observations for stable estimates;
HDAN/PPAN sit right at that boundary.
**How to avoid:** Check `res.convergence_flag` (or catch/log optimizer warnings) explicitly
per series; report GARCH's applicability per series honestly (may be a "GARCH not viable for
HDAN/PPAN, use ARIMA forecast SE instead" finding — itself a valid, useful, D-01-satisfying
research outcome, not a failure).
**Warning signs:** GARCH's reported volatility for HDAN/PPAN doesn't visibly track known
historical volatile periods, or is implausibly flat/constant across the whole series.

### Pitfall 4: ML (RandomForest/GradientBoosting) overfitting presented uncritically
**What goes wrong:** Tree-based models can post excellent in-sample and even excellent
walk-forward MAPE on small, autocorrelated series by essentially memorizing recent-value
patterns via lag features, without generalizing — CONTEXT.md's D-01 explicitly anticipates
and warns against this.
**Why it happens:** With ~48-164 rows and heavily autocorrelated commodity prices, a
lag-1 feature alone gives tree models a very strong (misleadingly strong) signal.
**How to avoid:** Per D-01's explicit instruction, report ML results with an explicit
overfitting-risk caveat section, not just a MAPE ranking table; compare ML's walk-forward
MAPE against a naive lag-1-only baseline specifically (if ML barely beats "just use last
month's value," that's the tell) rather than only against the fancier statsmodels candidates.
**Warning signs:** ML model's MAPE beats every statistical model by a wide margin — treat
this as a red flag requiring closer feature-importance inspection, not a straightforward win.

### Pitfall 5: FX rate having no significant predictors (already discovered this session)
**What goes wrong:** `run_single_series_candidates.py`'s existing comment already documents
that FX_rate had NO predictor reaching p<0.10 in the prior causality run — a naive
implementation of this phase might force a predictor set onto FX anyway "to be consistent"
with HDAN/PPAN/Diesel getting one.
**Why it happens:** Pressure to make every series "look the same" in the report structure.
**How to avoid:** Explicitly re-run Granger causality for FX against the EXPANDED predictor
set (Brent AND Urals now, plus gas/AN-family per D-05) before assuming the prior finding
still holds — D-05 explicitly asks to test a broader set than before, so the "FX has no
predictors" finding needs to be re-verified, not just carried forward as given. If it's
re-confirmed, keep the honest AR-only baseline framing from the existing script rather than
forcing a spurious predictor onto FX.
**Warning signs:** A predictor gets included for FX with a p-value that wouldn't have passed
the same threshold used for HDAN/PPAN/Diesel.

## Code Examples

See Architecture Patterns section above for the five load-bearing patterns (walk-forward
harness, iterative vs. direct multi-step, Granger/cointegration, Holt-Winters, GARCH). All
code there is directly reusable in the planner's task breakdown.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Single 12-month fixed holdout (`backend_research/model_harness.py`, `run_var_candidates.py`, etc., this project's own prior session) | Walk-forward/rolling-origin validation across many origins | D-07, this phase | More robust error estimates, especially important given D-06's horizon-dependent comparison — a single holdout can't show how error grows from month 1 to month 12 the way rolling origins with multi-step forecasts can |
| Brent-only diesel/FX predictor set (original Excel workbook) | Brent + Urals + gas + AN-family broad search | D-05, this phase | Wider predictor search than the shipped workbook ever did; may or may not find new signal, but must be tested per explicit user instruction |

**Deprecated/outdated:** None — statsmodels 0.14.6 and the existing `backend_research/`
harness pattern are both current and directly extensible; nothing here needs replacing, only
extending for D-06/D-07's new requirements.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `arch==8.0.0` is the correct, non-typosquatted GARCH package despite slopcheck's [SUS] name-similarity flag | Package Legitimacy Audit, Standard Stack | If wrong, an unrelated/malicious package could be installed under the `arch` name during Phase 2 execution — mitigated by requiring `checkpoint:human-verify` before install per protocol, and by the cross-check against `bashtage/arch`'s known GitHub org |
| A2 | Project's actual pandas/scikit-learn virtualenv versions match STACK.md's 3.0.5/1.9.0 pins, not the 2.2.3/1.7.2 found installed in this research environment | Standard Stack, version verification note | If the real project env is on older pandas (2.x), copy-on-write and dtype-inference behavior differs from what pandas 3.0.5-specific guidance assumes — low risk since walk-forward/statsmodels code in this research doesn't depend on pandas 3.0-specific features, but should be confirmed at execution time |
| A3 | p<0.10 Granger threshold (carried over from existing `causality_matrix.py`) is still the right threshold for the expanded D-04/D-05 predictor set | Architecture Patterns, Pattern 3 | If too loose, spurious predictors could be included in causal models given the small-N environment (PITFALLS.md's core warning); mitigated by recommending the report show both p<0.05 and p<0.10 tiers rather than a hard binary cutoff |
| A4 | GARCH(1,1) is the appropriate order/spec to start with for D-01's volatility requirement, without testing higher-order GARCH(p,q) or EGARCH/GJR-GARCH variants | Pattern 5 | If HDAN/PPAN/Diesel/FX have asymmetric volatility (price shocks affecting volatility differently up vs. down), a plain GARCH(1,1) may understate this; low risk given D-01 only specifies "GARCH" generically and the small-sample environment likely can't support richer variants anyway |

## Open Questions

1. **Where should the final research report/JSON live — `backend_research/results/` or `.planning/phases/02-model-research-backtesting/`?**
   - What we know: `backend_research/` is the existing convention for this kind of research
     code (has `data_loader.py`, `REPORT.md` already).
   - What's unclear: Whether the phase's deliverable report should ALSO be duplicated/
     summarized into a `.planning/phases/02-.../` artifact for Phase 3's planner to consume
     directly, or whether Phase 3's research step should just read `backend_research/results/`.
   - Recommendation: Planner should have the executor write the primary detailed report to
     `backend_research/REPORT.md` (continuing existing convention) AND write/update a concise
     summary (winning model + predictors + horizon strategy per series) into this phase's
     own output location so Phase 3's research/planning doesn't need to reverse-engineer
     JSON files to find the answer.

2. **Does the project's actual installed pandas/scikit-learn version match STACK.md's pin?**
   - What we know: This research environment shows pandas 2.2.3 and scikit-learn 1.7.2
     installed, vs. STACK.md's 3.0.5/1.9.0 pins.
   - What's unclear: Whether the project's own virtualenv (not this research shell) is
     correctly pinned per STACK.md, or whether STACK.md's pins are aspirational/未installed.
   - Recommendation: First task in Phase 2 execution should verify `pip freeze` inside the
     project's actual environment against STACK.md before writing version-sensitive code.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11/3.12 | Runtime | ✓ | 3.12 (this env) | — |
| statsmodels | ARIMA/SARIMAX/VAR/ETS/Granger/cointegration | ✓ | 0.14.6 | — |
| pandas | Data wrangling | ✓ | 2.2.3 (env) / 3.0.5 (STACK.md pin — verify) | — |
| scikit-learn | ML baseline family | ✓ | 1.7.2 (env) / 1.9.0 (STACK.md pin — verify) | — |
| arch | GARCH | ✗ (not installed; verified installable via `pip index`) | 8.0.0 available | Fallback if install blocked by human-verify gate: use ARIMA/SARIMAX forecast standard errors (which grow with horizon) as the volatility/spread source instead — noted in Pattern 5 |
| sqlite3 / reflex.db | Reading PriceRow training data | ✓ (assumed present from Phase 1) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `arch` (GARCH) — fallback is ARIMA/SARIMAX native
forecast standard errors if the `arch` install is blocked pending human verification of the
slopcheck [SUS] flag.

## Validation Architecture

This phase's "tests" are the backtest scripts themselves (MAPE against real held-out data),
not a conventional pytest suite testing application behavior — there's no existing pytest
framework wired up in `backend_research/`. Given the phase's research/script nature (no
Reflex UI, no `rx.State`), the nyquist validation model doesn't map cleanly onto "unit test
per requirement" — the actual validation IS the walk-forward backtest process, and FCST-07's
verification criterion is "a research report exists naming backtested winners," not a
pass/fail test suite.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (STACK.md pin) — recommended for ONE narrow purpose: unit-testing the `walk_forward.py` harness's slicing correctness (Pitfall 1), not the models themselves |
| Config file | none currently — Wave 0 |
| Quick run command | `pytest backend_research/test_walk_forward.py -x` |
| Full suite command | same (single small test file expected) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FCST-07 | Walk-forward harness never leaks future data into a training window | unit | `pytest backend_research/test_walk_forward.py::test_no_leakage -x` | ❌ Wave 0 |
| FCST-07 | Research report names a winning model + backtested error per series | manual-only (report review) | n/a — verified by reading the assembled report, not automatable | ❌ Wave 0 (report itself) |

### Sampling Rate
- **Per task commit:** run the relevant runner script and eyeball its JSON output against
  `backend_research/REPORT.md`'s prior single-holdout numbers as a sanity check (per
  PITFALLS.md Pitfall 1's explicit recommendation).
- **Per wave merge:** run `test_walk_forward.py` (leakage guard) plus a full pass of all
  runner scripts.
- **Phase gate:** `assemble_report.py` runs cleanly and produces a report naming a winner per
  series before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `backend_research/test_walk_forward.py` — covers the leakage-prevention assertion for
  the shared walk-forward harness (Pattern 1) — this is the one piece of this phase worth
  actual unit-testing, since a silent bug here invalidates every other result.
- [ ] Framework install: pytest already pinned in STACK.md, likely already installed —
  confirm via `pip show pytest` before assuming Wave 0 needs an install step.

*(No broader test infrastructure gap — this phase's primary "test" is the backtest process
itself, which is inherently manual-review/report-based per FCST-07's own definition.)*

## Security Domain

Not applicable in the conventional ASVS sense — this phase has no auth, session, network
input, or user-facing surface (pure offline research scripts reading local SQLite data and
writing local JSON/markdown). Skipping ASVS category table; the only security-adjacent
consideration is the Package Legitimacy Audit above (`arch` install verification), already
covered.

## Sources

### Primary (HIGH confidence)
- `pip index versions statsmodels` / `arch` — live PyPI registry lookups, 2026-08-21
- `pip show pandas scikit-learn statsmodels` (this environment) — installed version ground-truth
- `slopcheck install arch statsmodels scikit-learn pandas` — package legitimacy scan, 2026-08-21
- Existing project files: `backend_research/model_harness.py`, `causality_matrix.py`,
  `run_var_candidates.py`, `run_single_series_candidates.py`, `run_sarimax_tuned.py` —
  ground truth for prior-art API usage patterns (Granger F-test, VAR backtest, SARIMAX grid
  search) already validated working in this codebase
- `app/app/models.py` — authoritative 17-column `PriceRow` schema

### Secondary (MEDIUM confidence)
- Training-knowledge recall of `statsmodels.tsa.stattools.grangercausalitytests`/`.coint`,
  `statsmodels.tsa.holtwinters.ExponentialSmoothing`, `arch.arch_model` API signatures —
  consistent with the 0.14.x-era API surface and with the already-validated manual Granger
  F-test in `causality_matrix.py`, but not independently re-verified against live docs this
  session (Context7 not available for `arch`; statsmodels API cross-checked only via the
  existing working code in `backend_research/`, not a fresh docs fetch)
- WebSearch on `arch` package identity/currency — confirmed GitHub org and version-history
  shape via `pip index`, not a fresh docs read

### Tertiary (LOW confidence)
- Walk-forward harness `refit_every`/`min_train` specific numeric recommendations (Pitfall 2)
  — reasoned from PITFALLS.md's existing sample-size guidance, not independently benchmarked

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — statsmodels/pandas/scikit-learn already pinned and verified
  installed; `arch` verified on PyPI registry with clean version history, though flagged SUS
  by slopcheck's name-similarity heuristic (addressed via checkpoint gate)
- Architecture (walk-forward pattern): MEDIUM — no single canonical statsmodels-official
  walk-forward tutorial exists; pattern synthesized from general practice and cross-checked
  against the existing codebase's own (single-holdout) backtest pattern for consistency
- Pitfalls: HIGH for data-leakage/overfitting risks (directly corroborated by both
  PITFALLS.md's existing research and this session's own review of the FX-no-predictors
  finding already in the codebase); MEDIUM for GARCH-specific small-sample convergence risk
  (reasoned from general GARCH literature, not tested against this project's actual series)

**Research date:** 2026-08-21
**Valid until:** 30 days (stable stack; re-verify `arch` package legitimacy if not installed
within that window, since slopcheck scan results reflect this session's registry snapshot)
