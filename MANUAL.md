# Forecast Workbook — Manual

*Companion to `README.md`. This file shows each model's equation with today's actual fitted
values plugged in, and walks through the monthly roll-forward process step by step — add August
data, get a September forecast; add September, get October; and so on.*

**Important:** the numbers below are a snapshot as of the last time this file was written — they
are **not frozen into the workbook**. The workbook's `Regression` and `Forecast` tabs still use
live `LINEST` formulas, so every coefficient and forecast here will shift slightly as new months
are added to `Input`. Re-open the workbook to see the current live numbers; treat the equations
below as a worked example of *how* the math works, not a permanently-correct answer.

## How to read a "plugged-in" equation

Each model is a straight line fit on month-over-month % change (not raw price levels). The
general shape is:

```
predicted % change = (coefficient × prior month's % change) + ... + intercept
forecast price = last known price × (1 + predicted % change)
```

Everything below fills that shape in with the actual numbers currently sitting in the workbook.

---

## 1. HDAN / PPAN — bivariate VAR(1)

**Live formula home:** `Regression!D5:F5` (HDAN equation), `Regression!D6:F6` (PPAN equation).

**Equation, coefficients plugged in (snapshot):**

```
HDAN % change  =  0.5481 × (HDAN's last % change)  +  (−0.2294) × (PPAN's last % change)  +  0.00203
PPAN % change  =  0.1281 × (HDAN's last % change)  +   0.2245  × (PPAN's last % change)  +  0.00210
```

**Worked example — forecasting August from July's data:**

As of the last row in Input (2026-07): HDAN's most recent % change was **−10.84%**, PPAN's was
**−17.49%** (both computed in `PctChange!B79` / `PctChange!C79`, i.e. June→July move).

```
HDAN % change  =  0.5481×(−0.1084)  +  (−0.2294)×(−0.1749)  +  0.00203
               =  −0.0594  +  0.0401  +  0.00203
               =  −0.0173  (≈ −1.73%)

HDAN forecast  =  463.165 × (1 − 0.0173)  =  455.16
```

```
PPAN % change  =  0.1281×(−0.1084)  +  0.2245×(−0.1749)  +  0.00210
               =  −0.0139  +  (−0.0393)  +  0.00210
               =  −0.0511  (≈ −5.11%)

PPAN forecast  =  475.645 × (1 − 0.0511)  =  451.36
```

Both match what's currently in `Forecast!D2` / `Forecast!D3` — this is exactly what the
workbook is computing, spelled out by hand.

## 2. Diesel (USD/ton) — own momentum + Brent crude, lagged 2 months

**Live formula home:** `Regression!D3:E3`.

**Equation, coefficients plugged in (snapshot):**

```
Diesel % change  =  0.1703 × (Brent's % change, 2 months ago)  +  (−0.00053)
```

**Worked example:**

Brent's % change from 2 months before the forecast target (`PctChange!H77`, the May→June move)
was **+0.31%**.

```
Diesel % change  =  0.1703×(0.00314)  +  (−0.00053)
                 =  0.000535  −  0.00053
                 =  0.0000046  (≈ +0.0005%, essentially flat)

Diesel forecast  =  950.31 × (1 + 0.0000046)  =  950.31
```

This matches `Forecast!D4`. Note how small the swing is — Diesel's own recent price barely moves
on this predictor, which is consistent with the model's low error but also means it isn't
reacting to anything more recent than a 2-month-old Brent move.

## 3. USD/MNT FX rate — own momentum only

**Live formula home:** `Regression!D2:E2`.

**Equation, coefficients plugged in (snapshot):**

```
FX % change  =  0.6338 × (FX's own last % change)  +  0.00123
```

**Worked example:**

FX's most recent % change (`PctChange!K78`, May→June) was **+0.017%**.

```
FX % change  =  0.6338×(0.00017)  +  0.00123
             =  0.000106  +  0.00123
             =  0.00134  (≈ +0.13%)

FX forecast  =  3576.69 × (1 + 0.00134)  =  3581.47
```

Matches `Forecast!D5`. Recall the caution from the research report: FX's % change is borderline
stationary (close to a random walk), so this model's low error mostly reflects FX's genuinely
low month-to-month volatility, not real predictive skill — treat this forecast with more caution
than the commodity forecasts above.

