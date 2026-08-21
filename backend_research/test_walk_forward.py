"""Leakage-prevention and correctness tests for the shared walk-forward harness.

These tests exist because a single off-by-one in the train/forecast window
boundary silently produces implausibly good MAPE (RESEARCH.md Pitfall 1) —
this is the single most dangerous bug class in Phase 2. Write once, tested,
before any model-family runner script exists.
"""

import numpy as np
import pandas as pd
import pytest

from walk_forward import (
    LeakageError,
    mape_by_horizon,
    walk_forward_backtest,
)


def _make_series(n=60, start="2013-01"):
    idx = pd.period_range(start=start, periods=n, freq="M")
    values = np.arange(1, n + 1, dtype="float64") * 10.0
    return pd.Series(values, index=idx)


class _RecordingFitFn:
    """fit_fn that records train_series.index.max() at each call."""

    def __init__(self):
        self.calls = []

    def __call__(self, train_series, train_exog):
        self.calls.append(train_series.index.max())
        return _ConstantForecaster(last_value=train_series.iloc[-1])


class _ConstantForecaster:
    def __init__(self, last_value):
        self.last_value = last_value

    def forecast(self, steps, exog=None):
        return np.full(steps, self.last_value)


def test_no_leakage():
    series = _make_series(60)
    recorder = _RecordingFitFn()

    results = walk_forward_backtest(
        series, exog=None, fit_fn=recorder, min_train=36, horizon=12, step=1
    )

    assert len(recorder.calls) > 0
    for i, origin_train_max in enumerate(recorder.calls):
        origin = 36 + i
        first_target_period = series.index[origin]
        assert origin_train_max < first_target_period, (
            f"origin {origin}: train max {origin_train_max} not strictly before "
            f"first forecast target {first_target_period}"
        )
    assert not results.empty


def test_exog_window_alignment():
    series = _make_series(60)
    exog = pd.DataFrame(
        {"pred": np.arange(1, 61, dtype="float64")}, index=series.index
    )

    captured = {}

    def fit_fn(train_series, train_exog):
        assert len(train_exog) == len(train_series)

        class _F:
            def forecast(self, steps, exog=None):
                captured["exog_len"] = len(exog)
                return np.zeros(steps)

        return _F()

    walk_forward_backtest(
        series, exog=exog, fit_fn=fit_fn, min_train=36, horizon=12, step=1
    )

    assert captured["exog_len"] > 0


def test_horizon_records_complete():
    series = _make_series(60)
    recorder = _RecordingFitFn()

    results = walk_forward_backtest(
        series, exog=None, fit_fn=recorder, min_train=36, horizon=12, step=1
    )

    assert results["horizon_step"].min() >= 1
    assert results["horizon_step"].max() <= 12

    n_origins = len(recorder.calls)
    h1_rows = results[results["horizon_step"] == 1]
    assert len(h1_rows) == n_origins


def test_actual_matches_series():
    series = _make_series(60)
    recorder = _RecordingFitFn()

    results = walk_forward_backtest(
        series, exog=None, fit_fn=recorder, min_train=36, horizon=12, step=1
    )

    for _, row in results.iterrows():
        expected_actual = series.loc[row["origin_date"] + row["horizon_step"]]
        assert row["actual"] == expected_actual


def test_leakage_guard_raises():
    series = _make_series(10)

    def fit_fn(train_series, train_exog):
        return _ConstantForecaster(last_value=0.0)

    with pytest.raises(LeakageError):
        walk_forward_backtest(
            series, exog=None, fit_fn=fit_fn, min_train=20, horizon=12, step=1
        )


def test_mape_by_horizon():
    results_df = pd.DataFrame(
        {
            "origin_date": pd.period_range("2020-01", periods=4, freq="M"),
            "horizon_step": [1, 1, 2, 2],
            "forecast": [110.0, 90.0, 105.0, 115.0],
            "actual": [100.0, 100.0, 100.0, 100.0],
        }
    )

    result = mape_by_horizon(results_df)

    assert result.loc[1] == pytest.approx(10.0)
    assert result.loc[2] == pytest.approx(10.0)
