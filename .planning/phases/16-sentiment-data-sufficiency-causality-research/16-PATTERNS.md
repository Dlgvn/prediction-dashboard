# Phase 16: Sentiment Data Sufficiency & Causality Research - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** 5 new files (0 modified — this phase makes zero edits to existing files)
**Analogs found:** 5 / 5

This phase is a pure `backend_research/` research artifact — no `app/` code changes. Every
new file either directly imports from, or structurally mirrors, three existing
`backend_research/` modules: `causality_screen.py`, `db_loader.py`, and `walk_forward.py`.

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|-----------------|---------------|
| `backend_research/sentiment/sentiment_data_loader.py` | service (data loader) | file-I/O -> transform (CSV -> monthly DataFrame) | `backend_research/db_loader.py` | exact (same role: raw source -> monthly PeriodIndex DataFrame) |
| `backend_research/sentiment/run_sentiment_causality_screen.py` | service (batch screen / entry point) | batch (nested-loop statistical sweep -> frozen JSON) | `backend_research/causality_screen.py` (`run_granger_sweep`) | exact (same role, same data flow, this phase's own research explicitly models the loop on it) |
| `backend_research/sentiment/test_sentiment_data_loader.py` (or `test_sentiment_causality_screen.py`) | test | transform / event-driven (leakage-guard assertion) | `backend_research/test_walk_forward.py` | exact (same role: unit test of an offline research module, incl. a `pytest.raises(LeakageError)` case) |
| `backend_research/results/sentiment_causality_screen.json` | config/data artifact (frozen output) | batch (write-once) | `backend_research/results/causality_screen.json` | exact (identical shape: list of `{target, predictor, lag, F, p, n, tier, note?}` records) |
| `backend_research/REPORT-SENTIMENT.md` | report (generated/hand-written doc) | transform (JSON -> human-readable Markdown) | `backend_research/REPORT-PHASE2.md` ("Predictor screen (D-04/D-05)" section) | role-match (same repo convention: per-target table of predictor/lag/p-value/tier) |

**Files NOT created/modified this phase (explicitly out of scope, confirmed by CONTEXT.md):**
`causality_screen.py`, `db_loader.py`, `walk_forward.py` are all **imported from, unmodified**.
Nothing under `app/` is touched.

## Pattern Assignments

### `backend_research/sentiment/sentiment_data_loader.py` (service, file-I/O -> transform)

**Analog:** `backend_research/db_loader.py` (81 lines, read in full)

**Imports pattern** (`db_loader.py` lines 1-15):
```python
"""SQLite-backed data loader for Phase 2 research scripts.
...
"""

from pathlib import Path

import pandas as pd
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "app" / "reflex.db"

TARGETS = ["hdan", "ppan", "diesel_usd_ton", "fx_rate"]
```
Adapt for the new file (which lives one directory deeper, in `sentiment/`): use
`Path(__file__).resolve().parent.parent.parent / "archive"` to reach `archive/*.csv`
(three `.parent` calls, not two, since `sentiment_data_loader.py` is nested one level
below `db_loader.py`). Confirmed by RESEARCH.md's own Code Examples section (already
verified this path arithmetic this session).

