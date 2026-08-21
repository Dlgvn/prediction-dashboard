"""One function that fits a given model spec on a training window and returns
one-step-ahead holdout MAPE — reused across every single-series candidate model
(OLS+Granger, Lasso, Ridge, ElasticNet, tuned SARIMAX)."""
import pandas as pd, numpy as np
import statsmodels.api as sm
from sklearn.linear_model import Lasso, Ridge, ElasticNet

def backtest_ols(pct_df, price_series, target, predictors_with_lags, holdout=12):
    """predictors_with_lags: dict like {'Ammonia': 2, 'Baltic AN': 1}."""
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
    pred_pct = m.predict(Xho)
    ho_idx = hold.index
    actual = price_series.loc[ho_idx]
    prev = price_series.shift(1).loc[ho_idx]
    osa_pred = prev * (1 + pred_pct.values / 100)
    mape = (abs(osa_pred - actual) / actual).mean() * 100
    return {'model': 'OLS', 'target': target, 'mape': round(float(mape), 2), 'n': int(n),
            'predictors': predictors_with_lags, 'r2': round(float(m.rsquared), 3)}

def backtest_sklearn(pct_df, price_series, target, candidate_cols, model_cls, holdout=12, **model_kwargs):
    """candidate_cols: list of column names (already lagged) to offer the regularized model —
    it will select/shrink among them itself."""
    d = pct_df[[target] + candidate_cols].dropna()
    n = len(d)
    train, hold = d.iloc[:n-holdout], d.iloc[n-holdout:]
    model = model_cls(**model_kwargs)
    model.fit(train[candidate_cols], train[target])
    pred_pct = model.predict(hold[candidate_cols])
    ho_idx = hold.index
    actual = price_series.loc[ho_idx]
    prev = price_series.shift(1).loc[ho_idx]
    osa_pred = prev * (1 + pred_pct / 100)
    mape = (abs(osa_pred - actual) / actual).mean() * 100
    nonzero = [c for c, coef in zip(candidate_cols, getattr(model, 'coef_', [])) if abs(coef) > 1e-6]
    return {'model': model_cls.__name__, 'target': target, 'mape': round(float(mape), 2), 'n': int(n),
            'selected_features': nonzero}
