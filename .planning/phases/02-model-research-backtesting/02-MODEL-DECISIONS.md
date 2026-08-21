# Phase 2 Model Decisions -- Phase 3 Hand-off

Concise, per-series winner specification for Phase 3 to hard-code directly. Full backtest detail and per-family rankings live in `backend_research/REPORT-PHASE2.md`; this file exists so Phase 3's planner does not have to read JSON.

## HDAN (`hdan`)

- **Winning model**: SARIMAX(0, 1, 0)+exog (sarimax family)
- **Horizon strategy**: iterative
- **Predictor set**: ppan (lag 1), urea_china (lag 1), urea_black_sea (lag 1), ammonia (lag 3), baltic_an (lag 1), corn_us (lag 1)
- **Walk-forward MAPE**: h=1 9.48%, h=6 11.44%, h=12 n/a%, mean 1-12 13.33%
- **Volatility source for bull/bear spread**: garch
- **Caveats**:
  - RandomForest posted a lower raw MAPE (4.79%) but is backed by only 2 walk-forward origins (overfit_flags=['small_sample', 'suspiciously_strong']) -- not trusted as a winner over candidates validated across many more rolling origins.

## PPAN (`ppan`)

- **Winning model**: Direct-OLS VAR-system(h=1..12) system=[ppan, hdan, baltic_an, urals] (var family)
- **Horizon strategy**: direct
- **Predictor set**: hdan (system member), baltic_an (system member), urals (system member)
- **Walk-forward MAPE**: h=1 8.50%, h=6 17.78%, h=12 35.90%, mean 1-12 23.80%
- **Volatility source for bull/bear spread**: arima_forecast_se
- **Caveats**:
  - RandomForest posted a lower raw MAPE (12.14%) but is backed by only 2 walk-forward origins (overfit_flags=['small_sample', 'suspiciously_strong']) -- not trusted as a winner over candidates validated across many more rolling origins.
  - Falling back to ARIMA forecast-SE for the bull/bear spread: GARCH sigma does not widen monotonically with horizon (Pitfall 3).

## Diesel-USD (`diesel_usd_ton`)

- **Winning model**: Naive (baseline family)
- **Horizon strategy**: iterative
- **Predictor set**: none (univariate)
- **Walk-forward MAPE**: h=1 2.34%, h=6 8.40%, h=12 7.69%, mean 1-12 7.04%
- **Volatility source for bull/bear spread**: arima_forecast_se
- **Caveats**:
  - No candidate model beat the Naive baseline's mean 1-12 MAPE for this series -- no model earned its added complexity here; Naive is the legitimate, reportable winner.
  - RandomForest posted a lower raw MAPE (11.90%) but is backed by only 2 walk-forward origins (overfit_flags=['marginal_over_naive', 'small_sample']) -- not trusted as a winner over candidates validated across many more rolling origins.
  - Falling back to ARIMA forecast-SE for the bull/bear spread: GARCH horizon-1 sigma is unstable across refit origins (>50% relative spread).

## FX rate (`fx_rate`)

- **Winning model**: Naive (baseline family)
- **Horizon strategy**: iterative
- **Predictor set**: none (univariate)
- **Walk-forward MAPE**: h=1 0.39%, h=6 1.60%, h=12 2.98%, mean 1-12 1.72%
- **Volatility source for bull/bear spread**: arima_forecast_se
- **Caveats**:
  - No candidate model beat the Naive baseline's mean 1-12 MAPE for this series -- no model earned its added complexity here; Naive is the legitimate, reportable winner.
  - Falling back to ARIMA forecast-SE for the bull/bear spread: GARCH horizon-1 sigma is unstable across refit origins (>50% relative spread).

## Phase 3 must not

- Must not re-run order search (AIC grid search, auto_arima, or any hyperparameter sweep) at runtime -- STACK.md's anti-auto_arima rule. Orders/hyperparameters are hard-coded above from this backtest.
- Must not use a flat spread across series or horizons for the bull/bear bands -- FCST-03/FCST-04 require the spread to be series- and horizon-specific, per the volatility source named above.
- Must not adopt any model absent from this file -- FCST-07's threat model (T-02-13) requires that no un-backtested or overfit model reach the shipped forecasting module.
