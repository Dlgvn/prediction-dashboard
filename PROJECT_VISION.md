# Price Forecasting Workbook — Project Vision

*Rewritten 2026-08-20 to replace a stale, chronological version that no longer matched
what's actually built. This version is product-first: who it's for, what it delivers,
what it deliberately doesn't do — not a log of decisions in the order they happened.*

## 1. Who this is for, and what it answers

One person doing procurement or budgeting, opening this workbook once a month, asking:
**"What am I likely to pay next month, and how sure can I be?"** — not a data scientist,
not a spreadsheet auditor. Every number that matters for that question surfaces on the
**Dashboard** tab; everything else (raw data, regression internals) exists to support that
number, not to be read directly.

## 2. The four deliverables

Four things get forecasted, each with a point estimate *and* a 95% range — never a bare
number without its uncertainty:

| Product | What it is | Why it matters |
|---|---|---|
| **HDAN** | Ammonium nitrate price, grade 1 | Direct procurement cost |
| **PPAN** | Ammonium nitrate price, grade 2 | Direct procurement cost |
| **Diesel purchasing price (MNT)** | What actually gets paid, in local currency — not the USD import price | The real budgeting number; import price alone isn't what anyone pays |
| **USD/MNT FX rate** | The exchange rate itself | Its own product, tracked and reported independently — and the piece that turns Diesel's import price into a real purchasing price |

Diesel's headline number is deliberately the **purchasing price**, not the import
price — import price in USD isn't something anyone budgets against; the MNT number
actually paid is. FX rate is reported as its own deliverable in its own right, not
demoted to a hidden input.

## 3. How it works (brief — full detail lives in `README.md`, `MANUAL.md`, and the Regression tab)

- **HDAN and PPAN** are modeled together (VAR): each product's forecast uses both its own
  and the other's prior month's move, because the two are strongly correlated and each
  helps predict the other. This measurably beats forecasting either one alone (~9-10%
  holdout error vs. ~12-15% for a single-product model).
- **Diesel (USD)** is modeled on its own momentum plus crude oil two months earlier.
- **FX rate** is modeled on its own momentum only — no other series tested actually
  helped predict it, so the model doesn't pretend otherwise.
