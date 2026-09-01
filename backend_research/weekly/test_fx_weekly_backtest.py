"""Tests proving run_fx_weekly_backtest.py's FX weekly loader, wrapper
cleanliness, and horizon-matched MAPE / go-no-go comparison are computed
from the shared walk_forward_backtest harness's real output -- never
hardcoded or hardwired.

These exist because a "no-go is a valid outcome" screen is only
trustworthy if the comparison against BENCHMARK_MAPE is a live boolean
derived from measured data, not a constant that always resolves one way.
Uses plain assert and small local synthetic-series builders, matching
test_walk_forward.py's / test_weekly_sarimax_ets.py's house style -- no
fixtures framework.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from walk_forward import walk_forward_backtest  # noqa: E402,F401

# pytest prepends the test file's own directory, so this resolves without an extra shim.
from run_fx_weekly_backtest import (  # noqa: E402
    ARIMA_ORDER_GRID,
    BENCHMARK_MAPE,
    HORIZON_WEEKLY,
    MIN_TRAIN_WEEKLY,
    RESULTS_JSON,
    _HoltDampedWrapper,
    _SARIMAXWrapper,
    beats_benchmark,
    build_univariate_records,
    load_fx_weekly,
    select_arima_order,
)


def _make_fx_series(n=130, seed=0, jump=False):
    idx = pd.date_range("2020-01-06", periods=n, freq="7D")
    rng = np.random.default_rng(seed)
    values = rng.normal(0.5, 8.0, n).cumsum() + 3400.0
    if jump:
        values[-15:] += 400.0
    return pd.Series(values, index=idx)


def test_load_fx_weekly_shape():
    y = load_fx_weekly()
    assert y.shape[0] == 865
    assert y.index.min() == pd.Timestamp("2010-01-04")
    assert y.index.max() == pd.Timestamp("2026-07-27")
    assert y.dtype == "float64"


def test_select_arima_order_within_grid_bounds():
    y = _make_fx_series(n=120, seed=1)
    order, aic = select_arima_order(y)
    p_bound = max(o[0] for o in ARIMA_ORDER_GRID)
    d_bound = max(o[1] for o in ARIMA_ORDER_GRID)
    q_bound = max(o[2] for o in ARIMA_ORDER_GRID)
    assert 0 <= order[0] <= p_bound
    assert 0 <= order[1] <= d_bound
    assert 0 <= order[2] <= q_bound


def test_sarimax_wrapper_forecasts_five_clean_values():
    y = _make_fx_series(n=120, seed=2)
    wrapper = _SARIMAXWrapper(y, None, order=(1, 1, 0))
    preds = wrapper.forecast(steps=5)
    preds = np.asarray(preds).ravel()
    assert len(preds) == 5
    assert not np.any(np.isnan(preds))


def test_holt_damped_wrapper_forecasts_five_clean_values():
    y = _make_fx_series(n=120, seed=3)
    wrapper = _HoltDampedWrapper(y)
    preds = wrapper.forecast(steps=5)
    preds = np.asarray(preds).ravel()
    assert len(preds) == 5
    assert not np.any(np.isnan(preds))


def test_build_univariate_records_mape_is_data_derived_not_hardcoded():
    # A smooth series vs. one with a large injected jump near the end must produce
    # DIFFERENT mape_h4 values -- a hardcoded constant would produce the same number
    # for both, so a difference proves the value is computed from real backtest output.
    y_smooth = _make_fx_series(n=130, seed=4, jump=False)
    y_jump = _make_fx_series(n=130, seed=4, jump=True)

    records_smooth = build_univariate_records("FX", y_smooth)
    records_jump = build_univariate_records("FX", y_jump)

    sarimax_smooth = next(r for r in records_smooth if r["family"] == "sarimax")
    sarimax_jump = next(r for r in records_jump if r["family"] == "sarimax")

    assert sarimax_smooth["mape_h4"] is not None
    assert sarimax_jump["mape_h4"] is not None
    assert sarimax_smooth["mape_h4"] != sarimax_jump["mape_h4"]


def test_build_univariate_records_shape():
    y = _make_fx_series(n=130, seed=5)
    records = build_univariate_records("FX", y)
    assert len(records) == 2
    families = {r["family"] for r in records}
    assert families == {"sarimax", "ets"}
    for r in records:
        assert r["series"] == "FX"
        assert r["driver_variant"] == "univariate"
        assert r["benchmark_mape"] == BENCHMARK_MAPE["FX"]
        assert r["min_train"] == MIN_TRAIN_WEEKLY
        assert r["horizon"] == HORIZON_WEEKLY
        assert "n_origins" in r and "failed_origins" in r


def test_beats_benchmark_true_below_threshold():
    assert beats_benchmark(BENCHMARK_MAPE["FX"] - 0.5, "FX") is True


def test_beats_benchmark_false_above_threshold():
    assert beats_benchmark(BENCHMARK_MAPE["FX"] + 0.5, "FX") is False


def test_beats_benchmark_false_when_none():
    assert beats_benchmark(None, "FX") is False


def test_frozen_results_json_has_two_records_with_required_shape():
    assert RESULTS_JSON.exists()
    with open(RESULTS_JSON, encoding="utf-8") as f:
        records = json.load(f)

    assert len(records) == 2
    assert {r["series"] for r in records} == {"FX"}

    required_keys = {
        "series",
        "model",
        "family",
        "driver_variant",
        "mape_h4",
        "mape_h5",
        "benchmark_mape",
        "beats_benchmark_h4",
        "n_origins",
        "failed_origins",
        "min_train",
        "horizon",
    }
    for r in records:
        assert required_keys <= set(r)
        assert r["benchmark_mape"] == BENCHMARK_MAPE["FX"]
