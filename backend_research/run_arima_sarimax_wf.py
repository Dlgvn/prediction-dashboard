"""ARIMA grid search and SARIMAX (with causality-selected exog) under walk-forward
validation, testing both iterative and direct multi-step strategies (D-06).

Reuses the manual itertools.product grid-search style already validated in
run_sarimax_tuned.py -- no pmdarima (STACK.md rules this out beyond optional research
convenience; production ships a hard-coded order, not a runtime search).

ARIMA order is selected ONCE per series (by AIC on the first min_train window) and then
held fixed for the whole walk-forward run -- this is both the Pitfall 2 cost control and
mirrors how Phase 3 will ship a hard-coded order.

SARIMAX exog predictors come exclusively from causality_screen.shortlist_for(target) and
are always the SHIFTED (lagged) value -- never the contemporaneous/future actual -- per
RESEARCH.md Pitfall 1 (leakage).
"""

from __future__ import annotations

import itertools
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA

from causality_screen import shortlist_for
from db_loader import TARGETS, load_price_history
from walk_forward import mape_by_horizon, single_holdout_mape, walk_forward_backtest

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUT_JSON = RESULTS_DIR / "wf_arima_sarimax.json"

MIN_TRAIN = 36
HORIZON = 12
REFIT_EVERY = 1

# Prior single-holdout MAPE figures from backend_research/REPORT.md, used for the
# leakage sanity check (Pitfall 1): walk-forward MAPE dramatically BETTER than these
# should raise a loud alarm rather than be celebrated.
PRIOR_HOLDOUT_MAPE = {
    "hdan": 9.4,
    "ppan": 10.0,
    "diesel_usd_ton": 3.4,
    "fx_rate": 0.25,
}

ORDER_GRID = list(itertools.product(range(3), range(2), range(3)))  # p in 0-2, d in 0-1, q in 0-2


def select_arima_order(train_y: pd.Series) -> tuple[tuple[int, int, int], float]:
    """Select (p,d,q) by AIC on a single training window. Returns (order, aic)."""
    best_order = None
    best_aic = np.inf
    for order in ORDER_GRID:
        try:
            fitted = ARIMA(train_y.to_numpy(), order=order).fit()
            if fitted.aic < best_aic:
                best_aic = fitted.aic
                best_order = order
        except Exception:
            continue
    if best_order is None:
        best_order = (1, 1, 0)
        best_aic = None
    return best_order, best_aic


class _ARIMAWrapper:
    def __init__(self, train_y, order):
        self.fitted = ARIMA(train_y.to_numpy(), order=order).fit()

    def forecast(self, steps):
        return self.fitted.forecast(steps)


class _SARIMAXWrapper:
    def __init__(self, train_y, train_x, order):
        self.fitted = sm.tsa.SARIMAX(
            train_y.to_numpy(),
            exog=train_x.to_numpy() if train_x is not None else None,
            order=order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)

    def forecast(self, steps, exog=None):
        if exog is not None:
            return self.fitted.forecast(steps=steps, exog=np.asarray(exog))
        return self.fitted.forecast(steps=steps)


class _DirectMultistepWrapper:
    """Fits 12 separate OLS models (one per horizon) on data up to the training cutoff,
    then dispatches .forecast(steps) to the h-th direct model for h=1..steps. All window
    slicing stays inside walk_forward_backtest -- this wrapper only fits/predicts using
    the train_y/train_x it is handed.
    """

    def __init__(self, train_df: pd.DataFrame, target_col: str, feature_cols: list[str], max_h: int = 12):
        self.models = {}
        self.feature_cols = feature_cols
        y = train_df[target_col]

        for h in range(1, max_h + 1):
            target_h = y.shift(-h)
            feats = train_df[feature_cols]
            frame = pd.concat([target_h.rename("target_h"), feats], axis=1).dropna()
            if len(frame) < 10:
                self.models[h] = None
                continue
            X = sm.add_constant(frame[feature_cols])
            model = sm.OLS(frame["target_h"], X).fit()
            self.models[h] = model

        # Last row of features available at the training cutoff -- used to predict all h.
        self.last_features = train_df[feature_cols].iloc[[-1]]

    def forecast(self, steps, exog=None):
        preds = []
        X_last = sm.add_constant(self.last_features, has_constant="add")
        for h in range(1, steps + 1):
            model = self.models.get(h)
            if model is None:
                preds.append(np.nan)
                continue
            X_aligned = X_last.reindex(columns=model.params.index, fill_value=0.0)
            pred = model.predict(X_aligned)
            preds.append(float(pred.iloc[0]))
        return np.array(preds)


