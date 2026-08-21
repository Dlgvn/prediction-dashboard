"""Shared, validated data loading for all phase-1 research scripts.
Reuses the exact cleaning logic already validated this session (see chat history:
AN model re-validation and Diesel model re-validation)."""
import pandas as pd
import numpy as np

AN_CSV = "/Users/dlgvnbyr/Desktop/Prediction Dashboard/AN Data.csv"
DIESEL_CSV = "/Users/dlgvnbyr/Desktop/Prediction Dashboard/Diesel Data.csv"

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
