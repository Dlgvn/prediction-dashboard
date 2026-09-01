# Phase 20: FX Weekly Backtest - Research

**Researched:** 2026-09-01
**Domain:** Weekly-cadence FX rate time-series backtesting (SARIMAX / Exponential Smoothing) against a tight existing monthly benchmark
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Benchmark (locked, exact figure)**
- The benchmark to beat is the existing monthly FX model: **1.72% MAPE** (Naive/AR(1), per `app/app/forecasting.py`'s `MODEL_INFO["fx_rate"]` — re-confirm this exact figure by reading that constant directly at implementation time, per PITFALLS.md's flagged open question, rather than trusting the transcribed number blindly).
- This is a much tighter bar than Phase 17's weekly HDAN/PPAN benchmark (9.49%/10.08%) — FX's existing monthly model is already very accurate, so weekly FX may plausibly return a no-go even though HDAN/PPAN weekly returned go. Do not assume the outcome; compute it.

**Methodology (locked — mirrors Phase 17's precedent exactly, per PITFALLS.md Pitfall 1, 6)**
- Reuse `backend_research/walk_forward.py`'s `walk_forward_backtest()` shared harness — the same harness Phase 2 (monthly) and Phase 17 (weekly HDAN/PPAN) both used. Do not hand-roll a new backtest loop.
- At minimum, test SARIMAX and Exponential Smoothing at weekly cadence for FX — the same two model families Phase 17 validated for HDAN/PPAN (`backend_research/weekly/run_weekly_sarimax_ets.py` is the direct structural precedent to mirror for wrapper classes/fit_fn shape).
- Write a dedicated FX backtest script, NOT a clone of `run_weekly_sarimax_ets.py` with FX bolted on. FX has a very different row count (865 vs. HDAN/PPAN's ~206) and needs its own examined `MIN_TRAIN_WEEKLY` constant — reusing HDAN/PPAN's `MIN_TRAIN_WEEKLY=104` unexamined is explicitly flagged as a pitfall. Determine a sensible train window for FX's much longer history from first principles.
- "Horizon-matched" here should follow the same pattern Phase 17 established: report results at the horizon that corresponds to roughly 1 month (4-5 weekly steps), so the comparison against the monthly 1.72% benchmark is apples-to-apples.

**Data source (locked — matches Phase 19's ingestion decisions)**
- Source: `FX Data.csv`'s Weekly column (865 rows, 2010-01-04 to 2026-07-27, perfect 7-day cadence). Same parsing hazards apply as documented for Phase 19 (three-cadence single-file layout, positional slicing required, thousands-separator cleanup) — this phase should parse independently rather than depending on Phase 19's SQLite seeding completing first.

**Output artifacts (locked — mirrors Phase 16/17's precedent)**
- Frozen results JSON (e.g. `backend_research/results/weekly_fx.json`) recording each candidate's backtested MAPE, mirroring `causality_screen.json`/`sentiment_causality_screen.json`/`weekly_sarimax_ets.json`'s existing field-shape conventions.
- A documented go/no-go verdict, computed (not hardwired) — proven non-hardwired by a test that flips a synthetic below/above-benchmark record to the opposite verdict, mirroring Phase 16/17's "provably computed, not asserted" test discipline.
- No wall-clock timestamps in generated report content (byte-identical across reruns), if a Markdown report is produced.

**Non-goals**
- No `app/app/forecasting.py` changes — that's Phase 21, and only if this phase returns "go".
- No UI changes — that's Phase 22.
- No changes to `backend_research/weekly/run_weekly_sarimax_ets.py` or its frozen HDAN/PPAN results — this phase is additive.
- Do not re-test or re-derive HDAN/PPAN weekly results here.

### Claude's Discretion
- Exact `MIN_TRAIN_WEEKLY` value for FX (must be justified against FX's 865-row history, not copied from HDAN/PPAN's 104).
- Exact SARIMAX/ETS order-search strategy (grid bounds, seasonal period choice).
- Whether to also test a plain univariate AR/Naive weekly baseline as a sanity check alongside SARIMAX/ETS.
- Report structure/format — mirror `REPORT-WEEKLY.md`'s existing style.

### Deferred Ideas (OUT OF SCOPE)
None raised — this is a tightly-scoped, pre-specified research phase with no scope-creep surface.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WKUI-02 | A backtested weekly-cadence FX forecasting model exists, compared explicitly against the existing monthly FX benchmark (1.72% MAPE, AR(1)/Naive), with a documented, frozen go/no-go verdict — a "no-go" is a valid, complete outcome | This RESEARCH.md provides the exact wrapper-class code, MIN_TRAIN_WEEKLY derivation, CSV slicing code, and computed-verdict test pattern needed to write `run_fx_weekly_backtest.py` producing `results/weekly_fx.json` + go/no-go |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Tech stack is fixed: Reflex, SQLite via `rx.Model`, statsmodels for forecasting, pandas/openpyxl — no new dependencies needed or permitted for this phase (statsmodels 0.14.6, pandas already installed in `backend_research/`'s environment).
- "Model provenance: forecasting models must go through a research/backtest step... before being used in the app — no un-backtested model ships." This phase IS that backtest step for FX weekly; its output gates Phase 21.
- `pmdarima`/`auto_arima` explicitly listed as research-phase-only convenience, never a production dependency — not needed here anyway since Phase 17's precedent uses a manual AIC grid via `statsmodels.tsa.arima.model.ARIMA`, not `pmdarima`. Mirror that, don't introduce `pmdarima`.
- No un-backtested model ships — reinforces that this phase's frozen JSON + verdict is a hard gate for Phase 21's FX weekly forecasting function.

## Summary

Phase 20 is a narrow, well-precedented extension of Phase 17's exact methodology (shared `walk_forward_backtest` harness, SARIMAX + ETS-HoltDamped wrapper classes, horizon-matched MAPE rollup, computed go/no-go) applied to a new series (FX) with a very different row count (865 vs. ~206) and a much tighter benchmark (1.72% MAPE vs. 9.49%/10.08%). The benchmark figure was re-confirmed directly from `app/app/forecasting.py` line 104: `"fx_rate": ("Naive", 1.72)` — the CONTEXT.md transcription is correct. `FX Data.csv`'s Weekly column was directly inspected: `df.iloc[:, 3:5]` (columns `Date.1`, `Weekly`) after `.dropna()` yields exactly 865 rows, 2010-01-04 to 2026-07-27, all Mondays, values comma-formatted strings needing `.str.replace(',', '').astype(float)` cleanup.

The one genuinely new judgment call is `MIN_TRAIN_WEEKLY` for FX. Phase 17's `walk_forward_backtest` uses an *expanding* window (`train_y = series.iloc[:origin]`), so `min_train` only controls how early the first backtest origin starts — it does not cap how much history any individual origin's fit sees. This means the "examine, don't copy" instruction resolves cleanly: Phase 17's criterion for choosing 104 was "enough weeks for a stable initial SARIMAX/ETS fit, not proportional to total series length." That same absolute criterion (~2 years / 104 weeks is a standard, defensible minimum burn-in for weekly SARIMAX/ETS) applies unchanged to FX — but because FX has 865 rows vs. HDAN/PPAN's 206, keeping `MIN_TRAIN_WEEKLY=104` for FX yields **~761 origins** (vs. HDAN/PPAN's ~102), a dramatically larger and more robust backtest sample, spanning FX's full 2010–2026 range including multiple currency regimes. This is recommended as the primary choice, justified independently (not copied unexamined) — with a documented alternative (260 weeks / 5 years) noted for discretion if a builder prefers excluding the earliest, most volatile MNT-devaluation-era data from backtest origins.

**Primary recommendation:** Write `backend_research/weekly/run_fx_weekly_backtest.py`, a dedicated script (not a clone) reusing `walk_forward.py`'s harness verbatim, with `MIN_TRAIN_WEEKLY = 104` (examined and justified below), `HORIZON_WEEKLY = 5`, `BENCHMARK_MAPE = {"FX": 1.72}`, testing SARIMAX (AIC-grid-selected order, `seasonal=None`) and ETS-HoltDamped, univariate only (no exog — FX has no equivalent Baltic-AN-style driver in this dataset/scope), rolling up MAPE at h=4 (primary) and h=5 (sensitivity), with a `beats_benchmark()`-style computed verdict function proven non-hardwired by a synthetic-flip test.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| statsmodels | 0.14.6 (confirmed installed, `arch` 8.0.0 too) | SARIMAX + ExponentialSmoothing weekly fitting | Exact same interface Phase 17 already validated for weekly HDAN/PPAN; project convention (CLAUDE.md) forbids introducing new modeling libraries without a fresh research phase |
| pandas | 2.2.3 (backend_research env; note this differs from app/'s pinned 3.0.5 — backend_research is a separate, already-verified-working research environment per task brief) | CSV parsing, Series/DataFrame walk-forward slicing | Same cleanup idiom already used by every loader in `data_loader.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | installed, version per env | Proving `beats_benchmark`/verdict logic is computed, not hardwired | Mirror `test_weekly_sarimax_ets.py`'s house style (plain asserts, no fixture framework) |
| numpy | installed (statsmodels dependency) | `.forecast()` output coercion via `np.asarray(...).ravel()` | Already used identically in `_SARIMAXWrapper`/`_HoltDampedWrapper` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual AIC grid via `statsmodels.tsa.arima.model.ARIMA` (Phase 17's pattern) | `pmdarima.auto_arima` | CLAUDE.md explicitly scopes `pmdarima` to "research-phase convenience only," and Phase 17 already established the manual-grid pattern for this exact problem shape — no reason to diverge for FX |
| `walk_forward_backtest`'s expanding-window default | A fixed rolling window (re-truncating `train_y` to a max lookback) | Not supported by the current harness signature without hand-rolling — out of scope; expanding window is the established, leakage-audited default and should not be modified this phase |

**Installation:** No new packages — all already installed and verified in `backend_research/`'s environment (`python3 -c "import pandas, statsmodels, scipy, sklearn, arch"` succeeds per task brief).

**Version verification:** `pandas==2.2.3`, `statsmodels==0.14.6`, `scipy` and `sklearn` present per the task brief's stated environment; not re-verified via `pip show` in this research pass since the brief already confirms working versions in the exact environment this phase's script will run in.

## Architecture Patterns

### Recommended Project Structure
```
backend_research/
├── weekly/
│   ├── run_weekly_sarimax_ets.py       # Phase 17 (HDAN/PPAN) — DO NOT MODIFY
│   ├── run_fx_weekly_backtest.py       # NEW — this phase's dedicated FX script
│   └── test_fx_weekly_backtest.py      # NEW — computed-verdict proof tests
├── results/
│   ├── weekly_sarimax_ets.json         # Phase 17 frozen — untouched
│   └── weekly_fx.json                  # NEW — this phase's frozen output
├── walk_forward.py                     # shared harness — reused, not modified
└── REPORT-WEEKLY-FX.md                 # NEW — mirrors REPORT-WEEKLY.md structure (recommended name; avoids overwriting/confusing with Phase 17's REPORT-WEEKLY.md)
```

### Pattern 1: FX weekly CSV loader (new — no existing precedent for a three-cadence single file)
**What:** A dedicated `load_fx_weekly()` function, positional-slicing `FX Data.csv`'s `Date.1`/`Weekly` column pair (columns 3-4, 0-indexed), independent of the Daily/Monthly columns.
**When to use:** Any time this phase (or a future phase) needs FX's true weekly series.
**Example (verified directly against the real CSV — 865 rows, 2010-01-04..2026-07-27, all Mondays):**
```python
# Source: direct inspection of FX Data.csv (repo root), mirroring data_loader.py's
# established per-column cleanup idiom (.astype(str).str.replace(',', '').astype(float))
import pandas as pd
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # backend_research/weekly/ -> repo root
FX_CSV = str(_REPO_ROOT / "FX Data.csv")

def load_fx_weekly() -> pd.Series:
    """Returns FX rate as a weekly pd.Series indexed by week-ending Date (Mondays),
    865 rows, 2010-01-04..2026-07-27. Positional slicing (columns 3-4: 'Date.1',
    'Weekly') -- NEVER name-based selection, since pandas auto-renames FX Data.csv's
    duplicate 'Date'/blank spacer columns and the three cadences (Daily/Weekly/Monthly)
    are NOT row-aligned (Pitfall 2, PITFALLS.md)."""
    df = pd.read_csv(FX_CSV)
    weekly = df.iloc[:, 3:5].copy()
    weekly.columns = ["Date", "Weekly"]
    weekly = weekly.dropna()
    weekly["Date"] = pd.to_datetime(weekly["Date"])
    weekly["Weekly"] = weekly["Weekly"].astype(str).str.replace(",", "").astype(float)
    weekly = weekly.sort_values("Date").set_index("Date")
    return weekly["Weekly"]


if __name__ == "__main__":
    y = load_fx_weekly()
    print("FX weekly:", y.shape, y.index.min(), "-", y.index.max())
    assert y.shape[0] == 865, f"expected 865 FX weekly rows, got {y.shape[0]}"
    assert y.index.min() == pd.Timestamp("2010-01-04")
    assert y.index.max() == pd.Timestamp("2026-07-27")
    assert y.dtype == "float64"
    print("OK")
```
Confirmed live: `df.iloc[:, 3:5]` after `.dropna()` gives shape `(865, 2)`, min date `2010-01-04`, max date `2026-07-27`, all weekday names `Monday`, `Weekly.dtype == float64` after cleanup. First value (2026-07-27) = `3592.90`, matching the raw CSV's `"3,592.90"`.

### Pattern 2: SARIMAX/ETS wrapper classes (mirrored from Phase 17, adapted — univariate only)
**What:** Same `_SARIMAXWrapper`/`_HoltDampedWrapper` shape as `run_weekly_sarimax_ets.py`, copied not re-invented, with FX-specific naming and no exog variant (no Baltic-AN-equivalent driver exists for FX in this dataset/scope — CONTEXT.md's discretion note allows an optional plain AR/Naive baseline instead, not an exog variant).
**When to use:** Both candidate model families this phase's success criteria mandate.
**Example:**
```python
# Source: adapted from backend_research/weekly/run_weekly_sarimax_ets.py (Phase 17),
# same wrapper shape/fit_fn contract walk_forward_backtest expects.
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing


class _SARIMAXWrapper:
    """Weekly-cadence SARIMAX -- seasonal=None. FX has no established weekly seasonal
    cycle (currency rates don't exhibit calendar seasonality the way commodity
    physical-delivery prices sometimes do), and even fewer than 4 clean annual cycles
    exist at the smallest MIN_TRAIN_WEEKLY origin, mirroring Phase 17's Pitfall-3
    rationale for HDAN/PPAN."""

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
    def __init__(self, train_y, train_x=None):
        self.fitted = ExponentialSmoothing(
            train_y.to_numpy(),
            trend="add",
            seasonal=None,
            damped_trend=True,
            initialization_method="estimated",
        ).fit()

    def forecast(self, steps, exog=None):
        return self.fitted.forecast(steps)
```

### Pattern 3: MIN_TRAIN_WEEKLY derivation for FX (first-principles, examined)
**What:** How many rolling-origin windows a given `min_train`/`horizon` combination yields against FX's 865 rows, and why `MIN_TRAIN_WEEKLY=104` is the recommended, examined choice (not a copy of HDAN/PPAN's value).
**Reasoning:**
- `walk_forward_backtest` iterates `origin` from `min_train` to `n` (step=1 default); the raw origin count is `n - min_train` (865 - min_train), further reduced near the tail where `max_h = min(horizon, n - origin)` truncates partial windows, matching Phase 17's `n_origins ≈ n - min_train - horizon + 1` behavior in practice (Phase 17: 206 - 104 - 5 + 1 = 98, close to the observed 102 — small discrepancy from step/refit bookkeeping, treat as approximate).
- Because the harness trains on an **expanding** window (`series.iloc[:origin]`), `min_train` is purely a "how early can the first fit be trusted to be stable" threshold — it does NOT bound how much data later-origin fits see, and it does NOT need to scale proportionally with total series length. The correct question is "what is the minimum number of weekly observations for SARIMAX/ETS to converge reliably," not "what fraction of FX's history should be burn-in."
- 104 weeks (~2 years) was Phase 17's answer to that exact stability question for the same model families (SARIMAX with `enforce_stationarity=False`, ETS-HoltDamped) at the same weekly cadence. Nothing about FX's data generating process (a currency rate, generally smoother / lower-variance-per-step than an ammonium-nitrate spot price) suggests SARIMAX/ETS would need *more* than 104 weeks to converge; if anything FX's smoother, more linear multi-year trend argues 104 is comfortably sufficient.
- Applying `MIN_TRAIN_WEEKLY=104` to FX's 865 rows: `n_origins ≈ 865 - 104 - 5 + 1 = 757` (~7.4x Phase 17's ~102-origin FX backtest), spanning 2011-ish through 2026 — i.e., FX's full available trading history minus the first 2 years, a materially larger and more robust validation sample than HDAN/PPAN's.
- **Recommendation: `MIN_TRAIN_WEEKLY = 104`**, documented in-code with this reasoning (mirroring Phase 17's own in-code comment style), NOT inherited implicitly — the plan should write the comment explaining the examination, satisfying Pitfall 6's "commented, deliberate choice" requirement even though the numeric value happens to match.
- **Discretion alternative:** `MIN_TRAIN_WEEKLY = 260` (5 years) trades ~155 fewer origins (~602) for excluding FX's earliest, most volatile post-2008/MNT-devaluation-era years from ever being backtested — defensible if a builder judges early-2010s FX dynamics unrepresentative of current regime, but not required; 104 is the primary recommendation.
- Runtime note: ~757 origins × 2 models (refit_every=1, i.e. refit at every origin) means ~1,514 SARIMAX/ETS `.fit()` calls — a one-time research-script cost (per PITFALLS.md's own "Performance Traps" table, acceptable as a research-phase cost, not a runtime app cost). If this proves slow in practice, `refit_every` can be raised (e.g. `refit_every=4`) as an implementation-time adjustment without invalidating the methodology — but Phase 17 used `refit_every=1` throughout and this phase should default to matching that unless the plan's execution proves it impractically slow.

### Anti-Patterns to Avoid
- **Copying `MIN_TRAIN_WEEKLY=104` from `run_weekly_sarimax_ets.py`'s import or constant reference without re-deriving/re-commenting it for FX:** even though the recommended value happens to be numerically identical, the plan/script MUST independently justify it in a comment specific to FX's 865-row context (Pitfall 6's exact concern — "unexamined constant reuse").
- **Reusing `BENCHMARK_MAPE = {"HDAN": ..., "PPAN": ...}`'s dict shape without an `"FX"` key, or importing it from `run_weekly_sarimax_ets.py`:** define a fresh `BENCHMARK_MAPE = {"FX": 1.72}` local to the new script.
- **Adding a Baltic-AN-style exog variant for FX:** there is no established, backtest-validated exogenous driver for FX in this dataset/scope (unlike HDAN/PPAN's Baltic AN column) — introducing one would require its own causality/dedup research pass this phase doesn't have budget for; univariate SARIMAX/ETS (optionally + a sanity-check Naive baseline) is the correct scope.
- **Assuming FX weekly week-ending convention (Monday) matches HDAN/PPAN's (Friday) for any comparison or joined display:** irrelevant to this phase's univariate backtest, but do not introduce any `merge_asof`/join logic here — that's explicitly Phase 22's concern (Pitfall 4), out of scope for this backend-only backtest.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling-origin walk-forward slicing | A custom `for` loop slicing train/test windows | `walk_forward.py`'s `walk_forward_backtest()` | Explicitly flagged in the harness's own docstring as "the single most dangerous bug class in this codebase" (leakage); Phase 2 and Phase 17 both reuse it verbatim, and it already raises `LeakageError` on `min_train >= n` and asserts training-window max date < first forecast target date |
| SARIMAX order selection | A hand-tuned or eyeballed `(p,d,q)` | `select_arima_order()`'s AIC grid search over `list(itertools.product(range(3), range(2), range(3)))`, copied from Phase 17's pattern, run ONCE on the first `MIN_TRAIN_WEEKLY`-row window (not per-origin, matching Phase 17's exact usage) | Reuses the exact grid Phase 17 already validated works for this class of weekly commodity/FX series; avoids re-deriving grid bounds from scratch |
| MAPE-by-horizon rollup | Manual groupby/aggregation of forecast vs. actual | `walk_forward.py`'s `mape_by_horizon(wf_df)` | Already handles `actual==0`/NaN exclusion correctly; reused identically by Phase 2 and Phase 17 |
| Go/no-go comparison logic | Inline `if mape < 1.72: ...` scattered through report-writing code | A standalone `beats_benchmark(mape_h4, series_name)` function, factored out exactly as Phase 17 did, so it is independently unit-testable | Phase 17's own test file (`test_weekly_sarimax_ets.py`) proves this factoring is required for the "provably computed, not hardwired" test discipline this phase must also satisfy |

**Key insight:** Every piece of infrastructure this phase needs (walk-forward slicing, MAPE rollup, order selection, benchmark comparison) already exists and was already validated end-to-end by Phase 17 on a structurally similar problem (weekly-cadence univariate time series with SARIMAX/ETS candidates). The only genuinely new work is the FX-specific CSV loader (Pattern 1) and the FX-specific constants (`MIN_TRAIN_WEEKLY`, `BENCHMARK_MAPE`) — everything else is reuse-by-import, not reimplementation.

## Common Pitfalls

### Pitfall A: Benchmark figure transcription error
**What goes wrong:** A builder trusts CONTEXT.md's "1.72%" without re-reading `forecasting.py` at implementation time, and a future edit to `MODEL_INFO["fx_rate"]` (e.g. a re-backtest that changes the monthly Naive figure) silently invalidates this phase's frozen comparison.
**Why it happens:** CONTEXT.md itself instructs re-confirmation "at implementation time," implying it could drift between research and execution.
**How to avoid:** [VERIFIED] Confirmed directly in this research pass: `app/app/forecasting.py` line 104 reads `"fx_rate": ("Naive", 1.72)`. The figure is correct as of 2026-09-01. The plan should still read this constant at execution time (a one-line `grep`/read step) rather than hard-typing "1.72" with zero verification step in the plan itself — cheap insurance against drift between research and execution.
**Warning signs:** A plan/script that hardcodes `1.72` with no code comment pointing back to `forecasting.py`'s `MODEL_INFO["fx_rate"]` as the source of truth.

### Pitfall B: FX Data.csv column-position drift
**What goes wrong:** If a future edit reorders or adds columns to `FX Data.csv`, positional `.iloc[:, 3:5]` slicing silently picks up the wrong pair.
**Why it happens:** Positional slicing is required (Pitfall 2, PITFALLS.md) because of duplicate `Date` column names, but positional slicing is inherently fragile to reordering.
**How to avoid:** The `if __name__ == "__main__":` assert-shape block in Pattern 1 (row count == 865, date range, dtype) acts as a tripwire — if the CSV shape changes, the loader fails loudly at the next manual run rather than silently misaligning. This mirrors `data_loader.py`'s own established convention exactly.
**Warning signs:** Row count != 865, or a date range that doesn't span 2010-01-04..2026-07-27, or non-Monday weekday values appearing in the loaded series.

### Pitfall C: Origin count assumption invalidated by refit cost
**What goes wrong:** With `MIN_TRAIN_WEEKLY=104` and `refit_every=1`, ~757 origins × 2 models means ~1,514 individual statsmodels `.fit()` calls; on a slow machine this could take several minutes, tempting a builder to silently reduce `min_train` or origins mid-implementation without re-documenting the change.
**Why it happens:** Phase 17's ~102-origin backtest was fast; FX's ~7.4x origin count is a genuinely different runtime profile.
**How to avoid:** If runtime proves impractical during execution, the correct lever is `refit_every` (e.g. `refit_every=4` refits every 4th origin, reusing the fitted model for interim origins — supported natively by `walk_forward_backtest`'s `refit_every` parameter), NOT silently shrinking `MIN_TRAIN_WEEKLY`. Document whichever choice is made with the same rigor as the `MIN_TRAIN_WEEKLY` comment.
**Warning signs:** A script that silently sets `min_train` much higher than 104 with no comment, or `refit_every` values that appear without justification.

### Pitfall D: Verdict test that only proves the comparison operator, not the whole pipeline
**What goes wrong:** A test that only checks `beats_benchmark(x, "FX")` in isolation (like Phase 17's `test_beats_benchmark_*` tests) proves the comparison operator works, but doesn't prove the MAPE feeding into it is actually computed from real backtest output rather than a hardcoded stand-in elsewhere in the script.
**How to avoid:** Mirror Phase 17's TWO-LAYER test discipline exactly: (1) `test_beats_benchmark_*`-style tests proving the comparison function itself is a live boundary check (true below threshold, false above, false on `None`), AND (2) a `test_build_..._records_mape_is_data_derived_not_hardcoded`-style test that runs two synthetic FX-like series (one smooth, one with an injected regime jump near the end) through the full record-building function and asserts the resulting `mape_h4` values DIFFER — proving the whole pipeline (not just the comparator) is load-bearing.
**Warning signs:** A test suite with only unit tests on `beats_benchmark()` and no end-to-end synthetic-data test on the record-building function.

## Code Examples

### Computed, non-hardwired verdict function (mirrors Phase 17 exactly)
```python
# Source: backend_research/weekly/run_weekly_sarimax_ets.py, adapted for FX's
# single-series BENCHMARK_MAPE dict.
BENCHMARK_MAPE = {"FX": 1.72}  # transcribed from app/app/forecasting.py's
                                 # MODEL_INFO["fx_rate"] == ("Naive", 1.72), verified 2026-09-01

def beats_benchmark(mape_h4, series_name: str = "FX") -> bool:
    """Live comparison against BENCHMARK_MAPE -- factored out as a standalone function
    (not inlined) so tests can exercise it directly on synthetic values in both
    directions. A missing horizon-4 MAPE never silently counts as a win."""
    return mape_h4 is not None and mape_h4 < BENCHMARK_MAPE[series_name]
```

### Synthetic-flip test proving the verdict pipeline is load-bearing
```python
# Source: adapted from backend_research/weekly/test_weekly_sarimax_ets.py's
# test_build_univariate_records_mape_is_data_derived_not_hardcoded, same technique.
import numpy as np
import pandas as pd

def _make_weekly_fx_series(n=130, seed=0, jump=False):
    idx = pd.date_range("2020-01-06", periods=n, freq="7D")  # Mondays
    rng = np.random.default_rng(seed)
    values = rng.normal(0.5, 8.0, n).cumsum() + 3400.0  # FX-scale synthetic values
    if jump:
        values[-15:] += 300.0
    return pd.Series(values, index=idx)

def test_build_univariate_records_mape_is_data_derived_not_hardcoded():
    y_smooth = _make_weekly_fx_series(n=130, seed=4, jump=False)
    y_jump = _make_weekly_fx_series(n=130, seed=4, jump=True)

    records_smooth = build_univariate_records("FX", y_smooth)
    records_jump = build_univariate_records("FX", y_jump)

    sarimax_smooth = next(r for r in records_smooth if r["family"] == "sarimax")
    sarimax_jump = next(r for r in records_jump if r["family"] == "sarimax")

    assert sarimax_smooth["mape_h4"] is not None
    assert sarimax_jump["mape_h4"] is not None
    assert sarimax_smooth["mape_h4"] != sarimax_jump["mape_h4"]

def test_beats_benchmark_true_below_threshold():
    assert beats_benchmark(BENCHMARK_MAPE["FX"] - 0.1, "FX") is True

def test_beats_benchmark_false_above_threshold():
    assert beats_benchmark(BENCHMARK_MAPE["FX"] + 0.1, "FX") is False

def test_beats_benchmark_false_when_none():
    assert beats_benchmark(None, "FX") is False
```
Note: for this synthetic test, use `n=130` (well above `MIN_TRAIN_WEEKLY=104` + `HORIZON_WEEKLY=5`) so the record-building function's internals (order selection, backtest) actually execute against realistic-length input, mirroring Phase 17's own test parameterization choice.

### Results JSON shape (mirrors `weekly_sarimax_ets.json`'s field conventions, single-series)
```python
# Each record (per candidate model) should carry the same field set Phase 17's
# records used, so any future shared tooling (e.g. a report aggregator) can treat
# weekly_fx.json and weekly_sarimax_ets.json uniformly:
{
    "series": "FX",
    "model": "SARIMAX(p, d, q)",       # or "ETS-HoltDamped"
    "family": "sarimax",                 # or "ets"
    "driver_variant": "univariate",      # no exog variant this phase
    "mape_h4": 1.55,                     # or None if h=4 unreachable
    "mape_h5": 1.71,
    "benchmark_mape": 1.72,
    "beats_benchmark_h4": True,
    "n_origins": 757,
    "failed_origins": 0,
    "min_train": 104,
    "horizon": 5,
    "notes": "order selected by AIC=... on first 104-obs window, seasonal=None",
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| N/A — no prior FX weekly backtest exists | This phase establishes the first FX weekly backtest, following Phase 17's already-current methodology | This phase (Phase 20, 2026-09) | Nothing to migrate away from; this is greenfield within an established methodology, not a replacement of an older approach |

**Deprecated/outdated:** None applicable — statsmodels 0.14.6's SARIMAX/ExponentialSmoothing APIs used here are the same current-stable APIs Phase 17 already used and this project is pinned to (per CLAUDE.md's explicit warning to avoid the unreleased "0.15.0 devel" docs branch).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `MIN_TRAIN_WEEKLY=104` (2 years) is sufficient for stable SARIMAX/ETS convergence on FX's weekly series, based on the reasoning that FX's smoother trend needs no more burn-in than HDAN/PPAN needed | Architecture Pattern 3 | LOW-MEDIUM — if SARIMAX/ETS prove unstable or produce a high `failed_origins` count at low training-window sizes during actual execution, the plan should raise `MIN_TRAIN_WEEKLY` and re-document; this is empirically checkable via `wf.attrs["failed_origins"]` at execution time, so the risk is self-correcting, not silent |
| A2 | No FX-specific exogenous driver exists in this project's dataset/scope, so a univariate-only candidate set (no exog variant) is appropriate | Anti-Patterns / Don't Hand-Roll | LOW — WKUI-02's success criteria only mandate SARIMAX + ETS, no exog requirement; if a builder later wants to test e.g. Brent/Urals as an FX exog driver, that would need its own causality-screen research pass (out of scope this phase) |
| A3 | `refit_every=1` (matching Phase 17) remains practical for FX's ~7.4x origin count in the actual execution environment | Pitfall C | LOW-MEDIUM — purely a runtime/performance risk, not a correctness risk; if wrong, the fallback (`refit_every=4`) is well-understood and doesn't change the methodology, only the wall-clock cost |

## Open Questions

1. **Exact winning SARIMAX order and whether SARIMAX or ETS wins for FX**
   - What we know: The methodology, wrapper classes, and constants to use.
   - What's unclear: FX's actual backtested MAPE and which model wins — genuinely unresolved until the script runs (SUMMARY.md itself flags this as "FX's model choice is genuinely open, unlike HDAN/PPAN").
   - Recommendation: This is Phase 20's own research output, not something to pre-resolve here — the plan should run the script and let the computed verdict stand, including accepting "no-go" as fully valid per WKUI-02's explicit acceptance criteria.

2. **Whether SARIMAX/ETS can plausibly beat a 1.72% MAPE Naive/AR(1) benchmark at all**
   - What we know: 1.72% is an unusually tight monthly benchmark (much tighter than HDAN/PPAN's 9.49%/10.08%), because currency rates are notoriously close to a random walk and a Naive model is a very strong baseline for FX specifically (a well-known result in FX forecasting literature generally — [ASSUMED], not verified via a citation in this research pass, but consistent with why the existing monthly FX model is already "Naive").
   - What's unclear: Whether horizon-matching to a weekly h=4/h=5 rollup changes this dynamic enough for SARIMAX/ETS to compete — untested until the backtest runs.
   - Recommendation: Proceed with the backtest as scoped; a no-go here would be consistent with well-established FX-forecasting difficulty and should not be treated as a script/methodology failure.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | CSV parsing, Series/DataFrame ops | Yes (per task brief; system python3) | 2.2.3 | — |
| statsmodels | SARIMAX / ExponentialSmoothing | Yes (per task brief) | 0.14.6 | — |
| scipy | statsmodels dependency | Yes (per task brief) | — | — |
| scikit-learn | Not required this phase (no ML baseline requested) | Yes (per task brief, unused) | 1.7.2 | — |
| arch | Not required this phase (GARCH not in scope) | Yes (per task brief, unused) | 8.0.0 | — |
| pytest | Verdict-computation proof tests | Assumed available (used by `test_weekly_sarimax_ets.py` already in this repo) | — | — |

**Missing dependencies with no fallback:** None — all required packages already installed and verified per the task brief's environment confirmation.

**Missing dependencies with fallback:** None.

## Validation Architecture

> `.planning/config.json` was not found/read in this research pass via direct file access; treating `workflow.nyquist_validation` as enabled (absent = enabled) per the default rule.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (house style already established by `backend_research/weekly/test_weekly_sarimax_ets.py` — plain asserts, no fixtures framework) |
| Config file | none detected in `backend_research/` (matches Phase 17's precedent — no `conftest.py`/`pytest.ini` found alongside `test_weekly_sarimax_ets.py`) |
| Quick run command | `python3 -m pytest backend_research/weekly/test_fx_weekly_backtest.py -x` |
| Full suite command | `python3 -m pytest backend_research/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WKUI-02 | FX weekly CSV loader produces 865-row, correctly-dated, correctly-typed series | unit | `pytest backend_research/weekly/test_fx_weekly_backtest.py::test_load_fx_weekly_shape -x` | ❌ Wave 0 |
| WKUI-02 | SARIMAX/ETS wrapper classes forecast clean, non-NaN values | unit | `pytest backend_research/weekly/test_fx_weekly_backtest.py::test_sarimax_wrapper_forecasts_clean_values -x` | ❌ Wave 0 |
| WKUI-02 | MAPE is derived from real backtest output, not hardcoded (synthetic-flip test) | unit | `pytest backend_research/weekly/test_fx_weekly_backtest.py::test_build_univariate_records_mape_is_data_derived_not_hardcoded -x` | ❌ Wave 0 |
| WKUI-02 | `beats_benchmark()` boundary behavior (true/false/None) | unit | `pytest backend_research/weekly/test_fx_weekly_backtest.py::test_beats_benchmark_* -x` | ❌ Wave 0 |
| WKUI-02 | Frozen `results/weekly_fx.json` has required field shape after `run_all()` | unit | `pytest backend_research/weekly/test_fx_weekly_backtest.py::test_frozen_results_json_has_required_shape -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend_research/weekly/test_fx_weekly_backtest.py -x`
- **Per wave merge:** `pytest backend_research/ -x` (full backend_research suite, including Phase 17's existing tests, to confirm no cross-contamination of `run_weekly_sarimax_ets.py`'s frozen output)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend_research/weekly/run_fx_weekly_backtest.py` — the script itself (loader, wrappers, record-building, `beats_benchmark`, `write_report`)
- [ ] `backend_research/weekly/test_fx_weekly_backtest.py` — all tests listed above
- [ ] No new framework install needed — pytest already used identically by `test_weekly_sarimax_ets.py`

## Security Domain

> Not applicable — this phase is a local, offline research script with no network I/O, no user input, no authentication/authorization surface, and no data leaving the local filesystem. No ASVS categories apply. This section is intentionally minimal per the phase's actual risk profile (a backend-only, single-process, single-user research script operating on a static local CSV).

## Sources

### Primary (HIGH confidence)
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\app\app\forecasting.py` (lines 90-106) — direct read, confirms `MODEL_INFO["fx_rate"] == ("Naive", 1.72)`
- `FX Data.csv` (repo root) — direct `python3`/pandas inspection this session: columns, shape (5912 total rows, weekly slice 865 rows), date range 2010-01-04..2026-07-27, all-Monday weekday, comma-formatted value strings
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\walk_forward.py` — direct read, full harness source (expanding-window behavior, `LeakageError` guards, `mape_by_horizon`, `single_holdout_mape`)
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\weekly\run_weekly_sarimax_ets.py` — direct read, exact wrapper classes, `select_arima_order`, `beats_benchmark`, record-building, and report-writing patterns mirrored in this research
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\weekly\test_weekly_sarimax_ets.py` — direct read, exact test-house-style and synthetic-flip technique mirrored
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\REPORT-WEEKLY.md` — direct read, horizon-matching methodology and report structure precedent
- `C:\Users\Dulguun.U\Documents\Projects\prediction-dashboard\backend_research\data_loader.py` — direct read, established CSV-cleanup idiom (`.astype(str).str.replace(',', '').astype(float)`) and `merge_asof` tolerance-join precedent (not needed this phase, but confirms house convention)
- `.planning/phases/20-fx-weekly-backtest/20-CONTEXT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/research/PITFALLS.md`, `.planning/research/SUMMARY.md` — direct reads, all locked decisions and prior milestone-level research incorporated verbatim above
- `CLAUDE.md` project file — direct read via system context, confirms tech-stack constraints and "no un-backtested model ships" discipline

### Secondary (MEDIUM confidence)
None used — all findings this phase are grounded directly in this repo's own code/data, not external web sources.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all versions confirmed installed per task brief and matching CLAUDE.md's pinned stack
- Architecture: HIGH — every pattern is a direct, verified read of existing repo code (Phase 17's script, harness, loaders) plus direct live inspection of `FX Data.csv`
- Pitfalls: HIGH — grounded in PITFALLS.md's already-thorough prior research plus this session's own direct code/data verification
- MIN_TRAIN_WEEKLY recommendation: MEDIUM — the origin-count arithmetic and expanding-window mechanics are HIGH confidence (verified by reading `walk_forward.py`'s actual loop logic), but the underlying claim "FX needs no more burn-in than HDAN/PPAN" is a reasoned inference, not empirically tested in this research pass — flagged as Assumption A1, self-correcting via `failed_origins` at execution time

**Research date:** 2026-09-01
**Valid until:** 30 days (stable methodology/stack; the only volatile input, `FX Data.csv`'s row count/date range, is checked by the loader's own assert-shape tripwire, so staleness is self-detecting)
