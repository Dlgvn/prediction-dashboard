"""Naive / moving-average / SES / Holt-damped baselines under walk-forward validation.

Every later model family in this phase is judged against these numbers (Pitfall 4 /
D-01: "the baseline every other model must beat"). All four specs fit on price LEVELS
(not pct-change) so MAPE is directly comparable across families. Uses the shared
`walk_forward_backtest` harness for every model -- no bespoke loops, per RESEARCH.md's
"Don't Hand-Roll" guidance.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing

from db_loader import TARGETS, load_price_history
from walk_forward import mape_by_horizon, single_holdout_mape, walk_forward_backtest

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).resolve().parent / "results"
OUT_JSON = RESULTS_DIR / "wf_baseline_ets.json"

MIN_TRAIN = 36
HORIZON = 12
REFIT_EVERY = 1


class NaiveForecaster:
    """Random-walk benchmark: repeats the last training value for every horizon step."""

    def __init__(self, train_y):
        self.last = float(train_y.iloc[-1])

    def forecast(self, steps):
        return np.full(steps, self.last)


class MovingAverageForecaster:
    """Repeats the mean of the last `window` training observations."""

    def __init__(self, train_y, window: int = 3):
        self.mean = float(train_y.iloc[-window:].mean())

    def forecast(self, steps):
        return np.full(steps, self.mean)


class _SESWrapper:
    def __init__(self, train_y):
        self.fitted = SimpleExpSmoothing(train_y.to_numpy(), initialization_method="estimated").fit()

    def forecast(self, steps):
        return self.fitted.forecast(steps)


class _HoltDampedWrapper:
    def __init__(self, train_y):
        # seasonal=None -- fewer than two clean annual cycles for some series; see
        # RESEARCH.md Pattern 4 / Pitfall re: seasonal terms in that regime.
        self.fitted = ExponentialSmoothing(
            train_y.to_numpy(),
            trend="add",
            seasonal=None,
            damped_trend=True,
            initialization_method="estimated",
        ).fit()

    def forecast(self, steps):
        return self.fitted.forecast(steps)


SPECS = [
    ("Naive", "baseline", "iterative", lambda train_y, train_x: NaiveForecaster(train_y)),
    (
        "MovingAverage(3)",
        "baseline",
        "iterative",
        lambda train_y, train_x: MovingAverageForecaster(train_y, window=3),
    ),
    ("SES", "ets", "iterative", lambda train_y, train_x: _SESWrapper(train_y)),
    (
        "HoltDamped",
        "ets",
        "iterative",
        lambda train_y, train_x: _HoltDampedWrapper(train_y),
    ),
]


def build_records(series_name: str, y) -> list[dict]:
    y = y.dropna()
    n = len(y)
    records = []

    for model_name, family, strategy, fit_fn in SPECS:
        wf = walk_forward_backtest(
            y,
            None,
            fit_fn,
            min_train=MIN_TRAIN,
            horizon=HORIZON,
            step=1,
            refit_every=REFIT_EVERY,
        )
        mbh = mape_by_horizon(wf)
        mape_by_h = {str(h): (float(mbh[h]) if h in mbh.index else None) for h in range(1, 13)}
        mean_1_12 = float(np.nanmean([v for v in mape_by_h.values() if v is not None])) if any(
            v is not None for v in mape_by_h.values()
        ) else None

        try:
            holdout_mape = single_holdout_mape(y, None, fit_fn, holdout=12)
        except Exception as exc:
            holdout_mape = None
            print(f"  [warn] single_holdout_mape failed for {series_name}/{model_name}: {exc}")

        notes = f"n={n} after dropna"
        if model_name in ("SES", "HoltDamped"):
            notes += "; seasonal=None (insufficient annual cycles for some series)"
        notes += "; no direct multi-step variant for this family -- flat/native forecasts are inherently iterative"

        records.append(
            {
                "series": series_name,
                "model": model_name,
                "family": family,
                "horizon_strategy": strategy,
                "predictors": {},
                "mape_by_horizon": mape_by_h,
                "mape_mean_1_12": mean_1_12,
                "single_holdout_mape": holdout_mape,
                "n_origins": int(wf["origin_date"].nunique()) if len(wf) else 0,
                "refit_every": REFIT_EVERY,
                "failed_origins": len(wf.attrs.get("failed_origins", [])),
                "notes": notes,
            }
        )

    return records


def main():
    df = load_price_history()
    all_records = []

    for series_name in TARGETS:
        print(f"=== {series_name} ===")
        all_records.extend(build_records(series_name, df[series_name]))

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(all_records, f, indent=2)

    print("\nseries | model | h=1 | h=6 | h=12")
    for r in all_records:
        h1 = r["mape_by_horizon"]["1"]
        h6 = r["mape_by_horizon"]["6"]
        h12 = r["mape_by_horizon"]["12"]
        fmt = lambda v: f"{v:.2f}" if v is not None else "NA"
        print(f"{r['series']:16s} {r['model']:16s} {fmt(h1):>8s} {fmt(h6):>8s} {fmt(h12):>8s}")

    print(f"\nWrote {len(all_records)} records to {OUT_JSON}")


if __name__ == "__main__":
    main()
