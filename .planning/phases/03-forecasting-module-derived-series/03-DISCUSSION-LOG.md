# Phase 3: Forecasting Module & Derived Series - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-21
**Phase:** 3-Forecasting Module & Derived Series
**Areas discussed:** HDAN's missing future exog values, Bull/bear spread confidence level, Refit cadence, Module boundaries & testing

---

## HDAN's missing future exog values

| Option | Description | Selected |
|--------|-------------|----------|
| Forecast each predictor with its own simple model first | Fit lightweight models for the 6 exog predictors, feed forecasted paths into HDAN's SARIMAX | ✓ |
| Hold predictors flat at last known value | Simpler, loses information | |
| Fall back to a different HDAN model without exog | Avoids the problem, reconsiders Phase 2's winner | |

**User's choice:** Forecast each predictor with its own simple model first

| Option | Description | Selected |
|--------|-------------|----------|
| Naive/last-value drift | Fast, no fitting cost | |
| Simple ARIMA(1,1,0) or similar for each | One consistent lightweight model for all 6 | ✓ |
| Use ppan's real Phase 2 forecast for ppan; naive for rest | Mixed approach | |

**User's choice:** Simple ARIMA(1,1,0) or similar for each

**Follow-up:** PPAN's VAR system also forecasts HDAN jointly — which HDAN forecast is authoritative?

| Option | Description | Selected |
|--------|-------------|----------|
| SARIMAX's HDAN forecast is authoritative everywhere | HDAN's own model is more accurate for HDAN specifically | ✓ |
| Feed SARIMAX's HDAN forecast into PPAN's VAR system as its hdan input | Chain the two models | |

**User's choice:** SARIMAX's HDAN forecast is authoritative everywhere

---

## Bull/bear spread confidence level

| Option | Description | Selected |
|--------|-------------|----------|
| ±1 standard deviation (≈68% band) | Matches Excel workbook's ±MAPE-style philosophy | ✓ |
| ±1.96 standard deviations (~95% band) | Standard statistical convention, but workbook flagged similar intervals as under-covering | |

**User's choice:** ±1 standard deviation (≈68% band)

---

## Refit cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Refit on every forecast request | Simplest, always current, fit cost is milliseconds at this scale | ✓ |
| Cache fitted models, refit only when data changes | Faster repeat requests, adds cache-invalidation complexity |  |

**User's choice:** Refit on every forecast request

---

## Module boundaries & testing

| Option | Description | Selected |
|--------|-------------|----------|
| Per-series functions behind one dispatch function | Each model's real complexity stays visible | ✓ |
| One generic function with a model-type parameter | More uniform call site, but config dict encodes very different things per series | |

**User's choice:** Per-series functions behind one dispatch function

## Claude's Discretion

None — all presented gray areas were explicitly decided by the user, several with follow-up rounds.

## Deferred Ideas

None — discussion stayed within Phase 3's boundary.
