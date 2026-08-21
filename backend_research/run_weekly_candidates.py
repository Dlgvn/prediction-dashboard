"""Weekly-cadence backtest for HDAN/PPAN, extending the monthly Phase 1 research.
Mirrors run_single_series_candidates.py / run_var_candidates.py methodology (one-step-ahead
holdout MAPE) but at native weekly cadence, using AN Data.csv un-resampled plus the new
AN price weekly.csv drivers."""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

from data_loader import load_an_weekly, merged_weekly
from model_harness import backtest_ols

HOLDOUT = 12
results = []

an = load_an_weekly()
mg = merged_weekly()

# --- naive baseline (last value) ---
for target in ['HDAN', 'PPAN']:
    s = an[target]
    hold_idx = s.index[-HOLDOUT:]
    pred = s.shift(1).loc[hold_idx]
    actual = s.loc[hold_idx]
    mape = (abs(pred - actual) / actual).mean() * 100
    results.append({'model': 'naive', 'target': target, 'cadence': 'weekly',
                     'mape': round(float(mape), 2), 'n': int(len(s))})

# --- VAR(HDAN, PPAN) at weekly cadence, mirroring the monthly winner ---
an_pct = an[['HDAN', 'PPAN']].pct_change().dropna() * 100
n = len(an_pct)
train, hold = an_pct.iloc[:n - HOLDOUT], an_pct.iloc[n - HOLDOUT:]
try:
    best_aic, best_order = None, 1
    for p in range(1, 5):
        try:
            fit = VAR(train).fit(p)
            if best_aic is None or fit.aic < best_aic:
                best_aic, best_order = fit.aic, p
        except Exception:
            continue
    var_model = VAR(train).fit(best_order)
    preds = {t: [] for t in ['HDAN', 'PPAN']}
    history = train.copy()
    for date in hold.index:
        fc = var_model.forecast(history.values[-best_order:], steps=1)[0]
        for i, t in enumerate(['HDAN', 'PPAN']):
            preds[t].append(fc[i])
        history = pd.concat([history, pd.DataFrame([an_pct.loc[date]], index=[date])])
    for t in ['HDAN', 'PPAN']:
        pred_pct = np.array(preds[t])
        prev = an[t].shift(1).loc[hold.index]
        actual = an[t].loc[hold.index]
        osa_pred = prev.values * (1 + pred_pct / 100)
        mape = (abs(osa_pred - actual.values) / actual.values).mean() * 100
        results.append({'model': f'VAR(HDAN,PPAN) order={best_order}', 'target': t,
                         'cadence': 'weekly', 'mape': round(float(mape), 2), 'n': int(n)})
except Exception as e:
    results.append({'model': 'VAR(HDAN,PPAN)', 'target': 'both', 'error': str(e)})

# --- OLS+Granger, native weekly, same predictor set as the monthly baseline ---
mg_pct = mg.pct_change().dropna() * 100
results.append(backtest_ols(mg_pct, mg['HDAN'], 'HDAN',
    {'Baltic AN': 1, 'Ammonia': 2, 'Urea': 1}, holdout=HOLDOUT))
results.append(backtest_ols(mg_pct, mg['PPAN'], 'PPAN',
    {'Baltic AN': 1, 'Urea': 1, 'Brent': 2}, holdout=HOLDOUT))
for r in results[-2:]:
    r['cadence'] = 'weekly'
    r['model'] = 'OLS+Granger (monthly predictor set)'

# --- OLS+Granger extended with new weekly drivers (gas benchmarks, corn, ME ammonia, urea) ---
new_drivers = {
    'HDAN': {'Baltic AN': 1, 'Ammonia': 2, 'Urea': 1, 'MidEastAmmonia_wk': 1, 'BlackSeaUrea_wk': 1, 'Gas_HenryHub': 2},
    'PPAN': {'Baltic AN': 1, 'Urea': 1, 'Brent': 2, 'MidEastAmmonia_wk': 1, 'ChinaUrea_wk': 1, 'Gas_JKM': 2},
}
for target, preds in new_drivers.items():
    try:
        r = backtest_ols(mg_pct, mg[target], target, preds, holdout=HOLDOUT)
        r['cadence'] = 'weekly'
        r['model'] = 'OLS+Granger (+ new weekly drivers)'
        results.append(r)
    except Exception as e:
        results.append({'model': 'OLS+Granger (+ new weekly drivers)', 'target': target, 'error': str(e)})

# --- 4-week-ahead VAR forecast, horizon-matched to the monthly VAR(HDAN,PPAN) comparison ---
# (weekly one-step MAPE is not comparable to monthly one-step MAPE -- a week moves less than
# a month does. This answers the actual go/no-go question: does weekly data, rolled forward
# 4 steps, forecast ~1 month out at least as well as the existing monthly-native VAR did.)
HORIZON = 4
try:
    var_model_h = VAR(train).fit(best_order)
    errs = {'HDAN': [], 'PPAN': []}
    for i in range(len(hold) - HORIZON + 1):
        origin_idx = n - HOLDOUT + i - 1
        hist = an_pct.iloc[:origin_idx + 1]
        m = VAR(hist).fit(best_order)
        fc = m.forecast(hist.values[-best_order:], steps=HORIZON)
        cum_pct = (1 + fc[:, 0] / 100).prod() - 1, (1 + fc[:, 1] / 100).prod() - 1
        target_idx = origin_idx + HORIZON
        if target_idx >= len(an):
            continue
        base_price = an[['HDAN', 'PPAN']].iloc[origin_idx]
        actual_price = an[['HDAN', 'PPAN']].iloc[target_idx]
        for j, t in enumerate(['HDAN', 'PPAN']):
            pred_price = base_price[t] * (1 + cum_pct[j])
            errs[t].append(abs(pred_price - actual_price[t]) / actual_price[t] * 100)
    for t in ['HDAN', 'PPAN']:
        if errs[t]:
            results.append({'model': f'VAR(HDAN,PPAN) order={best_order}, {HORIZON}-week-ahead',
                             'target': t, 'cadence': 'weekly->monthly-horizon',
                             'mape': round(float(np.mean(errs[t])), 2), 'n': len(errs[t])})
except Exception as e:
    results.append({'model': f'VAR {HORIZON}-week-ahead', 'target': 'both', 'error': str(e)})

for r in results:
    print(r)
with open('results/weekly_candidates.json', 'w') as f:
    json.dump(results, f, indent=2)
