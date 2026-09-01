"""Database schema: wide monthly price table, weekly price table, plus global app
settings.

Field list and column order follow the D-05b/D-05c-corrected 16-series
contract (see 01-01-PLAN.md <interfaces>). D-05b retires the single
`natural_gas` column in favour of four named gas benchmarks. D-05c retires
the single `urea` column in favour of `urea_black_sea` + `urea_china`.
D-04: the global markup percentage lives on AppSetting (key="markup_pct"),
NOT as a per-row column on PriceRow.
"""

from typing import Optional

import reflex as rx
import sqlmodel


class PriceRow(rx.Model, table=True):
    """One row per tracked month, wide-table shape (D-01)."""

    date: str = sqlmodel.Field(unique=True, index=True)

    # sourced from AN Data.csv
    hdan: Optional[float] = None
    ppan: Optional[float] = None

    # sourced from AN price weekly.csv
    baltic_an: Optional[float] = None
    ammonia: Optional[float] = None
    urea_black_sea: Optional[float] = None
    urea_china: Optional[float] = None
    natural_gas_jkm: Optional[float] = None
    natural_gas_henry_hub: Optional[float] = None
    natural_gas_uk: Optional[float] = None
    natural_gas_netherlands: Optional[float] = None
    corn_us: Optional[float] = None
    corn_china: Optional[float] = None

    # sourced from Diesel Data.csv
    diesel_usd_ton: Optional[float] = None
    urals: Optional[float] = None
    fx_rate: Optional[float] = None
    brent: Optional[float] = None


class WeeklyPriceRow(rx.Model, table=True):
    """One row per genuine weekly observation (Phase 19). Never derived/resampled
    from PriceRow -- sourced natively from AN Data.csv's weekly rows and FX Data.csv's
    Weekly column. No diesel columns: no weekly diesel source data exists (by design,
    not omission -- see 19-CONTEXT.md)."""

    date: str = sqlmodel.Field(unique=True, index=True)

    # sourced from AN Data.csv (native weekly rows, no resampling)
    hdan: Optional[float] = None
    ppan: Optional[float] = None
    baltic_an: Optional[float] = None

    # sourced from FX Data.csv's Weekly column
    fx_rate: Optional[float] = None


class AppSetting(rx.Model, table=True):
    """Global key/value settings (D-04) — e.g. the markup percentage."""

    key: str = sqlmodel.Field(unique=True, index=True)
    value: float
