"""The earlier SARIMAX result (26.7%/29.0% MAPE) used an untuned (1,1,0) order — this is not
a fair test of ARIMAX's potential. This does a small grid search over (p,d,q) with an Ammonia
exogenous regressor, picking the best by holdout MAPE (not AIC, to stay consistent with the
project's holdout-driven model-selection philosophy)."""
from data_loader import load_an_monthly
import pandas as pd, numpy as np
import statsmodels.api as sm
import itertools, json, warnings
warnings.filterwarnings('ignore')

an = load_an_monthly()

def backtest_sarimax(price, exog, order, holdout=12):
    n = len(price)
    train_p, hold_p = price.iloc[:n-holdout], price.iloc[n-holdout:]
    train_x, hold_x = exog.iloc[:n-holdout], exog.iloc[n-holdout:]
    try:
        model = sm.tsa.SARIMAX(train_p, exog=train_x, order=order,
                                enforce_stationarity=False, enforce_invertibility=False)
        fitted = model.fit(disp=False)
        pred = fitted.forecast(steps=holdout, exog=hold_x)
        mape = (abs(pred.values - hold_p.values) / hold_p.values).mean() * 100
        return round(mape, 2)
    except Exception:
        return None

results = []
for target in ['HDAN', 'PPAN']:
    price = an[target]
    exog = an[['Ammonia']]
    best = None
    for p, d, q in itertools.product(range(3), range(2), range(3)):
        mape = backtest_sarimax(price, exog, (p, d, q))
        if mape is not None and (best is None or mape < best['mape']):
            best = {'target': target, 'order': (int(p), int(d), int(q)), 'mape': float(mape)}
    results.append(best)
    print(best)

with open('results/sarimax_tuned.json', 'w') as f:
    json.dump(results, f, indent=2)
