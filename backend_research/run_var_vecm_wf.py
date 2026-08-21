"""VAR systems from causality-screened predictors, plus VECM where the 02-02
cointegration sweep found a long-run equilibrium relationship, both under the
shared walk-forward harness (D-01's causal/econometric family).

Framing (Pitfall: mixing levels and percent-changes silently produces nonsense
MAPE -- see T-02-09):
  - VAR is fit on PERCENT CHANGES (stationary), consistent with
    run_var_candidates.py's prior framing. The fit_fn wrapper reconstructs
    price-level forecasts from the pct-change forecast path before returning,
    so the shared harness always compares levels to levels like every other
    family this phase.
  - VECM is fit on LEVELS -- the entire point of an error-correction model is
    the long-run level relationship -- so its wrapper does NOT do the
    pct-to-level reconstruction; `.predict()` already returns levels. A
    magnitude sanity assertion guards against the two framings being mixed up.

VAR order (lag) and, for VECM, the cointegration rank are each selected ONCE
on the first training window and then held fixed across all walk-forward
origins -- Pitfall 2 cost control, mirroring the ARIMA-order-fixing pattern in
plan 02-04's run_arima_sarimax_wf.py.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, select_coint_rank

from causality_screen import VECM_CANDIDATES, shortlist_for
from db_loader import TARGETS, load_price_history
from run_arima_sarimax_wf import _DirectMultistepWrapper, direct_ols_multistep  # noqa: F401 (reused per D-06)
from walk_forward import mape_by_horizon, single_holdout_mape, walk_forward_backtest

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUT_JSON = RESULTS_DIR / "wf_var_vecm.json"

MIN_TRAIN = 48  # min_train=48 (RESEARCH.md guard against degenerate multivariate fits at early origins)
HORIZON = 12
REFIT_EVERY = 1
MAX_ENDOGENOUS = 4  # target + up to 3 members; degrees-of-freedom cap per RESEARCH.md

# Prior single-holdout VAR figures from backend_research/REPORT.md, used for the
# leakage sanity check (Pitfall 1).
PRIOR_HOLDOUT_MAPE = {"hdan": 9.49, "ppan": 10.08, "diesel_usd_ton": None, "fx_rate": None}

FORCED_CROSS = {"hdan": "ppan", "ppan": "hdan"}


def build_var_system(target: str) -> tuple[list[str], list[str]]:
    """Ordered endogenous member list (excluding target) plus a per-member note.

    Members: D-04's forced other-AN-product cross-inclusion first, then up to
    the remaining slots filled by shortlist_for(target, tier="p10") in
    ascending-p order. Capped so target + members <= MAX_ENDOGENOUS (a
    degrees-of-freedom constraint: RESEARCH.md notes a 4-series VAR needs
    ~20-30 observations before the first origin to avoid degenerate fits,
    and PITFALLS.md flags small-sample overfitting as this project's core
    risk).
    """
    shortlist = shortlist_for(target, tier="p10")  # dict predictor -> lag, ascending p, cap 6
    screen_selected = list(shortlist.keys())

    members: list[str] = []
    notes: list[str] = []

    forced = FORCED_CROSS.get(target)
    if forced is not None:
        members.append(forced)
        if forced in screen_selected:
            notes.append(f"{forced}: forced by D-04 AN cross-inclusion (also screen-selected)")
        else:
            notes.append(f"{forced}: forced by D-04 AN cross-inclusion (screen did not surface it)")

    for p in screen_selected:
        if len(members) >= MAX_ENDOGENOUS - 1:
            break
        if p == forced:
            continue
        members.append(p)
        notes.append(f"{p}: screen-selected (causality p<0.10)")

    return members, notes


def _empty_record(series_name: str, family: str, note: str) -> dict:
    return {
        "series": series_name,
        "model": None,
        "family": family,
        "horizon_strategy": "iterative",
        "predictors": {},
        "mape_by_horizon": {str(h): None for h in range(1, 13)},
        "mape_mean_1_12": None,
        "single_holdout_mape": None,
        "n_origins": 0,
        "refit_every": REFIT_EVERY,
        "failed_origins": 0,
        "notes": note,
    }


def check_leakage(series_name, model_name, wf_mape):
    prior = PRIOR_HOLDOUT_MAPE.get(series_name)
    if prior is None or wf_mape is None:
        return
    if wf_mape < prior * 0.5:
        print(
            f"LEAKAGE SUSPECT: {series_name}/{model_name} walk-forward MAPE={wf_mape:.2f} "
            f"is dramatically better than prior single-holdout MAPE={prior} -- investigate before trusting this number."
        )


class _VARIterativeWrapper:
    """VAR fit on percent changes; forecast() reconstructs price levels.

    Ignores any `exog` passed by the harness at forecast time -- the whole
    point of a joint VAR is that member forecasts come from the model, not
    from observed future actuals (using future actuals there would leak).
    """

    def __init__(self, train_y_level: pd.Series, train_x_pct: pd.DataFrame | None, target_col: str, lag: int):
        target_pct = (train_y_level.pct_change() * 100).rename(target_col)
        if train_x_pct is not None and len(train_x_pct.columns):
            frame = pd.concat([target_pct, train_x_pct], axis=1).dropna()
        else:
            frame = target_pct.to_frame().dropna()
        self.cols = list(frame.columns)
        self.lag = max(1, lag)
        self.fitted = VAR(frame).fit(self.lag)
        self._history = frame.values[-self.lag :]
        self.last_level = float(train_y_level.iloc[-1])

    def forecast(self, steps, exog=None):
        pct_path = self.fitted.forecast(self._history, steps=steps)
        target_pct = pct_path[:, 0] / 100.0
        cum = np.cumprod(1 + target_pct)
        return self.last_level * cum


def select_var_lag(train_y_level: pd.Series, train_x_pct: pd.DataFrame | None, target_col: str, maxlags: int = 3) -> int:
    target_pct = (train_y_level.pct_change() * 100).rename(target_col)
    if train_x_pct is not None and len(train_x_pct.columns):
        frame = pd.concat([target_pct, train_x_pct], axis=1).dropna()
    else:
        frame = target_pct.to_frame().dropna()
    try:
        sel = VAR(frame).select_order(maxlags=maxlags)
        lag = sel.aic
        return int(lag) if lag and lag > 0 else 1
    except Exception:
        return 1


def build_var_records(levels: pd.DataFrame, target: str) -> list[dict]:
    members, member_notes = build_var_system(target)

    target_level = levels[target].iloc[1:]
    if members:
        member_pct = (levels[members].pct_change() * 100).iloc[1:]
    else:
        member_pct = pd.DataFrame(index=target_level.index)

    # Align lengths (both already share the same trimmed index from levels).
    combined_idx = target_level.index.intersection(member_pct.index) if len(members) else target_level.index
    target_level = target_level.loc[combined_idx]
    member_pct = member_pct.loc[combined_idx] if len(members) else member_pct

    lag = select_var_lag(target_level.iloc[:MIN_TRAIN], member_pct.iloc[:MIN_TRAIN] if len(members) else None, target)

    fit_fn = lambda train_y, train_x: _VARIterativeWrapper(train_y, train_x, target, lag)

    exog_arg = member_pct if len(members) else None
    wf = walk_forward_backtest(
        target_level, exog_arg, fit_fn, min_train=MIN_TRAIN, horizon=HORIZON, step=1, refit_every=REFIT_EVERY
    )
    mbh = mape_by_horizon(wf)
    mape_by_h = {str(h): (float(mbh[h]) if h in mbh.index else None) for h in range(1, 13)}
    present = [v for v in mape_by_h.values() if v is not None]
    mean_1_12 = float(np.nanmean(present)) if present else None

    try:
        holdout_mape = single_holdout_mape(target_level, exog_arg, fit_fn, holdout=12)
    except Exception:
        holdout_mape = None

    check_leakage(target, "VAR-iterative", mean_1_12)

    system_desc = ", ".join(member_notes) if member_notes else "no members (univariate VAR degenerate to AR)"
    records = [
        {
            "series": target,
            "model": f"VAR(lag={lag}) system=[{target}, {', '.join(members)}]",
            "family": "var",
            "horizon_strategy": "iterative",
            "predictors": {m: None for m in members},
            "mape_by_horizon": mape_by_h,
            "mape_mean_1_12": mean_1_12,
            "single_holdout_mape": holdout_mape,
            "n_origins": int(wf["origin_date"].nunique()) if len(wf) else 0,
            "refit_every": REFIT_EVERY,
            "failed_origins": len(wf.attrs.get("failed_origins", [])),
            "notes": (
                f"endogenous system: {target} (target) + {members}; {system_desc}; "
                f"MAX_ENDOGENOUS={MAX_ENDOGENOUS} is a degrees-of-freedom cap (RESEARCH.md: "
                "a 4-series VAR needs ~20-30 obs before the first origin to avoid degenerate "
                "fits), not a modelling preference; fit on pct-change, reconstructed to levels "
                "inside the wrapper before comparison"
            ),
        }
    ]

    # --- Direct multi-step counterpart (D-06), reusing plan 02-04's approach on LEVELS ---
    if members:
        direct_df = pd.concat([target_level.rename(target), levels[members].loc[combined_idx]], axis=1)
        for lg in (1, 2, 3):
            direct_df[f"{target}_lag{lg}"] = target_level.shift(lg)
        direct_df = direct_df.dropna(subset=[target])
        feature_cols = list(members) + [f"{target}_lag{lg}" for lg in (1, 2, 3)]

        def fit_direct(train_y, train_x):
            idx = train_y.index
            frame = direct_df.loc[direct_df.index.isin(idx)]
            return _DirectMultistepWrapper(frame, target, feature_cols, max_h=HORIZON)

        wf_direct = walk_forward_backtest(
            target_level, exog_arg, fit_direct, min_train=MIN_TRAIN, horizon=HORIZON, step=1, refit_every=REFIT_EVERY
        )
        mbh_d = mape_by_horizon(wf_direct)
        mape_by_h_d = {str(h): (float(mbh_d[h]) if h in mbh_d.index else None) for h in range(1, 13)}
        present_d = [v for v in mape_by_h_d.values() if v is not None]
        mean_1_12_d = float(np.nanmean(present_d)) if present_d else None

        check_leakage(target, "VAR-direct", mean_1_12_d)

        records.append(
            {
                "series": target,
                "model": f"Direct-OLS VAR-system(h=1..12) system=[{target}, {', '.join(members)}]",
                "family": "var",
                "horizon_strategy": "direct",
                "predictors": {m: None for m in members},
                "mape_by_horizon": mape_by_h_d,
                "mape_mean_1_12": mean_1_12_d,
                "single_holdout_mape": None,
                "n_origins": int(wf_direct["origin_date"].nunique()) if len(wf_direct) else 0,
                "refit_every": REFIT_EVERY,
                "failed_origins": len(wf_direct.attrs.get("failed_origins", [])),
                "notes": (
                    f"direct multi-step OLS reusing run_arima_sarimax_wf._DirectMultistepWrapper; "
                    f"features=VAR system members {members} (levels) + {target} lags 1-3"
                ),
            }
        )
    else:
        records.append(_empty_record(target, "var", f"no VAR members for {target}; direct strategy skipped (degenerate)"))

    return records


class _VECMWrapper:
    """VECM fit on LEVELS. Asserts forecast magnitude sanity (T-02-09)."""

    def __init__(self, train_df_levels: pd.DataFrame, coint_rank: int):
        self.fitted = VECM(train_df_levels, k_ar_diff=1, coint_rank=coint_rank, deterministic="ci").fit()
        self.last_level = float(train_df_levels.iloc[-1, 0])

    def forecast(self, steps, exog=None):
        preds = self.fitted.predict(steps=steps)
        target_preds = preds[:, 0]
        if self.last_level != 0:
            for v in target_preds:
                ratio = abs(v) / abs(self.last_level) if self.last_level else np.inf
                if ratio > 10 or ratio < 0.1:
                    raise AssertionError(
                        f"VECM forecast magnitude {v} is >10x away from last observed level "
                        f"{self.last_level} -- likely levels/pct-change framing bug (T-02-09)"
                    )
        return target_preds


def build_vecm_records(levels: pd.DataFrame) -> list[dict]:
    if not VECM_CANDIDATES:
        note = (
            "no cointegrating relationship found at p<0.05 in the Engle-Granger sweep; VECM not "
            "applicable -- plain VAR on differences is the correct specification"
        )
        return [_empty_record(t, "vecm", note) for t in TARGETS]

    records = []
    for candidate in VECM_CANDIDATES:
        a, b = candidate["pair"]
        pair_levels = levels[[a, b]].dropna()

        rank_sel = select_coint_rank(pair_levels.iloc[:MIN_TRAIN], det_order=0, k_ar_diff=1)
        coint_rank = int(rank_sel.rank) if rank_sel.rank > 0 else 1

        for target, other in ((a, b), (b, a)):
            series_for_wrapper = pair_levels[[target, other]]
            fit_fn = lambda train_y, train_x, _cr=coint_rank: _VECMWrapper(
                pd.concat([train_y.rename(target), train_x[other]], axis=1), _cr
            )

            wf = walk_forward_backtest(
                series_for_wrapper[target],
                series_for_wrapper[[other]],
                fit_fn,
                min_train=MIN_TRAIN,
                horizon=HORIZON,
                step=1,
                refit_every=REFIT_EVERY,
            )
            mbh = mape_by_horizon(wf)
            mape_by_h = {str(h): (float(mbh[h]) if h in mbh.index else None) for h in range(1, 13)}
            present = [v for v in mape_by_h.values() if v is not None]
            mean_1_12 = float(np.nanmean(present)) if present else None

            check_leakage(target, "VECM", mean_1_12)

            records.append(
                {
                    "series": target,
                    "model": f"VECM(k_ar_diff=1, coint_rank={coint_rank}) pair=[{a},{b}]",
                    "family": "vecm",
                    "horizon_strategy": "iterative",
                    "predictors": {other: None},
                    "mape_by_horizon": mape_by_h,
                    "mape_mean_1_12": mean_1_12,
                    "single_holdout_mape": None,
                    "n_origins": int(wf["origin_date"].nunique()) if len(wf) else 0,
                    "refit_every": REFIT_EVERY,
                    "failed_origins": len(wf.attrs.get("failed_origins", [])),
                    "notes": (
                        f"cointegrated pair {a}~{b} (p={candidate['p']}) per plan 02-02; "
                        f"coint_rank selected once via select_coint_rank on first window "
                        f"and held fixed; fit on LEVELS (not pct-change)"
                    ),
                }
            )
    return records


def main():
    levels = load_price_history()
    all_records: list[dict] = []

    print("=== VAR (causality-screened systems + D-04 forced AN cross-inclusion) ===")
    for target in TARGETS:
        recs = build_var_records(levels, target)
        all_records.extend(recs)

    print("=== VECM (cointegration-driven, per plan 02-02) ===")
    all_records.extend(build_vecm_records(levels))

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(all_records, f, indent=2)

    print("\nseries | family | strategy | h=1 | h=6 | h=12 | prior_holdout")
    for r in all_records:
        h1 = r["mape_by_horizon"]["1"]
        h6 = r["mape_by_horizon"]["6"]
        h12 = r["mape_by_horizon"]["12"]
        fmt = lambda v: f"{v:.2f}" if v is not None else "NA"
        prior = PRIOR_HOLDOUT_MAPE.get(r["series"])
        print(
            f"{r['series']:16s} {r['family']:6s} {r['horizon_strategy']:10s} "
            f"{fmt(h1):>8s} {fmt(h6):>8s} {fmt(h12):>8s}  (prior REPORT.md VAR: {prior})"
        )

    print(f"\nWrote {len(all_records)} records to {OUT_JSON}")


if __name__ == "__main__":
    main()
