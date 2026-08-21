"""RandomForest / GradientBoosting walk-forward backtests (D-01's ML comparison point).

D-01 admits ML "as a comparison point despite real overfitting risk on ~48-164 monthly
rows per series" and REQUIRES the research report to "explicitly flag this risk when
reporting ML results, not present them at face value." RESEARCH.md Pitfall 4's concrete
tell is an ML model barely beating "just use last month's value" while posting a
headline-good MAPE -- often because a lag-1 feature is doing all the work (memorised
random walk, not learned structure).

This module therefore does two things, not one:
1. Backtests RandomForestRegressor / GradientBoostingRegressor on lagged features under
   the shared walk_forward_backtest harness, in both direct (one regressor per horizon --
   the natural fit for tree models) and iterative (one 1-step regressor, recursed) forms.
2. Attaches machine-readable overfitting diagnostics (naive-margin, feature importances,
   lag-1 importance share, overfit_flags) to EVERY record, so the caveats cannot be lost
   between this script and the plan 02-07 report.

Regularisation is deliberate, not sklearn defaults (PITFALLS.md's core small-sample
warning): shallow trees, min_samples_leaf=3, fixed random_state=42 for reproducibility.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from causality_screen import shortlist_for
from db_loader import TARGETS, load_price_history
from walk_forward import mape_by_horizon, single_holdout_mape, walk_forward_backtest

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUT_JSON = RESULTS_DIR / "wf_ml_baseline.json"
BASELINE_ETS_JSON = RESULTS_DIR / "wf_baseline_ets.json"
ARIMA_SARIMAX_JSON = RESULTS_DIR / "wf_arima_sarimax.json"
VAR_VECM_JSON = RESULTS_DIR / "wf_var_vecm.json"

MIN_TRAIN = 48
HORIZON = 12
REFIT_EVERY = 3
OWN_LAGS = (1, 2, 3)

# Deliberately regularised for the small-sample regime (PITFALLS.md), not sklearn defaults.
MODEL_SPECS = {
    "RandomForest": (
        RandomForestRegressor,
        dict(n_estimators=300, max_depth=4, min_samples_leaf=3, random_state=42),
    ),
    "GradientBoosting": (
        GradientBoostingRegressor,
        dict(n_estimators=200, max_depth=2, learning_rate=0.05, min_samples_leaf=3, random_state=42),
    ),
}


def build_feature_frame(history: pd.DataFrame, target: str) -> tuple[pd.DataFrame, list[str], dict]:
    """Build the lagged feature frame for `target`.

    Features: the target's own lags 1-3, plus each predictor from
    `shortlist_for(target, tier="p10")` at its screen-selected lag. Every feature is a
    `.shift()` of the raw column -- observable at the origin date, same anti-leakage rule
    as plan 02-04's exog handling. Columns are named `{col}_lag{n}` so feature importances
    are self-describing.

    Returns (frame_with_target_and_features, feature_cols, notes_dict).
    """
    y = history[target]
    feature_cols: list[str] = []
    cols = {target: y}

    for lag in OWN_LAGS:
        name = f"{target}_lag{lag}"
        cols[name] = y.shift(lag)
        feature_cols.append(name)

    shortlist = shortlist_for(target, tier="p10")
    for predictor, lag in shortlist.items():
        name = f"{predictor}_lag{lag}"
        cols[name] = history[predictor].shift(lag)
        feature_cols.append(name)

    frame = pd.DataFrame(cols, index=history.index)

    notes = {
        "own_lags": list(OWN_LAGS),
        "shortlist_predictors": shortlist,
        "fallback_own_lags_only": len(shortlist) == 0,
    }
    return frame, feature_cols, notes


class _DirectMLWrapper:
    """One fitted regressor per horizon h in 1..12; .forecast(steps) dispatches h to
    model h. All window slicing stays in the shared harness -- this wrapper only
    fits/predicts on the train_df it is handed.
    """

    def __init__(self, train_df: pd.DataFrame, target: str, feature_cols: list[str], model_cls, model_kwargs, max_h=12):
        self.models: dict[int, object] = {}
        self.feature_cols = feature_cols
        y = train_df[target]

        for h in range(1, max_h + 1):
            target_h = y.shift(-h)
            frame = pd.concat([target_h.rename("target_h"), train_df[feature_cols]], axis=1).dropna()
            if len(frame) < 10:
                self.models[h] = None
                continue
            model = model_cls(**model_kwargs)
            model.fit(frame[feature_cols], frame["target_h"])
            self.models[h] = model

        self.last_features = train_df[feature_cols].iloc[[-1]]

    def forecast(self, steps, exog=None):
        preds = []
        for h in range(1, steps + 1):
            model = self.models.get(h)
            if model is None:
                preds.append(np.nan)
                continue
            preds.append(float(model.predict(self.last_features)[0]))
        return np.array(preds)


class _IterativeMLWrapper:
    """One 1-step-ahead regressor, recursed to 12 steps. At each step, predict step 1,
    shift the prediction into the target's lag-1 feature slot (cascading lag-2 <- old
    lag-1, lag-3 <- old lag-2 for own-lag features), then predict step 2, and so on.
    Non-target (predictor) features hold their last observed value across the recursion
    since their future values are not known at the origin -- the honest production
    scenario, not an artifact of convenience.
    """

    def __init__(self, train_df: pd.DataFrame, target: str, feature_cols: list[str], own_lag_cols: list[str], model_cls, model_kwargs):
        self.feature_cols = feature_cols
        self.own_lag_cols = own_lag_cols  # ordered lag1, lag2, lag3 (ascending lag)
        y = train_df[target]
        target_h1 = y.shift(-1)
        frame = pd.concat([target_h1.rename("target_h1"), train_df[feature_cols]], axis=1).dropna()
        self.model = None
        if len(frame) >= 10:
            self.model = model_cls(**model_kwargs)
            self.model.fit(frame[feature_cols], frame["target_h1"])
        self.last_features = train_df[feature_cols].iloc[[-1]].copy()

    def forecast(self, steps, exog=None):
        if self.model is None:
            return np.full(steps, np.nan)
        preds = []
        state = self.last_features.copy()
        for _ in range(steps):
            pred = float(self.model.predict(state[self.feature_cols])[0])
            preds.append(pred)
            # Cascade own lags: lag_n <- lag_(n-1)'s previous value, lag1 <- new prediction.
            if self.own_lag_cols:
                for i in range(len(self.own_lag_cols) - 1, 0, -1):
                    state.iloc[0, state.columns.get_loc(self.own_lag_cols[i])] = state.iloc[
                        0, state.columns.get_loc(self.own_lag_cols[i - 1])
                    ]
                state.iloc[0, state.columns.get_loc(self.own_lag_cols[0])] = pred
            # Non-target predictor features hold their last observed (already-lagged)
            # values across the recursion -- their future values are unknown at origin.
        return np.array(preds)


def fit_direct_ml(train_df, target, feature_cols, model_cls, model_kwargs, max_h=12):
    return _DirectMLWrapper(train_df, target, feature_cols, model_cls, model_kwargs, max_h=max_h)


def fit_iterative_ml(train_df, target, feature_cols, own_lag_cols, model_cls, model_kwargs):
    return _IterativeMLWrapper(train_df, target, feature_cols, own_lag_cols, model_cls, model_kwargs)


def _load_json(path: Path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _naive_mape(series_name: str) -> float | None:
    records = _load_json(BASELINE_ETS_JSON)
    if not records:
        return None
    for r in records:
        if r.get("series") == series_name and r.get("model") == "Naive":
            return r.get("mape_mean_1_12")
    return None


def _best_statistical_mape(series_name: str) -> float | None:
    """Best (lowest) mape_mean_1_12 across ARIMA/SARIMAX/VAR/VECM records for this series,
    skipping with a note if those result files do not exist yet (plan ordering does not
    guarantee them).
    """
    best = None
    for path in (ARIMA_SARIMAX_JSON, VAR_VECM_JSON):
        records = _load_json(path)
        if not records:
            continue
        for r in records:
            if r.get("series") != series_name:
                continue
            m = r.get("mape_mean_1_12")
            if m is None:
                continue
            if best is None or m < best:
                best = m
    return best


def _feature_importances(model, feature_cols: list[str], top_n: int = 10) -> dict[str, float]:
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return {}
    pairs = sorted(zip(feature_cols, importances), key=lambda p: p[1], reverse=True)[:top_n]
    return {name: float(val) for name, val in pairs}


def _lag1_share(importances: dict[str, float], target: str) -> float:
    lag1_key = f"{target}_lag1"
    total = sum(importances.values())
    if total <= 0:
        return 0.0
    return float(importances.get(lag1_key, 0.0) / total)


def _attach_diagnostics(record: dict, target: str, n_train_rows: int) -> None:
    naive_mape = _naive_mape(target)
    mape_mean = record.get("mape_mean_1_12")

    record["naive_mape_mean_1_12"] = naive_mape
    if naive_mape is not None and mape_mean is not None:
        record["margin_over_naive_pct_points"] = float(naive_mape - mape_mean)
    else:
        record["margin_over_naive_pct_points"] = None

    importances = record.pop("_full_model_importances", {})
    record["feature_importances"] = importances
    record["lag1_importance_share"] = _lag1_share(importances, target)

    flags: list[str] = []
    if record["lag1_importance_share"] > 0.5:
        flags.append("lag1_dominant")
    if record["margin_over_naive_pct_points"] is not None and record["margin_over_naive_pct_points"] < 1.0:
        flags.append("marginal_over_naive")
    if n_train_rows < 80:
        flags.append("small_sample")

    best_stat = _best_statistical_mape(target)
    if best_stat is None:
        record.setdefault("notes", "")
        record["notes"] += " | suspiciously_strong check skipped: no statistical-family results on disk yet."
    elif mape_mean is not None and mape_mean < best_stat * 0.7:
        flags.append("suspiciously_strong")

    record["overfit_flags"] = flags


def build_ml_records(df: pd.DataFrame, target: str) -> list[dict]:
    frame, feature_cols, feat_notes = build_feature_frame(df, target)
    own_lag_cols = [f"{target}_lag{lag}" for lag in OWN_LAGS]
    combined = frame.dropna()
    n_rows = len(combined)

    # hdan/ppan have only ~48 raw rows; after lag-shifting and dropna the usable feature
    # frame is a few rows shorter than the raw series (Pitfall 4's small-sample regime is
    # not hypothetical here). MIN_TRAIN=48 is infeasible against a 45-row frame, so shrink
    # per-series while leaving at least a couple of walk-forward origins -- the resulting
    # thin-origin runs are exactly what the "small_sample" overfit_flag exists to surface,
    # not something to paper over by silently lowering the bar unconditionally.
    effective_min_train = min(MIN_TRAIN, max(24, n_rows - 2))
    min_train_note = (
        f"min_train={effective_min_train}" if effective_min_train == MIN_TRAIN
        else f"min_train shrunk from {MIN_TRAIN} to {effective_min_train} (n={n_rows} after dropna)"
    )

    records: list[dict] = []

    for model_name, (model_cls, model_kwargs) in MODEL_SPECS.items():
        # --- Direct multi-step ---
        fit_fn_direct = lambda train_y, train_x, mc=model_cls, mk=model_kwargs: fit_direct_ml(
            frame.loc[frame.index.isin(train_y.index)], target, feature_cols, mc, mk, max_h=HORIZON
        )
        y_full = combined[target]
        x_full = combined[feature_cols]
        wf_direct = walk_forward_backtest(
            y_full, x_full, fit_fn_direct, min_train=effective_min_train, horizon=HORIZON, step=1, refit_every=REFIT_EVERY
        )
        mbh_d = mape_by_horizon(wf_direct)
        mape_by_h_d = {str(h): (float(mbh_d[h]) if h in mbh_d.index else None) for h in range(1, 13)}
        present_d = [v for v in mape_by_h_d.values() if v is not None]
        mean_1_12_d = float(np.nanmean(present_d)) if present_d else None

        try:
            holdout_d = single_holdout_mape(y_full, x_full, fit_fn_direct, holdout=12)
        except Exception:
            holdout_d = None

        # Refit on full history for feature importances (h=1 model as representative).
        full_wrapper_d = fit_direct_ml(combined, target, feature_cols, model_cls, model_kwargs, max_h=HORIZON)
        h1_model = full_wrapper_d.models.get(1)
        importances_d = _feature_importances(h1_model, feature_cols) if h1_model is not None else {}

        record_d = {
            "series": target,
            "model": model_name,
            "family": "ml",
            "horizon_strategy": "direct",
            "predictors": feat_notes["shortlist_predictors"],
            "mape_by_horizon": mape_by_h_d,
            "mape_mean_1_12": mean_1_12_d,
            "single_holdout_mape": holdout_d,
            "n_origins": int(wf_direct["origin_date"].nunique()) if len(wf_direct) else 0,
            "refit_every": REFIT_EVERY,
            "failed_origins": len(wf_direct.attrs.get("failed_origins", [])),
            "notes": (
                f"hyperparameters: {model_kwargs}; refit_every={REFIT_EVERY}; {min_train_note}; "
                f"direct multi-step, one regressor per horizon 1-12; "
                f"features={feature_cols}; n={n_rows} after dropna"
                + ("; no predictor passed causality screen, own-lags-only fallback" if feat_notes["fallback_own_lags_only"] else "")
            ),
            "_full_model_importances": importances_d,
        }
        _attach_diagnostics(record_d, target, n_rows)
        records.append(record_d)

        # --- Iterative ---
        fit_fn_iter = lambda train_y, train_x, mc=model_cls, mk=model_kwargs: fit_iterative_ml(
            frame.loc[frame.index.isin(train_y.index)], target, feature_cols, own_lag_cols, mc, mk
        )
        wf_iter = walk_forward_backtest(
            y_full, x_full, fit_fn_iter, min_train=effective_min_train, horizon=HORIZON, step=1, refit_every=REFIT_EVERY
        )
        mbh_i = mape_by_horizon(wf_iter)
        mape_by_h_i = {str(h): (float(mbh_i[h]) if h in mbh_i.index else None) for h in range(1, 13)}
        present_i = [v for v in mape_by_h_i.values() if v is not None]
        mean_1_12_i = float(np.nanmean(present_i)) if present_i else None

        try:
            holdout_i = single_holdout_mape(y_full, x_full, fit_fn_iter, holdout=12)
        except Exception:
            holdout_i = None

        full_wrapper_i = fit_iterative_ml(combined, target, feature_cols, own_lag_cols, model_cls, model_kwargs)
        importances_i = (
            _feature_importances(full_wrapper_i.model, feature_cols) if full_wrapper_i.model is not None else {}
        )

        record_i = {
            "series": target,
            "model": model_name,
            "family": "ml",
            "horizon_strategy": "iterative",
            "predictors": feat_notes["shortlist_predictors"],
            "mape_by_horizon": mape_by_h_i,
            "mape_mean_1_12": mean_1_12_i,
            "single_holdout_mape": holdout_i,
            "n_origins": int(wf_iter["origin_date"].nunique()) if len(wf_iter) else 0,
            "refit_every": REFIT_EVERY,
            "failed_origins": len(wf_iter.attrs.get("failed_origins", [])),
            "notes": (
                f"hyperparameters: {model_kwargs}; refit_every={REFIT_EVERY}; {min_train_note}; "
                f"iterative single-step regressor recursed to 12 steps; own lags cascade "
                f"predicted values, non-target predictor features hold their last observed "
                f"(already-lagged) value across the recursion since future values are "
                f"unknown at the origin -- the honest production scenario; "
                f"features={feature_cols}; n={n_rows} after dropna"
                + ("; no predictor passed causality screen, own-lags-only fallback" if feat_notes["fallback_own_lags_only"] else "")
            ),
            "_full_model_importances": importances_i,
        }
        _attach_diagnostics(record_i, target, n_rows)
        records.append(record_i)

    return records


def _print_summary(records: list[dict]) -> None:
    print("\nseries | model | strategy | MAPE(1-12) | naive_margin | lag1_share | flags")
    caveat_records = []
    for r in records:
        mape = r["mape_mean_1_12"]
        margin = r["margin_over_naive_pct_points"]
        fmt = lambda v: f"{v:.2f}" if v is not None else "NA"
        print(
            f"{r['series']:16s} {r['model']:18s} {r['horizon_strategy']:10s} "
            f"{fmt(mape):>10s} {fmt(margin):>13s} {r['lag1_importance_share']:.2f}   {r['overfit_flags']}"
        )
        if r["overfit_flags"]:
            caveat_records.append(r)

    if caveat_records:
        print("\n=== OVERFITTING CAVEATS -- these must appear in the research report ===")
        for r in caveat_records:
            print(
                f"  {r['series']}/{r['model']}/{r['horizon_strategy']}: flags={r['overfit_flags']} "
                f"(lag1_share={r['lag1_importance_share']:.2f}, "
                f"margin_over_naive={r['margin_over_naive_pct_points']})"
            )


def main():
    df = load_price_history()
    all_records: list[dict] = []

    for target in TARGETS:
        print(f"=== {target} ===")
        all_records.extend(build_ml_records(df, target))

    for r in all_records:
        r.pop("_full_model_importances", None)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(all_records, f, indent=2)

    _print_summary(all_records)
    print(f"\nWrote {len(all_records)} records to {OUT_JSON}")


if __name__ == "__main__":
    main()