def direct_ols_multistep(train_df: pd.DataFrame, target_col: str, feature_cols: list[str], h: int):
    """Fit a single direct-h OLS model: target_h = y.shift(-h), features = shifted
    predictors + y's own lags 1-3. Building block used inside _DirectMultistepWrapper."""
    y = train_df[target_col]
    target_h = y.shift(-h)
    feats = train_df[feature_cols]
    frame = pd.concat([target_h.rename("target_h"), feats], axis=1).dropna()
    X = sm.add_constant(frame[feature_cols])
    return sm.OLS(frame["target_h"], X).fit()


def fit_arima(train_y, train_x, order):
    return _ARIMAWrapper(train_y, order)


def fit_sarimax(train_y, train_x, order):
    return _SARIMAXWrapper(train_y, train_x, order)


def build_arima_record(series_name: str, y: pd.Series) -> tuple[dict, tuple[int, int, int]]:
    y = y.dropna()
    n = len(y)
    order, aic = select_arima_order(y.iloc[:MIN_TRAIN])

    fit_fn = lambda train_y, train_x: fit_arima(train_y, train_x, order)

    wf = walk_forward_backtest(y, None, fit_fn, min_train=MIN_TRAIN, horizon=HORIZON, step=1, refit_every=REFIT_EVERY)
    mbh = mape_by_horizon(wf)
    mape_by_h = {str(h): (float(mbh[h]) if h in mbh.index else None) for h in range(1, 13)}
    mean_1_12 = float(np.nanmean([v for v in mape_by_h.values() if v is not None]))

    try:
        holdout_mape = single_holdout_mape(y, None, fit_fn, holdout=12)
    except Exception:
        holdout_mape = None

    check_leakage(series_name, "ARIMA", mean_1_12)

    record = {
        "series": series_name,
        "model": f"ARIMA{order}",
        "family": "arima",
        "horizon_strategy": "iterative",
        "predictors": {},
        "mape_by_horizon": mape_by_h,
        "mape_mean_1_12": mean_1_12,
        "single_holdout_mape": holdout_mape,
        "n_origins": int(wf["origin_date"].nunique()) if len(wf) else 0,
        "refit_every": REFIT_EVERY,
        "failed_origins": len(wf.attrs.get("failed_origins", [])),
        "notes": f"order selected by AIC={aic} on first {MIN_TRAIN}-obs window, n={n} after dropna",
    }
    return record, order


def check_leakage(series_name, model_name, wf_mape):
    prior = PRIOR_HOLDOUT_MAPE.get(series_name)
    if prior is None or wf_mape is None:
        return
    if wf_mape < prior * 0.5:
        print(
            f"LEAKAGE SUSPECT: {series_name}/{model_name} walk-forward MAPE={wf_mape:.2f} "
            f"is dramatically better than prior single-holdout MAPE={prior} -- investigate before trusting this number."
        )


