"""Shared pytest fixtures for schema tests."""

import sys
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

# Ensure `app/` (this file's parent's parent) is on sys.path so
# `from app.models import PriceRow` resolves when pytest runs from app/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def session():
    """Provide an isolated in-memory SQLite session per test."""
    from app.models import AppSetting, PriceRow  # noqa: F401  (registers tables)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sess:
        yield sess


@pytest.fixture()
def synthetic_history():
    """Deterministic synthetic multi-series history for forecasting tests.

    60 monthly rows, sorted ascending (oldest first), with every column
    named in HDAN_PREDICTORS plus hdan, urals, diesel_usd_ton, fx_rate.
    Each column has a mild upward trend plus noise so ARIMA fits converge
    and trend-detection assertions are meaningful.
    """
    import numpy as np
    import pandas as pd

    from app.forecasting import HDAN_PREDICTORS

    rng = np.random.default_rng(20260821)
    n = 60
    index = pd.date_range("2021-01-01", periods=n, freq="MS")

    columns = list(HDAN_PREDICTORS) + ["hdan", "urals", "diesel_usd_ton", "fx_rate"]
    data = {}
    for i, col in enumerate(columns):
        base = 100.0 + 10.0 * i
        trend = np.linspace(0, 20, n)
        noise = rng.normal(0, 1.5, n)
        data[col] = base + trend + noise

    return pd.DataFrame(data, index=index)
