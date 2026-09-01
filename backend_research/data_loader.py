"""Shared, validated data loading for all phase-1 research scripts.
Reuses the exact cleaning logic already validated this session (see chat history:
AN model re-validation and Diesel model re-validation)."""
from pathlib import Path

import pandas as pd
import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
AN_CSV = str(_REPO_ROOT / "AN Data.csv")
DIESEL_CSV = str(_REPO_ROOT / "Diesel Data.csv")
AN_WEEKLY_CSV = str(_REPO_ROOT / "AN price weekly.csv")

def load_an_monthly():
    """Returns monthly DataFrame indexed by YM period: PPAN, HDAN, Baltic AN, Ammonia,
    Urea (last value per month), Natural_gas, Brent (weekly-averaged per month)."""
    df = pd.read_csv(AN_CSV)
    df.columns = [c.strip() for c in df.columns]
    df = df.drop(columns=['Unnamed: 10'], errors='ignore')
    for c in ['PPAN','HDAN','Baltic AN','Ammonia','Urea','Natural_gas','Brent']:
        df[c] = df[c].astype(str).str.replace(',', '').astype(float)
    df['Date'] = pd.to_datetime(df['Date'])
    df['YM'] = df['Date'].dt.to_period('M')
    flat_cols = ['PPAN','HDAN','Baltic AN','Ammonia','Urea']
    varying_cols = ['Natural_gas','Brent']
    monthly = df.groupby('YM')[flat_cols].last().join(df.groupby('YM')[varying_cols].mean()).sort_index()
    return monthly

def load_diesel_monthly():
    """Returns monthly DataFrame indexed by YM period: Diesel (USD/t), Brent (USD/t),
    FX_rate, Import_price_per_liter_usd, Purchased_price_mnt, Urals (USD/bbl, short window)."""
    df = pd.read_csv(DIESEL_CSV)
    df.columns = [c.strip() for c in df.columns]
    numeric_cols = [c for c in df.columns if c != 'Date']
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
    df['YM'] = df['Date'].dt.to_period('M')
    out = df.set_index('YM')[[
        'Import_Volume_Price_per_ton_USD', 'BRENT_Crude_Oil_Price_per_Ton (USD)',
        'FX_rate', 'Import_Volume_Price_per_Liter_USD', 'Purchased_Unit_Price_MNT',
        'URALS_Crude _Oil_(USD/BBL)',
    ]]
    out.columns = ['Diesel_usd_ton', 'Brent_usd_ton', 'FX_rate', 'Diesel_usd_liter',
                   'Purchase_mnt_liter', 'Urals_usd_bbl']
    return out

def load_an_weekly():
    """Returns native weekly DataFrame (no resampling) indexed by week-ending Date:
    PPAN, HDAN, Baltic AN, Ammonia, Urea, Natural_gas, Brent. AN Data.csv rows are already
    ~7 days apart -- this is the un-resampled counterpart to load_an_monthly()."""
    df = pd.read_csv(AN_CSV)
    df.columns = [c.strip() for c in df.columns]
    df = df.drop(columns=['Unnamed: 10'], errors='ignore')
    for c in ['PPAN', 'HDAN', 'Baltic AN', 'Ammonia', 'Urea', 'Natural_gas', 'Brent']:
        df[c] = df[c].astype(str).str.replace(',', '').astype(float)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').set_index('Date')
    return df[['PPAN', 'HDAN', 'Baltic AN', 'Ammonia', 'Urea', 'Natural_gas', 'Brent']]

def load_weekly_drivers():
    """Returns weekly DataFrame from AN price weekly.csv indexed by week-ending Date:
    JKM/HenryHub/UK/Netherlands gas, US/China corn, Baltic AN, Middle East Ammonia,
    Black Sea/China Urea. Dates are 'YYYY.MM.DD', descending; sparser columns (Urea/Ammonia
    reporting lags) are forward-filled after sorting ascending."""
    df = pd.read_csv(AN_WEEKLY_CSV)
    df.columns = [c.strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Week Ending'], format='%Y.%m.%d')
    df = df.drop(columns=['Week Ending']).sort_values('Date').set_index('Date')
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.ffill()
    df.columns = ['Gas_JKM', 'Gas_HenryHub', 'Gas_UK', 'Gas_Netherlands', 'Corn_US', 'Corn_China',
                  'BalticAN_wk', 'MidEastAmmonia_wk', 'BlackSeaUrea_wk', 'ChinaUrea_wk']
    return df

def merged_weekly(tolerance_days=3):
    """Joins load_an_weekly() and load_weekly_drivers() on nearest week-ending date within
    +/- tolerance_days (the two files' week-ending conventions aren't guaranteed to align)."""
    an = load_an_weekly()
    drv = load_weekly_drivers()
    merged = pd.merge_asof(
        an.sort_index(), drv.sort_index(), left_index=True, right_index=True,
        direction='nearest', tolerance=pd.Timedelta(days=tolerance_days),
    )
    return merged.dropna(subset=['BalticAN_wk'])

def merged_monthly():
    """Inner-joins AN and Diesel monthly frames on their shared YM index.
    AN spans 2022-08..2026-07, Diesel spans 2020-02..2026-06 — the merge naturally
    restricts to the overlapping window. Use load_an_monthly()/load_diesel_monthly()
    directly (not this) for any analysis that needs a series' full individual history."""
    an = load_an_monthly()
    di = load_diesel_monthly()
    return an.join(di, how='inner')

if __name__ == '__main__':
    an = load_an_monthly()
    di = load_diesel_monthly()
    mg = merged_monthly()
    print("AN monthly:", an.shape, an.index.min(), "-", an.index.max())
    print("Diesel monthly:", di.shape, di.index.min(), "-", di.index.max())
    print("Merged (overlap):", mg.shape, mg.index.min(), "-", mg.index.max())
    assert an.shape[0] == 48, f"expected 48 AN months, got {an.shape[0]}"
    assert di.shape[0] == 77, f"expected 77 Diesel months, got {di.shape[0]}"
    print("OK")
