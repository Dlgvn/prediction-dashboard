# Phase 17: Weekly Forecast Re-Research Spike - Research

**Researched:** 2026-09-01
**Domain:** Time-series forecasting (statsmodels SARIMAX / Exponential Smoothing) at weekly
cadence, walk-forward backtesting, data-hygiene comparison of two overlapping driver columns
**Confidence:** HIGH (all claims verified directly against this repo's code and this machine's
Python environment — no external library-API uncertainty; this phase reuses code already proven
to work, it does not adopt anything new)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Prior spike (must not repeat):**
- `.planning/quick/20260821-weekly-an-backtest/` ran weekly VAR(HDAN,PPAN) + OLS+Granger against
  `AN Data.csv`'s native weekly rows and `AN price weekly.csv`'s driver set. Result: **no-go**.
  One-step MAPE looked good (3.15%/3.98%) but R² was only 0.03-0.04 (persistence, not signal);
  the horizon-matched 4-week-ahead VAR rollup (10.35%/16.01%) underperformed the monthly-native
  VAR benchmark (**9.49%/10.08%**), especially on PPAN.
- That prior spike's own report (`backend_research/REPORT.md`, "Weekly cadence" section) named
  two specific follow-ups before revisiting — this phase does exactly those two, not a vague
  "try more models":
  1. Test **SARIMAX and Exponential Smoothing at weekly cadence** — the monthly SARIMAX
     exploration (`run_arima_sarimax_wf.py`) and ETS baseline (`run_baseline_ets.py`) were never
     repeated at weekly cadence; only VAR/OLS were tried weekly.
  2. **Resolve the Baltic-AN dedup question** — `AN Data.csv` has its own `Baltic AN` column and
     `AN price weekly.csv` has a separate `BalticAN_wk` column; sanity-check whether these are
     duplicate/overlapping sources (in which case only one should feed any model) or genuinely
     independent signal.
- Do NOT re-test plain weekly VAR(HDAN,PPAN) on the identical monthly-mirrored predictor set,
  and do NOT re-test the same OLS+Granger weekly-driver combination already tried — that is the
  "not a rerun" constraint from ROADMAP.md/WKLY-01 verbatim.

