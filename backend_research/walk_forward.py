"""Shared rolling-origin (walk-forward) backtest harness for Phase 2.

D-07 (02-CONTEXT.md) requires walk-forward validation, not a single fixed
holdout, for every model family tested this phase. This module is the ONLY
place in the repo that slices walk-forward windows — every runner script
(naive/ETS, ARIMA/SARIMAX, VAR, GARCH, ML) must import and reuse this
function rather than re-implementing its own loop (RESEARCH.md "Don't
Hand-Roll": walk-forward slicing is the single most dangerous bug class in
this phase). Stays model-agnostic: no model-fitting-library imports here.
"""

import numpy as np
import pandas as pd


class LeakageError(AssertionError):
    """Raised when the harness detects (or could not prevent) train/forecast leakage."""


def walk_forward_backtest(
    series,
    exog,
    fit_fn,
    min_train: int = 36,
    horizon: int = 12,
    step: int = 1,
    refit_every: int = 1,
) -> pd.DataFrame:
    """Rolling-origin backtest.

    series: full target Series, ascending PeriodIndex.
    exog: optional DataFrame of predictors aligned to series.index, or None.
    fit_fn: callable(train_series, train_exog) -> object with
        .forecast(steps, exog=future_exog) -> length-`steps` sequence.
    min_train: minimum training window length before the first origin.
    horizon: max steps ahead to forecast at each origin.
    step: origin stride.
    refit_every: refit the model every N origins (1 = every origin).

    Returns a DataFrame with columns [origin_date, horizon_step, forecast,
    actual]. `df.attrs["refit_every"]` records the cadence used;
    `df.attrs["failed_origins"]` lists origins whose fit/forecast raised.
    """
    n = len(series)

    if min_train >= n:
        raise LeakageError(
            f"walk_forward_backtest: min_train={min_train} >= len(series)={n}; "
            "degenerate training window, cannot guarantee no leakage"
        )

    records = []
    failed_origins = []
    fitted = None

    for i, origin in enumerate(range(min_train, n, step)):
        train_y = series.iloc[:origin]
        train_x = exog.iloc[:origin] if exog is not None else None

        first_target_date = series.index[origin]
        if train_y.index.max() >= first_target_date:
            raise LeakageError(
                f"walk_forward_backtest: origin index {origin}: training window max "
                f"date {train_y.index.max()} is not strictly before the first "
                f"forecast target date {first_target_date}"
            )

        max_h = min(horizon, n - origin)
        if max_h < 1:
            continue

        try:
            if fitted is None or i % refit_every == 0:
                fitted = fit_fn(train_y, train_x)

            if exog is not None:
                future_x = exog.iloc[origin : origin + max_h]
                preds = fitted.forecast(steps=max_h, exog=future_x)
            else:
                preds = fitted.forecast(steps=max_h)

            preds = np.asarray(preds).ravel()

            origin_date = series.index[origin - 1]
            for h in range(1, max_h + 1):
                records.append(
                    {
                        "origin_date": origin_date,
                        "horizon_step": h,
                        "forecast": preds[h - 1],
                        "actual": series.iloc[origin + h - 1],
                    }
                )
        except Exception:
            failed_origins.append(origin)
            continue

    results = pd.DataFrame(
        records, columns=["origin_date", "horizon_step", "forecast", "actual"]
    )
    results.attrs["refit_every"] = refit_every
    results.attrs["failed_origins"] = failed_origins
    return results


def mape_by_horizon(results_df: pd.DataFrame) -> pd.Series:
    """Mean absolute percentage error per horizon_step, ignoring actual==0/NaN rows."""
    df = results_df.copy()
    df = df[df["actual"].notna() & (df["actual"] != 0)]
    ape = (df["forecast"] - df["actual"]).abs() / df["actual"].abs() * 100
    return ape.groupby(df["horizon_step"]).mean()


def single_holdout_mape(series, exog, fit_fn, holdout: int = 12) -> float:
    """One fixed split at len(series)-holdout; mean MAPE over the holdout window.

    Exists so every runner can also report the D-07-comparability number
    against REPORT.md's prior single-holdout figures (HDAN 9.4%, PPAN 10.0%,
    Diesel-USD 3.4%, FX 0.25%).
    """
    n = len(series)
    origin = n - holdout
    if origin < 1:
        raise LeakageError(
            f"single_holdout_mape: holdout={holdout} >= len(series)={n}"
        )

    train_y = series.iloc[:origin]
    train_x = exog.iloc[:origin] if exog is not None else None

    fitted = fit_fn(train_y, train_x)

    if exog is not None:
        future_x = exog.iloc[origin : origin + holdout]
        preds = fitted.forecast(steps=holdout, exog=future_x)
    else:
        preds = fitted.forecast(steps=holdout)

    preds = np.asarray(preds).ravel()
    actual = series.iloc[origin : origin + holdout].to_numpy()

    mask = actual != 0
    ape = np.abs(preds[mask] - actual[mask]) / np.abs(actual[mask]) * 100
    return float(np.mean(ape))
