# Phase 17: Weekly Forecast Re-Research Spike -- Research Report

Generated deterministically by `backend_research/weekly/run_weekly_sarimax_ets.py` from `backend_research/results/weekly_sarimax_ets.json`. This is WKLY-01/WKLY-02's deliverable. A "no-go" is a complete and valid outcome, not a failure to fix. No `app/` code changed this phase, and no weekly UI ships this milestone regardless of outcome.

## Prior spike recap

The prior weekly-cadence spike (`.planning/quick/20260821-weekly-an-backtest/`) ended in a no-go: its horizon-matched 4-week rollup of a plain weekly VAR(HDAN,PPAN) scored 10.35% (HDAN) and 16.01% (PPAN), both worse than the existing monthly-native VAR benchmark. That spike named two follow-ups this report closes: (a) test SARIMAX/exponential-smoothing at weekly cadence, since only VAR/OLS were tried before, and (b) resolve whether AN Data.csv's Baltic AN column and AN price weekly.csv's BalticAN_wk column are duplicate or independent signal. The prior plain weekly VAR(HDAN,PPAN) and OLS+Granger weekly-driver combination are not retested here.

## Go/No-Go at a glance

| Series | Model | Driver variant | MAPE (h=4, ~1mo) | MAPE (h=5, sensitivity) | Benchmark MAPE | Beats benchmark (h=4)? |
|---|---|---|---|---|---|---|
| HDAN | SARIMAX(0, 1, 0) | univariate | 7.32% | 8.62% | 9.49% | yes |
| HDAN | ETS-HoltDamped | univariate | 7.72% | 9.12% | 9.49% | yes |
| HDAN | SARIMAX(0, 1, 0)+BalticAN(exog, duplicate) | baltic_an_exog_duplicate | 7.25% | 8.51% | 9.49% | yes |
| PPAN | SARIMAX(0, 1, 0) | univariate | 7.17% | 8.60% | 10.08% | yes |
| PPAN | ETS-HoltDamped | univariate | 7.95% | 9.56% | 10.08% | yes |
| PPAN | SARIMAX(0, 1, 0)+BalticAN(exog, duplicate) | baltic_an_exog_duplicate | 6.96% | 8.32% | 10.08% | yes |

**Overall verdict: go.** Computed rule: "go" only if at least one record for EACH of HDAN and PPAN has beats_benchmark_h4 == True; otherwise "no-go". HDAN clears the benchmark: yes. PPAN clears the benchmark: yes.

## Horizon-matched methodology

`MIN_TRAIN_WEEKLY=104` (~2 years of weekly history before the first backtest origin) and `HORIZON_WEEKLY=5` (covers a 5-week month). Both h=4 (primary, closest to an actual 30-day month) and h=5 (secondary sensitivity) are extracted from the same walk_forward_backtest run via mape_by_horizon, per CONTEXT.md's instruction to match actual weeks-per-month rather than hardcode 4. The benchmark being compared against is the fixed monthly-native VAR(HDAN,PPAN) figures -- 9.49% (HDAN) / 10.08% (PPAN) -- from Phase 2, never re-derived in this report.

## Baltic-AN dedup resolution

Plan 01's measured comparison (`results/baltic_an_dedup.json`) found verdict=**duplicate** (n=206, corr=0.983, mean_abs_pct_diff=2.697%). Preferred column: AN Data.csv (Baltic AN). This drove the SARIMAX+exog record's driver-set choice below (`baltic_an_exog_duplicate`).

## Per-series detail

### HDAN -- Go/No-Go: go

| Model | Driver variant | n_origins | failed_origins | MAPE (h=4) | MAPE (h=5) | Benchmark MAPE | Beats benchmark (h=4)? |
|---|---|---|---|---|---|---|---|
| SARIMAX(0, 1, 0) | univariate | 102 | 0 | 7.32% | 8.62% | 9.49% | yes |
| ETS-HoltDamped | univariate | 102 | 0 | 7.72% | 9.12% | 9.49% | yes |
| SARIMAX(0, 1, 0)+BalticAN(exog, duplicate) | baltic_an_exog_duplicate | 102 | 0 | 7.25% | 8.51% | 9.49% | yes |

### PPAN -- Go/No-Go: go

| Model | Driver variant | n_origins | failed_origins | MAPE (h=4) | MAPE (h=5) | Benchmark MAPE | Beats benchmark (h=4)? |
|---|---|---|---|---|---|---|---|
| SARIMAX(0, 1, 0) | univariate | 102 | 0 | 7.17% | 8.60% | 10.08% | yes |
| ETS-HoltDamped | univariate | 102 | 0 | 7.95% | 9.56% | 10.08% | yes |
| SARIMAX(0, 1, 0)+BalticAN(exog, duplicate) | baltic_an_exog_duplicate | 102 | 0 | 6.96% | 8.32% | 10.08% | yes |

## Closing WKLY-01 / WKLY-02

This report closes both WKLY-01 and WKLY-02 regardless of the computed verdict (**go**). SARIMAX and Exponential Smoothing were backtested at weekly cadence for HDAN and PPAN via the shared walk_forward_backtest harness, extended with a Baltic-AN-deduped SARIMAX+exog driver-set variant, and compared against the fixed monthly VAR benchmark -- satisfying WKLY-01's requirement for genuinely new candidates tested with horizon-matched methodology, and WKLY-02's requirement for a documented go/no-go against the fixed benchmark.
