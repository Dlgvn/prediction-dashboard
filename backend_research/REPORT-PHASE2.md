# Phase 2: Model Research & Backtesting -- Research Report

Generated deterministically by `assemble_report_v2.py` from `backend_research/results/wf_*.json` and the supporting predictor/cointegration/volatility screens. This is FCST-07's deliverable: a research report naming the backtested winner per series before any model reaches Phase 3.

## Winners at a glance

| Series | Winning model | Strategy | Mean MAPE 1-12 | h=12 MAPE | Volatility source |
|---|---|---|---|---|---|
| HDAN | SARIMAX(0, 1, 0)+exog | iterative | 13.33% | n/a% | garch |
| PPAN | Direct-OLS VAR-system(h=1..12) system=[ppan, hdan, baltic_an, urals] | direct | 23.80% | 35.90% | arima_forecast_se |
| Diesel-USD | Naive | iterative | 7.04% | 7.69% | arima_forecast_se |
| FX rate | Naive | iterative | 1.72% | 2.98% | arima_forecast_se |

## Which assumption won

Each method family bets on a different mechanism: **time-series** bets the past pattern continues (Naive/ETS/ARIMA); **causal/econometric** bets a screened driver leads the price (SARIMAX-with-exog, VAR, VECM); **ML** bets nonlinear feature interactions matter (RandomForest/GradientBoosting). Per series, the data supported:

- **HDAN**: causal/econometric (screened exogenous drivers) won (SARIMAX(0, 1, 0)+exog, 13.33% mean MAPE).
- **PPAN**: causal/econometric (VAR system) won (Direct-OLS VAR-system(h=1..12) system=[ppan, hdan, baltic_an, urals], 23.80% mean MAPE).
- **Diesel-USD**: time-series (naive persistence) won (Naive, 7.04% mean MAPE).
- **FX rate**: time-series (naive persistence) won (Naive, 1.72% mean MAPE).

## Per-series ranking tables

### HDAN

| Model | Family | Strategy | h=1 | h=6 | h=12 | Mean 1-12 | Single-holdout |
|---|---|---|---|---|---|---|---|
| RandomForest | ml | direct | 5.91% | n/a% | n/a% | 4.79% | 28.34% |
| RandomForest | ml | iterative | 5.91% | n/a% | n/a% | 7.78% | 32.41% |
| SARIMAX(0, 1, 0)+exog | sarimax | iterative | 9.48% | 11.44% | n/a% | 13.33% | 8.76% |
| GradientBoosting | ml | direct | 17.84% | n/a% | n/a% | 14.42% | 31.06% |
| GradientBoosting | ml | iterative | 17.84% | n/a% | n/a% | 21.07% | 34.77% |
| Direct-OLS VAR-system(h=1..12) system=[hdan, ppan, urea_china, urea_black_sea] | var | direct | 9.16% | 23.92% | 38.93% | 25.32% | n/a% |
| ARIMA(0, 1, 0) | arima | iterative | 9.65% | 25.56% | 33.50% | 25.42% | 24.13% |
| Naive | baseline | iterative | 9.65% | 25.56% | 33.50% | 25.42% | 24.13% |
| SES | ets | iterative | 9.67% | 25.55% | 33.50% | 25.42% | 24.13% |
| MovingAverage(3) | baseline | iterative | 14.07% | 25.23% | 32.57% | 26.25% | 23.06% |
| HoltDamped | ets | iterative | 10.44% | 26.36% | 37.28% | 27.02% | 26.55% |
| Direct-OLS+exog(h=1..12) | sarimax | direct | 17.33% | 41.66% | n/a% | 37.09% | n/a% |
| VAR(lag=1) system=[hdan, ppan, urea_china, urea_black_sea] | var | iterative | 7.53% | 31.58% | 12682.56% | 1169.51% | n/a% |

### PPAN