**Core loader pattern — monthly PeriodIndex output, matching `load_price_history()`'s
contract exactly** (`db_loader.py` lines 35-68):
```python
def load_price_history() -> pd.DataFrame:
    """Load the PriceRow table as a wide, month-indexed DataFrame.

    Returns a DataFrame indexed by a monthly pandas PeriodIndex (ascending, no
    duplicates), with TARGETS + PREDICTORS columns cast to float64 (SQL NULL ->
    NaN).
    """
    columns = ["date"] + TARGETS + PREDICTORS
    select_list = ", ".join(columns)
    query = f"SELECT {select_list} FROM pricerow ORDER BY date"

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    df.index = pd.PeriodIndex(pd.to_datetime(df["date"]), freq="M")
    df = df.drop(columns=["date"])

    if not df.index.is_monotonic_increasing:
        raise ValueError(
            "load_price_history: index is not monotonically increasing — "
            f"dates: {list(df.index)}"
        )
    if df.index.has_duplicates:
        dupes = df.index[df.index.duplicated()].tolist()
        raise ValueError(f"load_price_history: duplicate month index values: {dupes}")

    for col in TARGETS + PREDICTORS:
        df[col] = df[col].astype("float64")

    return df
```
**What to copy structurally:** the docstring contract ("Returns a DataFrame indexed by a
monthly pandas PeriodIndex ... "), the monotonic/no-duplicate-index assertions (raise
`ValueError`, don't silently coerce), and the "no `if __name__` side effects beyond a
diagnostic print" convention (see lines 76-81 below). `load_sentiment_monthly()` should
produce an index of the same `PeriodIndex(freq="M")` type so it merges cleanly onto
`load_price_history()`'s index without a manual `.asfreq()`/reindex step.

**Read-only / defensive-io convention** (`db_loader.py` lines 45-51): the read-only SQLite
URI (`file:{DB_PATH}?mode=ro`) is specific to the SQLite loader and does not apply to CSV
reads, but the surrounding discipline — open, use, always close in a `finally` (or here,
`pd.read_csv` which has no explicit close step needed) — is the pattern to preserve:
fail loudly on shape problems rather than silently returning a malformed frame.

**Diagnostic `__main__` block pattern** (`db_loader.py` lines 76-81):
```python
if __name__ == "__main__":
    frame = load_price_history()
    print(f"shape: {frame.shape}")
    print(f"index min/max: {frame.index.min()} .. {frame.index.max()}")
    print("non-null counts per column:")
    print(frame.count())
```
Copy this shape for `sentiment_data_loader.py`'s own `__main__` block — print
`monthly.shape`, index min/max, and per-column non-null counts so a human running the
script directly gets the same fast sanity-check every other loader in this codebase
provides.

**Simple transform-function pattern** (`db_loader.py` lines 71-73, `pct_change_frame`):
```python
def pct_change_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Percent-change transform (x100), first row dropped (NaN from pct_change)."""
    return (df.pct_change() * 100).iloc[1:]
```
**Do NOT reuse this function on sentiment columns** (RESEARCH.md Pattern 2 / Pitfall 2 —
sentiment predictors are levels, not pct-changed; applying `pct_change_frame()` to a
bounded `[-1,1]` score produces `inf`/sign-flip artifacts). `pct_change_frame` is only
ever called on the target side (`pct_change_frame(load_price_history())`), never on the
sentiment loader's output — this is the one place this phase deviates from
"just reuse the existing transform," and it must be a deliberate, documented deviation
(flag in `REPORT-SENTIMENT.md`, per RESEARCH.md's Anti-Patterns section).

---

### `backend_research/sentiment/run_sentiment_causality_screen.py` (service, batch)

**Analog:** `backend_research/causality_screen.py` (286 lines, read in full)

**Import pattern — direct reuse, not reimplementation** (this is the load-bearing
pattern for the entire phase; D-01/D-05/canonical_refs require importing these three
names verbatim, not copying their logic):
```python
# causality_screen.py itself imports flat (works because CWD == backend_research/ at
# script-invocation time):
from db_loader import PREDICTORS, TARGETS, load_price_history, pct_change_frame
```
The new nested file needs a `sys.path` shim before it can do the equivalent
(`backend_research/causality_screen.py`'s own import line 32 assumes CWD=backend_research/,
which breaks one level deeper — this is a real, previously-reproduced gotcha, not
speculative):
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend_research/
from causality_screen import granger_ftest, _tier, MIN_GRANGER_N
from db_loader import TARGETS, load_price_history, pct_change_frame
from sentiment_data_loader import load_sentiment_monthly
```

**Core F-test to import verbatim** (`causality_screen.py` lines 45-58):
```python
def granger_ftest(y: pd.Series, predictor: pd.Series, lag: int) -> tuple[float, float, int]:
    """Incremental F-test Granger causality (ported verbatim from causality_matrix.py).

    y, predictor: pandas Series sharing an index (percent-change / stationary data).
    Returns (F, p, n).
    """
    d = pd.DataFrame({"y": y, "y_lag1": y.shift(1), "x_lag": predictor.shift(lag)}).dropna()
    Xb = sm.add_constant(d[["y_lag1"]])
    Xf = sm.add_constant(d[["y_lag1", "x_lag"]])
    mb, mf = sm.OLS(d["y"], Xb).fit(), sm.OLS(d["y"], Xf).fit()
    n, k = len(d), Xf.shape[1]
    F = ((mb.ssr - mf.ssr) / 1) / (mf.ssr / (n - k))
    p = 1 - fdist.cdf(F, 1, n - k)
    return float(F), float(p), int(n)
```

**Tiering + floor to import verbatim** (`causality_screen.py` lines 38, 61-68):
```python
MIN_GRANGER_N = 24

def _tier(p: float, n: int) -> str:
    if n < MIN_GRANGER_N:
        return "ns"
    if p < 0.05:
        return "p05"
    if p < 0.10:
        return "p10"
    return "ns"
```

**Core sweep loop to structurally mirror (not import — this loop itself is new code,
but its shape/skip-branch/JSON-write pattern must match exactly)** (`causality_screen.py`
lines 83-139, `run_granger_sweep`):
```python
def run_granger_sweep() -> list[dict]:
    """Granger F-test across every target x predictor x lag(1-3) combo. No pre-filtering."""
    pct = pct_change_frame(load_price_history())
    results: list[dict] = []

    for target, predictor in _all_pairs():
        y = pct[target]
        x = pct[predictor]
        for lag in (1, 2, 3):
            d = pd.DataFrame({"y": y, "x": x.shift(lag)}).dropna()
            n_overlap = len(d)
            if n_overlap < MIN_GRANGER_N:
                record = {
                    "target": target, "predictor": predictor, "lag": lag,
                    "F": None, "p": None, "n": n_overlap,
                    "tier": "ns", "note": "insufficient overlap",
                }
                results.append(record)
                continue

            F, p, n = granger_ftest(y, x, lag)
            record = {
                "target": target, "predictor": predictor, "lag": lag,
                "F": round(F, 4), "p": round(p, 4), "n": n,
                "tier": _tier(p, n),
            }
            results.append(record)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(CAUSALITY_JSON, "w") as f:
        json.dump(results, f, indent=2)

    _print_granger_summary(results)
    return results
```
**Copy exactly for the new `run_sentiment_causality_screen()`**, substituting the
`target x predictor` pair generator (`_all_pairs()`, lines 71-80 — for sentiment, this
becomes `TARGETS x SENTIMENT_PREDICTORS`, a flat nested loop, not a helper function since
there's no "other targets as cross-predictors" case here per D-08's fixed 5-column set) and
substituting `x = sentiment[predictor]` (a LEVEL, not `pct[predictor]`) for the predictor
side only — the record dict shape (`target/predictor/lag/F/p/n/tier/note`) and the
`n < MIN_GRANGER_N` skip-with-`note` branch (D-07) must match field-for-field so
`REPORT-SENTIMENT.md`'s generation logic can reuse the same table-building approach as
`REPORT-PHASE2.md`.

**Results dir / JSON path convention** (`causality_screen.py` lines 34-36):
```python
RESULTS_DIR = Path(__file__).resolve().parent / "results"
CAUSALITY_JSON = RESULTS_DIR / "causality_screen.json"
```
For the sentiment screen (nested in `sentiment/`), point at the *existing flat*
`backend_research/results/` directory, not a new nested one — confirmed by directory
listing (`backend_research/results/` already holds `causality_screen.json`,
`cointegration.json`, `garch_volatility.json`, etc. all flat) and by CONTEXT.md's explicit
"mirroring causality_screen.json's shape" instruction:
```python
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"  # backend_research/results/
SENTIMENT_JSON = RESULTS_DIR / "sentiment_causality_screen.json"
```

**Summary-printing pattern to mirror** (`causality_screen.py` lines 142-156,
`_print_granger_summary`) — same per-target loop, filtering `tier in ("p05","p10")`,
sorted by p ascending; reuse this shape for a `_print_sentiment_summary`.

**`__main__` entry-point convention** (`causality_screen.py` lines 282-286):
```python
if __name__ == "__main__":
    run_granger_sweep()
    coint_results = run_cointegration_sweep()
    vecm_candidates = _compute_vecm_candidates(coint_results)
    _print_vecm_summary(vecm_candidates)
```
The new script's `__main__` block should be the single-call equivalent:
`run_sentiment_causality_screen()` (no cointegration/VECM step — D-08's scope is Granger
only, per CONTEXT.md's decisions; do not add a cointegration sweep for sentiment, it was
not requested and RESEARCH.md's Standard Stack table explicitly excludes any second test
beyond the Granger F-test per D-01).

**Best-lag-per-predictor pattern** (`causality_screen.py` lines 159-187, `shortlist_for`)
— referenced by D-02 ("A predictor qualifies at its single best (lowest-p) lag") as the
existing precedent to match. Not necessarily needed as a *function* in the new module
(the sentiment screen's own report-writing step can do this reduction inline), but the
dedup logic to mirror if a `shortlist_for`-equivalent helper is written:
```python
by_predictor: dict[str, dict] = {}
for r in records:
    if r["target"] != target:
        continue
    if r["p"] is None:
        continue
    ...
    current = by_predictor.get(r["predictor"])
    if current is None or r["p"] < current["p"]:
        by_predictor[r["predictor"]] = r
```

---

### `backend_research/sentiment/test_sentiment_data_loader.py` (test)

**Analog:** `backend_research/test_walk_forward.py` (`LeakageError` test case, lines 118-127)

**Leakage-guard test pattern to mirror** (`test_walk_forward.py` lines 118-127):
```python
def test_leakage_guard_raises():
    series = _make_series(10)

    def fit_fn(train_series, train_exog):
        return _ConstantForecaster(last_value=0.0)

    with pytest.raises(LeakageError):
        walk_forward_backtest(
            series, exog=None, fit_fn=fit_fn, min_train=20, horizon=12, step=1
        )
```
**Applies directly to RESEARCH.md's own guidance** (Pattern 3 / Common Pitfalls #3):
"write a unit test asserting it [`LeakageError`] *would* fire if the shift were removed,
mirroring `test_walk_forward.py::test_leakage_guard_raises`'s existing pattern." Copy this
structure: construct a case where the sentiment-month-vs-target-month boundary is
violated (e.g., call the merge helper with `lag=0` or with the shift step bypassed) and
assert `pytest.raises(LeakageError)`.

**Import pattern** (`test_walk_forward.py` lines 1-16, inferred from grep):
```python
from walk_forward import (
    ...
    LeakageError,
    ...
)
```
The new test file (in `sentiment/`) needs the same `sys.path` shim as
`run_sentiment_causality_screen.py` before `from walk_forward import LeakageError` will
resolve, since `walk_forward.py` lives in `backend_research/`, not `backend_research/sentiment/`.

**Also add a Pitfall-2 regression test** (RESEARCH.md's own explicit ask): "Add an
explicit unit test asserting the sentiment loader never emits `inf`." No direct existing
analog for this specific assertion; write as a small `assert not np.isinf(...).any()`
check on `load_sentiment_monthly()`'s output columns, following `test_walk_forward.py`'s
general house style (plain `assert`, no custom test framework beyond `pytest`).

---

### `backend_research/results/sentiment_causality_screen.json` (data artifact)

**Analog:** `backend_research/results/causality_screen.json` (existing frozen output of
`run_granger_sweep()`)

**Shape to mirror exactly** — a flat JSON array of records, one per
`(target, predictor, lag)` combination, written via the same `json.dump(results, f,
indent=2)` call shown in the `run_granger_sweep` excerpt above. Each record is one of two
shapes depending on whether `n >= MIN_GRANGER_N`:
```json
{"target": "hdan", "predictor": "weighted_compound", "lag": 1, "F": 2.31, "p": 0.14, "n": 30, "tier": "ns"}
```
or, when D-07's skip branch fires (expected for most/all sentiment records per RESEARCH.md's
computed N-ceiling of 14-20, all below `MIN_GRANGER_N=24`):
```json
{"target": "hdan", "predictor": "weighted_compound", "lag": 1, "F": null, "p": null, "n": 14, "tier": "ns", "note": "insufficient overlap"}
```

---

### `backend_research/REPORT-SENTIMENT.md` (report)

**Analog:** `backend_research/REPORT-PHASE2.md`, "Predictor screen (D-04/D-05)" section
(lines 135-151, read directly)

**Per-target table format to mirror:**
```markdown
### HDAN

| Predictor | Lag | p-value | Tier |
|---|---|---|---|
| ppan | 1 | 0.0030 | p05 |
| urea_china | 1 | 0.0191 | p05 |
```
Adapt column set to match D-04's go/no-go requirement: add an explicit `N` column (the
effective monthly sample size — RESEARCH.md's SENT-01 requirement and Pitfall 1 both
require this be stated per record, not just the raw CSV row count) and a `Note` column for
the `"insufficient overlap"` skip case:
```markdown
### HDAN — Go/No-Go: NO-GO (insufficient data)

**Max possible N before per-predictor dropna: 14** (below MIN_GRANGER_N=24)

| Predictor | Lag | N | p-value | Tier | Note |
|---|---|---|---|---|---|
| weighted_compound | 1 | 14 | — | ns | insufficient overlap |
```

**Top-of-report framing to mirror** (`REPORT-PHASE2.md` lines 1-12): a one-paragraph
provenance note (what script generated this, from which `results/*.json`) followed by a
"Winners at a glance" / go-no-go-at-a-glance summary table before the per-series detail
sections — for `REPORT-SENTIMENT.md` this becomes a per-series go/no-go summary table
(HDAN/PPAN/Diesel-USD/FX rate x go-or-no-go) up top, matching D-04's "reported per series"
requirement, before the detailed per-target predictor tables below it.

---

## Shared Patterns

### Granger F-test + tiering + floor (the phase's central reuse requirement)
**Source:** `backend_research/causality_screen.py` lines 38, 45-58, 61-68
(`MIN_GRANGER_N`, `granger_ftest`, `_tier`)
**Apply to:** `run_sentiment_causality_screen.py` — imported directly, never reimplemented,
per D-01/D-05 and the project's "Don't Hand-Roll" discipline (already cross-checked
against `statsmodels.tsa.stattools.grangercausalitytests` in `causality_screen.py`'s own
`CROSSCHECK_PAIR` logic, lines 42, 119-130 — no need to re-verify a reimplementation).

### Monthly PeriodIndex data contract
**Source:** `backend_research/db_loader.py` lines 35-68 (`load_price_history`)
**Apply to:** `sentiment_data_loader.py`'s `load_sentiment_monthly()` — must return a
`PeriodIndex(freq="M")`-indexed DataFrame so it merges onto `pct_change_frame(load_price_history())`'s
index without a reindex step, and should apply the same "raise `ValueError` on
non-monotonic/duplicate index" defensive checks db_loader.py uses.

### `sys.path` shim for nested-subfolder flat imports
**Source:** verified this session (RESEARCH.md Pitfall 4); not present in any existing
file (both `causality_screen.py` and `db_loader.py` sit flat in `backend_research/` and
never needed this)
**Apply to:** both `sentiment_data_loader.py` and `run_sentiment_causality_screen.py` (and
the test file), since they are the first `backend_research/` scripts placed one directory
deeper than their imports' targets:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

### Flat `results/` directory convention (no nested subfolder)
**Source:** directory listing of `backend_research/results/` (14 existing flat JSON
files, one per script) + CONTEXT.md's explicit discretion note
**Apply to:** `sentiment_causality_screen.json` — write to
`backend_research/results/sentiment_causality_screen.json`, not a nested
`backend_research/sentiment/results/` path, even though the *producing script* lives in
the nested `sentiment/` subfolder.

### LeakageError as the leakage-guard exception
**Source:** `backend_research/walk_forward.py` lines 16-17
```python
class LeakageError(AssertionError):
    """Raised when the harness detects (or could not prevent) train/forecast leakage."""
```
**Apply to:** the daily-to-monthly sentiment merge step in `sentiment_data_loader.py` (or
the merge point inside `run_sentiment_causality_screen.py`) — import this class rather
than defining a parallel `TimezoneLeakageError`, per CONTEXT.md's explicit Claude's-
Discretion instruction to extend the existing class.

## No Analog Found

None. Every new file this phase produces has a direct, close analog already read and
excerpted above (`db_loader.py`, `causality_screen.py`, `walk_forward.py`/
`test_walk_forward.py`, `causality_screen.json`, `REPORT-PHASE2.md`). This phase is
explicitly scoped (per CONTEXT.md) as an extension of an existing, working pipeline, not
new architecture — the planner should not need to fall back to RESEARCH.md's illustrative
code for anything covered above; RESEARCH.md's own Code Examples section was itself
derived by inspecting these same three files this session and is consistent with the
excerpts here.

## Metadata

**Analog search scope:** `backend_research/` (all `.py` files, `results/*.json`,
`REPORT*.md`); `archive/*.csv` and `archive/README.md` inspected as data-source references
(not code analogs). No search of `app/` — confirmed out of scope by CONTEXT.md's phase
boundary.
**Files scanned (read in full or via targeted grep):** `causality_screen.py` (286 lines,
full read), `db_loader.py` (81 lines, full read), `walk_forward.py` (144 lines, full read),
`test_walk_forward.py` (leakage-test section, lines 110-139), `REPORT-PHASE2.md`
(predictor-screen section, lines 1-40, 135-174), `archive/README.md` (methodology header),
`archive/news_sentiment_daily.csv`, `archive/news_sentiment_raw.csv`,
`archive/ml_features.csv` (headers + sample rows)
**Pattern extraction date:** 2026-08-31
