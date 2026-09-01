---
phase: 16-sentiment-data-sufficiency-causality-research
plan: 01
subsystem: backend_research/sentiment
tags: [sentiment, data-loader, leakage-guard, granger-causality, research]
requires: []
provides:
  - load_sentiment_monthly
  - merge_lagged
  - SENTIMENT_PREDICTORS
  - MN_OFFSET
affects:
  - backend_research/sentiment/run_sentiment_causality_screen.py (Plan 02, not yet built)
tech-stack:
  added: []
  patterns:
    - "Monthly PeriodIndex predictor frame, mirroring db_loader.load_price_history()'s contract"
    - "Calendar-label reindex (not positional shift) for lagged merges over a gappy monthly index"
    - "Reuse walk_forward.LeakageError rather than a parallel exception class"
key-files:
  created:
    - backend_research/sentiment/sentiment_data_loader.py
    - backend_research/sentiment/test_sentiment_data_loader.py
  modified: []
decisions:
  - "weighted_compound/sent_ema3/sent_ema10/sent_momentum are rebuilt from raw article timestamps corrected to Mongolia-local (UTC+8), never resampled from archive/news_sentiment_daily.csv, whose date column is UTC-day-bucketed and cannot be corrected after the fact."
  - "vix_regime_code is bucketed on ml_features.csv's own US-trading-day calendar with no MN_OFFSET shift, since that file is SPY/QQQ/DIA/VIX-source-keyed, not article-publication-timestamped."
  - "merge_lagged() reindexes the (possibly gappy) predictor onto the dense target index by calendar label before shifting, and includes y_lag1 in the dropna so its row count equals causality_screen.granger_ftest()'s true effective n."
metrics:
  duration: "~35 min"
  completed: "2026-09-01"
---

# Phase 16 Plan 01: Sentiment Data Loader Summary

Monthly-cadence sentiment predictor loader (`load_sentiment_monthly`) built from
`archive/news_sentiment_raw.csv`'s raw article timestamps with Mongolia-local (UTC+8)
timezone correction, plus a leakage-guarded calendar-based lagged-merge helper
(`merge_lagged`) that reuses `walk_forward.LeakageError`.

## What Was Built

- `backend_research/sentiment/sentiment_data_loader.py`:
  - `load_sentiment_monthly() -> pd.DataFrame` — reads `archive/news_sentiment_raw.csv`,
    shifts `published_at` by `MN_OFFSET = pd.Timedelta(hours=8)`, buckets to a monthly
    `PeriodIndex` by Mongolia-local calendar month, and recomputes `weighted_compound`
    per month from raw `compound`/`source_weight` values (the README's documented
    source-credibility-weighted formula). `sent_ema3`, `sent_ema10`, and `sent_momentum`
    are derived on the resulting monthly series (never resampled from the archive's
    day-unit columns). `vix_regime_code` is pulled from `archive/ml_features.csv`,
    bucketed on its own US-trading-day calendar (no MN_OFFSET), and merged in by month
    label. Zero-article months are simply absent from the groupby result — no
    fill/reindex/interpolate call exists anywhere in the function. The function raises
    `ValueError` on any index-contract violation (non-`PeriodIndex`/non-monthly,
    non-monotonic, duplicated) or on any `inf` in the five predictor columns. Verified
    against today's archive: 20 monthly rows, 2020-03..2026-08, no NaN, no inf,
    `weighted_compound` bounded in `[-1, 1]`.
  - `merge_lagged(y, x, lag) -> pd.DataFrame` — the leakage-guarded alignment point
    between a price target series and a sentiment predictor series. Raises
    `walk_forward.LeakageError` on `lag < 1` and on either series not being a monotonic
    monthly `PeriodIndex`. Reindexes the (possibly gappy) predictor onto the target's
    dense monthly index by calendar label before shifting by `lag`, so the shift is
    provably calendar-based rather than positional over a gappy index. Includes a
    `y_lag1` column and a defensive post-check (calendar-label recomputation) that
    would itself raise `LeakageError` if a future edit swapped the reindex for a
    positional shift.
  - `SENTIMENT_PREDICTORS = ["weighted_compound", "sent_ema3", "sent_ema10", "sent_momentum", "vix_regime_code"]`
    — exactly the five D-08 columns; D-09-excluded columns (`rolling_corr_60d`,
    `spy_return_next1d`, `qqq_return_next1d`, `dia_return_next1d`) never appear.

- `backend_research/sentiment/test_sentiment_data_loader.py` — 9 tests:
  - 4 `pytest.raises(LeakageError)` cases: `lag=0`, `lag=-1`, non-`PeriodIndex` `x`,
    non-`PeriodIndex` `y`.
  - Dense-fixture and gappy-fixture calendar-lag correctness tests (built with
    `pd.period_range`, independent of the real archive).
  - Three regression tests against the real, checked-in archive files: no `inf` in any
    `SENTIMENT_PREDICTORS` column, monthly index contract (`PeriodIndex`, monotonic, no
    duplicates) plus bounded `weighted_compound`, and no zero-article months.

## Verification

- `python3 sentiment/sentiment_data_loader.py` → shape `(20, 6)`, index `2020-03..2026-08`,
  all six columns fully non-null.
- `python3 -m pytest sentiment/test_sentiment_data_loader.py -q` → 9 passed.
- `python3 -m pytest -q` (full `backend_research/` suite) → 15 passed (6 pre-existing
  `test_walk_forward.py` + 9 new).
- Load-bearing guard check: temporarily changed `lag < 1` to `lag < 0` in
  `merge_lagged` — `test_merge_lagged_zero_lag_raises` failed as expected, confirming
  the guard is load-bearing rather than decorative. Reverted; full suite green again
  (15 passed).
- All plan acceptance-criteria greps pass: zero references to `news_sentiment_daily`,
  zero fill/reindex/asfreq calls, zero D-09-excluded-column references, exactly one
  `from walk_forward import LeakageError`, `vix_regime_code` used (numeric column
  only, string `vix_regime` never referenced).
- `git status --porcelain` shows exactly the two new files under
  `backend_research/sentiment/` — no other files created or modified.

## Deviations from Plan

None — plan executed exactly as written. One implementation-detail refinement made
during execution (not a deviation from the plan's intent): the module docstring and
D-06 comment initially quoted literal substrings (`news_sentiment_daily`, `.ffill(`,
etc.) that the plan's own acceptance-criteria greps forbid appearing anywhere outside
`#`-comment lines; reworded those docstring passages to convey the same explanation
without the literal forbidden substrings, then re-verified all greps return the
required counts.

## Known Stubs

None.

## Threat Flags

None — this plan's file-I/O surface (`archive/news_sentiment_raw.csv`,
`archive/ml_features.csv`) exactly matches the plan's threat model (T-16-01..T-16-04).
No new network, auth, or write path was introduced.

## Self-Check: PASSED

- FOUND: backend_research/sentiment/sentiment_data_loader.py
- FOUND: backend_research/sentiment/test_sentiment_data_loader.py
- FOUND commit: 5d9a5f9 (feat(16-01): monthly sentiment predictor loader ...)
- FOUND commit: 57372e8 (test(16-01): leakage-guard, no-inf, index-contract, and calendar-lag tests ...)
