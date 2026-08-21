"""Unit tests for app.forecasting primitives, GARCH unit conversion, SE widening."""

import numpy as np
import pytest

from app.forecasting import (
    HDAN_GARCH_SIGMA_PCT,
    InsufficientHistoryError,
    _apply_garch_spread,
    _apply_se_spread,
    _arima_forecast_se,
    _forecast_predictor,
    _naive_forecast,
    _require_series,
)


def test_require_series_raises_on_short_history():
    import pandas as pd

    history = pd.DataFrame({"hdan": [1.0, 2.0, 3.0, None, 5.0]})
    with pytest.raises(InsufficientHistoryError) as exc_info:
        _require_series(history, "hdan", horizon=1, min_rows=24)
    assert "hdan" in str(exc_info.value)


def test_require_series_raises_on_bad_horizon(synthetic_history):
    with pytest.raises(ValueError):
        _require_series(synthetic_history, "hdan", horizon=13)


def test_naive_forecast_holds_last_value(synthetic_history):
    series = synthetic_history["hdan"]
    result = _naive_forecast(series, horizon=6)
    assert len(result) == 6
    assert np.all(result == float(series.iloc[-1]))


def test_arima_forecast_se_positive_and_widening(synthetic_history):
    series = synthetic_history["fx_rate"]
    se = _arima_forecast_se(series, order=(1, 1, 2), horizon=12)
    assert len(se) == 12
    assert np.all(se > 0)
    assert np.all(np.diff(se) >= -1e-9)


def test_arima_forecast_se_returns_only_se(synthetic_history):
    series = synthetic_history["ppan"]
    result = _arima_forecast_se(series, order=(0, 1, 0), horizon=3)
    # Result must be a plain array of SEs, not a tuple/dict containing a
    # point forecast alongside it.
    assert isinstance(result, np.ndarray)
    assert result.shape == (3,)


def test_forecast_predictor_not_constant_for_trending_input(synthetic_history):
    series = synthetic_history["urea_china"]
    result = _forecast_predictor(series, horizon=6)
    assert len(result) == 6
    assert len(set(np.round(result, 6))) > 1


def test_forecast_predictor_falls_back_on_fit_failure():
    import pandas as pd

    # Degenerate constant series is likely to trip up the primary order;
    # regardless, the function must always return a horizon-length array.
    series = pd.Series([5.0] * 30)
    result = _forecast_predictor(series, horizon=4)
    assert len(result) == 4


def test_garch_spread_unit_conversion():
    horizon = 1
    base = [100.0] * horizon
    spread = _apply_garch_spread(base, horizon)
    bull = spread["bull"]
    assert bull[0] == pytest.approx(112.5327, abs=0.01)
    assert bull[0] != pytest.approx(1252.7, rel=0.01)
    assert bull[0] != pytest.approx(112.53 * 100, rel=0.01)


def test_garch_spread_shape_and_keys():
    horizon = 3
    base = [50.0, 51.0, 52.0]
    spread = _apply_garch_spread(base, horizon)
    assert set(spread.keys()) == {"base", "bull", "bear"}
    assert len(spread["bull"]) == horizon
    assert len(spread["bear"]) == horizon
    for i in range(horizon):
        expected_offset = base[i] * HDAN_GARCH_SIGMA_PCT[i] / 100.0
        assert spread["bull"][i] == pytest.approx(base[i] + expected_offset)
        assert spread["bear"][i] == pytest.approx(base[i] - expected_offset)


def test_apply_se_spread_shape_and_keys():
    base = [10.0, 20.0, 30.0]
    se = [1.0, 2.0, 3.0]
    spread = _apply_se_spread(base, se)
    assert set(spread.keys()) == {"base", "bull", "bear"}
    assert spread["bull"] == [11.0, 22.0, 33.0]
    assert spread["bear"] == [9.0, 18.0, 27.0]
