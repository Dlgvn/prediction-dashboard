# Forecast Workbook — Design

*Built from `backend_research/REPORT.md` findings. Reference: `AN forecast.xlsx` (layout/style
only — its hardcoded-coefficient formulas are not reused).*

## 1. Goal

Replace the research phase's Python findings with a live-formula Excel workbook that forecasts
HDAN, PPAN, Diesel purchasing price (MNT), and USD/MNT FX rate one month ahead, each with a point
estimate and a 95%-nominal range. No black-box: every number a live formula, recalculating as new
months are added.

## 2. Deliverables

- A **new workbook** (`AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx`, per README.md's existing
  description) — `AN forecast.xlsx` is left untouched, used only as a layout reference.
- A standalone **`README.md`** documenting methodology, formulas, and disclosed limitations —
  not a workbook tab.
- Dashboard tab: **deferred**, designed in a later session.

## 3. Coefficient sourcing

All model coefficients are fit **live in Excel via `LINEST`** over the PctChange tab's history —
not refit in Python and pasted as static numbers. This satisfies PROJECT_VISION.md's "no
black-box, everything live" principle: adding a month to Input recalculates every coefficient
automatically.

## 4. Tab structure

| Tab | Purpose |
|---|---|
| **Input** | One row per calendar month, the only tab meant for manual editing |
| **Data / PctChange** | Raw values and month-over-month % change (the transform every model fits on) |
| **Regression** | LINEST-based coefficient fitting for each of the four models |
| **Forecast** | Next-month roll-forward for all four series + derived Diesel-MNT |
| **Dashboard** | Deferred — KPI cards, forecast ± range, backtest charts (design later) |

## 5. Input tab

Columns: `Date | HDAN | PPAN | Baltic_AN | Ammonia | Urea | Natural_Gas | Brent | Diesel_USD_ton | Urals | FX_rate | Markup_%`

- **Source data:** `AN Data.csv` is weekly — HDAN/PPAN/Baltic_AN/Ammonia/Urea/Natural_Gas/Brent
  are averaged per calendar month before entry. `Diesel Data.csv` is already monthly (Diesel_USD_ton,
  Urals, FX_rate) and used as-is.
- **Pre-populated** from both CSVs' full history at build time.
- **History window: full per-series, not trimmed to the shortest series.** AN data starts
  2022-08 (n≈44-45, matching the report's HDAN/PPAN/OLS sample sizes); Diesel/FX data starts
  2020-02 (n≈74-76, matching the report's Diesel/FX sample sizes). Rows before 2022-08 have
  blank HDAN/PPAN/Baltic_AN/Ammonia/Urea/Natural_Gas cells — same "leave it blank, don't skip
  the row" convention README.md already describes for a series that lags behind others.
- **`Markup_%`**: single editable cell (not per-row), default **2.82%** (the backtest-winning
  full-history-average markup from `markup_comparison.json`, 9.25% MAPE vs. 10.27% for the
  stated 9% business rule). Editable because the 2.82%-vs-9% discrepancy is a business-context
  question, not a modeling one — see REPORT.md's open decision on this point.

## 6. Model equations (Forecast tab)

### HDAN / PPAN — bivariate VAR(1)

```
ΔHDAN_t = c₁ + a₁₁·ΔHDAN_{t-1} + a₁₂·ΔPPAN_{t-1}
ΔPPAN_t = c₂ + a₂₁·ΔHDAN_{t-1} + a₂₂·ΔPPAN_{t-1}
```

- `ΔX_t` = X's % change from month t-1 to t. `ΔX_{t-1}` = X's prior-month % change (predictor).
- Coefficients (`a₁₁, a₁₂, c₁, a₂₁, a₂₂, c₂`) fit live via `LINEST` over the PctChange tab.
- Forecast price: `HDAN_forecast = HDAN_last_actual × (1 + ΔHDAN_t_predicted)` (same pattern for PPAN).
- **Provenance:** `var_candidates.json` → `VAR(HDAN, PPAN)`, 9.49%/10.08% MAPE — beats the
  OLS+Granger baseline (12.02%/12.07%), Lasso/Ridge/ElasticNet (~18-20%, overfit on n≈44), and
  SARIMAX (~19-20%). Adding Diesel or FX to the VAR hurts PPAN specifically (13.6-13.9%), so
  they're excluded. Justified by Granger causality: PPAN→HDAN at lag 1 (F=9.07, p=0.004),
  HDAN→PPAN at lag 2 (F=3.81, p=0.058) — the winning VAR uses lag 1 for both, per the tested combo.

### Diesel (USD/ton)

```
ΔDiesel_t = c + b·ΔBrent_{t-2}
```

- `ΔBrent_{t-2}` = Brent's % change from 2 months prior (predictor).
- `c, b` fit live via `LINEST`.
- **Provenance:** `single_series_candidates.json` OLS+Granger winner, 3.38% MAPE, n=74.
  `diesel_crude_lag.json` confirms lag 2 as the only defensible lag (F=3.34, p=0.072); lags
  0/1/3/4 all fail (p ≥ 0.22).

### USD/MNT FX rate

```
ΔFX_t = c + φ·ΔFX_{t-1}
```

- Own-momentum AR(1) only — no cross-series predictor is defensible.
- **Provenance:** `causality_matrix.json` shows every FX relationship (Brent, HDAN, PPAN, both
  directions) at p ≥ 0.22. `single_series_candidates.json` AR1-only line, 0.25% MAPE — the
  report is explicit this reflects FX's genuinely low volatility, not real predictive skill.
  `stationarity_fx.json`: FX's % change is borderline stationary (ADF p=0.037, close to
  critical; KPSS p=0.10, boundary) — closer to a random walk than the commodity series. Add a
  caution note beside this formula, not just in the README.

### Diesel purchasing price (MNT) — derived, not its own model

```
Diesel_MNT_forecast = Diesel_USD_forecast × FX_forecast × (1 + Markup_%)
```

- Uses the two model outputs above and the Input tab's `Markup_%` cell.
- **Provenance:** `markup_comparison.json` (see §5).

## 7. Interval reporting (deferred to Dashboard build, noted here for continuity)

Analytic OLS intervals, labeled with their actual historical coverage rather than a bare "95%":
none of the tested methods hit 95% actual coverage (HDAN 75%, PPAN 91.7%, Diesel 75% for
analytic OLS — the best of the two tested methods per `interval_calibration.json`), likely due
to a 2026 price spike not captured in the fitted sample. State this plainly wherever the range
is shown, per REPORT.md's explicit disclosure recommendation.

## 8. Out of scope for this build

- Dashboard tab (KPI cards, backtest charts) — separate design session.
- Any change to `AN forecast.xlsx` itself.
- A fifth product or longer forecast horizon (per PROJECT_VISION.md §4's non-goals).
