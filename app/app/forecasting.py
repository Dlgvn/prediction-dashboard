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