| Model | Family | Strategy | h=1 | h=6 | h=12 | Mean 1-12 | Single-holdout |
|---|---|---|---|---|---|---|---|
| RandomForest | ml | direct | 10.48% | n/a% | n/a% | 12.14% | 30.43% |
| RandomForest | ml | iterative | 10.48% | n/a% | n/a% | 15.29% | 29.34% |
| GradientBoosting | ml | direct | 16.10% | n/a% | n/a% | 15.61% | 30.62% |
| GradientBoosting | ml | iterative | 16.10% | n/a% | n/a% | 21.97% | 28.40% |
| Direct-OLS VAR-system(h=1..12) system=[ppan, hdan, baltic_an, urals] | var | direct | 8.50% | 17.78% | 35.90% | 23.80% | n/a% |
| ARIMA(0, 1, 0) | arima | iterative | 11.81% | 26.24% | 32.72% | 27.53% | 26.61% |
| Naive | baseline | iterative | 11.81% | 26.24% | 32.72% | 27.53% | 26.61% |
| SES | ets | iterative | 11.81% | 26.24% | 32.72% | 27.53% | 26.61% |
| SARIMAX(0, 1, 0)+exog | sarimax | iterative | 12.63% | 31.07% | n/a% | 28.05% | 29.64% |
| MovingAverage(3) | baseline | iterative | 16.55% | 27.49% | 32.72% | 28.90% | 26.61% |
| HoltDamped | ets | iterative | 12.45% | 27.35% | 36.85% | 29.25% | 29.16% |
| Direct-OLS+exog(h=1..12) | sarimax | direct | 15.32% | 37.32% | n/a% | 37.57% | n/a% |
| VAR(lag=1) system=[ppan, hdan, baltic_an, urals] | var | iterative | 10.30% | 4.273e+06% | 1.038e+34% | 8.649e+32% | n/a% |

### Diesel-USD

| Model | Family | Strategy | h=1 | h=6 | h=12 | Mean 1-12 | Single-holdout |
|---|---|---|---|---|---|---|---|
| Naive | baseline | iterative | 2.34% | 8.40% | 7.69% | 7.04% | 7.66% |
| SES | ets | iterative | 2.34% | 8.40% | 7.69% | 7.04% | 7.66% |
| MovingAverage(3) | baseline | iterative | 3.72% | 9.13% | 7.81% | 7.61% | 7.77% |
| ARIMA(1, 1, 1) | arima | iterative | 1.97% | 8.39% | 10.07% | 7.71% | 10.98% |
| HoltDamped | ets | iterative | 2.07% | 8.64% | 10.23% | 7.89% | 11.24% |
| Direct-OLS VAR-system(h=1..12) system=[diesel_usd_ton, urea_china, ppan, natural_gas_jkm] | var | direct | 3.80% | 10.20% | 11.99% | 9.12% | n/a% |
| Direct-OLS+exog(h=1..12) | sarimax | direct | 5.88% | 19.73% | n/a% | 11.31% | n/a% |
| RandomForest | ml | direct | 12.55% | n/a% | n/a% | 11.90% | 9.32% |
| GradientBoosting | ml | direct | 13.00% | n/a% | n/a% | 11.93% | 9.42% |
| RandomForest | ml | iterative | 12.55% | n/a% | n/a% | 12.65% | 8.38% |
| SARIMAX(1, 1, 1)+exog | sarimax | iterative | 4.59% | 15.30% | n/a% | 13.35% | 6.42% |
| GradientBoosting | ml | iterative | 13.00% | n/a% | n/a% | 13.65% | 7.98% |
| VAR(lag=1) system=[diesel_usd_ton, urea_china, ppan, natural_gas_jkm] | var | iterative | 2.70% | 13.62% | 162427.19% | 13954.84% | n/a% |

### FX rate

