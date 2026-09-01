"""Leakage-guard, no-inf, index-contract, and calendar-lag regression tests for
`sentiment_data_loader.py`.

These tests exist for the same reason `test_walk_forward.py` exists: a single
off-by-one in a lag/shift boundary silently produces an implausibly good (or
wrong) result, and this phase's SENT-01 requirement means the reported
effective monthly sample size must be trustworthy. The calendar-lag tests use
synthetic fixtures (not the real archive) so they are exact and independent of
future archive refreshes; the data-contract tests (no-inf, index contract,
bounded weighted_compound, no zero-article months) run against the real,
checked-in archive files as regression tests.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from walk_forward import LeakageError

from sentiment_data_loader import SENTIMENT_PREDICTORS, load_sentiment_monthly, merge_lagged


def _dense_series(start="2024-01", periods=6, values=None):
    idx = pd.period_range(start=start, periods=periods, freq="M")
    if values is None:
        values = np.arange(1, periods + 1, dtype="float64")
    return pd.Series(values, index=idx)


def test_merge_lagged_zero_lag_raises():
    y = _dense_series(periods=6)
    x = _dense_series(periods=6)
    with pytest.raises(LeakageError):
        merge_lagged(y, x, lag=0)


def test_merge_lagged_negative_lag_raises():
    y = _dense_series(periods=6)
    x = _dense_series(periods=6)
    with pytest.raises(LeakageError):
        merge_lagged(y, x, lag=-1)


def test_merge_lagged_non_period_index_raises():
    y = _dense_series(periods=6)
    x = _dense_series(periods=6)
    x.index = pd.DatetimeIndex(x.index.to_timestamp())
    with pytest.raises(LeakageError):
        merge_lagged(y, x, lag=1)


def test_merge_lagged_y_non_period_index_raises():
    y = _dense_series(periods=6)
    x = _dense_series(periods=6)
    y.index = pd.DatetimeIndex(y.index.to_timestamp())
    with pytest.raises(LeakageError):
        merge_lagged(y, x, lag=1)


def test_merge_lagged_dense_calendar_correct():
    y = _dense_series(start="2024-01", periods=6, values=np.arange(100, 106, dtype="float64"))
    x = _dense_series(start="2024-01", periods=6, values=np.arange(1000, 1006, dtype="float64"))

    result = merge_lagged(y, x, lag=2)

    for month in result.index:
        expected_x = x.loc[month - 2]
        assert result.loc[month, "x_lag"] == expected_x


def test_merge_lagged_gappy_calendar_correct():
    # Target is dense monthly; predictor is present only in scattered months.
    y = _dense_series(start="2024-01", periods=8, values=np.arange(200, 208, dtype="float64"))
    gappy_index = pd.PeriodIndex(["2024-01", "2024-03", "2024-06"], freq="M")
    x = pd.Series([10.0, 30.0, 60.0], index=gappy_index)

    result = merge_lagged(y, x, lag=1)

    # Every returned row's x_lag must originate exactly from (target month - 1),
    # and only months with an observation at (target month - 1) may appear.
    for month in result.index:
        source_month = month - 1
        assert source_month in gappy_index
        assert result.loc[month, "x_lag"] == x.loc[source_month]

    # Target months whose (month - 1) predecessor has no observation must be
    # entirely absent from the result.
    for month in y.index:
        source_month = month - 1
        if source_month not in gappy_index:
            assert month not in result.index


def test_load_sentiment_monthly_no_inf():
    frame = load_sentiment_monthly()
    assert not np.isinf(frame[SENTIMENT_PREDICTORS].to_numpy(dtype="float64")).any()


def test_load_sentiment_monthly_index_contract():
    frame = load_sentiment_monthly()
    assert isinstance(frame.index, pd.PeriodIndex)
    assert frame.index.freqstr == "M"
    assert frame.index.is_monotonic_increasing
    assert not frame.index.has_duplicates
    assert frame["weighted_compound"].between(-1, 1).all()


def test_load_sentiment_monthly_no_zero_article_months():
    frame = load_sentiment_monthly()
    assert (frame["article_count"] > 0).all()
