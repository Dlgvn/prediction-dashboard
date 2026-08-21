from data_loader import load_an_monthly, load_diesel_monthly, merged_monthly
from model_harness import backtest_ols, backtest_sklearn
from sklearn.linear_model import Lasso, Ridge, ElasticNet
import json

an = load_an_monthly()
di = load_diesel_monthly()
an_pct = an.pct_change().dropna() * 100
di_pct = di.pct_change().dropna() * 100

results = []

# HDAN / PPAN: current OLS+Granger baseline (reuse validated lags from shipped workbook)
results.append(backtest_ols(an_pct, an['HDAN'], 'HDAN',
    {'Baltic AN': 1, 'Ammonia': 2, 'Urea': 1}))
results.append(backtest_ols(an_pct, an['PPAN'], 'PPAN',
    {'Baltic AN': 1, 'Urea': 1, 'Brent': 2}))

# Diesel: current OLS+Granger baseline
results.append(backtest_ols(di_pct, di['Diesel_usd_ton'], 'Diesel_usd_ton', {'Brent_usd_ton': 2}))

# FX rate: Task 3's causality_matrix.json found NO predictor (Brent, HDAN, or PPAN) reaching
# p<0.10 significance against FX_rate at any lag 1-3 (all p > 0.22, most p > 0.5 -- see
# results/causality_matrix.json rows with target='FX_rate'). So there is no defensible
# significant-predictor set to hand this an OLS+Granger model the way HDAN/PPAN/Diesel got one.
# The honest baseline here is AR1-only (predictors_with_lags={}) -- not a forced/invented
# predictor set just to mirror the other three targets.
results.append(backtest_ols(di_pct, di['FX_rate'], 'FX_rate', {}))

# Regularized candidates — offer each target its available same-frequency predictors at lags 1-3
for target, pct_df, price in [('HDAN', an_pct, an['HDAN']), ('PPAN', an_pct, an['PPAN']),
                                ('Diesel_usd_ton', di_pct, di['Diesel_usd_ton'])]:
    lagged_cols = []
    # NOTE: .copy() here (deviation from the plan's literal code, which reused an_pct/di_pct
    # directly). Without it, HDAN's iteration mutates an_pct in place by adding lag columns,
    # and PPAN's iteration (same an_pct object) then re-lags those already-lagged columns too
    # (e.g. 'PPAN_lag1_lag1'), polluting the candidate feature set with nonsense duplicates.
    # Diesel was unaffected only because it uses the separate di_pct object.
    base = (an_pct if pct_df is an_pct else di_pct).copy()
    for col in [c for c in base.columns if c != target]:
        for lag in (1, 2, 3):
            base[f'{col}_lag{lag}'] = base[col].shift(lag)
            lagged_cols.append(f'{col}_lag{lag}')
    for cls, kwargs in [(Lasso, {'alpha': 0.1}), (Ridge, {'alpha': 1.0}),
                         (ElasticNet, {'alpha': 0.1, 'l1_ratio': 0.5})]:
        try:
            results.append(backtest_sklearn(base, price, target, lagged_cols, cls, **kwargs))
        except Exception as e:
            results.append({'model': cls.__name__, 'target': target, 'error': str(e)})

for r in results:
    print(r)
with open('results/single_series_candidates.json', 'w') as f:
    json.dump(results, f, indent=2)
