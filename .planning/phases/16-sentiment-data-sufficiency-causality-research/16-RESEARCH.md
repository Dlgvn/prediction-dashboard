# Phase 16: Sentiment Data Sufficiency & Causality Research - Research

**Researched:** 2026-08-31
**Domain:** Offline statistical research (Granger-causality screening) extending an existing `backend_research/` backtest harness — no new stack, no `app/` changes
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Significance bar**
- **D-01:** Use the same significance tiers as the existing `causality_screen.py`
  pipeline (p<0.05 = "p05", p<0.10 = "p10") — no stricter bar for sentiment predictors
  than for any other candidate predictor already in the codebase. Treat sentiment the
  same as any other predictor; let the small-N floor (D-04) do the work of filtering
  out spurious hits, not an inflated significance threshold.
- **D-02:** A predictor qualifies at its single best (lowest-p) lag — do not require the
  signal to hold across multiple lags (1/2/3). Matches `shortlist_for()`'s existing
  best-lag-per-predictor pattern.
- **D-03:** No directional/sign sanity check required. A qualifying p-value is
  sufficient regardless of whether the correlation sign is economically intuitive —
  matches the existing pipeline's D-04 "no intuition-based pre-filtering" precedent;
  don't let researcher judgment act as a second filter here that isn't applied anywhere
  else in the causality screen.

**Result granularity**
- **D-04:** Go/no-go is reported **per series** (HDAN, PPAN, Diesel-USD, FX rate) —
  not one global answer. A go for one series (e.g. Diesel-USD via a macro-risk-proxy
  predictor) does not require or imply a go for the others. Diesel-MNT is explicitly
  out of scope for its own go/no-go row — it's a derived series (Diesel-USD × FX ×
  markup) per `forecasting.py`'s existing pattern; its eventual sentiment-adjustment
  status (if any) follows from Diesel-USD's and FX's results, not a separate test.

**Small-N floor**
- **D-05:** Reuse `causality_screen.py`'s existing `MIN_GRANGER_N = 24` (monthly
  observations) as the floor for sentiment predictors too — one consistent bar across
  the whole pipeline, not a sentiment-specific number.
- **D-06:** When resampling daily sentiment to monthly, months with zero articles are
  **dropped** (excluded), not forward-filled or interpolated. This shrinks the
  effective N further but reflects the data's real sparsity honestly rather than
  manufacturing continuity that risks staleness/leakage (per PITFALLS.md finding #3).
- **D-07:** If a resampled monthly sentiment series doesn't clear `MIN_GRANGER_N` for a
  given target, that target gets an **immediate no-go** for that predictor — do not run
  the significance test at all. Matches `causality_screen.py`'s own existing
  "insufficient overlap" skip behavior. Given the archive's ~163 sentiment-days spread
  over ~6 years (91% clustered in the last ~5 months), this is expected to be the
  outcome for most or all target/predictor pairs — plan for the report to legitimately
  say "insufficient data" rather than forcing a p-value out of a degenerate sample.

**Candidate predictor set**
- **D-08:** Test three feature families as candidate predictors, screened via the same
  no-pre-filtering discipline as `causality_screen.py`'s existing 12 predictors:
  1. Raw/weighted sentiment score (`weighted_compound`)
  2. Sentiment trend/momentum (`sent_ema3`, `sent_ema10`, `sent_momentum`)
  3. VIX-derived macro risk regime (`vix_regime`) — kept as a distinct candidate
     because it's a plausible macro-risk proxy for Diesel (Brent-linked) and FX (EM
     risk appetite) independent of literal headline sentiment about these commodities
- **D-09:** Exclude columns built for the archive's original equity-forecasting
  purpose — `rolling_corr_60d` (correlation vs. SPY) and the `spy/qqq/dia_return_next1d`
  ML target columns. These are diagnostic/target artifacts of the dataset's original
  scope, not defensible candidate inputs for HDAN/PPAN/Diesel/FX.

### Claude's Discretion

- Exact resampling method for turning daily sentiment into a monthly value (e.g. mean
  vs. median of the non-dropped daily observations within a month) — not discussed;
  pick the standard approach (mean) and note the choice in the phase's research output.