def build_sarimax_records(df: pd.DataFrame, series_name: str, order) -> list[dict]:
    shortlist = shortlist_for(series_name, tier="p10")
    y_full = df[series_name]

    if not shortlist:
        return [
            {
                "series": series_name,
                "model": f"SARIMAX{order}+exog",
                "family": "sarimax",
                "horizon_strategy": "iterative",
                "predictors": {},
                "mape_by_horizon": {str(h): None for h in range(1, 13)},
                "mape_mean_1_12": None,
                "single_holdout_mape": None,
                "n_origins": 0,
                "refit_every": REFIT_EVERY,
                "failed_origins": 0,
                "notes": (
                    "no predictor passed the causality screen at p<0.10; AR-only ARIMA "
                    "is the honest specification for this series"
                ),
            }
        ]

    # Build the aligned exog frame with predictors shifted by their chosen lag --
    # leakage rule: the value used at forecast time must have been observable at origin.
    exog_cols = {}
    for predictor, lag in shortlist.items():
        exog_cols[predictor] = df[predictor].shift(lag)
    exog = pd.DataFrame(exog_cols, index=df.index)

    combined = pd.concat([y_full.rename("y"), exog], axis=1).dropna()
    y = combined["y"]
    x = combined[list(shortlist.keys())]
    n = len(combined)

    records = []

    # --- Iterative SARIMAX ---
    fit_fn_iter = lambda train_y, train_x: fit_sarimax(train_y, train_x, order)
    wf = walk_forward_backtest(y, x, fit_fn_iter, min_train=MIN_TRAIN, horizon=HORIZON, step=1, refit_every=REFIT_EVERY)
    mbh = mape_by_horizon(wf)
    mape_by_h = {str(h): (float(mbh[h]) if h in mbh.index else None) for h in range(1, 13)}
    present = [v for v in mape_by_h.values() if v is not None]
    mean_1_12 = float(np.nanmean(present)) if present else None

    try:
        holdout_mape = single_holdout_mape(y, x, fit_fn_iter, holdout=12)
    except Exception:
        holdout_mape = None

    check_leakage(series_name, "SARIMAX-iterative", mean_1_12)

    records.append(
        {
            "series": series_name,
            "model": f"SARIMAX{order}+exog",
            "family": "sarimax",
            "horizon_strategy": "iterative",
            "predictors": shortlist,
            "mape_by_horizon": mape_by_h,
            "mape_mean_1_12": mean_1_12,
            "single_holdout_mape": holdout_mape,
            "n_origins": int(wf["origin_date"].nunique()) if len(wf) else 0,
            "refit_every": REFIT_EVERY,
            "failed_origins": len(wf.attrs.get("failed_origins", [])),
            "notes": f"exog shift(lag) applied per predictor: {shortlist}; n={n} after dropna",
        }
    )

    # --- Direct multi-step SARIMAX-family (OLS-based) ---
    feature_cols = list(shortlist.keys())
    direct_df = pd.concat([y.rename(series_name), x], axis=1)
    for lag in (1, 2, 3):
        direct_df[f"y_lag{lag}"] = y.shift(lag)
    direct_df = direct_df.dropna(subset=[series_name])
    all_feature_cols = feature_cols + [f"y_lag{lag}" for lag in (1, 2, 3)]

    def fit_direct(train_y, train_x):
        # train_y/train_x are the y/x slices from the harness; reconstruct the frame
        # the direct wrapper needs (target + shifted predictors + y's own lags).
        idx = train_y.index
        frame = direct_df.loc[direct_df.index.isin(idx)]
        return _DirectMultistepWrapper(frame, series_name, all_feature_cols, max_h=HORIZON)

    wf_direct = walk_forward_backtest(
        y, x, fit_direct, min_train=MIN_TRAIN, horizon=HORIZON, step=1, refit_every=REFIT_EVERY
    )
    mbh_d = mape_by_horizon(wf_direct)
    mape_by_h_d = {str(h): (float(mbh_d[h]) if h in mbh_d.index else None) for h in range(1, 13)}
    present_d = [v for v in mape_by_h_d.values() if v is not None]
    mean_1_12_d = float(np.nanmean(present_d)) if present_d else None

    check_leakage(series_name, "SARIMAX-direct", mean_1_12_d)

    records.append(
        {
            "series": series_name,
            "model": f"Direct-OLS+exog(h=1..12)",
            "family": "sarimax",
            "horizon_strategy": "direct",
            "predictors": shortlist,
            "mape_by_horizon": mape_by_h_d,
            "mape_mean_1_12": mean_1_12_d,
            "single_holdout_mape": None,
            "n_origins": int(wf_direct["origin_date"].nunique()) if len(wf_direct) else 0,
            "refit_every": REFIT_EVERY,
            "failed_origins": len(wf_direct.attrs.get("failed_origins", [])),
            "notes": (
                "direct multi-step OLS, one model per horizon 1-12; loses h rows of training "
                "data per horizon which matters most for the shortest series"
            ),
        }
    )

    return records


def main():
    df = load_price_history()
    all_records = []

    for series_name in TARGETS:
        print(f"=== {series_name} ===")
        y = df[series_name].dropna()
        arima_record, order_tuple = build_arima_record(series_name, y)
        all_records.append(arima_record)

        sarimax_records = build_sarimax_records(df, series_name, order_tuple)
        all_records.extend(sarimax_records)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(all_records, f, indent=2)

    print("\nseries | model | strategy | h=1 | h=6 | h=12 | prior_holdout")
    for r in all_records:
        h1 = r["mape_by_horizon"]["1"]
        h6 = r["mape_by_horizon"]["6"]
        h12 = r["mape_by_horizon"]["12"]
        fmt = lambda v: f"{v:.2f}" if v is not None else "NA"
        prior = PRIOR_HOLDOUT_MAPE.get(r["series"])
        print(
            f"{r['series']:16s} {r['model']:22s} {r['horizon_strategy']:10s} "
            f"{fmt(h1):>8s} {fmt(h6):>8s} {fmt(h12):>8s}  (prior: {prior})"
        )

    print(f"\nWrote {len(all_records)} records to {OUT_JSON}")


if __name__ == "__main__":
    main()
