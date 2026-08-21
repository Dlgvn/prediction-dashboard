"""Framework-independent forecasting primitives for the prediction dashboard.

This module has ZERO `import reflex` (D-08). It holds every frozen model
constant Phase 3 is allowed to use -- each one transcribed from a named
Phase 2 output file -- plus the shared forecast primitives that plans
02-04 compose (Naive point forecast, auxiliary ARIMA forecast-standard-error
helper, HDAN predictor sub-model helper). No runtime order-selection search
of any kind (AIC grid search, automatic ARIMA order tools, or any
hyperparameter sweep) is permitted here or in any module built on top of
it -- see `02-MODEL-DECISIONS.md` "Phase 3 must not". All inputs/outputs
are plain pandas/numpy/float objects;
no ORM instance and no `rx.session()` ever appears in this file.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

# ---------------------------------------------------------------------------
# Frozen constants -- every value below is transcribed from a named Phase 2
# output file. See 02-MODEL-DECISIONS.md and the <planner_verified_facts>
# block in 03-01-PLAN.md for provenance. Do not re-derive or re-search any
# of these at runtime.
# ---------------------------------------------------------------------------

# HDAN's SARIMAX(0,1,0)+exog predictor set, in load-bearing order (exog
# column alignment -- see 03-RESEARCH.md Pitfall 2). Never rebuild from a
# dict or set.
HDAN_PREDICTORS = [
    "ppan",
    "urea_china",
    "urea_black_sea",
    "ammonia",
    "baltic_an",
    "corn_us",
]

# Per-predictor lag, from 02-MODEL-DECISIONS.md HDAN predictor set.
HDAN_PREDICTOR_LAGS = {
    "ppan": 1,
    "urea_china": 1,
    "urea_black_sea": 1,
    "ammonia": 3,
    "baltic_an": 1,
    "corn_us": 1,
}

# HDAN's winning SARIMAX order (02-MODEL-DECISIONS.md).
HDAN_SARIMAX_ORDER = (0, 1, 0)

# HDAN's GARCH(1,1) volatility, from backend_research/results/garch_volatility.json
# -> hdan.sigma_by_horizon, h=1..12. These are PERCENT-RETURN units
# (run_garch.py fits on series.pct_change() * 100) -- D-06b freezes this
# static array; `arch` is never imported by `app/`.
HDAN_GARCH_SIGMA_PCT = [
    12.532726174302507,
    12.583026997209927,
    12.633127540913241,
    12.6830301788432,
    12.73273723791998,
    12.782250999819277,
    12.83157370219443,
    12.880707539856434,
    12.929654665913594,
    12.978417192872477,
    13.026997193701803,
    13.075396702860736,
]

# Auxiliary ARIMA orders used ONLY to derive forecast-standard-error spreads
# for series whose winning model is not itself an ARIMA (ppan, diesel_usd_ton,
# fx_rate). Source: backend_research/results/wf_arima_sarimax.json,
# family == "arima" records.
ARIMA_SE_ORDER = {
    "ppan": (0, 1, 0),
    "diesel_usd_ton": (1, 1, 1),
    "fx_rate": (1, 1, 2),
}

# PPAN's Direct-OLS VAR-system members, in order (02-MODEL-DECISIONS.md).
PPAN_SYSTEM_MEMBERS = ["hdan", "baltic_an", "urals"]

# PPAN target lags used by the direct-OLS VAR system.
PPAN_TARGET_LAGS = (1, 2, 3)

MAX_HORIZON = 12
MIN_HISTORY_ROWS = 24

# Orders used by `_forecast_predictor` to project an exogenous predictor
# forward when it is needed as SARIMAX exog input (not a winning-model
# order for any tracked series -- purely a helper for feeding predictors).
PREDICTOR_ARIMA_ORDER = (1, 1, 0)
PREDICTOR_ARIMA_FALLBACK_ORDER = (0, 1, 0)


class InsufficientHistoryError(ValueError):
    """Raised when input history is too short or too sparse to forecast.

    This is the module's single typed failure mode for degenerate input,
    so the Phase 4/5 state layer can catch one exception type rather than
    a raw statsmodels traceback.
    """


def _require_series(
    history: pd.DataFrame,
    column: str,
    horizon: int,
    min_rows: int = MIN_HISTORY_ROWS,
) -> pd.Series:
    """Validate and return a cleaned, non-null series ready for fitting.

    Raises `InsufficientHistoryError` if `column` is missing from `history`
    or has fewer than `min_rows` non-null values. Raises `ValueError` if
    `horizon` is not an int in 1..MAX_HORIZON.
    """
    if column not in history.columns:
        raise InsufficientHistoryError(
            f"Column '{column}' is not present in the supplied history."
        )

    if not isinstance(horizon, int) or isinstance(horizon, bool) or not (
        1 <= horizon <= MAX_HORIZON
    ):
        raise ValueError(
            f"horizon must be an int in 1..{MAX_HORIZON}, got {horizon!r}."
        )

    cleaned = history[column].dropna()
    if len(cleaned) < min_rows:
        raise InsufficientHistoryError(
            f"Column '{column}' has {len(cleaned)} non-null rows, "
            f"but at least {min_rows} are required to forecast."
        )

    return cleaned


# ---------------------------------------------------------------------------
# Shared forecast primitives
# ---------------------------------------------------------------------------


def _naive_forecast(series: pd.Series, horizon: int) -> np.ndarray:
    """Repeat the last non-null value of `series` for `horizon` steps."""
    last_value = float(series.dropna().iloc[-1])
    return np.full(horizon, last_value)


def _arima_forecast_se(series: pd.Series, order: tuple, horizon: int) -> np.ndarray:
    """Return per-horizon ARIMA forecast standard errors, in series units.

    Deliberately returns ONLY `.se_mean` -- never `.predicted_mean`. The
    point forecast for any given series comes from that series' actual
    winning model (VAR / Naive / SARIMAX), never from this auxiliary ARIMA
    fit; returning `.predicted_mean` here would silently swap in the
    runner-up model's point forecast (Pitfall 3). Uses `.se_mean` (not
    `.se`, which does not exist on this object, and not an in-sample
    residual std, which would not widen with horizon and would violate
    FCST-05).
    """
    fitted = ARIMA(series.dropna().to_numpy(), order=order).fit()
    forecast_result = fitted.get_forecast(steps=horizon)
    return np.asarray(forecast_result.se_mean)


def _forecast_predictor(series: pd.Series, horizon: int) -> np.ndarray:
    """Project an exogenous predictor forward via ARIMA (per D-02).

    Never holds flat at the last value. Falls back to
    PREDICTOR_ARIMA_FALLBACK_ORDER if the primary order's fit raises.
    """
    values = series.dropna().to_numpy()
    try:
        fitted = ARIMA(values, order=PREDICTOR_ARIMA_ORDER).fit()
    except Exception:
        fitted = ARIMA(values, order=PREDICTOR_ARIMA_FALLBACK_ORDER).fit()
    return np.asarray(fitted.forecast(steps=horizon))


def _apply_garch_spread(base, horizon: int) -> dict:
    """Apply HDAN's frozen GARCH percent-return sigma to a base forecast.

    `HDAN_GARCH_SIGMA_PCT` is in PERCENT-RETURN units (see the constant's
    definition), so the offset divides by 100.0 to convert to a fraction
    of `base` before scaling -- omitting this division is the classic
    off-by-100 bug this helper guards against (Pitfall 1).
    """
    base_arr = np.asarray(base, dtype=float)
    sigma_pct = np.asarray(HDAN_GARCH_SIGMA_PCT[:horizon], dtype=float)
    offset = base_arr * sigma_pct / 100.0  # percent-return -> fraction of base
    return {
        "base": base_arr.tolist(),
        "bull": (base_arr + offset).tolist(),
        "bear": (base_arr - offset).tolist(),
    }


def _build_future_exog(history: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Build HDAN's lag-aware future exog frame for `horizon` steps ahead.

    Fit-time convention (from `run_arima_sarimax_wf.build_sarimax_records`):
    the exog value the model sees at time `t` for predictor `p` is
    `history[p]` shifted by `p`'s own lag, i.e. the predictor's value at
    `t - lag_p`. So at future step `h` (1-indexed) the exog value needed
    for predictor `p` is that predictor's value at `T + h - lag_p`, where
    `T` is the position of the last observed row. For lag-1 predictors this
    means step h=1 uses the last observed actual and steps h>=2 use the
    forecast path directly; for `ammonia` (lag 3) steps h=1..3 use the last
    three *observed* actuals and only step h=4 onward uses the forecast
    path -- using the forward path directly for ammonia would shift its
    contribution three months early (see 03-02-PLAN.md planner_correction).
    """
    columns: dict[str, np.ndarray] = {}
    for predictor in HDAN_PREDICTORS:
        observed = _require_series(history, predictor, horizon)
        lag = HDAN_PREDICTOR_LAGS[predictor]
        t_last = len(observed) - 1

        if t_last + 1 - lag < 0:
            raise InsufficientHistoryError(
                f"Predictor '{predictor}' has lag {lag} but only "
                f"{t_last + 1} observed rows are available."
            )

        path = _forecast_predictor(observed, horizon)
        extended = np.concatenate([observed.to_numpy(), path])

        future_values = np.array(
            [extended[t_last + h - lag] for h in range(1, horizon + 1)],
            dtype=float,
        )
        columns[predictor] = future_values

    frame = pd.DataFrame(columns)
    return frame[HDAN_PREDICTORS]


def _apply_se_spread(base, se) -> dict:
    """Apply an ARIMA forecast-SE spread to a base forecast.

    `se` (from `_arima_forecast_se`) is already in the series' own units,
    so no unit conversion applies here (contrast with the GARCH path in
    `_apply_garch_spread`, which converts from percent-return units).
    """
    base_arr = np.asarray(base, dtype=float)
    se_arr = np.asarray(se, dtype=float)
    return {
        "base": base_arr.tolist(),
        "bull": (base_arr + se_arr).tolist(),
        "bear": (base_arr - se_arr).tolist(),
    }