## 4. Diesel purchasing price (MNT) — derived, not its own fitted model

**Live formula home:** `Forecast!D6`.

```
Diesel-MNT forecast  =  Diesel-USD forecast × FX forecast × (1 + Markup_%)
                     =  950.31 × 3581.47 × (1 + 0.0282)
                     =  3,499,504
```

`Markup_%` lives at `Input!M2`, currently **2.82%**. This is the empirical backtest-winning
value, not the business's originally stated 9% — it's an editable cell precisely because that
gap needs a human decision (see README.md's "Open flag" section), not because the model is
uncertain about the arithmetic.

---

## Monthly roll-forward: how to actually do this, month after month

The workbook is built so that **adding one row to `Input` is the entire monthly task** — nothing
else needs to be touched. Here's the concrete walkthrough for a run of consecutive months
(September through January, as an example):

### Step 0 — before you touch anything

Close the workbook in Excel if it's open. An open Excel session can silently overwrite changes
made by another tool on save — this has happened once already in this project's history. If
you're editing by hand in Excel itself, this doesn't apply; it only matters if a script (like
`scripts/build_workbook.py`) touches the file while Excel also has it open.

### September

1. Open `AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx`, go to the **Input** tab.
2. Add one new row for **August's actuals** (the row you add always reports the month that just
   finished, since that's when the real numbers become known) — HDAN, PPAN, Baltic_AN, Ammonia,
   Urea, Natural_Gas, Brent, Diesel_USD_ton, Urals, FX_rate. If Diesel/FX data isn't available
   yet for August (it tends to lag AN data by about a month, per the historical pattern), leave
   those cells blank on the same row rather than skipping the row — same rule as before.
3. Save. Every formula in PctChange, Regression, and Forecast recalculates automatically.
4. **Read September's forecast.** Easiest: open the **Dashboard** tab, which shows each
   product's current value, next-month forecast, and an approximate ±MAPE range in one row.
   The same numbers, without the range, are also on `Forecast!D2:D6` (HDAN, PPAN, Diesel-USD,
   FX, Diesel-MNT) if you want to see the bare roll-forward calculation.

### October

1. Add one new row for **September's actuals** (now known, since September has passed).
2. Save.
3. Read `Forecast!D2:D6` again — these now show **October's** forecast. The Regression tab's
   coefficients will have shifted slightly too, since they refit on the growing history
   automatically — that's expected, not a bug.

### November, December, January — same pattern, repeating

Each month:
1. Add the row for the month that just completed.
2. Save.
3. Read the Forecast tab — it always shows **next month's** forecast, one step ahead of
   whatever you just entered.

There is no separate "roll the model forward" action beyond adding the row — the live formulas
do that automatically. The only thing that changes month to month is which row is the "last
actual" the formulas reference (`Input!B79`-style references shift down as rows are added,
since they're written relative to the current last row at build time — see the note below if
you add rows by hand in Excel rather than re-running the build script).

### A note on adding rows by hand vs. re-running the build script

The `Forecast` tab's formulas reference specific row numbers (e.g. `Input!B79`) that were
correct for the workbook's row count *at build time*. Two ways to keep this correct as the
workbook grows:

- **Preferred:** re-run `python3 scripts/build_workbook.py` after updating the source CSVs
  (`AN Data.csv`, `Diesel Data.csv`) with the new month's data — it rebuilds all row references
  to match the new row count automatically. This is the safest option and matches how this
  workbook was originally built.
- **Manual Excel editing:** if you add a row directly in Excel's Input tab instead, you'll need
  to manually extend the `PctChange` tab's formulas down one row (same pattern as the row
  above it) and update the `Forecast` tab's `Input!` / `PctChange!` row references to point at
  the new last row. This is more error-prone — prefer re-running the build script when possible.

### How far ahead can you forecast?

Only one month at a time, by design (per `PROJECT_VISION.md` §4's "no forecasting beyond what
the data can support"). To get a September forecast you need August's actuals in Input; to get
October's you need September's, and so on — there's no multi-month-ahead formula, because the
research backing this workbook only validated one-month-ahead accuracy (the MAPEs throughout
this manual and README are all one-month-ahead holdout errors).