| Model | Family | Strategy | h=1 | h=6 | h=12 | Mean 1-12 | Single-holdout |
|---|---|---|---|---|---|---|---|
| Naive | baseline | iterative | 0.39% | 1.60% | 2.98% | 1.72% | 0.31% |
| SES | ets | iterative | 0.39% | 1.60% | 2.98% | 1.72% | 0.31% |
| MovingAverage(3) | baseline | iterative | 0.70% | 1.74% | 3.11% | 1.88% | 0.39% |
| HoltDamped | ets | iterative | 0.33% | 1.99% | 3.37% | 1.98% | 0.53% |
| SARIMAX(1, 1, 2)+exog | sarimax | iterative | 0.52% | 2.16% | 3.70% | 2.24% | 0.64% |
| ARIMA(1, 1, 2) | arima | iterative | 0.32% | 2.14% | 4.01% | 2.25% | 1.75% |
| GradientBoosting | ml | iterative | 1.15% | 2.92% | 4.49% | 2.99% | 1.27% |
| RandomForest | ml | iterative | 1.52% | 3.64% | 4.59% | 3.51% | 2.06% |
| GradientBoosting | ml | direct | 1.15% | 4.51% | 6.35% | 4.18% | 4.55% |
| RandomForest | ml | direct | 1.52% | 4.01% | 7.10% | 4.52% | 4.50% |
| Direct-OLS VAR-system(h=1..12) system=[fx_rate, diesel_usd_ton, natural_gas_uk, urea_china] | var | direct | 1.07% | 5.03% | 13.78% | 6.15% | n/a% |
| Direct-OLS+exog(h=1..12) | sarimax | direct | 0.76% | 5.05% | 22.16% | 7.26% | n/a% |
| VAR(lag=1) system=[fx_rate, diesel_usd_ton, natural_gas_uk, urea_china] | var | iterative | 0.52% | 347.66% | 4.923e+26% | 4.103e+25% | n/a% |

## Iterative vs. direct multi-step (D-06)

D-06 requires comparing iterative and direct multi-step forecasting per series and horizon band rather than committing to one upfront -- the answer is allowed to differ by series.

### HDAN

| Horizon band | Iterative mean MAPE | Direct mean MAPE | Winner |
|---|---|---|---|
| 1-3 | 14.99% | 14.86% | direct |
| 4-6 | 22.03% | 27.89% | iterative |
| 7-12 | 364.77% | 39.49% | direct |

### PPAN

| Horizon band | Iterative mean MAPE | Direct mean MAPE | Winner |
|---|---|---|---|
| 1-3 | 18.83% | 17.19% | direct |
| 4-6 | 204439.76% | 28.23% | direct |
| 7-12 | 2.531e+32% | 37.56% | direct |

### Diesel-USD

| Horizon band | Iterative mean MAPE | Direct mean MAPE | Winner |
|---|---|---|---|
| 1-3 | 6.00% | 8.53% | iterative |
| 4-6 | 8.85% | 12.19% | iterative |
| 7-12 | 4193.90% | 11.18% | direct |

### FX rate

| Horizon band | Iterative mean MAPE | Direct mean MAPE | Winner |
|---|---|---|---|
| 1-3 | 1.10% | 1.81% | iterative |
| 4-6 | 16.38% | 3.87% | direct |
| 7-12 | 9.117e+24% | 8.21% | direct |

The iterative VAR family shows explosive MAPE at long horizons for several series (short-overlap predictor data compounding error through the recursion); the direct-OLS VAR variant stays bounded and is the safer family choice where VAR is used at all (see 02-05-SUMMARY.md).

## Predictor screen (D-04/D-05)

### HDAN

| Predictor | Lag | p-value | Tier |
|---|---|---|---|
| ppan | 1 | 0.0030 | p05 |
| urea_china | 1 | 0.0191 | p05 |
| urea_black_sea | 1 | 0.0332 | p05 |
| ammonia | 3 | 0.0410 | p05 |
| baltic_an | 1 | 0.0428 | p05 |
| ammonia | 2 | 0.0474 | p05 |
| baltic_an | 2 | 0.0637 | p10 |
| corn_us | 1 | 0.0736 | p10 |
| urals | 1 | 0.0807 | p10 |
| natural_gas_netherlands | 2 | 0.0869 | p10 |
| brent | 1 | 0.0989 | p10 |

### PPAN

| Predictor | Lag | p-value | Tier |
|---|---|---|---|
| baltic_an | 1 | 0.0453 | p05 |
| urals | 3 | 0.0673 | p10 |
| urea_china | 1 | 0.0691 | p10 |
| brent | 1 | 0.0876 | p10 |
| natural_gas_netherlands | 2 | 0.0998 | p10 |

### Diesel-USD