**Methodology (locked, reuse existing harness):**
- Reuse `backend_research/walk_forward.py`'s `walk_forward_backtest()` rolling-origin harness —
  the same shared harness Phase 2's monthly research used — rather than hand-rolling a new
  backtest loop. The prior weekly spike's 4-week rollup used an ad-hoc loop with only 9
  rolling-origin windows (explicitly flagged in its own report as "thin... indicative, not
  conclusive"); this phase should get a properly-sized walk-forward window count by using the
  shared harness, matching Phase 2's rigor bar.
- "Horizon-matched" means: forecast weekly-cadence models out to whatever horizon corresponds to
  ~1 calendar month (4-5 weekly steps, matching actual weeks-per-month rather than a fixed 4),
  then compare that rolled-forward error against the monthly-native VAR's 1-month-ahead MAPE —
  never compare a raw weekly one-step MAPE directly against the monthly figures (the prior report
  explicitly flags this as an invalid comparison).
- The benchmark to beat is exact and fixed: **HDAN 9.49%, PPAN 10.08%** (monthly-native
  VAR(HDAN,PPAN), Phase 2's winner). The go/no-go report must state a side-by-side comparison
  against these exact figures for each series.
- Candidate model families for this phase: SARIMAX (weekly cadence) and Exponential Smoothing
  (weekly cadence), at minimum. The Baltic-AN dedup resolution is a data-hygiene fix that should
  be tried as a variant driver set on top of whichever model(s) it's relevant to (e.g. VAR or a
  regression variant), not a new model family.
- Reuse `backend_research/data_loader.py`'s existing `load_an_weekly()`, `load_weekly_drivers()`,
  `merged_weekly()` — these already exist from the prior spike and need no changes for the new
  model families. Any dedup fix (candidate 2) should be additive (e.g. a documented choice of
  which Baltic AN column to prefer, or an explicit comparison of both) rather than a rewrite of
  these loaders.

**Scope / non-goals:**
- No `app/` code changes. No weekly-cadence UI ships this milestone even if this spike returns a
  "go" (ROADMAP.md is explicit: "research-only" and "no weekly UI ships this milestone regardless
  of the outcome").
- A "no-go" is a complete, valid, non-blocking outcome for closing WKLY-01/WKLY-02 — same
  discipline as Phase 16's no-go closeout.
- This phase is independent of Phase 16 (already closed, no-go) — no shared code or blocking
  dependency between them.

### Claude's Discretion
- Exact SARIMAX/ETS order search strategy (grid search bounds, seasonal period choice — note AN
  data is native weekly, not necessarily seasonal-daily/weekly in a textbook sense; use judgment
  matching how `run_arima_sarimax_wf.py`/`run_baseline_ets.py` did it at monthly cadence, adapted
  for weekly frequency).
- Whether to test the new model families against `merged_weekly()`'s full driver set as exogenous
  regressors or univariate-only first, then add drivers — pick whichever ordering most directly
  produces a clean go/no-go signal without redundant runs.
- Report structure/format — mirror `backend_research/REPORT.md`'s existing "Weekly cadence"
  section and `backend_research/REPORT-SENTIMENT.md`'s per-series go/no-go table style (Phase 16
  precedent) for consistency, but the plan can adapt as needed.
- Python environment: system `python3` (verified: pandas 2.2.3, statsmodels 0.14.6, scipy,
  pytest, scikit-learn 1.7.2, arch 8.0.0 all installed and working on this machine as of
  2026-09-01) — same research environment Phase 16 used. Do not use `app/.venv` (pandas 3.0.5,
  wrong environment for `backend_research/` scripts per `ENV.md`).

### Deferred Ideas (OUT OF SCOPE)

None raised — this is a tightly-scoped, pre-specified research phase with no scope-creep surface
(no UI, no new capabilities suggested).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WKLY-01 | Re-research backtest tests genuinely new candidate variables/model families (SARIMAX, ETS at weekly cadence; Baltic-AN dedup), same walk-forward/horizon-matched methodology as prior spike | This document specifies the `fit_fn` wrappers for `SARIMAX`/`ExponentialSmoothing` at weekly cadence, the shared-harness parameterization (`min_train`, `horizon`, `step`), and the Baltic-AN dedup comparison procedure — all reusing existing repo code, none of it a rerun of the prior VAR/OLS combination |
| WKLY-02 | Documented go/no-go compared explicitly against 9.49%/10.08% monthly MAPE | This document specifies the horizon-matched rollup/aggregation procedure that converts weekly-step forecasts into a 1-month-ahead comparable MAPE, and the recommended report structure (mirroring `REPORT-SENTIMENT.md`'s computed-verdict house style) for stating that comparison |
</phase_requirements>

## Summary

This phase is almost entirely a "wire together existing, working pieces" job, not new research
into an unfamiliar library. `backend_research/walk_forward.py`'s `walk_forward_backtest()` is
cadence-agnostic (it operates on whatever `PeriodIndex`/`DatetimeIndex` the passed `series` has,
counting steps not calendar time), so the exact same harness that ran monthly SARIMAX/ETS in
`run_arima_sarimax_wf.py`/`run_baseline_ets.py` will run unmodified against weekly data — the
`_SARIMAXWrapper`, `_ARIMAWrapper`, `_SESWrapper`, and `_HoltDampedWrapper` classes in those two
scripts can be imported or near-verbatim copied with only the `min_train`/`horizon` constants
changed for weekly cadence.

One concrete blocker was found and verified on this machine: `backend_research/data_loader.py`'s
`AN_CSV`/`DIESEL_CSV`/`AN_WEEKLY_CSV` module constants are hardcoded absolute macOS paths
(`/Users/dlgvnbyr/Desktop/Prediction Dashboard/...`) that do not exist on this Windows machine —
calling `load_an_weekly()` as-is raises `FileNotFoundError` `[VERIFIED: ran python3
data_loader.load_an_weekly() directly on this machine, reproduced the failure]`. The CSVs
themselves are present at the repo root (`AN Data.csv`, `AN price weekly.csv`,
206 and 711 rows respectively `[VERIFIED: read directly with pandas]`). CONTEXT.md's locked
decision says reuse these loaders "as-is... need no changes for the new model families," but "as
written" is not runnable here; the honest resolution is a **minimal path fix** (make the three
constants relative to the repo root via `Path(__file__)`, matching the pattern `db_loader.py`
already uses for `app/reflex.db`) — not a rewrite of the loading/cleaning logic, which stays
untouched. This is additive/config-only and should not be read as violating the "no rewrite"
constraint.

The Baltic-AN dedup question resolves to a direct, cheap comparison: both source files carry a
column literally named `Baltic AN` (`AN Data.csv`, stripped header) and `Baltic AN` (`AN price
weekly.csv`, renamed to `BalticAN_wk` by `load_weekly_drivers()`) `[VERIFIED: read raw CSV
headers]`. `AN price weekly.csv` spans 2013-01 to 2026-08 (711 rows) while `AN Data.csv` spans
only 2022-08 to 2026-07 (206 rows, exactly weekly, `diff == -7 days` in every row)
`[VERIFIED: measured directly]` — so on the overlapping window the two Baltic AN columns can be
merged on date and compared for correlation/mean-absolute-difference to determine duplicate vs.
independent, without needing any new library.

**Primary recommendation:** Build a new `backend_research/weekly/` module mirroring Phase 16's
`backend_research/sentiment/` house style (flat script + test file + frozen JSON + deterministic
Markdown report, no `__init__.py`), containing: (1) a repo-root-relative path fix inside
`data_loader.py` or a thin loader shim, (2) `fit_fn` wrappers for weekly SARIMAX/ExponentialSmoothing
adapted from `run_arima_sarimax_wf.py`/`run_baseline_ets.py`, (3) a Baltic-AN dedup comparison
script, and (4) a horizon-matched rollup that reuses `walk_forward_backtest()`'s own multi-step
`horizon` parameter (no need for `run_weekly_candidates.py`'s hand-rolled iterative-refit loop) to
produce a 4-5-week-ahead MAPE directly comparable to 9.49%/10.08%.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| statsmodels | 0.14.6 `[VERIFIED: installed and importable via system python3 on this machine, matches CLAUDE.md pin]` | `SARIMAX`, `ExponentialSmoothing`, `ARIMA` | Already the project's locked forecasting library (CLAUDE.md); `run_arima_sarimax_wf.py`/`run_baseline_ets.py` already use it identically at monthly cadence |
| pandas | 2.2.3 `[VERIFIED: installed, matches ENV.md pin]` | Weekly `DatetimeIndex`/`PeriodIndex` handling, CSV parsing, merge_asof | Already used throughout `backend_research/` |
| pytest | installed `[VERIFIED]` | Regression tests for the new weekly module | House style set by `test_walk_forward.py` and Phase 16's `sentiment/test_*.py` |

No new packages are needed. This phase adds zero new dependencies — everything required is
already in `backend_research/requirements-research.txt` and already verified working on this
machine.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled iterative-refit loop (`run_weekly_candidates.py`'s approach) for the horizon-matched rollup | `walk_forward_backtest(series, exog, fit_fn, min_train=..., horizon=5, step=1, refit_every=1)` | The shared harness already does exactly this — refits every origin, forecasts `horizon` steps ahead, and returns every `(origin, horizon_step, forecast, actual)` row so `mape_by_horizon` can pull out the h=4 or h=5 slice. Locked decision explicitly requires this over the ad-hoc loop. |
| Rewriting `data_loader.py`'s CSV parsing logic | Only patching the three hardcoded path constants | CONTEXT.md's "additive, not a rewrite" instruction for the loaders; the cleaning/parsing logic already works, only the machine-specific absolute paths are wrong |

**Installation:** None required — no new packages.

**Version verification:** `python3 -c "import statsmodels; print(statsmodels.__version__)"` →
`0.14.6` `[VERIFIED]`; `python3 -c "import pandas; print(pandas.__version__)"` → `2.2.3`
`[VERIFIED]`, both run directly on this machine 2026-09-01, matching CLAUDE.md's/ENV.md's pins.

## Architecture Patterns

### Recommended Project Structure
```
backend_research/
├── weekly/                              # new, mirrors backend_research/sentiment/
│   ├── run_weekly_sarimax_ets.py        # SARIMAX + ETS fit_fn wrappers, walk-forward runs, JSON+report
│   ├── test_weekly_sarimax_ets.py       # record-shape / non-hardwired-verdict tests, house style of test_walk_forward.py
│   └── baltic_an_dedup.py               # standalone dedup comparison script (see Pattern 3)
├── data_loader.py                        # PATCH ONLY: AN_CSV/DIESEL_CSV/AN_WEEKLY_CSV -> Path(__file__).resolve().parent.parent / "AN Data.csv" etc.
├── results/
│   └── weekly_sarimax_ets.json          # frozen output, flat dir alongside existing */results/*.json (Phase 16 precedent: flat, not nested)
└── REPORT-WEEKLY.md                      # deterministic go/no-go report, mirrors REPORT-SENTIMENT.md
```

### Pattern 1: `walk_forward_backtest`'s `fit_fn` interface (cadence-agnostic)

**What:** `walk_forward_backtest(series, exog, fit_fn, min_train, horizon, step, refit_every)`
slices `series`/`exog` purely by integer position (`.iloc[:origin]`), never by calendar
arithmetic. `fit_fn(train_y, train_x) -> object with .forecast(steps, exog=future_exog)`. This
means it is inherently cadence-agnostic: give it a weekly-indexed `Series` and it produces a
weekly-step walk-forward backtest with zero code changes.

**When to use:** Every SARIMAX/ETS run this phase, in place of `run_weekly_candidates.py`'s
hand-rolled loop.

**Example (adapted from `run_arima_sarimax_wf.py`'s `_SARIMAXWrapper`/`_SESWrapper`, weekly cadence):**
```python
# Source: backend_research/walk_forward.py, backend_research/run_arima_sarimax_wf.py (verbatim pattern, weekly params)
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from walk_forward import walk_forward_backtest, mape_by_horizon

class _SARIMAXWrapper:
    def __init__(self, train_y, train_x, order):
        self.fitted = sm.tsa.SARIMAX(
            train_y.to_numpy(),
            exog=train_x.to_numpy() if train_x is not None else None,
            order=order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)

    def forecast(self, steps, exog=None):
        if exog is not None:
            return self.fitted.forecast(steps=steps, exog=np.asarray(exog))
        return self.fitted.forecast(steps=steps)

class _HoltDampedWrapper:
    def __init__(self, train_y):
        self.fitted = ExponentialSmoothing(
            train_y.to_numpy(), trend="add", seasonal=None,
            damped_trend=True, initialization_method="estimated",
        ).fit()

    def forecast(self, steps):
        return self.fitted.forecast(steps)

fit_fn = lambda train_y, train_x: _SARIMAXWrapper(train_y, train_x, order=(1, 1, 1))
wf = walk_forward_backtest(hdan_weekly, exog_df, fit_fn, min_train=104, horizon=5, step=1, refit_every=1)
mbh = mape_by_horizon(wf)          # Series indexed by horizon_step 1..5
month_matched_mape = mbh[5]        # or mbh[4], see Pattern 2 for which
```

### Pattern 2: Horizon-matched rollup — align to actual weeks-per-month, don't hardcode 4

**What:** CONTEXT.md's locked decision explicitly forbids treating "4 weeks" as a fixed
stand-in for "1 month" — real months are 4.0-4.43 weeks. `walk_forward_backtest`'s `horizon`
parameter already returns every `horizon_step` from 1 to `horizon` per origin (not just the last
one), so the correct approach is: set `horizon=5` (covers the longest realistic month), then at
report time compute the MAPE for **both** `horizon_step=4` and `horizon_step=5` via
`mape_by_horizon(wf)`, and report whichever (or both, with the actual mean weeks/month noted) most
honestly represents "1 calendar month ahead" — do not silently pick whichever number is smaller.
`AN Data.csv`'s weekly cadence is exactly 7 days per row `[VERIFIED: diff().dt.days == -7 for
205/205 gaps]`, so month length in this data varies from exactly 4 rows (28-day months, rare) to 5
rows (most months); the honest choice, matching the prior spike's own precedent of using 4
`[CITED: backend_research/REPORT.md "Weekly cadence" section]`, is to report the 4-step number as
primary (closest to a 30-day month) and the 5-step number as a secondary sensitivity check, both
against the same 9.49%/10.08% benchmark, rather than picking only one silently.

**When to use:** The final go/no-go comparison table (WKLY-02).

### Pattern 3: Baltic-AN dedup as a data comparison, not a model

**What:** A short standalone script that: (1) loads both raw columns on their native indices,
(2) `merge_asof`s them onto a common weekly index (same ±3-day tolerance `merged_weekly()`
already uses), (3) computes Pearson correlation and mean absolute percentage difference between
the two Baltic AN series over the overlapping window (2022-08 through 2026-07, 206 dates), and
(4) states a documented recommendation (prefer one, average both, or treat as independent) based
on that measured correlation — not an assumed answer.

**Example:**
```python
# Source: pattern only, no external API — pandas merge_asof already used by merged_weekly()
import pandas as pd
from data_loader import load_an_weekly, load_weekly_drivers

an = load_an_weekly()[["Baltic AN"]].rename(columns={"Baltic AN": "baltic_an_data_csv"})
drv = load_weekly_drivers()[["BalticAN_wk"]]
cmp = pd.merge_asof(an.sort_index(), drv.sort_index(), left_index=True, right_index=True,
                     direction="nearest", tolerance=pd.Timedelta(days=3)).dropna()
corr = cmp["baltic_an_data_csv"].corr(cmp["BalticAN_wk"])
mape_between = (cmp["baltic_an_data_csv"] - cmp["BalticAN_wk"]).abs() / cmp["baltic_an_data_csv"].abs() * 100
# corr close to 1.0 and low mape_between -> duplicate source, prefer one; else -> independent signal, may combine
```

**Then:** whichever verdict this produces, use it to define the driver-set VARIANT fed into the
VAR/OLS-style comparison model this phase's exogenous-driver tests use (per CONTEXT.md: the dedup
fix is "a variant driver set on top of whichever model(s) it's relevant to," not a new model
family).

### Anti-Patterns to Avoid
- **Hardcoding `min_train`/`horizon` at their monthly values (36/12) for weekly data:** 36 weekly
  observations is under 9 months, too short to fit a reasonable SARIMAX with any seasonal terms
  and leaves few walk-forward origins from a 206-row series; likewise `horizon=12` weeks (~3
  months) is not "horizon-matched to 1 month" per CONTEXT.md's locked definition. Use weekly-scale
  values (`min_train` ~2 years = 104 weeks, `horizon` = 5) instead — see Common Pitfalls for the
  budget math.
- **Comparing weekly one-step MAPE to the monthly 9.49%/10.08% benchmark:** already flagged as
  invalid by the prior spike's own report and re-stated as a locked constraint here; only the
  horizon-matched (Pattern 2) number is a valid comparison.
- **Re-deriving `load_an_weekly()`/`merged_weekly()`'s cleaning logic instead of patching the path
  constants:** the loaders' parsing is already validated; the only defect found is the
  machine-specific absolute path, which is a one-line fix per constant.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling-origin backtest loop | A new hand-rolled `for` loop like `run_weekly_candidates.py`'s 4-week rollup section | `walk_forward.walk_forward_backtest()` | Locked decision explicitly requires this; it already handles leakage assertions (`LeakageError`), origin/window slicing, per-horizon-step aggregation, and failed-origin tracking that a hand-rolled loop would have to reimplement and re-verify |
| MAPE-by-horizon aggregation | Custom groupby/mean code | `walk_forward.mape_by_horizon(results_df)` | Already implemented, already handles `actual==0`/NaN exclusion |
| SARIMAX/ETS order search | A new grid-search implementation | `itertools.product` grid + AIC selection pattern from `run_arima_sarimax_wf.py`'s `select_arima_order()`, `ExponentialSmoothing(... damped_trend=True)` pattern from `run_baseline_ets.py` | Both patterns are already validated in this repo at monthly cadence; weekly cadence only changes the grid bounds and `seasonal_periods`, not the search structure |
| Merging two weekly-cadence CSVs with slightly offset dates | Custom date-matching logic | `pd.merge_asof(..., direction="nearest", tolerance=pd.Timedelta(days=3))` | Already the pattern `merged_weekly()` uses; same tolerance choice reused for the Baltic-AN dedup comparison keeps methodology consistent |

**Key insight:** This phase is a composition problem, not an implementation problem. Nearly every
building block needed (harness, wrappers, order-search pattern, merge pattern) already exists and
is already validated elsewhere in this repo at a different cadence. Hand-rolling any of these
again would reintroduce exactly the kind of bug (leakage, mis-aligned lag) the shared harness was
built to prevent.

## Common Pitfalls

### Pitfall 1: `data_loader.py`'s hardcoded macOS paths break on this machine
**What goes wrong:** `AN_CSV`, `DIESEL_CSV`, `AN_WEEKLY_CSV` are absolute paths under
`/Users/dlgvnbyr/Desktop/Prediction Dashboard/`. Calling any of `load_an_monthly()`,
`load_an_weekly()`, `load_weekly_drivers()`, `merged_weekly()`, `load_diesel_monthly()`,
`merged_monthly()` unmodified raises `FileNotFoundError` on this Windows machine.
**Why it happens:** The module was written and last run on a different (Mac) machine; the CSVs
were never moved into a machine-independent, repo-relative location in `data_loader.py` itself
(unlike `db_loader.py`, which already uses `Path(__file__).resolve().parent.parent / "app" /
"reflex.db"`).
**How to avoid:** Patch the three path constants to `Path(__file__).resolve().parent.parent /
"AN Data.csv"` etc. (repo root, one level up from `backend_research/`) — verified this is exactly
where the CSVs live on this machine. This is a config-only change; do not touch the parsing
logic below it.
**Warning signs:** `FileNotFoundError: [Errno 2] No such file or directory: '/Users/dlgvnbyr/...'`
`[VERIFIED: reproduced directly on this machine, 2026-09-01]`.

### Pitfall 2: Too-short `min_train`/too-long `horizon` degrades or breaks SARIMAX fitting at weekly cadence
**What goes wrong:** `AN Data.csv`'s weekly series has only 206 observations total (2022-08 to
2026-07) `[VERIFIED]`. If `min_train` is set too high (e.g. reusing the monthly value of 36
verbatim would be far too low for weekly — the opposite problem: 36 weeks is under 9 months, not
enough history for stable SARIMAX/ETS fits with any seasonal component), the harness has very few
usable walk-forward origins (`n - min_train`) once `horizon` is subtracted, and results become as
"thin" as the prior spike's flagged 9-window problem — the exact failure mode this phase is meant
to fix.
**Why it happens:** Monthly-cadence constants don't translate 1:1 to weekly cadence; a monthly
`min_train=36` (3 years) is a very different fraction of series length than a weekly
`min_train=36` (8 months) would be.
**How to avoid:** Budget explicitly: with n=206 weekly rows, a `min_train` of ~104 (2 years)
leaves ~100 usable origins even after subtracting `horizon=5`, comfortably larger than the prior
spike's 9-window sample and still leaving a meaningful multi-year training window for SARIMAX/ETS
convergence. Document the exact origin count achieved (`wf["origin_date"].nunique()`, already
returned by `walk_forward_backtest`) in the report so the "properly-sized" claim (locked decision)
is verifiable, not asserted.
**Warning signs:** `walk_forward_backtest` returning very few rows, or a high count of
`results.attrs["failed_origins"]`.

### Pitfall 3: Seasonal period choice for weekly AN data is not textbook-obvious
**What goes wrong:** Weekly commodity price data doesn't have an obvious `seasonal_periods` the
way retail/weather data does (52 for annual seasonality assumes 4+ years of clean data; AN Data
only has ~4 years, 206 points — barely 4 annual cycles, likely too few for statsmodels to
reliably estimate 52 seasonal parameters, and `run_baseline_ets.py`'s own monthly precedent
explicitly used `seasonal=None` for the same reason ("fewer than two clean annual cycles for some
series")).
**Why it happens:** Naively setting `seasonal_periods=52` because "52 weeks in a year" without
checking whether the series has enough repeated cycles to estimate it reliably.
**How to avoid:** Default to `seasonal=None` for both SARIMAX (no seasonal `(P,D,Q,s)` term,
i.e. plain ARIMA order) and ExponentialSmoothing, matching `run_baseline_ets.py`'s own justified
choice — and if a seasonal variant is tried as a discretionary extra, treat any results from it
with explicit caution given <4 clean annual cycles, and say so in the report. This is a
`[CITED: backend_research/run_baseline_ets.py]`-sourced convention, not a hard rule from
statsmodels itself.
**Warning signs:** `ConvergenceWarning` or non-convertible/huge-magnitude seasonal coefficients
from `ExponentialSmoothing(..., seasonal="add", seasonal_periods=52)` on this series length.

### Pitfall 4: SARIMAX/ETS convergence warnings on short training windows
**What goes wrong:** Early walk-forward origins (right at `min_train`) have the least training
data; SARIMAX with `enforce_stationarity=False, enforce_invertibility=False` (the existing
`_SARIMAXWrapper` pattern) can still throw `ConvergenceWarning` or occasionally fail to converge
on short/volatile early windows.
**Why it happens:** Same tradeoff as any walk-forward backtest — the first few origins are always
data-starved relative to later ones.
**How to avoid:** `walk_forward_backtest`'s existing `try/except` around `fit_fn`/`forecast`
already catches exceptions and records them in `failed_origins` rather than crashing the whole
run — no new exception handling needed. Suppress `ConvergenceWarning` the same way
`run_arima_sarimax_wf.py`/`run_baseline_ets.py` already do (`warnings.filterwarnings("ignore")`
at module top), and report the `failed_origins` count explicitly rather than silently dropping it.
**Warning signs:** Nonzero `results.attrs["failed_origins"]`; report this count in the go/no-go
document (Phase 2/16 precedent: never hide a nonzero failure count).

### Pitfall 5: `merged_weekly()`'s driver file has a much longer history than the AN weekly file — don't accidentally widen the effective sample
**What goes wrong:** `AN price weekly.csv` spans 2013-01 to 2026-08 (711 rows) while `AN Data.csv`
(the actual HDAN/PPAN target series) only spans 2022-08 to 2026-07 (206 rows)
`[VERIFIED: measured directly]`. `merged_weekly()` already correctly bounds this by joining on
`an` (the shorter, target-bearing frame) and `dropna(subset=["BalticAN_wk"])`, so the merged frame
is correctly limited to ~206 rows — but any new script that loads `load_weekly_drivers()`
independently (e.g. for the dedup check) must remember the driver file's own useful window for
comparison is only the 2022-08–2026-07 overlap, not its full 2013–2026 span, or the dedup
correlation will be computed over mismatched populations if not merged first.
**Why it happens:** Easy to forget when writing a standalone comparison script that doesn't reuse
`merged_weekly()`.
**How to avoid:** Always join both Baltic AN columns via `merge_asof` (Pattern 3) before comparing
them; never compute a raw correlation on differently-lengthed unaligned series.
**Warning signs:** A correlation/dedup script producing a `NaN` or the wrong `n` if `.corr()` is
called on raw unaligned Series.

## Code Examples

### Weekly SARIMAX wrapper reused verbatim from monthly cadence
```python
# Source: backend_research/run_arima_sarimax_wf.py, lines 81-94 (unchanged — cadence-agnostic)
class _SARIMAXWrapper:
    def __init__(self, train_y, train_x, order):
        self.fitted = sm.tsa.SARIMAX(
            train_y.to_numpy(),
            exog=train_x.to_numpy() if train_x is not None else None,
            order=order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)

    def forecast(self, steps, exog=None):
        if exog is not None:
            return self.fitted.forecast(steps=steps, exog=np.asarray(exog))
        return self.fitted.forecast(steps=steps)
```

### Weekly-scale walk-forward call and horizon-matched extraction
```python
# Source: pattern combining backend_research/walk_forward.py + this document's Pattern 2
from walk_forward import walk_forward_backtest, mape_by_horizon, single_holdout_mape

MIN_TRAIN_WEEKLY = 104   # ~2 years; leaves ~100 origins from a 206-row series
HORIZON_WEEKLY = 5       # covers a 5-week month; report both h=4 and h=5

fit_fn = lambda train_y, train_x: _SARIMAXWrapper(train_y, train_x, order=order)
wf = walk_forward_backtest(hdan_weekly, exog_or_none, fit_fn,
                            min_train=MIN_TRAIN_WEEKLY, horizon=HORIZON_WEEKLY,
                            step=1, refit_every=1)
mbh = mape_by_horizon(wf)
n_origins = wf["origin_date"].nunique()
n_failed = len(wf.attrs["failed_origins"])
result = {
    "model": f"SARIMAX{order}",
    "cadence": "weekly->monthly-horizon",
    "mape_4week": float(mbh.get(4)),
    "mape_5week": float(mbh.get(5)),
    "n_origins": int(n_origins),
    "failed_origins": n_failed,
}
```

### Path fix for `data_loader.py` (Pitfall 1)
```python
# Recommended patch — repo-root-relative, mirrors db_loader.py's DB_PATH pattern
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
AN_CSV = str(_REPO_ROOT / "AN Data.csv")
DIESEL_CSV = str(_REPO_ROOT / "Diesel Data.csv")
AN_WEEKLY_CSV = str(_REPO_ROOT / "AN price weekly.csv")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `run_weekly_candidates.py`'s hand-rolled iterative 4-week rollup loop (9 windows) | `walk_forward_backtest(..., horizon=5)` producing every horizon step per origin | This phase | Far more usable origins from the same 206-row series; also gives both a 4-week and 5-week reading instead of only 4, matching the locked "match actual weeks-per-month" instruction |
| `data_loader.py`'s absolute macOS path constants | Repo-root-relative `Path(__file__)` constants | This phase (recommended fix) | Makes the existing, already-validated loaders actually runnable on this (Windows) machine without touching their parsing logic |

**Deprecated/outdated:** Nothing library-level is deprecated here — statsmodels 0.14.6 API
surface used (`SARIMAX`, `ExponentialSmoothing`) is unchanged from the monthly scripts already in
this repo; no version-skew risk since the pin is identical to what's already validated.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `min_train=104` (2 years) / `horizon=5` weeks is a reasonable weekly-cadence parameterization (Claude's discretion per CONTEXT.md) | Pitfall 2, Code Examples | If wrong, the plan may need to tune these constants at execution time based on actual `n_origins`/`failed_origins` observed; not a blocking risk since it's explicitly discretionary and the harness reports these diagnostics for correction |
| A2 | `seasonal=None` is the right default for weekly AN SARIMAX/ETS given <4 clean annual cycles | Pitfall 3 | If AN prices do have exploitable weekly-within-year seasonality the report would understate ETS/SARIMAX's potential; mitigated by treating any seasonal variant tried as a discretionary extra with explicit caution, not as the primary candidate |

**If this table is empty:** N/A — two low-risk discretionary parameterization assumptions logged
above; both are explicitly within CONTEXT.md's "Claude's Discretion" grant, not disputed facts.

## Open Questions

1. **Which of h=4 or h=5 should be the "primary" number in the go/no-go table?**
   - What we know: Both are computable directly from the same `walk_forward_backtest(horizon=5)`
     run via `mape_by_horizon`; the prior spike used a fixed 4.
   - What's unclear: Whether reviewers reading the final report expect a single number matched
     1:1 against 9.49%/10.08%, or a small range.
   - Recommendation: Report both explicitly (Pattern 2) rather than silently picking one — this
     is more honest and costs nothing extra since both come from the same backtest run.

2. **Should the Baltic-AN dedup outcome feed into the SARIMAX/ETS exogenous-driver variant, or
   only into a VAR/OLS variant?**
   - What we know: CONTEXT.md says the dedup fix is "a variant driver set on top of whichever
     model(s) it's relevant to (e.g. VAR or a regression variant)."
   - What's unclear: Whether a SARIMAX-with-exog run using the deduped Baltic AN column also
     counts, or whether that would double up with the univariate-first SARIMAX candidate.
   - Recommendation: Whichever ordering choice is made under "univariate-only first, then add
     drivers" (also Claude's discretion), reuse the same deduped Baltic AN choice consistently
     across every driver-bearing model tried this phase, and state the choice once in the
     Methodology section rather than re-deriving it per model.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| statsmodels | SARIMAX / ExponentialSmoothing | ✓ `[VERIFIED]` | 0.14.6 | — |
| pandas | CSV loading, merge_asof, resampling | ✓ `[VERIFIED]` | 2.2.3 | — |
| pytest | Regression tests | ✓ `[VERIFIED]` | installed | — |
| `AN Data.csv` / `AN price weekly.csv` (repo-root CSVs) | `data_loader.py`'s weekly loaders | ✓ `[VERIFIED: present at repo root, readable]` | 206 / 711 rows | — |
| `data_loader.py`'s current path constants | same loaders, as currently written | ✗ `[VERIFIED: FileNotFoundError reproduced]` | — | Patch to repo-root-relative paths (Pitfall 1) — no external fallback needed, this is an in-repo fix |

**Missing dependencies with no fallback:** None — the one gap found (Pitfall 1) has a direct,
in-scope fix.

**Missing dependencies with fallback:** `data_loader.py` path constants — fallback is the
one-line patch already specified above, not a different library or approach.

## Validation Architecture

*(Not applicable in the pytest/CI sense — `.planning/config.json` was not found in this
non-git-initialized checkout, but the project's own established discipline, followed by every
prior `backend_research/` phase including Phase 2 and Phase 16, is: shared walk-forward harness +
frozen JSON output + pytest regression tests + deterministic Markdown report. This phase should
follow that same discipline rather than a formal test-framework mapping, since `backend_research/`
scripts are offline research tools, not application code with user-facing behaviors to unit-test
in the traditional sense.)*

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, `[VERIFIED]`) |
| Config file | none detected under `backend_research/` (matches existing `test_walk_forward.py`/`sentiment/test_*.py` — no `pytest.ini`/`conftest.py` in this dir today) |
| Quick run command | `cd backend_research && python3 -m pytest weekly/ -q` |
| Full suite command | `cd backend_research && python3 -m pytest -q` (must stay green — proves no regression to `test_walk_forward.py` or `sentiment/test_*.py`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WKLY-01 | New weekly SARIMAX/ETS records have correct shape and are genuinely new (not the prior VAR/OLS combo) | unit | `pytest weekly/test_weekly_sarimax_ets.py -q` | ❌ Wave 0 (create) |
| WKLY-01 | Baltic-AN dedup comparison produces a non-hardwired verdict from measured correlation | unit | `pytest weekly/test_weekly_sarimax_ets.py -k dedup -q` (or a separate `test_baltic_an_dedup.py`) | ❌ Wave 0 (create) |
| WKLY-02 | Horizon-matched MAPE (h=4/h=5) is computed from the shared harness, not hardcoded, and compared to 9.49/10.08 in the frozen report | manual + script exit code | `python3 weekly/run_weekly_sarimax_ets.py` then inspect `REPORT-WEEKLY.md` | ❌ Wave 0 (create) |

### Sampling Rate
- **Per task commit:** `cd backend_research && python3 -m pytest weekly/ -q`
- **Per wave merge:** `cd backend_research && python3 -m pytest -q` (full suite)
- **Phase gate:** Full suite green plus a successful, reproducible run of
  `run_weekly_sarimax_ets.py` producing `REPORT-WEEKLY.md` before considering the phase done.

### Wave 0 Gaps
- [ ] `backend_research/weekly/run_weekly_sarimax_ets.py` — does not exist yet, covers WKLY-01/02
- [ ] `backend_research/weekly/test_weekly_sarimax_ets.py` — does not exist yet
- [ ] `backend_research/data_loader.py` path-constant patch (Pitfall 1) — required before any
      weekly loader call succeeds on this machine
- Framework install: none needed — pytest/statsmodels/pandas already present

## Security Domain

This phase is a pure offline `backend_research/` script addition, structurally identical in trust
profile to Phase 16's closed-out security posture (see `.planning/phases/16-.../16-02-PLAN.md`'s
`<threat_model>` section, which this phase mirrors rather than re-deriving from scratch):

- No network exposure, no user input, no authentication/session/authorization surface — reads
  only static, git-tracked/repo-local CSV files and writes only fixed, module-constant paths
  under `backend_research/`.
- The one integrity-relevant risk category (Tampering — a wrong-but-confident-looking MAPE number
  reaching the frozen report) is mitigated the same way Phase 16 mitigated it: reuse
  `walk_forward_backtest`'s existing `LeakageError` guard (train window strictly precedes the
  first forecast target date) unmodified, and keep the go/no-go verdict computed from the frozen
  JSON records rather than hand-typed into the report.
