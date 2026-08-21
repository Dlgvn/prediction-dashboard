"""Unit tests for app.forecasting primitives, GARCH unit conversion, SE widening."""

import numpy as np
import pandas as pd
import pytest

from app.forecasting import (
    HDAN_GARCH_SIGMA_PCT,
    HDAN_PREDICTORS,
    InsufficientHistoryError,
    _apply_garch_spread,
    _apply_se_spread,
    _arima_forecast_se,
    _build_future_exog,
    _forecast_predictor,
    _naive_forecast,
    _require_series,
    forecast_hdan,
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


def test_build_future_exog_shape_order_and_no_nan(synthetic_history):
    frame = _build_future_exog(synthetic_history, horizon=12)
    assert list(frame.columns) == HDAN_PREDICTORS
    assert len(frame) == 12
    assert frame.isna().sum().sum() == 0


def test_build_future_exog_lag1_predictor_uses_last_observed(synthetic_history):
    frame = _build_future_exog(synthetic_history, horizon=12)
    # ppan has lag 1
    last_observed = float(synthetic_history["ppan"].dropna().iloc[-1])
    assert frame["ppan"].iloc[0] == pytest.approx(last_observed)


def test_future_exog_respects_ammonia_lag_3(synthetic_history):
    """Regression test for the planner_correction in 03-02-PLAN.md.

    03-RESEARCH.md Pattern 1 incorrectly claims the future exog frame can
    simply reuse `_forecast_predictor`'s forward path directly for every
    predictor. That is only true for lag-1 predictors. For `ammonia`
    (lag 3), rows 0-2 of the future frame must equal the last three
    OBSERVED ammonia values (T-2, T-1, T), and only row 3 onward should
    come from the forecast path. Do NOT "simplify" this back to the
    forward path -- that silently shifts ammonia's contribution three
    months early with no exception raised.
    """
    frame = _build_future_exog(synthetic_history, horizon=12)
    observed_tail = synthetic_history["ammonia"].dropna().iloc[-3:].to_numpy()
    np.testing.assert_allclose(
        frame["ammonia"].iloc[0:3].to_numpy(), observed_tail, rtol=1e-9
    )

    last_observed = float(synthetic_history["ammonia"].dropna().iloc[-1])
    assert frame["ammonia"].iloc[3] != pytest.approx(last_observed, rel=1e-6)


def test_build_future_exog_raises_on_short_ammonia_history():
    short_history = pd.DataFrame(
        {p: [1.0] * 30 for p in HDAN_PREDICTORS}, index=range(30)
    )
    short_history["ammonia"] = [1.0, 2.0] + [None] * 28
    with pytest.raises(InsufficientHistoryError) as exc_info:
        _build_future_exog(short_history, horizon=6)
    assert "ammonia" in str(exc_info.value)


def test_forecast_hdan_shape_and_finite(synthetic_history):
    result = forecast_hdan(synthetic_history, horizon=12)
    assert set(result.keys()) == {"base", "bull", "bear"}
    for key in ("base", "bull", "bear"):
        assert len(result[key]) == 12
        assert np.isfinite(np.asarray(result[key])).all()


def test_forecast_hdan_garch_unit_conversion(synthetic_history):
    result = forecast_hdan(synthetic_history, horizon=12)
    base0 = result["base"][0]
    expected_half_width = base0 * 12.532726174302507 / 100
    assert result["bull"][0] - base0 == pytest.approx(expected_half_width, rel=1e-9)


def test_forecast_hdan_bull_base_bear_ordering(synthetic_history):
    result = forecast_hdan(synthetic_history, horizon=12)
    for i in range(12):
        assert result["bull"][i] > result["base"][i] > result["bear"][i]


def test_forecast_hdan_band_widens(synthetic_history):
    result = forecast_hdan(synthetic_history, horizon=12)
    half_widths = [result["bull"][i] - result["base"][i] for i in range(12)]
    assert all(
        half_widths[i] < half_widths[i + 1] for i in range(len(half_widths) - 1)
    )


def test_forecast_hdan_raises_on_missing_hdan_column(synthetic_history):
    history = synthetic_history.drop(columns=["hdan"])
    with pytest.raises(InsufficientHistoryError):
        forecast_hdan(history, horizon=6)
