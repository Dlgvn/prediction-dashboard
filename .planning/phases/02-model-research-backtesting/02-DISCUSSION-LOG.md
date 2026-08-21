# Phase 2: Model Research & Backtesting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-21
**Phase:** 2-Model Research & Backtesting
**Areas discussed:** Method scope, Predictor candidates, Multi-step horizon approach, Backtest split strategy, Weekly-mode proxy research

---

## Method scope

User opened this area with a detailed freeform taxonomy of forecasting method families
(time-series, causal/econometric, machine learning, technical/market-based, qualitative/
judgment-based), each with the underlying assumption it bets on, and requested a fresh
model-research start using AN price weekly.csv, AN Data.csv, and Diesel Data.csv.

| Option | Description | Selected |
|--------|-------------|----------|
| Time-series: Naive/MA, Exp. Smoothing, ARIMA, GARCH | Baseline + core statistical candidates + volatility modeling | ✓ |
| Causal/econometric: Regression, VAR, cointegration/Granger | Predictor-driven models with rigor on which predictors earn inclusion | ✓ |
| Machine learning: Random forest, gradient boosting | Nonlinear relationships, real overfitting risk on small samples | ✓ |
| Technical/market-based (momentum, support/resistance) | Trading-pattern methods | |
| Qualitative/judgment (scenario planning, Delphi) | Human-panel methods for sparse/structurally-different futures | (selected, then re-scoped below) |

**User's choice:** Time-series + causal/econometric + ML + qualitative/Delphi (technical/market-based not selected)

**Follow-up:** Qualitative/Delphi isn't backtestable. Clarified how it fits Phase 2.

| Option | Description | Selected |
|--------|-------------|----------|
| Document it as the v2 mechanism, not Phase 2 work | Formalize the connection to v2's news/sentiment scenarios; don't build now | ✓ |
| Build a manual scenario-override field now | Expand Phase 2/3 scope beyond current REQUIREMENTS.md v1 list | |

**User's choice:** Document it as the v2 mechanism, not Phase 2 work

---

## Predictor candidates

| Option | Description | Selected |
|--------|-------------|----------|
| Test all predictors for HDAN/PPAN, let Granger causality/VAR decide | No pre-filtering by intuition | ✓ |
| Limit HDAN/PPAN predictors to obviously relevant ones | Natural gas + Baltic AN/Ammonia only | |

**User's choice:** Test all predictors for HDAN/PPAN

| Option | Description | Selected |
|--------|-------------|----------|
| Brent, Urals, lagged own-history for Diesel/FX | Matches existing workbook approach plus Urals | |
| Also test natural gas and AN-family series as Diesel/FX predictors | Broader search despite no obvious mechanism | ✓ |

**User's choice:** Also test natural gas and AN-family series as Diesel/FX predictors

---

## Multi-step horizon approach

| Option | Description | Selected |
|--------|-------------|----------|
| Iterative/recursive forecasting | Feed 1-step forecasts back in for steps 2-12 | |
| Direct multi-step models | Separate model per horizon | |
| Test both, compare backtest accuracy per horizon | Let results decide per series | ✓ |

**User's choice:** Test both, compare backtest accuracy per horizon

---

## Backtest split strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Walk-forward / rolling-origin | Repeatedly train up to month N, forecast N+1..N+12, roll forward | ✓ |
| Single fixed holdout | Matches original backend_research's 12-month-holdout approach | |

**User's choice:** Walk-forward / rolling-origin

---

## Weekly-mode proxy research

| Option | Description | Selected |
|--------|-------------|----------|
| Skip it — stay focused on monthly models | Weekly mode is v2 scope, no v1 consumer for this research | ✓ |
| Test it now while the data's already loaded | Low marginal cost, answer ready for future milestone | |

**User's choice:** Skip it — stay focused on monthly models

## Claude's Discretion

None — all presented gray areas were explicitly decided by the user.

## Deferred Ideas

- Weekly-mode Baltic AN → HDAN/PPAN proxy research — future weekly-mode milestone
- Scenario planning / Delphi qualitative override — v2 news/sentiment mechanism, not Phase 2/3
- Technical/market-based methods — not selected, no current driver to revisit