- `security_enforcement` status in `.planning/config.json` could not be checked (no
  `.planning/config.json` found in this checkout at research time); given the project's own
  established precedent (Phase 16) explicitly ran and passed this section, this phase should
  follow the same STRIDE disposition rather than skip it.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — offline script |
| V3 Session Management | no | No sessions — offline script |
| V4 Access Control | no | No access boundary — single local user's own machine |
| V5 Input Validation | yes (data hygiene, not security) | Existing `dropna`/`ffill`/dtype-coercion patterns already in `data_loader.py`; `walk_forward.LeakageError` as the train/forecast integrity guard |
| V6 Cryptography | no | Not applicable — no secrets, no crypto operations |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A wrong effective-N or MAPE silently reaching the frozen report | Tampering (data integrity) | Compute the verdict from the frozen JSON records at report-generation time, never hand-type a number into the Markdown (Phase 16 precedent) |
| Write path escaping `backend_research/` | Tampering | Keep output paths as fixed module-level `Path` constants (`RESULTS_JSON`, `REPORT_PATH`), never derived from data — mirrors Phase 16's `T-16-06` mitigation |

## Sources

### Primary (HIGH confidence — direct repo/code inspection and live execution on this machine)
- `backend_research/walk_forward.py` — full read, `walk_forward_backtest`/`mape_by_horizon`/
  `single_holdout_mape` signatures and internal slicing logic