- **Diesel purchasing price (MNT)** is arithmetic, not its own model: Diesel-USD forecast
  × FX-rate forecast × a measured markup (the historical gap between import price and
  what's actually paid).
- Every model is fit on month-over-month % change and was backtested (in the research phase,
  `backend_research/`) on months it never saw during fitting. **The Dashboard's range is a
  simple ±MAPE band, not a calibrated statistical interval** — a proper analytic interval was
  tested in research and still under-covers its stated 95% target on this data, so the built
  workbook doesn't claim more precision than that; see §5 for the actual implementation and
  REPORT.md's interval-calibration section for the underlying finding.

## 4. What this deliberately doesn't do

- **No black-box models.** Every forecast is a live, readable Excel formula — no Python
  model running behind the scenes at report time. (Python was used to *research* which
  model to use; the workbook itself computes everything live.)
- **No forecasting beyond what the data can support.** The horizon is bounded, and the
  workbook says plainly when a range is less trustworthy further out, rather than
  implying month 6 is as reliable as month 1.
- **No adding a fifth product without a deliberate decision.** Diesel and FX were added
  to the original HDAN/PPAN scope because they're genuinely part of the same budgeting
  picture (Diesel prices alongside AN products; FX converts Diesel to what's actually
  paid). The next candidate predictor or product should clear the same bar — a real,
  named reason it belongs, not "we have the data so why not."
- **No silent complexity.** If a trade-off exists (a predictor that helps but isn't
  individually significant, a markup that beats an assumed business rule but contradicts
  it), it's written down where the model lives, not smoothed over.

## 5. Current state (as built)

*Rewritten 2026-08-20, same day as the build, to replace an earlier version of this section
that described the planned 7-tab design rather than what was actually built. The plan changed
during design review — see `docs/plans/2026-08-20-forecast-workbook-design.md` for why.*

`AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx` — **5 tabs**, all live formulas:

- **Input** — the only tab meant for monthly editing: one row per month
  (`Date, HDAN, PPAN, Baltic_AN, Ammonia, Urea, Natural_Gas, Brent, Diesel_USD_ton, Urals,
  FX_rate`), plus a single editable `Markup_%` cell. Pre-populated from `AN Data.csv` and
  `Diesel Data.csv`, each series keeping its own full available history (AN-sourced columns
  from 2022-08, Diesel/FX-sourced columns from 2020-02) rather than trimmed to the shortest
  series.
- **PctChange** — live month-over-month `% change` formulas for every Input column.
- **Regression** — live `LINEST` formulas fitting the three underlying models (FX AR(1),
  Diesel-USD on Brent lag-2, bivariate VAR(HDAN, PPAN)) over PctChange history. Coefficients
  refit automatically as Input grows — no pasted numbers.
- **Forecast** — one row per series: last actual → predicted % change → forecast, plus the
  derived Diesel-MNT purchasing price. Point estimates only.
- **Dashboard** — one KPI row per product (HDAN, PPAN, Diesel-USD, FX rate, Diesel-MNT):
  current value, next-month forecast (live, pulled from Forecast), an approximate ±MAPE range,
  and the backtest MAPE. The MAPE values are **static**, taken from `backend_research/REPORT.md`
  — they don't recalculate as Input grows, and the range is a simple band, not a calibrated
  statistical interval (see §3's disclosure of why a proper interval isn't used). No backtest
  charts — considered and deliberately left out, the KPI rows are the whole Dashboard for now.

**No README tab.** Methodology lives in the standalone `README.md` and `MANUAL.md` files
instead of a workbook tab (a deliberate change from the original plan — kept the workbook
itself leaner).

**Accuracy (12-month holdout, from the research phase in `backend_research/`):** HDAN 9.4% MAPE
· PPAN 10.0% MAPE · Diesel-USD 3.4% MAPE · FX 0.25% MAPE. These are the research report's
numbers, not something the built workbook currently recomputes on its own — the workbook fits
live coefficients but doesn't yet have its own live backtest/MAPE display (that's Dashboard work).

**Live workflow:** adding a month's actuals to Input grows every model's training window and
its coefficients refit automatically. See `MANUAL.md` for the exact monthly walkthrough,
including the caveat that the Forecast tab's row references are set at build time — re-running
`scripts/build_workbook.py` after updating the source CSVs is the safest way to add a month,
safer than hand-editing Input directly in Excel.

## 6. Forward roadmap (bounded — not an open list)

Three concrete next steps, each with a real reason to exist, evaluated one at a time
rather than batched into another open-ended expansion:

1. **Revisit the range calculation if more precision is wanted.** The Dashboard currently
   ships a simple ±MAPE band rather than a calibrated statistical interval, because a proper
   analytic interval requires leverage-adjusted matrix algebra that `LINEST` alone doesn't
   expose, and because the research phase already found even that proper interval under-covers
   its stated 95% target. Worth a deliberate look only if the ±MAPE approximation proves too
   loose in practice — not a known problem yet, just a disclosed simplification.
2. **Confirm the Diesel-MNT markup with whoever owns the contract terms.** Already partly
   resolved: `Markup_%` is an editable Input cell (currently 2.82%, the backtest-winning
   value) rather than a hardcoded choice between it and the business's stated 9% rule — so the
   workbook no longer forces a silent pick. What's still open is the actual business
   confirmation: which number reflects current contract terms, and should the cell be changed.
3. **Decide, don't drift, on anything beyond these four products.** Any future addition
   (a fifth series, a longer horizon, a different model class) gets the same treatment
   this document just went through: a clear reason it belongs, a defined scope, before
   any building starts — not organic growth mid-conversation.
