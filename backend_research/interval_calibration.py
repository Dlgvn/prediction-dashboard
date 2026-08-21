"""For each of HDAN, PPAN, Diesel (already-validated OLS+Granger models), computes both
backtest-error-based and analytic-OLS-based 95% intervals on the holdout set, then measures
actual coverage: what fraction of holdout actuals fell inside each interval type."""
from data_loader import load_an_monthly, load_diesel_monthly
from model_harness import backtest_ols
import pandas as pd, numpy as np
import statsmodels.api as sm
from scipy import stats
import json

def coverage_check(pct_df, price_series, target, predictors_with_lags, holdout=12):
    d = pd.DataFrame(index=pct_df.index)
    d['y'] = pct_df[target]
    d['y_lag1'] = pct_df[target].shift(1)
    for p, lag in predictors_with_lags.items():
        d[f'{p}_lag{lag}'] = pct_df[p].shift(lag)
    d = d.dropna()
    n = len(d)
    train, hold = d.iloc[:n-holdout], d.iloc[n-holdout:]
    Xtr = sm.add_constant(train.drop(columns='y'))
    Xho = sm.add_constant(hold.drop(columns='y'), has_constant='add')
    m = sm.OLS(train['y'], Xtr).fit()

    # Backtest-error method: point +/- 1.96 * holdout RMSE of pct-change errors (from a
    # rolling structure would be ideal, but with n=12 holdout months use the in-sample
    # residual std as the best available proxy, consistent with the existing MAPE-based
    # range already used in the shipped Forecast tab)
    resid_std = np.std(m.resid)
    pred_pct = m.predict(Xho)

    ho_idx = hold.index
    actual = price_series.loc[ho_idx]
    prev = price_series.shift(1).loc[ho_idx]

    # Method A: backtest-error band (+/- 1.96 * training residual std, in pct-change space)
    upper_a = prev * (1 + (pred_pct.values + 1.96*resid_std) / 100)
    lower_a = prev * (1 + (pred_pct.values - 1.96*resid_std) / 100)
    coverage_a = ((actual.values >= lower_a) & (actual.values <= upper_a)).mean()

    # Method B: analytic OLS prediction interval (get_prediction, includes parameter uncertainty)
    pred_obj = m.get_prediction(Xho)
    ci = pred_obj.conf_int(alpha=0.05, obs=True)  # observation-level (prediction) interval
    upper_b = prev * (1 + ci[:, 1] / 100)
    lower_b = prev * (1 + ci[:, 0] / 100)
    coverage_b = ((actual.values >= lower_b) & (actual.values <= upper_b)).mean()

    return {'target': target, 'n_holdout': int(len(hold)),
            'backtest_error_coverage': round(float(coverage_a), 3),
            'analytic_ols_coverage': round(float(coverage_b), 3),
            'target_coverage': 0.95}

an = load_an_monthly()
di = load_diesel_monthly()
an_pct = an.pct_change().dropna() * 100
di_pct = di.pct_change().dropna() * 100

results = [
    coverage_check(an_pct, an['HDAN'], 'HDAN', {'Baltic AN': 1, 'Ammonia': 2, 'Urea': 1}),
    coverage_check(an_pct, an['PPAN'], 'PPAN', {'Baltic AN': 1, 'Urea': 1, 'Brent': 2}),
    coverage_check(di_pct, di['Diesel_usd_ton'], 'Diesel_usd_ton', {'Brent_usd_ton': 2}),
]
for r in results:
    print(r)
with open('results/interval_calibration.json', 'w') as f:
    json.dump(results, f, indent=2)
