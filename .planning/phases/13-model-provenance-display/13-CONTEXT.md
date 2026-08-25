# Phase 13: Model Provenance Display — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Show which model produced each series' forecast, plus its backtested accuracy (MAPE), on the existing forecast summary cards. Root cause confirmed: `forecasting.py` currently only has this information as docstring prose (e.g. `"Model: SARIMAX(0,1,0)+exog, backtested mean 1-12 MAPE of 13.33%"`), never a real, importable constant — it must be extracted into an actual data structure before the UI can read it.

In scope: a new `MODEL_INFO`-style constant in `forecasting.py`, a thin computed var on `DashboardState`, and one new line on each of the 4 existing summary cards (`SUMMARY_CARD_SERIES`).
Out of scope: any change to the forecasting models/logic themselves (frozen per Phase 2/3 decisions — no re-fitting, no re-selection), any AI-generated/dynamic "drivers" explanation (explicitly out of scope per v1.2 REQUIREMENTS.md), full model diagnostics (AIC/BIC/residuals).
</domain>

<decisions>
## Implementation Decisions

### Diesel MNT label
- **D-01:** Diesel MNT (a derived series, not its own fitted model) shows `"Derived (Diesel USD × FX)"` as its model label, not a combined "Naive + Naive" or any implication of a fifth independently-fitted model. No accuracy percentage for this card's model line, since it has no independent backtest of its own — its accuracy is inherited from the two component forecasts.

### Placement
- **D-02:** Model info is a new line on the existing forecast summary cards (Phase 6/8 pattern), not a caption near the fan chart. Consistent with how All-time high/low and YoY were added in Phase 8 — one more compact line per card.

### Wording
- **D-03:** Accuracy is shown as a plain MAPE percentage (e.g. "13.3% typical error"), not a qualitative tier like "High confidence" — matches the app's existing numeric-first style (YoY %, direction %) and avoids inventing new accuracy-tier definitions.

### Claude's Discretion
- Exact copy wording and line ordering on the card (e.g. "Model: SARIMAX · 13.3% typical error" vs. two separate sub-lines) — follow the existing card-line visual pattern (muted label + value) established by "All-time high/low" and "YoY".
- Where exactly in the card stack the new line sits relative to existing lines (base value → expected range → direction → high/low → YoY → **model** is the natural append-at-end position, matching how Phase 8 appended after Phase 6's lines).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/forecasting.py` — `forecast_hdan` (docstring: "SARIMAX(0,1,0)+exog... MAPE of 13.33%"), `forecast_ppan_var_system` (docstring: "Direct-OLS VAR-system(h=1..12)... MAPE of 23.80%"), `forecast_diesel_usd` (docstring: "Naive... MAPE of 7.04%"), `forecast_fx` (docstring: "Naive... MAPE of 1.72%"), `forecast_all` (the single dispatcher, returns exactly 5 keys: `hdan`, `ppan`, `diesel_usd_ton`, `fx_rate`, `diesel_mnt`) — these MAPE/model-name values currently exist ONLY as prose; must become real constants
- `app/app/state.py` — `SUMMARY_CARD_SERIES` (line ~116, the 4-key tuple: `hdan`, `ppan`, `diesel_mnt`, `fx_rate`), `summary_cards` computed var (line ~488, the established flat-string-dict-per-card pattern with `hilo_label`/`hilo_text`, `yoy_label`/`yoy_text` as the precedent to extend), `_latest_actual_for` (the per-series helper pattern)
- `app/app/app.py` — `_summary_card()` render function — where the new line is appended, following the exact same `rx.hstack` muted-label + value pattern already used for the high/low and YoY lines

### v1.3 milestone research (MANDATORY)
- `.planning/research/SUMMARY.md` — Phase 3 (this phase): "codebase already has an established idiom (`summary_cards`/`freshness_chips` 'list of flat string dicts') to copy directly" — standard pattern, no deep research needed
- `.planning/research/PITFALLS.md` — Pitfall 4: model metadata must not become a second, driftable source of truth — add name/MAPE as real constants in `forecasting.py`, consumed via the existing single `forecast_all()` call site; never hand-type MAPE literals directly into `state.py`/`app.py`
- `.planning/research/ARCHITECTURE.md` — recommends: new frozen `MODEL_INFO` dict in `forecasting.py` → new thin `@rx.var` in `state.py` → new small badge/line component in `app.py`, reusing the existing flat-dict idiom; "Model-metadata phase's first task should be adding constants to `forecasting.py`, not `state.py`"

### Prior phase precedent
- `.planning/phases/08-forecast-context-enrichment/` — established the exact card-line pattern (muted label + value line, appended after existing content) this phase directly extends
- `.planning/phases/02-model-research-backtesting/02-MODEL-DECISIONS.md` (if present) — the original source of the winning model names/MAPEs cited in `forecasting.py`'s docstrings; cross-check the extracted constants against it for accuracy

### Project-level
- `.planning/REQUIREMENTS.md` — VIS-05
- `.planning/ROADMAP.md` — Phase 13 entry

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `summary_cards`'s flat-string-dict-per-card shape — the new model fields should be added as new keys on the same dict (e.g. `model_label`, `model_text`), not a separate computed var, matching how `hilo_label`/`hilo_text` and `yoy_label`/`yoy_text` were added in Phase 8.

### Established Patterns
- Model selection is frozen and hard-coded per series (Phase 2/3 decisions) — this phase reads that existing frozen knowledge, it does not re-derive or re-validate it.
- `forecast_all()` remains the single dispatcher/call site — the new `MODEL_INFO` constant must not require calling `forecast_all` again or introduce a second entry point into the forecasting module.

### Integration Points
- `forecasting.py` needs a new exported constant (e.g. `MODEL_INFO: dict[str, tuple[str, float | None]]` keyed by the same series keys `forecast_all` uses: `hdan`, `ppan`, `diesel_usd_ton`, `fx_rate`, plus a `diesel_mnt` entry per D-01 with `None` accuracy).
- `state.py`'s `summary_cards` loop already iterates `SUMMARY_CARD_SERIES` — the model info lookup slots directly into that existing loop.
- `app.py`'s `_summary_card()` gets one new `rx.hstack` line, styled identically to the existing high/low and YoY lines (muted label + `RADIX_SIZE_BODY` value, no new theme tokens).

</code_context>

<specifics>
## Specific Ideas

No new visual references — this phase extends the existing Phase 6/8 card design exactly, adding one more line in the same visual language.

</specifics>

<deferred>
## Deferred Ideas

- AI-generated or dynamic "drivers" explanation text — already explicitly out of scope per v1.2 REQUIREMENTS.md Out of Scope section (would require either a low-value static caption or real model-coefficient attribution, a forecasting research question).
- Full model diagnostics (AIC/BIC, residual plots, all-candidate comparison table) — explicitly flagged as an anti-feature for this non-technical audience per v1.3 research (FEATURES.md).

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-model-provenance-display*
*Context gathered: 2026-08-24*
