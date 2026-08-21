from data_loader import load_diesel_monthly
import pandas as pd, numpy as np
import statsmodels.api as sm
from scipy.stats import f as fdist
import json

di = load_diesel_monthly()
pct = di[['Diesel_usd_liter', 'Brent_usd_ton']].pct_change().dropna() * 100

results = []
for lag in (0, 1, 2, 3, 4):
    d = pd.DataFrame({
        'y': pct['Diesel_usd_liter'],
        'y_lag1': pct['Diesel_usd_liter'].shift(1),
        'x_lag': pct['Brent_usd_ton'].shift(lag),
    }).dropna()
    if lag == 0:
        # lag 0 excluded from the base-vs-AR1 comparison by project convention
        # (can't be causally ordered), but still reported for completeness
        pass
    Xb = sm.add_constant(d[['y_lag1']])
    Xf = sm.add_constant(d[['y_lag1', 'x_lag']])
    mb, mf = sm.OLS(d['y'], Xb).fit(), sm.OLS(d['y'], Xf).fit()
    n, k = len(d), Xf.shape[1]
    F = ((mb.ssr - mf.ssr) / 1) / (mf.ssr / (n - k))
    p = 1 - fdist.cdf(F, 1, n - k)
    results.append({'lag': lag, 'F': round(float(F), 3), 'p': round(float(p), 4), 'n': int(n)})
    print(results[-1])

best = min([r for r in results if r['lag'] != 0], key=lambda r: r['p'])
print("Best defensible lag (excluding lag 0):", best)
with open('results/diesel_crude_lag.json', 'w') as f:
    json.dump({'all_lags': results, 'selected': best}, f, indent=2)
