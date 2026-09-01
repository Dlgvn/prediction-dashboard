"""Monthly sentiment predictor loader for the Phase 16 causality screen.

Builds a Mongolia-local (UTC+8), monthly-cadence sentiment predictor frame
from `archive/news_sentiment_raw.csv`'s full article timestamps, plus
`archive/ml_features.csv`'s numeric `vix_regime_code`. Deliberately rebuilds
`weighted_compound` (and the derived EMA/momentum columns) from the raw,
per-article rows rather than resampling the archive's pre-aggregated daily
sentiment file -- that file's `date` column is date-only (already bucketed to
a UTC calendar day), so it cannot be timezone-corrected to Mongolia-local
after the fact.

Also provides `merge_lagged()`, the single leakage-guarded alignment point
between a price target series and a sentiment predictor series, reusing
`walk_forward.LeakageError` rather than defining a parallel exception class.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# This file sits one level below backend_research/ (in backend_research/sentiment/),
# so the flat `from walk_forward import ...` used throughout backend_research/ needs
# a sys.path shim to resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from walk_forward import LeakageError  # noqa: E402

ARCHIVE_DIR = Path(__file__).resolve().parent.parent.parent / "archive"
RAW_CSV = ARCHIVE_DIR / "news_sentiment_raw.csv"
ML_FEATURES_CSV = ARCHIVE_DIR / "ml_features.csv"

# Mongolia is a fixed UTC+8 offset with no DST observed at any point across the
# archive's 2020-2026 coverage, so a flat Timedelta shift is correct (no tz
# database / DST-transition handling needed).
MN_OFFSET = pd.Timedelta(hours=8)

# Exactly the five D-08 predictor columns. D-09 explicitly excludes
# rolling_corr_60d, spy_return_next1d, qqq_return_next1d, dia_return_next1d --
# none of those may ever be added to this list.
SENTIMENT_PREDICTORS = [
    "weighted_compound",
    "sent_ema3",
    "sent_ema10",
    "sent_momentum",
    "vix_regime_code",
]


def load_sentiment_monthly() -> pd.DataFrame:
    """Load a monthly, Mongolia-local sentiment predictor frame.

    Returns a DataFrame indexed by a monthly pandas PeriodIndex (ascending, no
    duplicates), with the five SENTIMENT_PREDICTORS columns (cast to float64,
    no inf) plus `article_count`. Months with zero articles are simply absent
    from the groupby result -- D-06 requires dropping, never forward-filling
    or interpolating, zero-article months, so no gap-filling or reindex-to-
    calendar call of any kind appears anywhere in this function.
    """
    raw = pd.read_csv(RAW_CSV)
    published_at = pd.to_datetime(raw["published_at"], utc=True)

    # Shift to Mongolia-local time before bucketing to month, then drop the tz
    # (localize to None) before to_period("M") so pandas 2.2.3 does not emit
    # the "dropping timezone information" warning.
    local_month = (published_at + MN_OFFSET).dt.tz_localize(None).dt.to_period("M")

    grouped = raw.assign(local_month=local_month).groupby("local_month", sort=True)

    def _weighted_compound(group: pd.DataFrame) -> float:
        # archive/README.md: "High-credibility sources ... receive a 1.5x
        # source weight in the weighted_compound daily aggregate." Recomputed
        # here from raw rows (not resampled from the archive's precomputed
        # daily weighted_compound column, which inherits UTC-day bucketing).
        return float((group["compound"] * group["source_weight"]).sum() / group["source_weight"].sum())

    weighted_compound = grouped.apply(_weighted_compound, include_groups=False)
    article_count = grouped.size()

    monthly = pd.DataFrame(
        {
            "weighted_compound": weighted_compound,
            "article_count": article_count,
        }
    )

    # Genuine month-unit trend columns computed on the monthly weighted_compound
    # series itself. Do NOT resample the archive's day-unit sent_ema3/sent_ema10
    # columns -- a monthly mean of a 3-day EMA is dimensionally meaningless.
    # These values will therefore not match a naive resample of the archive's
    # day-unit columns; that is intentional.
    monthly["sent_ema3"] = monthly["weighted_compound"].ewm(span=3, adjust=False).mean()
    monthly["sent_ema10"] = monthly["weighted_compound"].ewm(span=10, adjust=False).mean()
    monthly["sent_momentum"] = monthly["sent_ema3"] - monthly["sent_ema10"]

    ml_features = pd.read_csv(ML_FEATURES_CSV, parse_dates=["date"])
    # Use the numeric vix_regime_code column only -- the string vix_regime
    # column would make sm.OLS inside granger_ftest raise a casting error.
    # ml_features.csv is keyed on the US trading-day calendar (SPY/QQQ/DIA/VIX
    # source data), not on article-publication timestamps, so the UTC->Mongolia
    # article-time correction (MN_OFFSET) does not apply here.
    ml_month = ml_features["date"].dt.to_period("M")
    vix_regime_code = (
        ml_features.assign(_month=ml_month).groupby("_month")["vix_regime_code"].mean()
    )
    # Label-aligned assignment; months with no ml_features coverage stay NaN --
    # do not fill.
    monthly["vix_regime_code"] = vix_regime_code

    monthly.index.name = "date"
    monthly = monthly.sort_index()

    if not isinstance(monthly.index, pd.PeriodIndex) or monthly.index.freqstr != "M":
        raise ValueError(
            "load_sentiment_monthly: index is not a monthly PeriodIndex — "
            f"got {type(monthly.index)} freq={getattr(monthly.index, 'freqstr', None)}"
        )
    if not monthly.index.is_monotonic_increasing:
        raise ValueError(
            "load_sentiment_monthly: index is not monotonically increasing — "
            f"dates: {list(monthly.index)}"
        )
    if monthly.index.has_duplicates:
        dupes = monthly.index[monthly.index.duplicated()].tolist()
        raise ValueError(f"load_sentiment_monthly: duplicate month index values: {dupes}")

    for col in SENTIMENT_PREDICTORS:
        monthly[col] = monthly[col].astype("float64")

    inf_mask = np.isinf(monthly[SENTIMENT_PREDICTORS]).any()
    if inf_mask.any():
        bad_cols = inf_mask[inf_mask].index.tolist()
        raise ValueError(f"load_sentiment_monthly: inf values present in columns: {bad_cols}")

    return monthly[SENTIMENT_PREDICTORS + ["article_count"]]


def merge_lagged(y: pd.Series, x: pd.Series, lag: int) -> pd.DataFrame:
    """Leakage-guarded, calendar-based lagged merge of a target and predictor.

    Aligns a (dense, monthly) target series `y` against a (possibly gappy,
    monthly) predictor series `x`, shifted `lag` calendar months. Raises
    walk_forward.LeakageError rather than silently returning a same-month (or
    positionally-misaligned) frame.

    Returns a DataFrame with columns `y`, `y_lag1`, `x_lag` (post-dropna).
    Including `y_lag1` makes len(frame) equal the exact n that
    causality_screen.granger_ftest() will compute internally when the same
    two columns are used as its regressors, so the reported n is the true
    effective sample size -- a documented refinement over
    causality_screen.run_granger_sweep()'s overlap precheck, which omits
    y_lag1 and can therefore overstate n.
    """
    if lag < 1:
        raise LeakageError(
            f"merge_lagged: lag must be >= 1 (contemporaneous or negative lag "
            f"leaks the target month's own outcome into the predictor); got lag={lag}"
        )

    if not isinstance(y.index, pd.PeriodIndex) or y.index.freqstr != "M":
        raise LeakageError(
            f"merge_lagged: y.index must be a monthly PeriodIndex, got "
            f"{type(y.index)} freq={getattr(y.index, 'freqstr', None)}"
        )
    if not y.index.is_monotonic_increasing:
        raise LeakageError("merge_lagged: y.index must be monotonically increasing")
    if not isinstance(x.index, pd.PeriodIndex) or x.index.freqstr != "M":
        raise LeakageError(
            f"merge_lagged: x.index must be a monthly PeriodIndex, got "
            f"{type(x.index)} freq={getattr(x.index, 'freqstr', None)}"
        )

    # Project the (possibly gappy) predictor series onto the target's dense
    # monthly index by calendar label, leaving NaN in uncovered months. Never
    # fill. This is what makes the subsequent positional .shift(lag) equivalent
    # to a true calendar-month shift, since x_on_y now shares y's dense,
    # contiguous index.
    x_on_y = x.reindex(y.index)

    frame = pd.DataFrame(
        {"y": y, "y_lag1": y.shift(1), "x_lag": x_on_y.shift(lag)}
    ).dropna()

    # Defensive post-check: recompute the expected predictor values by direct
    # calendar-label lookup and confirm the shift-based x_lag column agrees.
    # Should never fire while the x.reindex(y.index) step above is in place;
    # it exists to catch a future edit that removes the reindex or swaps in a
    # positional shift over the (gappy) original x.index.
    expected = x_on_y.reindex(frame.index - lag)
    expected.index = frame.index
    mismatch = ~np.isclose(frame["x_lag"].to_numpy(), expected.to_numpy(), equal_nan=True)
    if mismatch.any():
        bad_months = frame.index[mismatch].tolist()
        raise LeakageError(
            f"merge_lagged: calendar-lag mismatch detected at months {bad_months} — "
            "x_lag does not equal the value at (target month - lag); a positional "
            "shift may have been substituted for the calendar-label reindex."
        )

    return frame[["y", "y_lag1", "x_lag"]]


if __name__ == "__main__":
    frame = load_sentiment_monthly()
    print(f"shape: {frame.shape}")
    print(f"index min/max: {frame.index.min()} .. {frame.index.max()}")
    print("non-null counts per column:")
    print(frame.count())
