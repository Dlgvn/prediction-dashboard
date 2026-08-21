"""FX rate has never been stationarity-tested (only HDAN/PPAN have, this session).
This confirms % change is the right transform for FX rate too, before any model uses it."""
from data_loader import load_diesel_monthly
from statsmodels.tsa.stattools import adfuller, kpss
import json

di = load_diesel_monthly()
fx_pct = di['FX_rate'].pct_change().dropna() * 100

adf = adfuller(fx_pct)
kp = kpss(fx_pct, nlags='auto')

result = {
    'series': 'FX_rate_pct_change',
    'n': len(fx_pct),
    'adf_stat': adf[0], 'adf_pvalue': adf[1],
    'kpss_stat': kp[0], 'kpss_pvalue': kp[1],
    'stationary_verdict': 'stationary' if adf[1] < 0.05 else 'ambiguous/non-stationary',
}
print(result)
with open('results/stationarity_fx.json', 'w') as f:
    json.dump(result, f, indent=2)