| Predictor | Lag | p-value | Tier |
|---|---|---|---|
| urea_china | 2 | 0.0021 | p05 |
| ppan | 1 | 0.0021 | p05 |
| natural_gas_jkm | 3 | 0.0039 | p05 |
| natural_gas_netherlands | 3 | 0.0046 | p05 |
| ammonia | 1 | 0.0080 | p05 |
| ammonia | 2 | 0.0115 | p05 |
| urea_china | 1 | 0.0208 | p05 |
| natural_gas_jkm | 1 | 0.0311 | p05 |
| urea_black_sea | 3 | 0.0346 | p05 |
| hdan | 1 | 0.0409 | p05 |
| natural_gas_jkm | 2 | 0.0428 | p05 |
| natural_gas_netherlands | 1 | 0.0450 | p05 |
| corn_us | 1 | 0.0545 | p10 |
| baltic_an | 3 | 0.0615 | p10 |
| corn_us | 2 | 0.0618 | p10 |
| natural_gas_henry_hub | 2 | 0.0698 | p10 |
| baltic_an | 2 | 0.0733 | p10 |
| brent | 2 | 0.0799 | p10 |
| urea_black_sea | 1 | 0.0829 | p10 |

### FX rate

| Predictor | Lag | p-value | Tier |
|---|---|---|---|
| diesel_usd_ton | 3 | 0.0000 | p05 |
| natural_gas_uk | 1 | 0.0046 | p05 |
| urea_china | 2 | 0.0084 | p05 |
| urea_black_sea | 1 | 0.0143 | p05 |
| natural_gas_netherlands | 1 | 0.0400 | p05 |
| natural_gas_jkm | 1 | 0.0526 | p10 |
| corn_us | 1 | 0.0622 | p10 |
| ammonia | 2 | 0.0689 | p10 |
| urea_black_sea | 2 | 0.0752 | p10 |
| corn_china | 3 | 0.0839 | p10 |
| natural_gas_uk | 2 | 0.0867 | p10 |

**FX predictor finding**: against the EXPANDED Brent+Urals+gas+AN-family predictor set, fx_rate now clears the causality screen with 11 predictor/lag pairs at p<0.10 (see table above) -- this overturns the prior study's "no predictors" finding for FX (Pitfall 5), reported honestly rather than forcing symmetry with the other series.

## Cointegration & VECM

Engle-Granger cointegration sweep tested 60 target/predictor pairs; 2 showed cointegration at p<0.05: hdan~ammonia (p=0.0254), ppan~ammonia (p=0.0395).

None of these pairs matched the VAR system membership used in plan 02-05's candidate VAR systems, so VECM_CANDIDATES stayed empty for all four target series and VECM was not applicable -- plain VAR on differences is the correct specification here, per the explicit non-applicability records in `wf_var_vecm.json`.

## Volatility / bull-bear spread source (D-01 GARCH)

| Series | GARCH viable | Converged | Widens with horizon | Stable across origins | sigma h=1 | sigma h=6 | sigma h=12 | Source used |
|---|---|---|---|---|---|---|---|---|
| HDAN | True | True | True | True | 12.53 | 12.78 | 13.08 | garch |
| PPAN | True | True | False | True | 12.50 | 11.88 | 11.76 | arima_forecast_se |
| Diesel-USD | True | True | True | False | 5.10 | 8.09 | 10.63 | arima_forecast_se |
| FX rate | True | True | True | False | 0.21 | 0.49 | 0.69 | arima_forecast_se |

Spreads must widen with horizon for the shipped bull/bear bands to be meaningful. PPAN's GARCH sigma does not widen monotonically (Pitfall 3) and Diesel-USD/FX's horizon-1 sigma is unstable across refit origins -- both fall back to the ARIMA forecast-SE source rather than shipping an unreliable GARCH spread. Only HDAN's GARCH fit is viable, widening and stable enough to use directly.

## ML overfitting caveats (D-01)

This section is mandatory even where no overfit flag fired -- stated explicitly below rather than omitted.

