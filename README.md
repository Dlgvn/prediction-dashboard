# Price Forecasting Workbook

Live-formula Excel workbook forecasting **HDAN**, **PPAN**, **Diesel purchasing price
(MNT)**, and the **USD/MNT FX rate** — for procurement/budgeting, one month ahead.
Built for one person doing procurement or budgeting, opening this workbook once a
month, asking "what am I likely to pay next month?" See `PROJECT_VISION.md` for the
full picture of who this is for and what it deliberately doesn't do.

## Start here

Open **`AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx`** and go to the **Dashboard** tab —
that's the one view with current value, next-month forecast, an approximate range, and
backtest accuracy for all four series. Everything else in the workbook (Input,
PctChange, Regression, Forecast) supports the Dashboard's numbers and lets you trace
any of them back to source data.

## Monthly workflow

See `MANUAL.md` for a worked example (each equation with real numbers plugged in) and a
step-by-step walkthrough of doing this for a run of consecutive months. Short version:

1. Open the workbook, go to the **Input** tab.
2. Add one new row with the month's actuals: `Date, HDAN, PPAN, Baltic_AN, Ammonia,
   Urea, Natural_Gas, Brent, Diesel_USD_ton, Urals, FX_rate`.
3. That's it — PctChange, Regression, and Forecast all recalculate automatically from
   live formulas. No other tab needs editing.

If a series isn't known yet for the current month (Diesel/FX data currently lags
HDAN/PPAN by about a month in the source data), leave those cells blank on the same
row rather than adding a separate row — each row is one calendar month shared by every
series.

**Before editing the file with any tool other than Excel itself: close it in Excel
first.** An open Excel session can silently overwrite script-based changes on save —
this has happened once already in this project's history.

## What's in this folder

| File | What it is |
|---|---|
| `AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx` | **The live workbook.** 5 tabs: Input, PctChange, Regression, Forecast, Dashboard. |
| `AN Data.csv`, `Diesel Data.csv` | Raw source data the workbook was built from |
| `AN price weekly.csv` | Weekly-cadence driver data (JKM/Henry Hub/UK/Netherlands gas, US/China corn, Middle East Ammonia, Black Sea/China Urea), used only in `backend_research/`'s weekly-cadence backtest — not part of the monthly workbook build |
| `AN forecast.xlsx` | A colleague's earlier, separate forecasting attempt — reference only (layout/style reference during design), untouched by any build script |
| `PROJECT_VISION.md` | Who this is for, what it delivers, what it deliberately doesn't do, and the roadmap |
| `docs/plans/2026-08-20-forecast-workbook-design.md` | Design intent: tab structure, model equations, coefficient provenance, what was deferred and why |
| `docs/plans/2026-08-20-forecast-workbook-implementation.md` | Build plan: how `build_workbook.py` constructs each tab, task-by-task |
| `MANUAL.md` | Each model's equation with today's actual coefficients plugged in and worked by hand, plus a step-by-step monthly roll-forward walkthrough (add a month, read next month's forecast, repeat) |
| `backend_research/` | The Python research behind the model choices (data, causality tests, model comparisons, full report) |
| `scripts/build_workbook.py` | The script that builds the workbook from the two source CSVs. Re-run this (don't hand-edit in Excel) whenever the design changes. |

## Workbook structure

- **Input** — one row per calendar month (rows 2–79, columns A–K), plus a single
  editable **`Markup_%`** cell at `M2` (currently 0.0282, i.e. 2.82%). AN-sourced
  columns (HDAN, PPAN, Baltic_AN, Ammonia, Urea, Natural_Gas, Brent) run from 2022-08
  onward; Diesel/FX-sourced columns (Diesel_USD_ton, Urals, FX_rate) run from 2020-02
  onward. Each series keeps its full available history rather than being trimmed to
  the shortest one — months before a series' start, or not yet reported, are left
  blank on that row.
- **PctChange** — live month-over-month `% change` formulas for every Input column,
  recalculating as Input grows.
- **Regression** — live `LINEST` formulas fitting the three underlying models over
  PctChange history. Coefficients aren't pasted numbers; they refit automatically
  every time Input gets a new row.
- **Forecast** — one row per series with the next month's roll-forward: last actual →
  predicted % change → forecast value, plus the derived Diesel-MNT purchasing price.
- **Dashboard** — one KPI row per product (HDAN, PPAN, Diesel-USD, FX rate, Diesel-MNT):
  current value, next-month forecast (pulled live from Forecast), an **approximate**
  ±MAPE range, and the backtest MAPE. The MAPE values are **static**, taken from
  `backend_research/REPORT.md`'s 12-month holdout backtest — they don't recalculate as
  Input grows. The range is a simple ±MAPE band, not a calibrated statistical interval;
  a proper analytic interval was tested in the research phase and still under-covers
  its stated 95% target (see REPORT.md's interval-calibration section), so this
  simpler band doesn't claim more precision than the research actually supports.

## The four models, briefly

Every coefficient below is a live formula, not a fixed number — re-check it in the
workbook itself; the values shown are what the current fit computes as of this
history.

- **HDAN / PPAN — bivariate VAR(1).** Each product's forecast uses both its own and
  the other's prior-month % change. Coefficients live in `Regression!D5:F5` (HDAN
  equation: a₁₁, a₁₂, c₁ = 0.548, −0.229, 0.00203) and `Regression!D6:F6` (PPAN
  equation: a₂₁, a₂₂, c₂ = 0.128, 0.225, 0.00210). Forecast values are computed on the
  **Forecast** tab (`C2:D2` for HDAN, `C3:D3` for PPAN) from the last actual (`Input`
  column B/C, row 79) and these coefficients.
- **Diesel (USD/ton)** — its own momentum plus Brent crude two months earlier.
  Coefficients live in `Regression!D3:E3` (slope, intercept = 0.170, −0.00053).
  Forecast on `Forecast!C4:D4`.
- **FX rate (USD/MNT)** — own-momentum AR(1) only; no other series tested was a
  defensible predictor. Coefficients live in `Regression!D2:E2` (slope, intercept =
  0.634, 0.00123). Forecast on `Forecast!C5:D5`.
- **Diesel purchasing price (MNT)** — not its own model, just arithmetic:
  `Diesel_MNT = Diesel_USD_forecast × FX_forecast × (1 + Markup_%)`, computed on
  `Forecast!D6` from `Forecast!D4`, `Forecast!D5`, and `Input!M2`.

Full derivation, backtest MAPEs, and Granger-causality justification for each model
are in `docs/plans/2026-08-20-forecast-workbook-design.md` §6 and in
`backend_research/`.

## Open flag: the markup rate

`Input!M2` (`Markup_%`, default 2.82%) is **user-editable on purpose**. Backtesting
found 2.82% — the historical average gap between import price and actual paid price —
beats the business's stated 9% markup rule on holdout accuracy (per
`backend_research`'s markup comparison). That's a real discrepancy between what the
data says and what the business rule says, and it isn't resolved here: whoever owns
the contract terms should confirm which number is currently correct, then edit the
cell if it needs to change. See `PROJECT_VISION.md` §6 for this as an open roadmap
item.

## Weekly cadence: tested, not adopted

`AN Data.csv` is actually native weekly for HDAN/PPAN (the workbook resamples it to monthly), and
`AN price weekly.csv` adds real weekly drivers not otherwise available. Both were backtested as a
possible weekly forecast mode — see `backend_research/REPORT.md`'s "Weekly cadence (Phase 1
follow-up)" section. Result: no-go. A weekly VAR(HDAN,PPAN) rolled forward 4 weeks underperforms
the monthly VAR this workbook uses (10.35%/16.01% vs. 9.49%/10.08% MAPE), so the workbook's
monthly cadence and models are unchanged. See `.planning/STATE.md` for the current status of this
as an open item.

## What this deliberately doesn't do

See `PROJECT_VISION.md` §4 for the full non-goals list — short version: no
behind-the-scenes model at report time (everything above is a live Excel formula, no
Python re-run needed to read the workbook), no forecasting further out than the data
can honestly support, and no fifth product added without a deliberate scope decision
first. Backtest charts (actual vs. predicted, historical) were considered for the
Dashboard and deliberately left out — the KPI cards above are the whole Dashboard for
now; charts remain a possible future addition, not a gap in the current build.
