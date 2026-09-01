# Phase 20: FX Weekly Backtest -- Research Report

Generated deterministically by `backend_research/weekly/run_fx_weekly_backtest.py` from `backend_research/results/weekly_fx.json`. This is WKUI-02's deliverable. A "no-go" is a complete and valid outcome, not a failure to fix. No `app/` code changed this phase, and `run_weekly_sarimax_ets.py`'s frozen HDAN/PPAN results are untouched.

## Go/No-Go at a glance

| Model | MAPE (h=4, ~1mo) | MAPE (h=5, sensitivity) | Benchmark MAPE | Beats benchmark (h=4)? |
|---|---|---|---|---|
| SARIMAX(0, 1, 1) | 0.89% | 1.06% | 1.72% | yes |
| ETS-HoltDamped | 0.86% | 1.02% | 1.72% | yes |

**Overall verdict: go.** Computed rule: "go" if ANY record has beats_benchmark_h4 == True, otherwise "no-go" -- computed here from `records` in Python, never hand-typed.

## Horizon-matched methodology

`MIN_TRAIN_WEEKLY=104` -- examined specifically for FX's 865-row history: walk_forward_backtest uses an expanding window, so min_train only controls how early the first backtest origin starts, not a length-proportional fraction of burn-in. Phase 17 established 104 weeks (~2 years) as sufficient for SARIMAX/ETS to converge stably at weekly cadence for HDAN/PPAN; FX's data-generating process (a currency rate) is generally smoother / lower-variance-per-step than an ammonium-nitrate spot price, so nothing suggests FX needs MORE burn-in. Applied to FX's 865 rows this yields ~757 backtest origins, spanning FX's full 2011-2026 history. `HORIZON_WEEKLY=5` (covers a 5-week month); both h=4 (primary, closest to an actual 30-day month) and h=5 (secondary sensitivity) are extracted from the same walk_forward_backtest run via mape_by_horizon. The benchmark being compared against is the fixed monthly-native Naive/AR(1) figure -- 1.72% -- from `app/app/forecasting.py`'s `MODEL_INFO["fx_rate"]`, never re-derived here.

## Model detail

| Model | n_origins | failed_origins | MAPE (h=4) | MAPE (h=5) | Benchmark MAPE | Beats benchmark (h=4)? |
|---|---|---|---|---|---|---|
| SARIMAX(0, 1, 1) | 761 | 0 | 0.89% | 1.06% | 1.72% | yes |
| ETS-HoltDamped | 761 | 0 | 0.86% | 1.02% | 1.72% | yes |

## Closing WKUI-02

This report closes WKUI-02 regardless of the computed verdict (**go**). SARIMAX and Exponential Smoothing were backtested at weekly cadence for FX via the shared walk_forward_backtest harness, with an independently-examined MIN_TRAIN_WEEKLY for FX's 865-row history, and compared against the fixed monthly-native FX benchmark (1.72%) -- satisfying WKUI-02's requirement for a documented go/no-go against the existing monthly benchmark.