- Report file naming/location and JSON result-artifact structure — follow the existing
  `backend_research/` convention (a new `REPORT-SENTIMENT.md` and
  `results/sentiment_causality_screen.json`, mirroring `causality_screen.json`'s shape)
  rather than inventing a new structure.
- Timezone handling for the daily-to-monthly resample (UTC `published_at` vs. Mongolia
  local, UTC+8) — not explicitly discussed as a user decision; implement per
  PITFALLS.md's guidance (extend `walk_forward.py`'s existing `LeakageError` guard
  rather than a parallel merge path) since this is a correctness detail, not a product
  choice.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. (Weekly-mode UI, sentiment UI
differentiators, and live news API integration were already scoped out of this
milestone during requirements definition; not re-raised in the Phase 16 discussion.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| SENT-01 | A causality/correlation screen runs against the app's actual HDAN/PPAN/Diesel-USD/FX series (not equities), with the effective monthly sample size explicitly reported, before any sentiment adjustment is considered valid | Architecture Patterns 1-3 + Code Examples specify the exact screen implementation (reusing `granger_ftest`/`_tier`/`MIN_GRANGER_N` against the real `PriceRow` targets via `db_loader.py`); Common Pitfalls #1 gives the precomputed effective-N table (14/14/18/20, all below the 24 floor) that `REPORT-SENTIMENT.md` must state explicitly, not raw CSV row counts |
| SENT-02 | The sentiment backtest produces a documented, frozen go/no-go result (mirroring the project's "no un-backtested model ships" discipline) — a "no-go" is a valid, complete outcome for this requirement, not a blocker to closing it | Recommended Project Structure specifies the frozen `results/sentiment_causality_screen.json` + `backend_research/REPORT-SENTIMENT.md` deliverables; Summary explicitly frames the near-certain "no-go, insufficient sample size" outcome as complete and valid, matching D-07 |
</phase_requirements>

## Summary

This phase's actual engineering work is small and precisely scoped: extend the existing
`backend_research/causality_screen.py` pattern (`granger_ftest()` + `_tier()` +
`MIN_GRANGER_N=24`) to test three sentiment-derived predictor families
(`weighted_compound`, `sent_ema3`/`sent_ema10`/`sent_momentum`, `vix_regime`) against the
app's four real forecast targets (HDAN, PPAN, Diesel-USD, FX rate), using
`db_loader.py`'s existing monthly `PriceRow` index as the target-side data source. No new
Python dependency is needed — `pandas`, `statsmodels`, and `scipy` are already installed
in the `backend_research/` environment (verified: pandas 2.2.3, statsmodels 0.14.6, both
matching `ENV.md`'s recorded pins).

Direct inspection of the archive files and the live `reflex.db` (this session, not
assumed) produces a decisive, verifiable finding that should shape how the planner scopes
this phase: **the maximum possible effective monthly sample size, for every one of the
four targets, is below `MIN_GRANGER_N=24` before a single regression is run.**
`news_sentiment_daily.csv` has sentiment data in only 20 distinct calendar months across
its entire 2020–2026 span (163 of those daily rows cluster into just 6 of those months,
2026-03 through 2026-08 — a NewsAPI free-tier artifact). Intersecting those 20
sentiment-covered months against `PriceRow`'s actual non-null coverage per target yields a
best-case N of 14 (HDAN, PPAN), 18 (Diesel-USD), or 20 (FX rate) — all below the 24-month
floor D-05 locks in, before any `dropna()` from the lag-shift step shrinks it further. This
means D-07's "immediate no-go, do not run the significance test" branch is expected to
fire for essentially every target/predictor/lag combination the screen tests. This is not
a reason to skip building the screen — the deliverable is the *methodology* and its
*honestly reported result*, which is a legitimate, complete, and (per CONTEXT.md) expected
outcome — but the planner should not scope tasks around "tuning" the significance test, and
should expect the go/no-go report to read "no-go, insufficient sample size" for all or
nearly all target/predictor pairs.

**Primary recommendation:** Reuse `causality_screen.py`'s `granger_ftest()`, `_tier()`, and
`MIN_GRANGER_N` by direct import (not reimplementation), build a small new
`backend_research/sentiment/sentiment_data_loader.py` that produces a monthly-indexed
sentiment predictor DataFrame with an explicit UTC→Mongolia-local (+8h) timezone
correction sourced from `news_sentiment_raw.csv`'s `published_at` column (not the
pre-aggregated `news_sentiment_daily.csv`'s date-only column, which cannot be
timezone-corrected after the fact), and freeze results to
`backend_research/results/sentiment_causality_screen.json` (flat, alongside the existing
`causality_screen.json`) plus `backend_research/REPORT-SENTIMENT.md`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sentiment causality/correlation screen | Offline Research Script (`backend_research/`, not a running-app tier) | Database / Storage (read-only SQLite via `db_loader.py`) | This phase produces zero `app/` changes (confirmed by CONTEXT.md's phase boundary and ARCHITECTURE.md's Pattern 3 precedent for research spikes) — it is a batch script that reads the live `PriceRow` table read-only and static `archive/*.csv` files, writes a frozen JSON + Markdown report, and never runs inside the Reflex process |
| Frozen go/no-go artifact (`results/sentiment_causality_screen.json`, `REPORT-SENTIMENT.md`) | Offline Research Script | — | Consumed only by a human (and, conditionally, Phase 18's planner) — never read at app runtime, mirroring how `backend_research/REPORT.md`/`02-MODEL-DECISIONS.md` are consumed today |

No Browser/SSR/API/CDN tier involvement at all this phase — flagging this explicitly
because it is easy for a planner used to this project's usual `app/`-touching phases to
default-assume some UI or state.py change belongs here. It does not.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.2.3 (installed, confirmed via `python3 -c "import pandas; print(pandas.__version__)"` this session) [VERIFIED: local environment] | Load/resample/merge daily sentiment CSVs to monthly cadence, merge onto `db_loader.load_price_history()`'s monthly PeriodIndex | Already the project's data-handling library, already installed in `backend_research/`; `ENV.md` explicitly warns to write pandas-2.2.3-safe code (no pandas-3.0-only copy-on-write assumptions) |
| statsmodels | 0.14.6 (installed, confirmed this session) [VERIFIED: local environment] | `sm.OLS` inside the reused `granger_ftest()` incremental F-test | Already pinned and installed; this phase imports `causality_screen.granger_ftest` directly rather than reimplementing OLS/F-test logic |
| scipy | transitive dependency of statsmodels (already installed) [VERIFIED: local environment] | `scipy.stats.f` (`fdist`) inside the reused `granger_ftest()` | Rides in with statsmodels; no separate install |

### Supporting

None. This phase needs no new supporting libraries — it is a pure extension of code
already in the repository.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `causality_screen.granger_ftest()` via import | Copy the F-test logic into a new sentiment-specific function | Rejected — CONTEXT.md's canonical refs explicitly require reusing `granger_ftest()` "verbatim, not reimplement[ed]"; duplicating it would drift from the single tested implementation and violate the project's Don't-Hand-Roll discipline (see below) |
| `scipy.stats.pearsonr`/`spearmanr` as an additional correlation check (suggested generically in `.planning/research/STACK.md`) | Granger F-test only (as `causality_screen.py` already does for every other predictor) | Not needed — D-01 locks the significance bar to the *existing* `causality_screen.py` tiers, which are Granger-F-test-based, not correlation-based; adding a second, differently-calibrated correlation test would introduce an inconsistent second bar this phase's own decisions (D-01) explicitly reject |

**Installation:**
```bash
# Nothing to install — pandas/statsmodels/scipy already present in backend_research/'s
# environment (confirmed this session: pandas 2.2.3, statsmodels 0.14.6).
```

**Version verification:** Ran directly in this session:
```bash
python3 -c "import statsmodels; print(statsmodels.__version__)"   # -> 0.14.6
python3 -c "import pandas; print(pandas.__version__)"             # -> 2.2.3
```
Both match `backend_research/ENV.md`'s recorded pins exactly — no drift to reconcile for
this phase.

## Package Legitimacy Audit

**Not applicable — this phase installs zero new external packages.** Every library used
(`pandas`, `statsmodels`, `scipy`) is already installed and pinned in the
`backend_research/` environment, verified above. No `pip install` step, no `slopcheck` run,
no new entries needed in `requirements-research.txt`.

## Architecture Patterns

### System Architecture Diagram

```
archive/news_sentiment_raw.csv           archive/ml_features.csv (or
  (published_at: UTC datetime,            sentiment_market_panel.csv)
   compound, source_weight)                 (vix_regime / vix_regime_code,
        │                                    US-trading-day keyed)
        │ convert published_at → Mongolia            │
        │ local (+8h fixed offset), derive            │
        │ local_month; recompute weighted_compound,   │
        │ article_count, monthly EMA3/EMA10/momentum  │
        │ per local_month                             │
        ▼                                              ▼
┌───────────────────────────────────────────────────────────┐
│  backend_research/sentiment/sentiment_data_loader.py       │
│  → monthly-indexed DataFrame, columns:                     │
│    weighted_compound, sent_ema3, sent_ema10,                │
│    sent_momentum, vix_regime_code                           │
│  (PeriodIndex freq="M", matches db_loader's index exactly) │
└───────────────────────────┬──────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────┐
│  backend_research/db_loader.py (UNCHANGED, imported)        │
│  load_price_history() → monthly PriceRow DataFrame           │
│  pct_change_frame() → target pct-change (stationary) series  │
└───────────────────────────┬──────────────────────────────┘
                             │
                             ▼  merge on shared monthly PeriodIndex
┌───────────────────────────────────────────────────────────┐
│  backend_research/sentiment/run_sentiment_causality_screen.py │
│  for target in [hdan, ppan, diesel_usd_ton, fx_rate]:          │
│    for predictor in [weighted_compound, sent_ema3, sent_ema10, │
│                       sent_momentum, vix_regime_code]:          │
│      for lag in (1, 2, 3):                                       │
│        n = len(overlap after dropna)                             │
│        if n < MIN_GRANGER_N (24, imported from causality_screen):│
│           record "insufficient overlap", tier="ns" (D-07)        │
│        else:                                                     │
│           F, p, n = granger_ftest(y_target_pct_change,           │
│                                    x_predictor_level, lag)        │
│           tier = _tier(p, n)  (imported, p05/p10/ns, D-01)       │
└───────────────────────────┬──────────────────────────────┘
                             │
                             ▼
     backend_research/results/sentiment_causality_screen.json (frozen)
                             │
                             ▼
     backend_research/REPORT-SENTIMENT.md
       — per-series (D-04) go/no-go table: HDAN, PPAN, Diesel-USD, FX rate
       — effective monthly N stated explicitly per series (never raw row counts)
       — best-lag-per-predictor only (D-02), no directional filtering (D-03)
```

A reader can trace the primary use case end-to-end: raw timestamped articles enter on the
left, get timezone-corrected and resampled to monthly, merge onto the exact same monthly
index the rest of the codebase already uses for prices, run through the *unmodified*
Granger F-test the rest of the project already trusts, and terminate in a frozen JSON +
human-readable go/no-go report. Nothing in this path touches `app/`.

### Recommended Project Structure

```
backend_research/
├── sentiment/                              # NEW
│   ├── sentiment_data_loader.py            # NEW — raw CSVs -> monthly predictor frame
│   └── run_sentiment_causality_screen.py   # NEW — the screen itself (entry point)
├── results/
│   └── sentiment_causality_screen.json     # NEW — flat, alongside causality_screen.json
│                                              (see "Location decision" below — this
│                                              deviates from ARCHITECTURE.md's earlier
│                                              backend_research/sentiment/results/
│                                              suggestion; CONTEXT.md's explicit path
│                                              wins)
├── REPORT-SENTIMENT.md                     # NEW — top-level, alongside REPORT.md/
│                                              REPORT-PHASE2.md
├── causality_screen.py                     # UNCHANGED — imported from, not modified
├── db_loader.py                            # UNCHANGED — imported from, not modified
└── walk_forward.py                         # UNCHANGED — LeakageError imported for the
                                               timezone-guard assertion (see Pitfall 3)
```

**Location decision (resolves a discrepancy between two upstream research docs):**
`.planning/research/ARCHITECTURE.md` (written before CONTEXT.md's discussion) proposed a
*nested* `backend_research/sentiment/results/sentiment_backtest.json`. CONTEXT.md's
Claude's-Discretion note (written after discussion, and therefore the more current,
user-facing instruction) says explicitly: "follow the existing `backend_research/`
convention (a new `REPORT-SENTIMENT.md` and `results/sentiment_causality_screen.json`,
mirroring `causality_screen.json`'s shape) rather than inventing a new structure." The
existing convention is a single **flat** `backend_research/results/` directory holding
every script's output (`causality_screen.json`, `cointegration.json`,
`weekly_candidates.json`, `garch_volatility.json`, etc. all sit together — confirmed by
directory listing this session). Recommendation: use the flat, existing
`backend_research/results/sentiment_causality_screen.json` path, not a nested
`sentiment/results/` subfolder — this is the literal, closer reading of CONTEXT.md's
instruction and matches what "the existing convention" actually is on disk today.

### Pattern 1: Reuse `granger_ftest`/`_tier`/`MIN_GRANGER_N` by import, not copy

**What:** `backend_research/sentiment/run_sentiment_causality_screen.py` imports directly:
```python
# Source: backend_research/causality_screen.py (existing, unmodified)
from causality_screen import granger_ftest, _tier, MIN_GRANGER_N
from db_loader import TARGETS, load_price_history, pct_change_frame
```

**When to use:** Always, for this phase — D-01 and D-05 both explicitly require using the
*exact same* tiering/floor logic as the rest of the pipeline, not a sentiment-specific
reimplementation. Reusing by import (rather than copy-paste) makes that guarantee
structural, not just a documentation promise.

**Concrete gotcha — import path.** `causality_screen.py` and `db_loader.py` both use flat,
unqualified imports (`from db_loader import ...`) that only resolve when the *working
directory at import time* is `backend_research/` itself (verified this session:
`from db_loader import TARGETS` fails with `ModuleNotFoundError` when run from the repo
root, succeeds when run from inside `backend_research/`). Placing the new screen inside a
`backend_research/sentiment/` *subfolder* breaks this unless the subfolder script
explicitly adds the parent directory to `sys.path` before importing. Concretely, both new
files need:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend_research/
from causality_screen import granger_ftest, _tier, MIN_GRANGER_N
from db_loader import TARGETS, load_price_history, pct_change_frame
```
Without this, the script will raise `ModuleNotFoundError: No module named 'db_loader'` the
moment it's run via `python backend_research/sentiment/run_sentiment_causality_screen.py`
from the repo root (the natural way a human or CI would invoke it). This is a real,
verified gotcha, not a hypothetical one — confirmed by direct reproduction this session.

**Example — the screen's core loop (illustrative, matches `run_granger_sweep`'s shape):**
```python
# Source: adapted from backend_research/causality_screen.py's run_granger_sweep()
def run_sentiment_causality_screen() -> list[dict]:
    pct = pct_change_frame(load_price_history())         # targets, pct-change (stationary)
    sentiment = load_sentiment_monthly()                   # predictors, LEVEL (see Pitfall A)

    results: list[dict] = []
    for target in TARGETS:                                 # hdan, ppan, diesel_usd_ton, fx_rate
        y = pct[target]
        for predictor in SENTIMENT_PREDICTORS:              # 5 concrete columns, D-08
            x = sentiment[predictor]
            for lag in (1, 2, 3):
                d = pd.DataFrame({"y": y, "x": x.shift(lag)}).dropna()
                n_overlap = len(d)
                if n_overlap < MIN_GRANGER_N:                # D-07: immediate no-go
                    results.append({
                        "target": target, "predictor": predictor, "lag": lag,
                        "F": None, "p": None, "n": n_overlap,
                        "tier": "ns", "note": "insufficient overlap",
                    })
                    continue
                F, p, n = granger_ftest(y, x, lag)
                results.append({
                    "target": target, "predictor": predictor, "lag": lag,
                    "F": round(F, 4), "p": round(p, 4), "n": n,
                    "tier": _tier(p, n),
                })
    return results
```

### Pattern 2: Sentiment predictors are LEVELS, not pct-changed like price targets

**What:** `causality_screen.run_granger_sweep()` pct-changes *every* column (both `y` and
`x`) because every existing predictor (`baltic_an`, `ammonia`, `brent`, etc.) is a raw
price level that needs pct-change to become approximately stationary. Sentiment predictors
are categorically different: `weighted_compound` is already bounded `[-1, 1]`,
`vix_regime_code` is a small ordinal `{0,1,2,3}`, and `sent_momentum` is already a
difference-of-EMAs (already a "change" quantity). Pct-changing a bounded score that
crosses zero produces division-by-zero or sign-flip artifacts (e.g. `(-0.1 - 0.1) / 0.1 =
-200%`, or an outright `inf` if the prior value was exactly `0`). **Do not reuse
`pct_change_frame()` on the sentiment columns.** Feed the sentiment predictor as its raw
monthly *level* into `granger_ftest(y, predictor, lag)` — only the target `y` should come
from `pct_change_frame(load_price_history())`. `granger_ftest()` itself is agnostic to
this (it just takes two aligned Series), so no change to that function is needed — this is
purely a caller-side data-preparation decision.

**When to use:** Every sentiment predictor in this screen, all 4 targets, all 3 lags.

**Trade-offs:** None — this is a correctness requirement, not a design choice with
alternatives. Getting it backwards (pct-changing sentiment) would silently corrupt every
p-value in the screen with `inf`/`NaN` artifacts that `dropna()` would partially mask,
producing a misleadingly small effective N and/or spurious extreme F-statistics.

### Pattern 3: Timezone-safe daily→monthly resample (leakage guard, extends `walk_forward.LeakageError`)

**What:** `news_sentiment_daily.csv`'s `date` column is date-only (no time-of-day) and,
per direct inspection, matches the **UTC** calendar date of the underlying articles'
`published_at` timestamps in `news_sentiment_raw.csv` (verified this session: e.g. a raw
row with `published_at=2026-08-22T09:25:02Z` has `date=2026-08-22`). Because it is
date-only, it **cannot be corrected for timezone after the fact** — adding 8 hours to a
date with no time component doesn't change which calendar day it lands on. The leakage
risk PITFALLS.md Pitfall 3 flags (Mongolia is UTC+8; an article published late in the UTC
day is already "tomorrow" locally) can therefore only be fixed by working from
`news_sentiment_raw.csv`'s full `published_at` timestamp, not the pre-aggregated daily
file.

**Recommended implementation:**
```python
# backend_research/sentiment/sentiment_data_loader.py
import pandas as pd
from pathlib import Path
from walk_forward import LeakageError    # reused, not reimplemented (D-flex note)

MN_OFFSET = pd.Timedelta(hours=8)   # Mongolia is UTC+8 year-round (no DST since 2017)

def _load_raw_local() -> pd.DataFrame:
    raw = pd.read_csv(RAW_CSV, parse_dates=["published_at"])
    raw["published_at"] = pd.to_datetime(raw["published_at"], utc=True)
    raw["local_dt"] = raw["published_at"] + MN_OFFSET
    raw["local_month"] = raw["local_dt"].dt.to_period("M")

    # Leakage guard: any row whose UTC-date-derived month differs from its
    # Mongolia-local-derived month is exactly the boundary case Pitfall 3 warns
    # about. Assert none exist post-correction (the correction should have
    # resolved them) -- this makes the "leakage-safe" claim testable, not just
    # asserted in prose.
    utc_month = raw["published_at"].dt.to_period("M")
    if (utc_month != raw["local_month"]).any() and _SANITY_MODE:
        # Expected to be non-empty pre-correction; this is a log point, not a
        # failure, once local_month is what downstream code actually uses.
        pass
    return raw
```
The monthly `weighted_compound` should be recomputed directly from raw rows grouped by
`local_month` (using the README's documented formula,
`sum(compound * source_weight) / sum(source_weight)`), not by resampling the archive's
pre-computed daily `weighted_compound` column — that column inherits the UTC-day
bucketing bug. `article_count` = row count per `local_month`, also from raw, not from
`news_sentiment_daily.csv`.

**Raise `LeakageError` (imported from `walk_forward.py`, per CONTEXT.md's explicit
instruction to extend it rather than write a parallel guard) at the point the monthly
sentiment frame is merged onto the target-side data**, if any sentiment month's
`local_month` would post-date the price row it's being tested as a *lagged* predictor for
— e.g. if `lag=1` and a sentiment month equals the target month rather than strictly
preceding it. In practice `x.shift(lag)` in Pattern 1's loop already enforces this
mechanically (a lag-1 predictor is definitionally the prior month's value), so this
`LeakageError` should function as a defensive assertion that never fires if the shift
logic is correct — write a unit test asserting it *would* fire if the shift were removed,
mirroring `test_walk_forward.py::test_leakage_guard_raises`'s existing pattern.

**Trade-off note for the planner:** given the confirmed max-N ceiling (14–20, all below
`MIN_GRANGER_N=24`), this timezone correction cannot change the phase's overall go/no-go
outcome — it changes at most which specific month a handful of sparse single-article days
get bucketed into, and D-07's insufficient-overlap floor fires regardless. It is still
worth implementing correctly (not skipping) because (a) SENT-01 explicitly requires a
leakage-safe merge as part of what makes the screen "rigorous," and (b) if the archive is
ever refreshed with denser, more continuous coverage in a future milestone, this is exactly
the kind of subtle bug that would otherwise silently corrupt a *real* future finding.
Recommend the planner budget this as a small, well-defined task rather than either skipping
it (violates PITFALLS.md Pitfall 3 / SENT-01's rigor requirement) or over-building it (e.g.
full DST-aware `zoneinfo` handling is unnecessary — Mongolia has used a fixed UTC+8 offset
without daylight saving since 2017 [ASSUMED — general knowledge, not verified against a
live timezone database this session; low risk either way since a fixed +8h offset is
correct for the entire archive's 2020–2026 date range regardless]).

### Anti-Patterns to Avoid

- **Resampling the archive's pre-computed daily `sent_ema3`/`sent_ema10` columns directly
  to monthly via `.resample("M").mean()`:** these are *day-unit* EMAs (3-day and 10-day
  lookback). Taking a monthly mean of a 3-day EMA produces a doubly-smoothed, dimensionally
  confused quantity that is neither a real monthly trend nor comparable to the archive's
  own stated methodology. Instead, build the corrected monthly `weighted_compound` series
  first (Pattern 3), then compute genuine *month-unit* EMAs on top of it
  (`.ewm(span=3).mean()`, `.ewm(span=10).mean()` on the monthly series) for
  `sent_ema3`/`sent_ema10`/`sent_momentum` at monthly cadence. This is a deliberate,
  documented deviation from a naive "just resample the existing columns" approach — flag it
  explicitly in `REPORT-SENTIMENT.md`'s methodology section so a future reader isn't
  confused about why the monthly EMA values don't match a naive resample of the archive's
  daily ones.
- **Reusing `pct_change_frame()` on sentiment columns** (Pattern 2, above) — silently
  produces `inf`/`NaN` artifacts.
- **Treating `news_sentiment_daily.csv`'s row count (163) or `article_count` sum as
  "sample size"** — SENT-01 explicitly requires reporting *effective monthly sample size*
  (i.e., `n` after `dropna()` in the Granger test), not raw daily-file row counts. The
  concrete numbers to report per target (see Common Pitfalls below) are 14/14/18/20 as an
  *upper bound*, likely lower after each lag's `dropna()`.
- **Skipping the significance test entirely and hand-writing "no-go" into the JSON**
  because the outcome is highly predictable — D-07's skip behavior must be a *computed*
  branch (`if n < MIN_GRANGER_N`), not a hardcoded result, so the pipeline is honest and
  reproducible (and correct again automatically if the archive is ever refreshed with more
  data).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Granger-causality F-test | A new incremental F-test implementation for sentiment predictors | `causality_screen.granger_ftest()` (import) | D-flex/canonical_refs explicitly require reuse "verbatim, not reimplement"; the existing function is already cross-checked against `statsmodels.tsa.stattools.grangercausalitytests` (see `CROSSCHECK_PAIR` logic) — a reimplementation would need to redo that verification |
| Significance tiering (p05/p10/ns) | A new sentiment-specific threshold function | `causality_screen._tier()` (import) | D-01 locks this to be identical across the whole pipeline — no stricter bar for sentiment |
| Thin-sample floor | A new sentiment-specific minimum-N constant | `causality_screen.MIN_GRANGER_N` (import, currently `24`) | D-05 explicitly reuses this exact constant |
| Monthly price-history loading | A parallel SQLite reader for the sentiment screen | `db_loader.load_price_history()` / `pct_change_frame()` (import) | Canonical refs explicitly require reusing these "rather than re-implementing"; also guarantees the sentiment screen's target-side data is byte-identical to every other model's target-side data in this codebase |
| Leakage assertion for the daily→monthly boundary | A parallel `TimezoneLeakageError` class | `walk_forward.LeakageError` (import, raise from the merge step) | CONTEXT.md's Claude's-Discretion note explicitly instructs extending this class rather than writing a parallel guard |

**Key insight:** almost nothing in this phase should be genuinely new logic — the correct
shape of the deliverable is "wire three new predictor columns into an existing, trusted
pipeline," not "design a new statistical methodology." The places where new code
*is* warranted (Pattern 2's level-vs-pct-change distinction, Pattern 3's raw-timestamp
timezone correction) are narrow, specific gaps in what the existing pipeline was built to
handle (it was built for price-level predictors on a dense monthly grid, not bounded daily
sentiment scores on a sparse one) — everything else should be a direct import.

## Common Pitfalls

### Pitfall 1: Reporting raw CSV row counts (163, 117, 119) instead of effective monthly N

**What goes wrong:** A report that says "the sentiment dataset has 163 days of coverage"
sounds like meaningful sample size but is not the number that matters for a monthly
Granger test.
**Why it happens:** The archive's own README and file names invite treating row count as
sample size.
**How to avoid:** State the *computed* `n` from each Granger test record (post-`dropna()`)
in `REPORT-SENTIMENT.md`, per target, and additionally state the pre-test upper bound this
research already computed directly from the data (verified this session, not estimated):

| Target | Sentiment-covered months (any article) | Price-covered months among those | Max possible N before per-predictor dropna |
|---|---|---|---|
| HDAN | 20 (out of 165 total PriceRow months, 2013-01..2026-09) | 14 | 14 |
| PPAN | 20 | 14 | 14 |
| Diesel-USD | 20 | 18 | 18 |
| FX rate | 20 | 20 | 20 |

All four are below `MIN_GRANGER_N=24`. This table should appear directly in
`REPORT-SENTIMENT.md` as the headline evidence for why D-07's immediate-no-go branch is
expected to fire broadly.
**Warning signs:** Any report sentence citing "163 days" or "6 years of coverage" as
evidence of sufficiency.

### Pitfall 2: Sentiment predictor pct-changed like a price series (Pattern 2, restated as a warning)

**What goes wrong:** Silent `inf`/`NaN` corruption of p-values if `pct_change_frame()` is
applied to `weighted_compound`/`vix_regime_code` instead of using raw levels.
**How to avoid:** Only the target `y` comes from `pct_change_frame(load_price_history())`;
sentiment predictors are levels. Add an explicit unit test asserting the sentiment loader
never emits `inf`.

### Pitfall 3: Daily→monthly bucket assignment using the pre-aggregated file's date-only column

**What goes wrong:** Loses the ability to correct for the UTC vs. Mongolia-local (+8h)
boundary case (PITFALLS.md Pitfall 3), since a date-only value has no time component to
shift.
**How to avoid:** Build the monthly sentiment frame from `news_sentiment_raw.csv`'s
`published_at` (has time-of-day), not `news_sentiment_daily.csv`'s `date` (Pattern 3).

### Pitfall 4: `backend_research/sentiment/` subfolder scripts failing with `ModuleNotFoundError`

**What goes wrong:** `from db_loader import ...` / `from causality_screen import ...`
silently only work when CWD is `backend_research/` itself; placing new scripts one level
deeper breaks this (verified by direct reproduction this session).
**How to avoid:** `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` before
any flat import, in both new files (Pattern 1).

### Pitfall 5: Conflating `vix_regime` (categorical string) with `vix_regime_code` (numeric)

**What goes wrong:** `vix_regime` in `ml_features.csv`/`sentiment_market_panel.csv` is a
string (`"low"/"normal"/"elevated"/"extreme"`) — `sm.OLS` inside `granger_ftest()` cannot
regress on a string column and will raise a dtype/casting error, not silently produce a
wrong answer, so this fails loudly — but it's worth flagging explicitly since D-08 names
the *feature* as `vix_regime` while the numeric column that must actually be used is
`vix_regime_code` (already present in `ml_features.csv`, encoded `0=low, 1=normal,
2=elevated, 3=extreme`).
**How to avoid:** Use `vix_regime_code`, resampled to monthly (mean, per D-flex's "pick
mean" instruction, since it's D-06's uniform resample choice applied here too — a monthly
mean of the ordinal code is a reasonable continuous proxy for "how risk-off was this month
on average").
**Warning signs:** A `TypeError`/`ValueError` from `sm.OLS.fit()` about string-to-float
casting — this is the tell that the string column, not the code column, was passed.

## Code Examples

### Loading and monthly-resampling the news_sentiment_raw.csv-derived predictor

```python
# Source: derived from archive/README.md's documented weighted_compound formula and
# direct inspection of archive/news_sentiment_raw.csv's columns this session
import pandas as pd
from pathlib import Path

ARCHIVE = Path(__file__).resolve().parent.parent.parent / "archive"
MN_OFFSET = pd.Timedelta(hours=8)

def load_sentiment_monthly() -> pd.DataFrame:
    raw = pd.read_csv(ARCHIVE / "news_sentiment_raw.csv")
    raw["published_at"] = pd.to_datetime(raw["published_at"], utc=True)
    raw["local_month"] = (raw["published_at"] + MN_OFFSET).dt.to_period("M")

    monthly = raw.groupby("local_month").apply(
        lambda g: pd.Series({
            "weighted_compound": (g["compound"] * g["source_weight"]).sum()
                                  / g["source_weight"].sum(),
            "article_count": len(g),
        }),
        include_groups=False,
    )
    monthly["sent_ema3"] = monthly["weighted_compound"].ewm(span=3, adjust=False).mean()
    monthly["sent_ema10"] = monthly["weighted_compound"].ewm(span=10, adjust=False).mean()
    monthly["sent_momentum"] = monthly["sent_ema3"] - monthly["sent_ema10"]

    ml = pd.read_csv(ARCHIVE / "ml_features.csv", parse_dates=["date"])
    ml["local_month"] = (ml["date"] + MN_OFFSET).dt.to_period("M")
    vix = ml.groupby("local_month")["vix_regime_code"].mean()
    monthly["vix_regime_code"] = vix

    monthly.index.name = "date"
    return monthly  # PeriodIndex freq="M", matches db_loader.load_price_history()'s index
```
Note: `ml_features.csv`'s `date` column is trading-day-keyed (US market calendar, tied to
`market_prices.csv`'s SPY/QQQ/DIA/VIX source), not article-publication-timestamped, so no
UTC→Mongolia correction applies to the `vix_regime_code` merge — it's a different kind of
"which day" question (US market open days) than the sentiment article timezone issue.

### Merging onto `db_loader`'s target frame and running the screen (ties Patterns 1+2 together)

```python
# Source: this research, composing causality_screen.py + db_loader.py's existing exports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from causality_screen import granger_ftest, _tier, MIN_GRANGER_N
from db_loader import TARGETS, load_price_history, pct_change_frame
from sentiment_data_loader import load_sentiment_monthly

SENTIMENT_PREDICTORS = [
    "weighted_compound", "sent_ema3", "sent_ema10", "sent_momentum", "vix_regime_code",
]

def run_sentiment_causality_screen() -> list[dict]:
    pct = pct_change_frame(load_price_history())     # targets: pct-change (Pattern 2)
    sentiment = load_sentiment_monthly()               # predictors: levels (Pattern 2)

    results = []
    for target in TARGETS:
        y = pct[target]
        for predictor in SENTIMENT_PREDICTORS:
            x = sentiment[predictor]
            for lag in (1, 2, 3):
                import pandas as pd
                d = pd.DataFrame({"y": y, "x": x.shift(lag)}).dropna()
                n = len(d)
                if n < MIN_GRANGER_N:
                    results.append({
                        "target": target, "predictor": predictor, "lag": lag,
                        "F": None, "p": None, "n": n,
                        "tier": "ns", "note": "insufficient overlap",
                    })
                    continue
                F, p, n_used = granger_ftest(y, x, lag)
                results.append({
                    "target": target, "predictor": predictor, "lag": lag,
                    "F": round(F, 4), "p": round(p, 4), "n": n_used,
                    "tier": _tier(p, n_used),
                })
    return results
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| Phase 2's `causality_screen.py` screened 12 fundamental price/commodity predictors against 4 targets, no sentiment | This phase extends the same methodology to 3 sentiment feature families | This phase (v2.0) | Establishes whether sentiment belongs in the predictor universe at all before any Phase 18 UI work; the finding (near-certain no-go on data-sufficiency grounds) is itself the deliverable, not a stepping stone to a shipped model |

**Deprecated/outdated:** N/A — no prior sentiment-specific research exists in this
codebase to supersede; this is the first pass.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Mongolia has used a fixed UTC+8 offset with no daylight-saving observance since 2017, so a flat `+8h` `Timedelta` correctly represents UTC→Mongolia-local for the entire 2020-2026 archive date range | Pattern 3 / Code Examples | LOW — if wrong, at most a handful of single-article days near month boundaries get bucketed into the adjacent month; given the confirmed N-ceiling of 14-20 (already 4-10 below the 24 floor), this cannot change the phase's go/no-go conclusion, only the audit trail's precision |
| A2 | `news_sentiment_daily.csv`'s `date` column is derived directly from the UTC calendar date of each day's `published_at` timestamps (i.e., no timezone conversion was applied when the archive was built) | Pattern 3 | LOW-MEDIUM — this is inferred from one matching sample row (`published_at=2026-08-22T09:25:02Z` → `date=2026-08-22`), not exhaustively verified across all 163 rows; if wrong for some rows, the raw-timestamp rebuild in Pattern 3 is still correct regardless (it doesn't depend on this assumption — it bypasses the pre-aggregated file entirely) |

## Open Questions

1. **Should the "no-go" report additionally state what data collection would be needed for
   a future re-attempt to plausibly clear the bar (e.g., "N more months of continuous,
   commodity/FX-relevant sentiment coverage")?**
   - What we know: `.planning/research/STACK.md`'s "Stack Patterns by Variant" section
     already frames this as a legitimate follow-up ("collect continuous commodity/FX-relevant
     news for N more months... future work, explicitly out of scope").
   - What's unclear: whether SENT-01/SENT-02's success criteria require this framing inside
     `REPORT-SENTIMENT.md` itself, or whether it's optional narrative color.
   - Recommendation: include a brief closing paragraph noting the data-collection gap
     honestly (mirrors the project's existing "no un-backtested model ships" transparency
     norm), but treat it as optional narrative, not a blocking success criterion — SENT-01/
     SENT-02 are satisfied by the screen + frozen go/no-go result regardless.

2. **Does any predictor/target/lag combination among the 20 sentiment-covered months
   possibly reach the 24-month floor if a *different* resampling choice were made (e.g.,
   forward-filling zero-article months instead of dropping them)?**
   - What we know: D-06 explicitly locks the "drop, don't forward-fill" choice, closing
     this question by decision rather than leaving it open.
   - What's unclear: nothing — this is settled by CONTEXT.md, listed here only so the
     planner doesn't need to re-derive why forward-fill wasn't considered (it was
     explicitly rejected as "manufacturing continuity that risks staleness/leakage").
   - Recommendation: no action needed; D-06 stands.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | Sentiment loader, monthly resample/merge | Yes | 2.2.3 (confirmed this session) | — |
| statsmodels | Reused `granger_ftest()` | Yes | 0.14.6 (confirmed this session) | — |
| scipy | Transitive, inside `granger_ftest()` | Yes | (transitive, resolved by statsmodels) | — |
| `app/reflex.db` (SQLite, read via `db_loader.py`) | Target-side price history | Yes — confirmed readable this session, 165 monthly rows, 2013-01 through 2026-09 | — | — |
| `archive/*.csv` (static, checked-in) | Sentiment predictor source | Yes — confirmed readable this session (`news_sentiment_raw.csv`: 9,617 rows; `news_sentiment_daily.csv`: 163 rows; `ml_features.csv`: 116 rows) | — | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None — everything this phase needs is already
present and verified working in the `backend_research/` environment.

## Project Constraints (from CLAUDE.md)

- Reflex/SQLite/statsmodels/pandas/openpyxl stack is locked at the project level — not
  relevant to this phase's *additions* (it adds nothing to that stack), but confirms this
  phase must not introduce a competing data-handling library.
- "No un-backtested model ships" — this phase's entire purpose is producing the
  research/backtest evidence SENT-01/SENT-02 require before any sentiment-adjusted
  behavior could ever reach `app/`; nothing in this phase ships to the app regardless of
  outcome.
- GSD workflow enforcement (`~/CLAUDE.md`): file-changing work must go through a GSD
  command (`/gsd:plan-phase` → execute-phase), not ad hoc edits — this research document is
  itself part of that GSD flow (research step of `/gsd:plan-phase`).
- code-review-graph MCP tools should be preferred over Grep/Glob for codebase exploration
  per `~/CLAUDE.md`; for this research pass, direct `Read`/`Bash` inspection of specific,
  already-named files (`causality_screen.py`, `db_loader.py`, `walk_forward.py`,
  `archive/*.csv`) was more precise than a semantic graph query, since the exact files to
  inspect were already known from CONTEXT.md's canonical references — no exploratory
  search was needed.

## Sources

### Primary (HIGH confidence)

- Direct read of `backend_research/causality_screen.py` (full file) — HIGH confidence,
  source of `granger_ftest()`, `_tier()`, `MIN_GRANGER_N`, `shortlist_for()` signatures and
  exact behavior
- Direct read of `backend_research/walk_forward.py` (full file) — HIGH confidence, source
  of `LeakageError`'s exact definition and existing usage pattern
- Direct read of `backend_research/db_loader.py` (full file) — HIGH confidence, source of
  `TARGETS`, `load_price_history()`, `pct_change_frame()` exact behavior and the
  read-only-SQLite-URI pattern
- Direct inspection of `archive/README.md`, `archive/news_sentiment_daily.csv`,
  `archive/news_sentiment_raw.csv`, `archive/ml_features.csv`,
  `archive/sentiment_market_panel.csv` (headers, row counts, sample rows, this session) —
  HIGH confidence
- Live computation against `app/reflex.db` and the archive CSVs, this session (Python/
  pandas, not estimated): sentiment-covered-months count (20), per-target price/sentiment
  overlap ceiling (14/14/18/20), `news_sentiment_daily.csv` month-level article
  concentration (148/163 rows in 5 recent months) — HIGH confidence, directly reproducible
- `backend_research/ENV.md` — HIGH confidence, confirmed pandas 2.2.3 / statsmodels 0.14.6
  match this session's live `import` checks exactly, no drift
- `backend_research/REPORT-PHASE2.md` ("Predictor screen (D-04/D-05)" section) — HIGH
  confidence, exact report-table format this phase's `REPORT-SENTIMENT.md` should mirror

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`,
  `FEATURES.md` (v2.0 milestone research, 2026-08-31) — MEDIUM-HIGH per their own stated
  confidence; used here for architectural framing and pitfall cross-referencing, superseded
  in specific file-location details by CONTEXT.md's more recent discretion notes (see
  "Location decision" above)

### Tertiary (LOW confidence)

- A1 in the Assumptions Log (Mongolia's fixed UTC+8 offset, no DST since 2017) — general
  knowledge, not independently re-verified against a live timezone database this session

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; existing versions directly confirmed via
  live `import` checks this session
- Architecture: HIGH — grounded in direct reads of the three files this phase extends
  (`causality_screen.py`, `db_loader.py`, `walk_forward.py`) plus a reproduced import-path
  failure confirming the subfolder gotcha
- Pitfalls: HIGH — the headline data-sufficiency finding (N ceiling of 14-20, all below
  `MIN_GRANGER_N=24`) is computed directly from the live database and archive files in this
  session, not estimated or inherited from upstream research documents

**Research date:** 2026-08-31
**Valid until:** Effectively indefinite for the methodology (stable, unversioned stdlib/
pandas/statsmodels code); the specific N-ceiling numbers (14/14/18/20) will drift if
`app/reflex.db` gains new monthly rows or `archive/` is refreshed with a denser sentiment
export before this phase executes — re-run the two verification snippets in "Version
verification"/Pitfall 1's table if more than a few days elapse before planning executes.
