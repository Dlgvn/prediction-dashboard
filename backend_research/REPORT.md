# Phase 1 Backend Research — Consolidated Report

Generated from backend_research/results/*.json. Review before any Excel work starts.

## Executive Summary

Plain-language synthesis of the findings below, for the review gate. The raw JSON sections
that follow are the source of truth; this section interprets them.

### FX rate stationarity

FX rate's month-over-month % change is technically stationary (ADF p = 0.037, just under the
0.05 threshold), but it's borderline — the KPSS test (p = 0.10, at the boundary of its reportable
range) and the ADF statistic itself (-2.98, close to critical values) both suggest FX rate behaves
closer to a random walk than the commodity series (HDAN, PPAN, Diesel) do. % change is still the
right transform to use, but FX forecasts should be treated with more caution than the commodity
forecasts.

### Cross-series causality

| Relationship | Lag | F | p | Significant (p<0.10)? |
|---|---|---|---|---|
| HDAN <- PPAN | 1 | 9.07 | 0.004 | Yes — strongest link in the matrix |
| PPAN <- HDAN | 2 | 3.81 | 0.058 | Yes |
| HDAN <- Diesel | 2 | 3.57 | 0.066 | Yes (marginal) |
| FX_rate <- anything (Brent, HDAN, PPAN) | 1-3 | — | 0.22-0.98 | No |
| Diesel <- FX_rate | 1-3 | — | 0.30-0.51 | No |

HDAN and PPAN show mutual Granger causality — each helps predict the other, at different lags
(PPAN leads HDAN by 1 month strongly; HDAN leads PPAN by 2 months more weakly). This supports
modeling them jointly (see VAR results below). Diesel has a marginal, one-directional link into
HDAN. FX_rate shows no significant relationship (p<0.10) with any other series in either
direction — it behaves independently of the commodity series in this sample.

### Diesel-crude lag

Lag 2 is reconfirmed as the best defensible lag between Brent crude and diesel import price
(F = 3.34, p = 0.072), consistent with the design-time finding. No other lag (0, 1, 3, 4) comes
close.

### Single-series candidates

| Target | OLS+Granger (baseline) | Lasso | Ridge | ElasticNet |
|---|---|---|---|---|
| HDAN | **12.02%** | 19.78% | 19.91% | 19.80% |
| PPAN | **12.07%** | 18.20% | 18.42% | 18.25% |
| Diesel | **3.38%** | 4.33% | 4.42% | 4.36% |
| FX_rate | 0.25% (AR1-only) | — | — | — |

The hand-picked, sparse OLS+Granger baseline beats every regularized (Lasso/Ridge/ElasticNet)
alternative on all three targets it was tested against, often by a wide margin (HDAN/PPAN roughly
7-8 points better). With only ~44-45 usable months, the regularized models — offered the full
lag-1-through-3 set across every predictor — don't have enough data to out-shrink a few
well-chosen lags. FX_rate's 0.25% MAPE from an AR1-only model is not a genuine modeling win; it
just reflects how low FX_rate's month-to-month volatility is.

### VAR candidates

| Combo | HDAN | PPAN | Diesel | FX_rate |
|---|---|---|---|---|
| VAR(HDAN, PPAN) | **9.49%** | **10.08%** | — | — |
| VAR(HDAN, PPAN, Diesel) | 10.17% | 13.64% | 3.43% | — |
| VAR(HDAN, PPAN, FX_rate) | 9.46% | 10.58% | — | 0.22% |
| VAR(HDAN, PPAN, Diesel, FX_rate) | 10.31% | 13.85% | 3.39% | 0.26% |

The bivariate VAR(HDAN, PPAN) is the clear winner overall — it beats the OLS+Granger baseline on
both series (9.49%/10.08% vs. 12.02%/12.07%) and lines up with the earlier documented result
(8.9%/10.5%). Adding Diesel to the VAR does not help, and specifically hurts PPAN (13.6-13.9% in
both 3-way and 4-way combos that include Diesel). Diesel itself is essentially unaffected by
being in a VAR (~3.4%, tied with its own OLS baseline of 3.38%) — it doesn't need HDAN/PPAN/FX
as VAR partners.

### SARIMAX tuned

| Target | Best order | MAPE | vs. untuned (1,1,0) baseline |
|---|---|---|---|
| HDAN | (0,0,1) | 19.08% | 26.7% -> 19.08% (improved) |
| PPAN | (0,0,2) | 19.60% | 29.0% -> 19.60% (improved) |

Tuning meaningfully improves SARIMAX over the untuned baseline, but tuned SARIMAX still trails
both OLS+Granger (12.02%/12.07%) and VAR (9.49%/10.08%) substantially. SARIMAX is not competitive
for this dataset regardless of tuning.

### Markup comparison

| Treatment | Holdout MAPE |
|---|---|
| Fixed 9% | 10.27% |
| Trailing 12-month average | 10.54% |
| **Full-history average** | **9.25%** (markup ratio ≈ 1.0282, i.e. ~2.82%) |

Full-history average markup is the empirical backtest winner, narrowly beating fixed-9% (9.25%
vs. 10.27% MAPE) and trailing-12mo average (10.54%). **Important caveat, to be weighed explicitly
at the review gate, not auto-applied:** the winning treatment's actual markup value is ~2.82%,
far below the business's stated 9% markup rule. This gap may reflect a real historical average
that simply differs from the intended business rule, or it may reflect a recent contract/pricing
change not yet fully reflected in the historical window. Because this has real pricing
implications, it needs an explicit human decision, not an automatic pick of whichever number
minimizes backtest MAPE.

### Interval calibration

| Target | Backtest-error coverage | Analytic OLS coverage | Target |
|---|---|---|---|
| HDAN | 0.583 | 0.750 | 0.95 |
| PPAN | 0.667 | 0.917 | 0.95 |
| Diesel | 0.750 | 0.750 | 0.95 |

None of the six coverage checks (2 methods x 3 targets) reach the 0.95 target. Analytic OLS
prediction intervals are consistently closer to 95% than backtest-error bands across all three
targets (and strictly better for HDAN and PPAN), so analytic OLS is the recommended interval
method. But the systematic under-coverage itself — actual forecast errors falling outside the
stated interval more often than a 95% interval should allow — is a real, disclosable finding, not
noise to explain away. It likely reflects structural breaks (e.g., the 2026 Hormuz-related price
spike) that the fitted sample doesn't fully capture. This should be stated plainly in any
downstream reporting of forecast intervals, not hidden behind a nominal "95% interval" label.

## single_series_candidates

```json
[
  {
    "model": "OLS",
    "target": "HDAN",
    "mape": 12.02,
    "n": 45,
    "predictors": {
      "Baltic AN": 1,
      "Ammonia": 2,
      "Urea": 1
    },
    "r2": 0.318
  },
  {
    "model": "OLS",
    "target": "PPAN",
    "mape": 12.07,
    "n": 45,
    "predictors": {
      "Baltic AN": 1,
      "Urea": 1,
      "Brent": 2
    },
    "r2": 0.074
  },
  {
    "model": "OLS",
    "target": "Diesel_usd_ton",
    "mape": 3.38,
    "n": 74,
    "predictors": {
      "Brent_usd_ton": 2
    },
    "r2": 0.244
  },
  {
    "model": "OLS",
    "target": "FX_rate",
    "mape": 0.25,
    "n": 75,
    "predictors": {},
    "r2": 0.393
  },
  {
    "model": "Lasso",
    "target": "HDAN",
    "mape": 19.78,
    "n": 44,
    "selected_features": [
      "PPAN_lag1",
      "PPAN_lag2",
      "PPAN_lag3",
      "Baltic AN_lag2",
      "Baltic AN_lag3",
      "Ammonia_lag1",
      "Ammonia_lag2",
      "Ammonia_lag3",
      "Urea_lag1",
      "Urea_lag2",
      "Urea_lag3",
      "Natural_gas_lag1",
      "Natural_gas_lag2",
      "Natural_gas_lag3",
      "Brent_lag1",
      "Brent_lag2",
      "Brent_lag3"
    ]
  },
  {
    "model": "Ridge",
    "target": "HDAN",
    "mape": 19.91,
    "n": 44,
    "selected_features": [
      "PPAN_lag1",
      "PPAN_lag2",
      "PPAN_lag3",
      "Baltic AN_lag1",
      "Baltic AN_lag2",
      "Baltic AN_lag3",
      "Ammonia_lag1",
      "Ammonia_lag2",
      "Ammonia_lag3",
      "Urea_lag1",
      "Urea_lag2",
      "Urea_lag3",
      "Natural_gas_lag1",
      "Natural_gas_lag2",
      "Natural_gas_lag3",
      "Brent_lag1",
      "Brent_lag2",
      "Brent_lag3"
    ]
  },
  {
    "model": "ElasticNet",
    "target": "HDAN",
    "mape": 19.8,
    "n": 44,
    "selected_features": [
      "PPAN_lag1",
      "PPAN_lag2",
      "PPAN_lag3",
      "Baltic AN_lag2",
      "Baltic AN_lag3",
      "Ammonia_lag1",
      "Ammonia_lag2",
      "Ammonia_lag3",
      "Urea_lag1",
      "Urea_lag2",
      "Urea_lag3",
      "Natural_gas_lag1",
      "Natural_gas_lag2",
      "Natural_gas_lag3",
      "Brent_lag1",
      "Brent_lag2",
      "Brent_lag3"
    ]
  },
  {
    "model": "Lasso",
    "target": "PPAN",
    "mape": 18.2,
    "n": 44,
    "selected_features": [
      "HDAN_lag1",
      "HDAN_lag2",
      "HDAN_lag3",
      "Baltic AN_lag2",
      "Baltic AN_lag3",
      "Ammonia_lag1",
      "Ammonia_lag2",
      "Ammonia_lag3",
      "Urea_lag1",
      "Urea_lag2",
      "Urea_lag3",
      "Natural_gas_lag1",
      "Natural_gas_lag2",
      "Natural_gas_lag3",
      "Brent_lag1",
      "Brent_lag2",
      "Brent_lag3"
    ]
  },
  {
    "model": "Ridge",
    "target": "PPAN",
    "mape": 18.42,
    "n": 44,
    "selected_features": [
      "HDAN_lag1",
      "HDAN_lag2",
      "HDAN_lag3",
      "Baltic AN_lag1",
      "Baltic AN_lag2",
      "Baltic AN_lag3",
      "Ammonia_lag1",
      "Ammonia_lag2",
      "Ammonia_lag3",
      "Urea_lag1",
      "Urea_lag2",
      "Urea_lag3",
      "Natural_gas_lag1",
      "Natural_gas_lag2",
      "Natural_gas_lag3",
      "Brent_lag1",
      "Brent_lag2",
      "Brent_lag3"
    ]
  },
  {
    "model": "ElasticNet",
    "target": "PPAN",
    "mape": 18.25,
    "n": 44,
    "selected_features": [
      "HDAN_lag1",
      "HDAN_lag2",
      "HDAN_lag3",
      "Baltic AN_lag1",
      "Baltic AN_lag2",
      "Baltic AN_lag3",
      "Ammonia_lag1",
      "Ammonia_lag2",
      "Ammonia_lag3",
      "Urea_lag1",
      "Urea_lag2",
      "Urea_lag3",
      "Natural_gas_lag1",
      "Natural_gas_lag2",
      "Natural_gas_lag3",
      "Brent_lag1",
      "Brent_lag2",
      "Brent_lag3"
    ]
  },
  {
    "model": "Lasso",
    "target": "Diesel_usd_ton",
    "mape": 4.33,
    "n": 73,
    "selected_features": [
      "Brent_usd_ton_lag1",
      "Brent_usd_ton_lag2",
      "Brent_usd_ton_lag3",
      "FX_rate_lag2",
      "FX_rate_lag3",
      "Diesel_usd_liter_lag1",
      "Diesel_usd_liter_lag2",
      "Diesel_usd_liter_lag3",
      "Purchase_mnt_liter_lag1",
      "Purchase_mnt_liter_lag2",
      "Purchase_mnt_liter_lag3",
      "Urals_usd_bbl_lag1",
      "Urals_usd_bbl_lag2",
      "Urals_usd_bbl_lag3"
    ]
  },
  {
    "model": "Ridge",
    "target": "Diesel_usd_ton",
    "mape": 4.42,
    "n": 73,
    "selected_features": [
      "Brent_usd_ton_lag1",
      "Brent_usd_ton_lag2",
      "Brent_usd_ton_lag3",
      "FX_rate_lag1",
      "FX_rate_lag2",
      "FX_rate_lag3",
      "Diesel_usd_liter_lag1",
      "Diesel_usd_liter_lag2",
      "Diesel_usd_liter_lag3",
      "Purchase_mnt_liter_lag1",
      "Purchase_mnt_liter_lag2",
      "Purchase_mnt_liter_lag3",
      "Urals_usd_bbl_lag1",
      "Urals_usd_bbl_lag2",
      "Urals_usd_bbl_lag3"
    ]
  },
  {
    "model": "ElasticNet",
    "target": "Diesel_usd_ton",
    "mape": 4.36,
    "n": 73,
    "selected_features": [
      "Brent_usd_ton_lag1",
      "Brent_usd_ton_lag2",
      "FX_rate_lag2",
      "FX_rate_lag3",
      "Diesel_usd_liter_lag1",
      "Diesel_usd_liter_lag2",
      "Diesel_usd_liter_lag3",
      "Purchase_mnt_liter_lag1",
      "Purchase_mnt_liter_lag2",
      "Purchase_mnt_liter_lag3",
      "Urals_usd_bbl_lag1",
      "Urals_usd_bbl_lag2",
      "Urals_usd_bbl_lag3"
    ]
  }
]
```

## diesel_crude_lag

```json
{
  "all_lags": [
    {
      "lag": 0,
      "F": 1.441,
      "p": 0.2339,
      "n": 75
    },
    {
      "lag": 1,
      "F": 0.183,
      "p": 0.6702,
      "n": 75
    },
    {
      "lag": 2,
      "F": 3.339,
      "p": 0.0718,
      "n": 74
    },
    {
      "lag": 3,
      "F": 1.553,
      "p": 0.2168,
      "n": 73
    },
    {
      "lag": 4,
      "F": 0.481,
      "p": 0.4903,
      "n": 72
    }
  ],
  "selected": {
    "lag": 2,
    "F": 3.339,
    "p": 0.0718,
    "n": 74
  }
}
```

## var_candidates

```json
[
  {
    "cols": [
      "HDAN",
      "PPAN"
    ],
    "lag_order": 1,
    "mape_by_series": {
      "HDAN": 9.49,
      "PPAN": 10.08
    }
  },
  {
    "cols": [
      "HDAN",
      "PPAN",
      "Diesel_usd_ton"
    ],
    "lag_order": 1,
    "mape_by_series": {
      "HDAN": 10.17,
      "PPAN": 13.64,
      "Diesel_usd_ton": 3.43
    }
  },
  {
    "cols": [
      "HDAN",
      "PPAN",
      "FX_rate"
    ],
    "lag_order": 1,
    "mape_by_series": {
      "HDAN": 9.46,
      "PPAN": 10.58,
      "FX_rate": 0.22
    }
  },
  {
    "cols": [
      "HDAN",
      "PPAN",
      "Diesel_usd_ton",
      "FX_rate"
    ],
    "lag_order": 1,
    "mape_by_series": {
      "HDAN": 10.31,
      "PPAN": 13.85,
      "Diesel_usd_ton": 3.39,
      "FX_rate": 0.26
    }
  }
]
```

## stationarity_fx

```json
{
  "series": "FX_rate_pct_change",
  "n": 76,
  "adf_stat": -2.9754428561918167,
  "adf_pvalue": 0.03725224385036396,
  "kpss_stat": 0.155399051336881,
  "kpss_pvalue": 0.1,
  "stationary_verdict": "stationary"
}
```

## markup_comparison

```json
{
  "fixed_9pct": 10.27,
  "trailing_12mo_avg": 10.54,
  "full_history_avg": 9.25,
  "full_history_avg_value": 1.0282
}
```

## causality_matrix

```json
[
  {
    "target": "FX_rate",
    "predictor": "Brent_usd_ton",
    "lag": 1,
    "F": 0.071,
    "p": 0.791,
    "n": 45,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "Brent_usd_ton",
    "lag": 2,
    "F": 0.117,
    "p": 0.7338,
    "n": 44,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "Brent_usd_ton",
    "lag": 3,
    "F": 0.098,
    "p": 0.7561,
    "n": 43,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "HDAN",
    "lag": 1,
    "F": 0.0,
    "p": 0.9848,
    "n": 45,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "HDAN",
    "lag": 2,
    "F": 0.455,
    "p": 0.5037,
    "n": 44,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "HDAN",
    "lag": 3,
    "F": 1.519,
    "p": 0.2249,
    "n": 43,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "PPAN",
    "lag": 1,
    "F": 0.02,
    "p": 0.8878,
    "n": 45,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "PPAN",
    "lag": 2,
    "F": 0.567,
    "p": 0.4556,
    "n": 44,
    "significant_p10": false
  },
  {
    "target": "FX_rate",
    "predictor": "PPAN",
    "lag": 3,
    "F": 0.294,
    "p": 0.5904,
    "n": 43,
    "significant_p10": false
  },
  {
    "target": "Diesel_usd_ton",
    "predictor": "FX_rate",
    "lag": 1,
    "F": 1.107,
    "p": 0.2987,
    "n": 45,
    "significant_p10": false
  },
  {
    "target": "Diesel_usd_ton",
    "predictor": "FX_rate",
    "lag": 2,
    "F": 0.439,
    "p": 0.5111,
    "n": 44,
    "significant_p10": false
  },
  {
    "target": "Diesel_usd_ton",
    "predictor": "FX_rate",
    "lag": 3,
    "F": 0.696,
    "p": 0.4091,
    "n": 43,
    "significant_p10": false
  },
  {
    "target": "HDAN",
    "predictor": "Diesel_usd_ton",
    "lag": 1,
    "F": 0.299,
    "p": 0.5875,
    "n": 45,
    "significant_p10": false
  },
  {
    "target": "HDAN",
    "predictor": "Diesel_usd_ton",
    "lag": 2,
    "F": 3.565,
    "p": 0.0661,
    "n": 44,
    "significant_p10": true
  },
  {
    "target": "HDAN",
    "predictor": "Diesel_usd_ton",
    "lag": 3,
    "F": 0.933,
    "p": 0.3399,
    "n": 43,
    "significant_p10": false
  },
  {
    "target": "PPAN",
    "predictor": "Diesel_usd_ton",
    "lag": 1,
    "F": 0.0,
    "p": 0.998,
    "n": 45,
    "significant_p10": false
  },
  {
    "target": "PPAN",
    "predictor": "Diesel_usd_ton",
    "lag": 2,
    "F": 1.783,
    "p": 0.1892,
    "n": 44,
    "significant_p10": false
  },
  {
    "target": "PPAN",
    "predictor": "Diesel_usd_ton",
    "lag": 3,
    "F": 2.716,
    "p": 0.1072,
    "n": 43,
    "significant_p10": false
  },
  {
    "target": "HDAN",
    "predictor": "PPAN",
    "lag": 1,
    "F": 9.066,
    "p": 0.0044,
    "n": 45,
    "significant_p10": true
  },
  {
    "target": "HDAN",
    "predictor": "PPAN",
    "lag": 2,
    "F": 0.047,
    "p": 0.829,
    "n": 44,
    "significant_p10": false
  },
  {
    "target": "HDAN",
    "predictor": "PPAN",
    "lag": 3,
    "F": 0.064,
    "p": 0.8016,
    "n": 43,
    "significant_p10": false
  },
  {
    "target": "PPAN",
    "predictor": "HDAN",
    "lag": 1,
    "F": 0.674,
    "p": 0.4164,
    "n": 45,
    "significant_p10": false
  },
  {
    "target": "PPAN",
    "predictor": "HDAN",
    "lag": 2,
    "F": 3.812,
    "p": 0.0577,
    "n": 44,
    "significant_p10": true
  },
  {
    "target": "PPAN",
    "predictor": "HDAN",
    "lag": 3,
    "F": 0.269,
    "p": 0.6067,
    "n": 43,
    "significant_p10": false
  }
]
```

## sarimax_tuned

```json
[
  {
    "target": "HDAN",
    "order": [
      0,
      0,
      1
    ],
    "mape": 19.08
  },
  {
    "target": "PPAN",
    "order": [
      0,
      0,
      2
    ],
    "mape": 19.6
  }
]
```

## interval_calibration

```json
[
  {
    "target": "HDAN",
    "n_holdout": 12,
    "backtest_error_coverage": 0.583,
    "analytic_ols_coverage": 0.75,
    "target_coverage": 0.95
  },
  {
    "target": "PPAN",
    "n_holdout": 12,
    "backtest_error_coverage": 0.667,
    "analytic_ols_coverage": 0.917,
    "target_coverage": 0.95
  },
  {
    "target": "Diesel_usd_ton",
    "n_holdout": 12,
    "backtest_error_coverage": 0.75,
    "analytic_ols_coverage": 0.75,
    "target_coverage": 0.95
  }
]
```

## Weekly cadence (Phase 1 follow-up, 2026-08-21)

Follow-up to the analysis above, prompted by two things: (1) `AN Data.csv` turns out to already
be **native weekly** for HDAN/PPAN (rows ~7 days apart) — the original research resampled it to
monthly (last-of-month) without testing the native cadence directly; (2) a second file, `AN price
weekly.csv`, supplies weekly drivers not previously available (JKM/Henry Hub/UK/Netherlands
natural gas, US/China corn, Middle East Ammonia, Black Sea/China Urea). Together these directly
address the "Baltic AN proxy for HDAN/PPAN is unvalidated" weekly-mode blocker in `.planning/STATE.md`.

Code: `data_loader.load_an_weekly()`, `load_weekly_drivers()`, `merged_weekly()`;
`run_weekly_candidates.py`; results in `results/weekly_candidates.json`.

### One-step-ahead (week-over-week) MAPE

| Model | HDAN | PPAN |
|---|---|---|
| Naive (last value) | 3.44% | 4.66% |
| VAR(HDAN, PPAN), weekly, order=4 | 3.37% | 4.31% |
| OLS+Granger, weekly, monthly's predictor set | 3.55% | 4.75% |
| OLS+Granger, weekly, + new weekly drivers | **3.15%** | **3.98%** |

Adding the new weekly drivers (Middle East Ammonia, Black Sea/China Urea, gas benchmarks) gives
the best one-step MAPE for both series, beating naive and the weekly VAR. But this is a shallow
win: R² is only 0.031 (HDAN) / 0.044 (PPAN), meaning these regressions explain very little
variance week-to-week — most of the "accuracy" here is naive-like persistence (AN prices move
little week-over-week), not real predictive signal. **Weekly one-step MAPE is not directly
comparable to the monthly VAR's 9.49%/10.08%** — a week moves less than a month does by
construction, so a lower number here doesn't mean a better model.

### Horizon-matched comparison (rolled forward 4 weeks ≈ 1 month)

To answer the actual question — does weekly-native data forecast ~1 month out at least as well
as the existing monthly VAR — the weekly VAR(HDAN,PPAN) was rolled forward 4 steps and compared
against actual prices 4 weeks later, on a rolling-origin basis:

| Model | HDAN | PPAN |
|---|---|---|
| Monthly-native VAR(HDAN,PPAN) (existing result, 1-month-ahead) | 9.49% | 10.08% |
| Weekly-native VAR(HDAN,PPAN), 4-week-ahead | 10.35% | **16.01%** |

The weekly-rolled forecast is worse on both series, and substantially worse on PPAN — compounding
four weekly one-step forecasts accumulates more error than fitting the monthly-native VAR
directly, and the rolling-origin holdout here is thin (n=9 windows), so this comparison itself
should be treated as indicative, not conclusive.

### Go/no-go recommendation

**No-go, for now.** The two weekly data sources close the *data availability* gap (native weekly
HDAN/PPAN exists, and new weekly drivers exist), but the *modeling* result doesn't support
switching to or adding a weekly forecast mode yet: the new drivers' one-step improvement is weak
(low R²) and likely reflects AN price persistence rather than real signal, and the horizon-matched
4-week rollup underperforms the existing monthly VAR, especially for PPAN. Two follow-ups worth
doing before revisiting this: (a) test SARIMAX/exponential-smoothing at weekly cadence rather than
only VAR/OLS, since the monthly SARIMAX exploration wasn't repeated here; (b) sanity-check whether
`AN price weekly.csv`'s own Baltic AN series should replace `AN Data.csv`'s Baltic AN column, since
they may be duplicate/overlapping sources rather than independent signal.

## Open decisions for review

- [ ] HDAN/PPAN: keep current OLS+Granger, or replace with VAR/other winner? -> RECOMMEND: replace with bivariate VAR(HDAN, PPAN) — clear win on both series (9.49%/10.08% vs. 12.02%/12.07% OLS+Granger baseline), and adding Diesel or FX to the VAR only hurts PPAN.
- [ ] FX rate: which model, which predictors/lags? -> RECOMMEND: no cross-series predictor is defensible — causality matrix shows nothing reaches p<0.10 for FX_rate in either direction, so an AR1-only (or simple) univariate model is the honest choice; treat FX as structurally independent of the commodity series.
- [ ] Diesel-MNT markup: fixed 9%, trailing 12mo average, or other? -> RECOMMEND: full-history average (9.25% MAPE) is the empirical backtest winner, but its implied markup (~2.82%) is far below the stated 9% business rule — flag this discrepancy to the user explicitly before adopting it; do not auto-apply the backtest winner without confirming whether 9% reflects a newer contract not yet in the historical data.
- [ ] Interval method: backtest-error, analytic OLS, or per-series mixed? -> RECOMMEND: analytic OLS — consistently closer to 0.95 coverage than backtest-error across all three targets — but disclose that even analytic OLS under-covers on all three series (0.75-0.917), likely due to structural breaks (e.g. 2026 Hormuz spike) not captured in the fitted sample.
- [ ] Diesel import-price lag: confirmed at 2, or does Task 4 disagree? -> RECOMMEND: confirmed at lag 2 (F=3.34, p=0.072), consistent with the design-time finding; no other lag comes close.