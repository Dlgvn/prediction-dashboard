"""Compares three treatments of the diesel import->purchase markup on final MNT purchase-price
holdout MAPE: fixed 9%, trailing-12-month average, and (if a predictor emerges) a small model."""
from data_loader import load_diesel_monthly
import pandas as pd, numpy as np, json

di = load_diesel_monthly()
di['import_mnt'] = di['Diesel_usd_liter'] * di['FX_rate']
di['markup_ratio'] = di['Purchase_mnt_liter'] / di['import_mnt']

holdout = 12
n = len(di)
train, hold = di.iloc[:n-holdout], di.iloc[n-holdout:]

results = {}

# Treatment 1: fixed 9%
pred_fixed = hold['import_mnt'] * 1.09
mape_fixed = (abs(pred_fixed - hold['Purchase_mnt_liter']) / hold['Purchase_mnt_liter']).mean() * 100
results['fixed_9pct'] = round(mape_fixed, 2)

# Treatment 2: trailing 12-month average markup, recomputed at each holdout point
# (walk-forward: at each holdout month, use the mean of the prior 12 actual months' markup)
preds_trailing = []
for i in range(len(hold)):
    idx = n - holdout + i
    trailing_ratio = di['markup_ratio'].iloc[max(0, idx-12):idx].mean()
    preds_trailing.append(di['import_mnt'].iloc[idx] * trailing_ratio)
preds_trailing = pd.Series(preds_trailing, index=hold.index)
mape_trailing = (abs(preds_trailing - hold['Purchase_mnt_liter']) / hold['Purchase_mnt_liter']).mean() * 100
results['trailing_12mo_avg'] = round(mape_trailing, 2)

# Treatment 3: full-history average markup (simplest possible baseline, for comparison)
full_avg = train['markup_ratio'].mean()
pred_full_avg = hold['import_mnt'] * full_avg
mape_full_avg = (abs(pred_full_avg - hold['Purchase_mnt_liter']) / hold['Purchase_mnt_liter']).mean() * 100
results['full_history_avg'] = round(mape_full_avg, 2)
results['full_history_avg_value'] = round(full_avg, 4)

# Cast to native Python types to avoid numpy float64/int64/bool_ TypeError in json.dump
results = {k: float(v) for k, v in results.items()}

print(results)
with open('results/markup_comparison.json', 'w') as f:
    json.dump(results, f, indent=2)
