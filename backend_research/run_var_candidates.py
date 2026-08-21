"""Bivariate VAR(HDAN,PPAN) reproduces the earlier documented result (8.9%/10.5% MAPE) as a
sanity check, then extends to VAR(HDAN,PPAN,Diesel), VAR(HDAN,PPAN,FX), and the full joint
VAR(HDAN,PPAN,Diesel,FX) using the merged overlap-window data."""
from data_loader import merged_monthly
from statsmodels.tsa.api import VAR
import pandas as pd, numpy as np, json

mg = merged_monthly()
pct = mg.pct_change().dropna() * 100

def backtest_var(pct_df, price_df, cols, holdout=12, maxlags=3):
    d = pct_df[cols].dropna()
    n = len(d)
    train, hold = d.iloc[:n-holdout], d.iloc[n-holdout:]
    model = VAR(train)
    sel = model.select_order(maxlags=maxlags)
    lag = sel.aic if sel.aic > 0 else 1
    fitted = model.fit(lag)
    mapes = {}
    history = train.values.tolist()
    preds = []
    for i in range(len(hold)):
        pred = fitted.forecast(np.array(history[-lag:]), steps=1)[0]
        preds.append(pred)
        history.append(hold.iloc[i].values.tolist())
    preds = pd.DataFrame(preds, columns=cols, index=hold.index)
    for c in cols:
        actual = price_df[c].loc[hold.index]
        prev = price_df[c].shift(1).loc[hold.index]
        osa_pred = prev * (1 + preds[c].values / 100)
        mapes[c] = round(float((abs(osa_pred - actual) / actual).mean() * 100), 2)
    return {'cols': cols, 'lag_order': int(lag), 'mape_by_series': mapes}

price_cols = {'HDAN': mg['HDAN'], 'PPAN': mg['PPAN'], 'Diesel_usd_ton': mg['Diesel_usd_ton'],
              'FX_rate': mg['FX_rate']}
price_df = pd.DataFrame(price_cols)

combos = [
    ['HDAN', 'PPAN'],
    ['HDAN', 'PPAN', 'Diesel_usd_ton'],
    ['HDAN', 'PPAN', 'FX_rate'],
    ['HDAN', 'PPAN', 'Diesel_usd_ton', 'FX_rate'],
]
results = [backtest_var(pct, price_df, combo) for combo in combos]
for r in results:
    print(r)
with open('results/var_candidates.json', 'w') as f:
    json.dump(results, f, indent=2)
