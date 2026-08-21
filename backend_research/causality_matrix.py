"""Generalizes the incremental-F-test Granger method (already used for HDAN/PPAN/Diesel
this session) into a reusable function, then runs it across every target x predictor x lag
combination relevant to the four-series expansion: FX as predictor of diesel/HDAN/PPAN,
FX as a target of Brent, and diesel/HDAN/PPAN cross-relationships for the joint VAR candidate."""
from data_loader import merged_monthly, load_an_monthly, load_diesel_monthly
import pandas as pd, numpy as np
import statsmodels.api as sm
from scipy.stats import f as fdist
import json

def granger_ftest(y, predictor, lag):
    """y, predictor: pandas Series with a shared index. Returns (F, p, n)."""
    d = pd.DataFrame({'y': y, 'y_lag1': y.shift(1), 'x_lag': predictor.shift(lag)}).dropna()
    Xb = sm.add_constant(d[['y_lag1']])
    Xf = sm.add_constant(d[['y_lag1', 'x_lag']])
    mb, mf = sm.OLS(d['y'], Xb).fit(), sm.OLS(d['y'], Xf).fit()
    n, k = len(d), Xf.shape[1]
    F = ((mb.ssr - mf.ssr) / 1) / (mf.ssr / (n - k))
    p = 1 - fdist.cdf(F, 1, n - k)
    return F, p, n

mg = merged_monthly()
pct = mg.pct_change().dropna() * 100

pairs = [
    ('FX_rate', 'Brent_usd_ton'), ('FX_rate', 'HDAN'), ('FX_rate', 'PPAN'),
    ('Diesel_usd_ton', 'FX_rate'), ('HDAN', 'Diesel_usd_ton'), ('PPAN', 'Diesel_usd_ton'),
    ('HDAN', 'PPAN'), ('PPAN', 'HDAN'),
]
results = []
for target, predictor in pairs:
    for lag in (1, 2, 3):
        F, p, n = granger_ftest(pct[target], pct[predictor], lag)
        results.append({'target': target, 'predictor': predictor, 'lag': lag,
                         'F': round(float(F), 3), 'p': round(float(p), 4), 'n': int(n),
                         'significant_p10': bool(p < 0.10)})
        print(results[-1])

with open('results/causality_matrix.json', 'w') as f:
    json.dump(results, f, indent=2)