- `backend_research/data_loader.py` — full read; `load_an_weekly`/`load_weekly_drivers`/
  `merged_weekly` reused as-is; hardcoded path bug found and reproduced live
- `backend_research/db_loader.py` — read for the `Path(__file__)`-relative pattern to mirror in
  the fix
- `backend_research/run_arima_sarimax_wf.py`, `backend_research/run_baseline_ets.py` — full read,
  wrapper classes and order-search pattern
- `backend_research/run_var_candidates.py` — source of the 9.49%/10.08% benchmark reproduction
  logic
- `backend_research/run_weekly_candidates.py` — full read, the prior spike's own hand-rolled
  rollup and the exact prior results (3.15%/3.98% one-step, 10.35%/16.01% 4-week rollup)
- `backend_research/REPORT.md` "Weekly cadence" section — full read, prior go/no-go text and the
  two named follow-ups
- `.planning/phases/16-sentiment-data-sufficiency-causality-research/16-02-PLAN.md` and
  `backend_research/REPORT-SENTIMENT.md` — house style for computed, non-hardwired verdicts,
  frozen JSON + deterministic report pattern
- Live command output on this machine (2026-09-01): `python3 -c "import statsmodels;
  print(statsmodels.__version__)"` → `0.14.6`; `python3 -c "import pandas; print(pandas.__version__)"`
  → `2.2.3`; direct `pd.read_csv` of both source CSVs (206 and 711 rows, headers, date ranges);
  reproduced `data_loader.load_an_weekly()`'s `FileNotFoundError`

### Secondary (MEDIUM confidence)
None — no external web sources were needed; this phase's methodology is entirely internal to the
repo's own established patterns.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, versions verified live on this machine
- Architecture: HIGH — every pattern is a direct reuse of code already in this repo, verified by
  reading the actual source, not recalled from training data
- Pitfalls: HIGH — Pitfall 1 (hardcoded paths) was reproduced live, not assumed; Pitfalls 2-5 are
  derived from measured data properties (n=206, exact 7-day gaps, 711-row driver file) rather than
  guessed

**Research date:** 2026-09-01
**Valid until:** Effectively indefinite for the methodology (internal repo patterns don't drift
on the timescale of external library docs); re-verify only if `AN Data.csv`/`AN price weekly.csv`
are refreshed with new rows before the plan executes, or if `backend_research/requirements-research.txt`
changes.