| Series | Model | Strategy | Mean MAPE 1-12 | Naive mean MAPE | Margin vs. naive (pts) | n_origins | lag1 importance share | Overfit flags |
|---|---|---|---|---|---|---|---|---|
| HDAN | RandomForest | direct | 4.79% | 25.42% | 20.63 | 2 | 0.106 | small_sample, suspiciously_strong |
| HDAN | RandomForest | iterative | 7.78% | 25.42% | 17.63 | 2 | 0.106 | small_sample, suspiciously_strong |
| HDAN | GradientBoosting | direct | 14.42% | 25.42% | 11.00 | 2 | 0.046 | small_sample |
| HDAN | GradientBoosting | iterative | 21.07% | 25.42% | 4.35 | 2 | 0.046 | small_sample |
| PPAN | RandomForest | direct | 12.14% | 27.53% | 15.38 | 2 | 0.056 | small_sample, suspiciously_strong |
| PPAN | RandomForest | iterative | 15.29% | 27.53% | 12.24 | 2 | 0.056 | small_sample, suspiciously_strong |
| PPAN | GradientBoosting | direct | 15.61% | 27.53% | 11.92 | 2 | 0.015 | small_sample, suspiciously_strong |
| PPAN | GradientBoosting | iterative | 21.97% | 27.53% | 5.56 | 2 | 0.015 | small_sample |
| Diesel-USD | RandomForest | direct | 11.90% | 7.04% | -4.86 | 2 | 0.152 | marginal_over_naive, small_sample |
| Diesel-USD | GradientBoosting | direct | 11.93% | 7.04% | -4.89 | 2 | 0.124 | marginal_over_naive, small_sample |
| Diesel-USD | RandomForest | iterative | 12.65% | 7.04% | -5.60 | 2 | 0.152 | marginal_over_naive, small_sample |
| Diesel-USD | GradientBoosting | iterative | 13.65% | 7.04% | -6.60 | 2 | 0.124 | marginal_over_naive, small_sample |
| FX rate | GradientBoosting | iterative | 2.99% | 1.72% | -1.27 | 25 | 0.496 | marginal_over_naive, small_sample |
| FX rate | RandomForest | iterative | 3.51% | 1.72% | -1.80 | 25 | 0.398 | marginal_over_naive, small_sample |
| FX rate | GradientBoosting | direct | 4.18% | 1.72% | -2.46 | 25 | 0.496 | marginal_over_naive, small_sample |
| FX rate | RandomForest | direct | 4.52% | 1.72% | -2.80 | 25 | 0.398 | marginal_over_naive, small_sample |

Every ML candidate above carries at least one overfit flag (`small_sample`, `suspiciously_strong`, or `marginal_over_naive`). None was crowned the winner on the strength of `lag1_dominant` or `marginal_over_naive` diagnostics per the pick_winner adjudication rule; HDAN and PPAN's lowest-raw-MAPE ML candidates were additionally excluded from winning outright for resting on only 2 walk-forward origins (see winners.json caveats and the thin-sample exclusion above) -- consistent with D-01's instruction not to present ML at face value.

## Comparison with the prior single-holdout study

| Series | Prior study (single holdout) | This study, winner (mean MAPE 1-12) | This study, winner (single holdout) |
|---|---|---|---|
| HDAN | 9.40% | 13.33% | 8.76% |
| PPAN | 10.00% | 23.80% | n/a% |
| Diesel-USD | 3.40% | 7.04% | 7.66% |
| FX rate | 0.25% | 1.72% | 0.31% |

The two methodologies are not directly equivalent (D-07): the prior study used a single fixed 12-month holdout on the original workbook's model coefficients and 2-file/10-column predictor set, while this study uses walk-forward/rolling-origin validation (repeated re-fit, forecast, roll forward) against the new 16-column predictor set from Phase 1. A mean MAPE 1-12 dramatically BETTER than the prior study's single-horizon numbers is treated as a leakage red flag rather than good news and is called out explicitly at the human acceptance checkpoint for this plan, not silently accepted.

## Out of scope, and why

- **Technical/market-based methods (D-02)**: not tested this phase -- the user did not select this family, and momentum/support-resistance methods are a poorer fit for monthly fundamentals-driven commodity data than for intraday trading.
- **Scenario planning / Delphi-style qualitative judgment (D-03)**: explicitly out of Phase 2's scope because it isn't backtestable against history the way the other methods are. **This is the mechanism REQUIREMENTS.md already reserves for v2's live news/sentiment-driven bull/bear adjustment** -- noted here explicitly so Phase 3/v2 planners see the throughline, but Phase 2 does not build or test anything for it.
- **Weekly-mode proxy research (D-08)**: not investigated this phase -- weekly forecast mode is v2/deferred scope per REQUIREMENTS.md; this phase stays focused on the monthly models FCST-07 actually requires.
