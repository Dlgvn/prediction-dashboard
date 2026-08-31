"""Unit tests for app.forecasting primitives, GARCH unit conversion, SE widening."""

import numpy as np
import pandas as pd
import pytest

from app.forecasting import (
    ARIMA_SE_ORDER,
    DIESEL_LITERS_PER_TON,
    HDAN_GARCH_SIGMA_PCT,
    HDAN_PREDICTORS,
    MODEL_INFO,
    InsufficientHistoryError,
    _apply_garch_spread,
    _apply_se_spread,
    _arima_forecast_se,
    _build_future_exog,
    _forecast_predictor,
    _naive_forecast,
    _require_series,
    diesel_mnt_forecast,
    forecast_all,
    forecast_diesel_usd,
    forecast_fx,
    forecast_hdan,
    forecast_ppan_var_system,
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


def test_ppan_var_system_shape_and_finite(synthetic_history):
    result = forecast_ppan_var_system(synthetic_history, horizon=12)
    assert set(result.keys()) == {"base", "bull", "bear", "warning"}
    for key in ("base", "bull", "bear"):
        assert len(result[key]) == 12
        assert np.isfinite(np.asarray(result[key])).all()
    assert "hdan" not in result
    # No gap in synthetic_history's system-member columns -> no warning.
    assert result["warning"] == ""


def test_ppan_responds_to_system_members(synthetic_history):
    baseline = forecast_ppan_var_system(synthetic_history, horizon=12)

    perturbed_history = synthetic_history.copy()
    last_urals = perturbed_history["urals"].iloc[-1]
    perturbed_history.loc[perturbed_history.index[-1], "urals"] = last_urals * 1.2

    perturbed = forecast_ppan_var_system(perturbed_history, horizon=12)

    base_arr = np.asarray(baseline["base"])
    perturbed_arr = np.asarray(perturbed["base"])
    assert np.any(np.abs(base_arr - perturbed_arr) > 1e-6)


def test_ppan_var_system_band_equals_arima_se(synthetic_history):
    result = forecast_ppan_var_system(synthetic_history, horizon=12)
    expected_se = _arima_forecast_se(synthetic_history["ppan"], (0, 1, 0), 12)
    actual_half_width = np.asarray(result["bull"]) - np.asarray(result["base"])
    assert actual_half_width == pytest.approx(expected_se, rel=1e-9)


def test_ppan_var_system_raises_on_missing_member(synthetic_history):
    history = synthetic_history.drop(columns=["urals"])
    with pytest.raises(InsufficientHistoryError):
        forecast_ppan_var_system(history, horizon=6)


def test_ppan_var_system_warns_on_stale_anchor_row(synthetic_history):
    """A recent gap in a single system-member column (urals) while ppan/hdan
    stay current must not silently anchor on a stale feature row -- it must
    still produce a valid forecast AND surface a non-empty warning naming
    the stale column.
    """
    history = synthetic_history.copy()
    history.loc[history.index[-2] :, "urals"] = np.nan

    result = forecast_ppan_var_system(history, horizon=3)

    # Forecast is still produced and numerically valid.
    for key in ("base", "bull", "bear"):
        assert len(result[key]) == 3
        assert np.isfinite(np.asarray(result[key])).all()

    # Staleness is surfaced, mentioning the offending column.
    assert result["warning"] != ""
    assert "urals" in result["warning"]


def test_ppan_var_system_no_warning_when_anchor_is_current(synthetic_history):
    result = forecast_ppan_var_system(synthetic_history, horizon=3)
    assert result["warning"] == ""


def test_forecast_all_surfaces_ppan_warning(synthetic_history):
    history = synthetic_history.copy()
    history.loc[history.index[-1], "urals"] = np.nan

    result = forecast_all(history, horizon=3, markup_pct=0.0)

    assert "warning" in result
    assert result["warning"] != ""
    assert "urals" in result["warning"]
    # Series output shape is unaffected by the added key.
    for key in ("hdan", "ppan", "diesel_usd_ton", "fx_rate", "diesel_mnt"):
        assert len(result[key]) == 3


def test_forecast_diesel_usd_holds_last_value(synthetic_history):
    result = forecast_diesel_usd(synthetic_history, horizon=12)
    assert len(set(result["base"])) == 1
    last_value = float(synthetic_history["diesel_usd_ton"].dropna().iloc[-1])
    assert result["base"][0] == pytest.approx(last_value)


def test_forecast_fx_holds_last_value(synthetic_history):
    result = forecast_fx(synthetic_history, horizon=12)
    assert len(set(result["base"])) == 1
    last_value = float(synthetic_history["fx_rate"].dropna().iloc[-1])
    assert result["base"][0] == pytest.approx(last_value)


def test_diesel_and_fx_use_distinct_volatility_orders(synthetic_history):
    assert ARIMA_SE_ORDER["diesel_usd_ton"] != ARIMA_SE_ORDER["fx_rate"]

    diesel = forecast_diesel_usd(synthetic_history, horizon=12)
    fx = forecast_fx(synthetic_history, horizon=12)

    diesel_base = diesel["base"][-1]
    fx_base = fx["base"][-1]
    diesel_relative_half_width = (diesel["bull"][-1] - diesel_base) / diesel_base
    fx_relative_half_width = (fx["bull"][-1] - fx_base) / fx_base

    assert diesel_relative_half_width != pytest.approx(
        fx_relative_half_width, abs=1e-6
    )


def test_diesel_and_fx_bands_widen_with_horizon(synthetic_history):
    for forecaster in (forecast_diesel_usd, forecast_fx):
        result = forecaster(synthetic_history, horizon=12)
        half_widths = [
            result["bull"][i] - result["base"][i] for i in range(12)
        ]
        assert all(
            half_widths[i] <= half_widths[i + 1] + 1e-9
            for i in range(len(half_widths) - 1)
        )


def test_forecast_fx_raises_on_missing_column(synthetic_history):
    history = synthetic_history.drop(columns=["fx_rate"])
    with pytest.raises(InsufficientHistoryError):
        forecast_fx(history, horizon=6)


def test_forecast_diesel_usd_raises_on_missing_column(synthetic_history):
    history = synthetic_history.drop(columns=["diesel_usd_ton"])
    with pytest.raises(InsufficientHistoryError):
        forecast_diesel_usd(history, horizon=6)


# ---------------------------------------------------------------------------
# Task 1: diesel_mnt_forecast + forecast_all
# ---------------------------------------------------------------------------


def test_diesel_mnt_forecast_zero_markup_is_plain_product():
    diesel_fc = {"base": [10.0, 11.0], "bull": [12.0, 13.0], "bear": [8.0, 9.0]}
    fx_fc = {"base": [3000.0, 3010.0], "bull": [3100.0, 3110.0], "bear": [2900.0, 2910.0]}
    result = diesel_mnt_forecast(diesel_fc, fx_fc, markup_pct=0.0)
    assert set(result.keys()) == {"base", "bull", "bear"}
    for i in range(2):
        assert result["base"][i] == pytest.approx(
            diesel_fc["base"][i] * fx_fc["base"][i] / DIESEL_LITERS_PER_TON
        )
        assert result["bull"][i] == pytest.approx(
            diesel_fc["bull"][i] * fx_fc["bull"][i] / DIESEL_LITERS_PER_TON
        )
        assert result["bear"][i] == pytest.approx(
            diesel_fc["bear"][i] * fx_fc["bear"][i] / DIESEL_LITERS_PER_TON
        )


def test_diesel_mnt_forecast_applies_markup():
    diesel_fc = {"base": [10.0], "bull": [12.0], "bear": [8.0]}
    fx_fc = {"base": [3000.0], "bull": [3100.0], "bear": [2900.0]}
    result = diesel_mnt_forecast(diesel_fc, fx_fc, markup_pct=5.0)
    assert result["base"][0] == pytest.approx(
        10.0 * 3000.0 * 1.05 / DIESEL_LITERS_PER_TON
    )


def test_forecast_all_shape_and_keys(synthetic_history):
    result = forecast_all(synthetic_history, horizon=6, markup_pct=5.0)
    series_keys = {
        "hdan",
        "ppan",
        "diesel_usd_ton",
        "fx_rate",
        "diesel_mnt",
    }
    # `warning` is an additive sixth key -- a plain str, not a row list.
    assert set(result.keys()) == series_keys | {"warning"}
    for key in series_keys:
        rows = result[key]
        assert len(rows) == 6
        for row in rows:
            assert set(row.keys()) == {"month", "base", "bull", "bear"}
        assert [row["month"] for row in rows] == [1, 2, 3, 4, 5, 6]


def test_forecast_all_diesel_mnt_agrees_with_diesel_usd_and_fx(synthetic_history):
    result = forecast_all(synthetic_history, horizon=6, markup_pct=5.0)
    for i in range(6):
        expected = (
            result["diesel_usd_ton"][i]["base"]
            * result["fx_rate"][i]["base"]
            * 1.05
            / DIESEL_LITERS_PER_TON
        )
        assert result["diesel_mnt"][i]["base"] == pytest.approx(expected)


def test_forecast_all_calls_diesel_usd_and_fx_exactly_once(monkeypatch, synthetic_history):
    calls = {"diesel_usd": 0, "fx": 0}

    real_diesel = forecast_diesel_usd
    real_fx = forecast_fx

    def counting_diesel(history, horizon):
        calls["diesel_usd"] += 1
        return real_diesel(history, horizon)

    def counting_fx(history, horizon):
        calls["fx"] += 1
        return real_fx(history, horizon)

    monkeypatch.setattr("app.forecasting.forecast_diesel_usd", counting_diesel)
    monkeypatch.setattr("app.forecasting.forecast_fx", counting_fx)

    from app.forecasting import forecast_all as patched_forecast_all

    patched_forecast_all(synthetic_history, horizon=6, markup_pct=0.0)

    assert calls["diesel_usd"] == 1
    assert calls["fx"] == 1


def test_forecast_all_raises_on_invalid_horizon(synthetic_history):
    with pytest.raises(ValueError):
        forecast_all(synthetic_history, horizon=13, markup_pct=5.0)
    with pytest.raises(ValueError):
        forecast_all(synthetic_history, horizon=0, markup_pct=5.0)


# ---------------------------------------------------------------------------
# Task 2: FCST-02..FCST-05 requirement-level tests
# ---------------------------------------------------------------------------


def test_forecast_all_shape(synthetic_history):
    """FCST-02: One call to forecast_all returns base/bull/bear for HDAN,
    PPAN, Diesel-USD, FX, and Diesel-MNT at the chosen horizon."""
    result = forecast_all(synthetic_history, horizon=12, markup_pct=5.0)
    series_keys = {
        "hdan",
        "ppan",
        "diesel_usd_ton",
        "fx_rate",
        "diesel_mnt",
    }
    # `warning` is an additive sixth key (empty str here -- no stale-anchor
    # condition in synthetic_history) alongside the five P-02 series keys.
    assert set(result.keys()) == series_keys | {"warning"}
    assert result["warning"] == ""
    for key in series_keys:
        rows = result[key]
        assert len(rows) == 12
        for row in rows:
            for field in ("base", "bull", "bear"):
                assert np.isfinite(row[field])
            assert row["bull"] > row["base"] > row["bear"], key


def test_diesel_mnt_derivation(synthetic_history):
    """FCST-03: Diesel-MNT is computed as
    Diesel-USD x FX x (1 + markup_pct/100) / DIESEL_LITERS_PER_TON
    per horizon step, never modeled independently."""
    result = forecast_all(synthetic_history, horizon=12, markup_pct=5.0)
    for i in range(12):
        for edge in ("base", "bull", "bear"):
            expected = (
                result["diesel_usd_ton"][i][edge]
                * result["fx_rate"][i][edge]
                * 1.05
                / DIESEL_LITERS_PER_TON
            )
            assert result["diesel_mnt"][i][edge] == pytest.approx(expected)

    # Diesel-MNT is not independently modeled: scaling the input fx_rate
    # column by 2x should scale diesel_mnt.base by approximately 2x.
    scaled_history = synthetic_history.copy()
    scaled_history["fx_rate"] = scaled_history["fx_rate"] * 2.0
    scaled_result = forecast_all(scaled_history, horizon=12, markup_pct=5.0)

    for i in range(12):
        ratio = (
            scaled_result["diesel_mnt"][i]["base"] / result["diesel_mnt"][i]["base"]
        )
        assert ratio == pytest.approx(2.0, rel=0.05)


def test_spread_uses_named_volatility_source(synthetic_history):
    """FCST-04: Every series' band uses its named volatility source, not one
    flat spread percentage shared across series."""
    result = forecast_all(synthetic_history, horizon=12, markup_pct=5.0)

    relative_half_widths = {}
    for key in ("hdan", "ppan", "diesel_usd_ton", "fx_rate"):
        row = result[key][-1]
        relative_half_widths[key] = (row["bull"] - row["base"]) / row["base"]

    values = list(relative_half_widths.values())
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            assert values[i] != pytest.approx(values[j], rel=1e-3), (
                relative_half_widths
            )

    # HDAN's h=1 half-width matches the GARCH formula.
    hdan_h1 = result["hdan"][0]
    expected_hdan_half_width = hdan_h1["base"] * HDAN_GARCH_SIGMA_PCT[0] / 100.0
    assert hdan_h1["bull"] - hdan_h1["base"] == pytest.approx(
        expected_hdan_half_width, rel=1e-6
    )

    # PPAN's h=1 half-width matches its ARIMA(0,1,0) SE.
    ppan_h1 = result["ppan"][0]
    expected_ppan_se = _arima_forecast_se(
        synthetic_history["ppan"], ARIMA_SE_ORDER["ppan"], 1
    )[0]
    assert ppan_h1["bull"] - ppan_h1["base"] == pytest.approx(
        expected_ppan_se, rel=1e-6
    )


def test_spread_widens_with_horizon(synthetic_history):
    """FCST-05: Every series' band widens with horizon."""
    result = forecast_all(synthetic_history, horizon=12, markup_pct=5.0)

    for key in ("hdan", "ppan", "diesel_usd_ton", "fx_rate", "diesel_mnt"):
        rows = result[key]
        half_widths = [row["bull"] - row["base"] for row in rows]
        assert half_widths[-1] > half_widths[0], key
        assert all(
            half_widths[i] <= half_widths[i + 1] + 1e-9
            for i in range(len(half_widths) - 1)
        ), key


def test_model_info_has_exactly_forecast_all_keys():
    """VIS-05: MODEL_INFO keys must match forecast_all's 5 returned keys exactly."""
    assert set(MODEL_INFO) == {"hdan", "ppan", "diesel_usd_ton", "fx_rate", "diesel_mnt"}


def test_model_info_hdan():
    assert MODEL_INFO["hdan"] == ("SARIMAX", 13.33)


def test_model_info_ppan():
    assert MODEL_INFO["ppan"] == ("Direct-OLS VAR", 23.80)


def test_model_info_diesel_usd_ton():
    assert MODEL_INFO["diesel_usd_ton"] == ("Naive", 7.04)


def test_model_info_fx_rate():
    assert MODEL_INFO["fx_rate"] == ("Naive", 1.72)


def test_model_info_diesel_mnt_has_no_mape():
    """D-01: Diesel MNT is derived, has no independent backtest MAPE."""
    name, mape = MODEL_INFO["diesel_mnt"]
    assert name == "Derived (Diesel USD × FX ÷ 1,136 L)"
    assert mape is None


def test_model_info_mape_values_are_float_or_none():
    for name, mape in MODEL_INFO.values():
        assert isinstance(name, str)
        assert mape is None or isinstance(mape, float)


def test_model_info_matches_forecast_all_output_keys(synthetic_history):
    """No-drift guard: MODEL_INFO keys track forecast_all's five series keys
    (the additive `warning` key is not a modeled series, so it's excluded)."""
    result = forecast_all(synthetic_history, horizon=1, markup_pct=5.0)
    assert set(MODEL_INFO) == set(result.keys()) - {"warning"}
