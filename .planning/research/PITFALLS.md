# Pitfalls Research

**Domain:** Small-scale statsmodels time-series forecasting + Reflex (Python full-stack) dashboard, single user
**Researched:** 2026-08-21
**Confidence:** MEDIUM (Reflex-specific findings are officially documented but sparsely covered for gotchas; statsmodels sample-size findings are corroborated across multiple sources; scenario-band honesty findings are domain reasoning informed by the existing Excel workbook's own MAPE backtest approach)

## Critical Pitfalls

### Pitfall 1: Fitting VAR/ARIMA/SARIMAX on too little history and getting confident-looking garbage

**What goes wrong:**
HDAN/PPAN monthly history starts 2022-08 (~48 monthly points by now), Diesel/FX monthly history starts 2020-02 (~78 points). VAR with even 2-3 endogenous variables and a couple of lags burns degrees of freedom fast — a VAR(2) on 3 series already estimates a lot of parameters. With <50 observations, coefficient estimates become unstable and confidence intervals become artificially narrow (the model looks precise because it's overfit, not because it's accurate). This is worse for HDAN/PPAN's shorter history than for Diesel/FX.

**Why it happens:**
statsmodels will happily fit and produce point forecasts + confidence intervals with almost any N — it doesn't warn you when N is too small relative to parameter count. Developers see "the model ran and gave numbers" and treat that as validation.

**How to avoid:**
- Explicitly cap model complexity to what the sample size supports (e.g., prefer low-order AR/VAR, avoid seasonal terms with <2 full seasonal cycles of data).
- Use the existing `backend_research/REPORT.md` backtest MAPE numbers as the sanity baseline — if a new model's holdout error is much better than those, be suspicious of overfitting rather than celebrating.
- Always backtest on a genuine holdout (last N months held out, not in-sample fit statistics) before shipping a model — this project's stated constraint ("no un-backtested model ships") already enforces this; just make sure the holdout is long enough (project used 12-month holdout for the Excel workbook) to be meaningful, not 2-3 points.
- For HDAN/PPAN specifically, given the shortest history, prefer simpler models (AR, single-predictor regression) over VAR unless backtesting clearly shows VAR wins.

**Warning signs:**
- Forecast confidence intervals that look implausibly tight given how volatile the historical series actually is.
- A model's in-sample fit is excellent but holdout backtest error is much worse (classic overfit signature).
- Adding more lags/variables to VAR keeps "improving" in-sample AIC but holdout MAPE gets worse.

**Phase to address:**
Model research/backtest phase (mirrors `backend_research/`) — before any model is wired into the dashboard.

---

### Pitfall 2: Weekly-mode data gap silently produces a broken or misleading forecast

**What goes wrong:**
No weekly HDAN, PPAN, Diesel, or FX data exists — only Baltic AN/Ammonia/Urea/Natural Gas at weekly cadence, and even that's a different commodity family than HDAN/PPAN. If weekly mode is implemented naively (e.g., interpolating monthly data down to "fake weekly" points, or silently using Baltic AN as a stand-in without validating the proxy relationship), the dashboard will render a chart that looks like real weekly forecasting but is actually noise or a poorly-validated proxy — indistinguishable from real forecasting in the UI.

**Why it happens:**
Once the UI supports picking a horizon in weeks, it's tempting to make it "just work" by resampling/interpolating monthly data rather than blocking the feature until the underlying data problem is actually solved. Interpolated data looks like real data in a chart.

**How to avoid:**
- Do not ship weekly mode until the proxy relationship (Baltic AN → HDAN/PPAN) is backtested and shown to hold, per design doc §6 option (a); or scope weekly mode to only products with genuine weekly data per option (b), with Diesel/FX visibly staying monthly-only even in "weekly mode."
- If a proxy is used, label it as a proxy/estimate in the UI, not present it identically to the directly-modeled series.
- Never present linearly-interpolated monthly data as if it were empirically observed weekly data.

**Warning signs:**
- Weekly forecast chart exists but there's no documented validation of the Baltic AN → HDAN/PPAN relationship.
- Weekly mode "just works" for Diesel/FX despite no weekly Diesel/FX data existing anywhere.

**Phase to address:**
Explicitly gate weekly mode behind its own research/backtest phase, separate from and after the monthly model research phase. Should not be bundled into v1 forecast engine phase.

---

### Pitfall 3: Bull/bear bands presented as if they were precise probability intervals

**What goes wrong:**
v1 defines bull/bear as base ± a statistical spread (backtest error or historical volatility). If this is computed once (e.g., ± MAPE at the model's average horizon) and then applied uniformly across all horizons (1 month out and 12 months out get the same ± band), the dashboard silently understates uncertainty at longer horizons and overstates it at short ones — the exact "misleadingly precise" failure mode the question flags. A single global MAPE-derived band also doesn't distinguish between the different series' actual backtested accuracy (HDAN 9.4% MAPE vs. FX 0.25% MAPE per PROJECT.md) if implemented sloppily with one shared spread constant.

**Why it happens:**
It's simpler to code "base * (1 ± X%)" once than to compute horizon-dependent and series-dependent error bands. The existing Excel workbook uses a static ±MAPE band from a report, which is exactly the kind of shortcut the design doc explicitly wants to avoid repeating ("computed dynamically instead of pasted from a static report") — but "dynamic" still needs to vary correctly by horizon and by series, or it just recreates the same problem in code.

**How to avoid:**
- Compute the spread per-series (each of HDAN/PPAN/Diesel/FX has its own backtested error), not a single shared percentage.
- Widen the band as horizon increases (forecast uncertainty compounds over time) — at minimum, use the model's own multi-step forecast error growth (statsmodels ARIMA/VAR expose forecast standard errors that grow with horizon; use those rather than a flat single-period MAPE repeated across all months).
- Never label the bull/bear band as a formal confidence interval (e.g., "95% CI") unless it was actually derived as one from the model's forecast variance — if it's a heuristic (e.g., ±1 backtested MAPE), label it as a heuristic scenario range, not a statistical guarantee.
- Add a visible disclaimer/tooltip that bull/bear reflects historical model error, not a probabilistic guarantee, especially since the derived Diesel-MNT figure compounds two independent forecast errors (Diesel-USD × FX) — its band should not simply be the narrower of the two component bands.

**Warning signs:**
- The bull/bear band width doesn't change between a 1-month and 12-month forecast.
- All four series show visually similar band widths despite very different backtested MAPEs (0.25% for FX vs 10% for PPAN).
- Diesel-MNT (derived) shows a tighter band than either of its two input forecasts.

**Phase to address:**
Scenario/band computation phase, after the base forecast models are chosen and backtested — needs the per-series backtest error numbers as an input, so must come after model research, not before.

---

### Pitfall 4: Reflex state leaking or resetting unexpectedly across the single user's sessions

**What goes wrong:**
Reflex instantiates a session-specific State instance per WebSocket connection. For a genuinely single-user app this is usually low-risk, but common mistakes are: storing forecast results or the editable data table only in ephemeral `rx.State` (in-memory, per-session) instead of persisting to the SQLite `rx.Model`, so a page refresh or reconnect loses in-progress edits; or conversely, doing expensive forecast recomputation in `State.__init__`/on every page load instead of caching, causing noticeable lag each time the single user opens the dashboard.

**Why it happens:**
Reflex's docs emphasize that State is the reactive source of truth for the UI, which nudges developers toward putting everything in State vars, including things that should be durably persisted (actuals table edits) or expensively cached (forecast runs).

**How to avoid:**
- Data the user enters (actuals rows) must be written through to SQLite (`rx.Model`) immediately on submit, not held only in State — State should be a thin reflection of DB contents, reloaded on connect, not the source of truth for durable data.
- Forecast results should be computed on-demand (button click / horizon change), not on every state re-render, and can be cached in State for the current session without needing to be persisted (they're cheap to recompute from stored actuals).
- Use `reflex db init` / `reflex db makemigrations` from the start once the schema is defined, so schema changes during development don't require hand-editing the SQLite file.

**Warning signs:**
- Refreshing the browser tab loses table edits the user just made.
- Opening the dashboard is slow because forecasts recompute unconditionally on load rather than on demand.
- Schema changes require manually deleting the `.db` file during development (a sign migrations aren't being used).

**Phase to address:**
Data persistence / SQLite integration phase — establish the "State reflects DB, DB is source of truth" pattern early, before the forecast-display and data-entry UI phases build on top of it.

---

### Pitfall 5: Single-process Reflex deployment surprises when the "occasional single user" assumption is stress-tested even lightly

**What goes wrong:**
The design explicitly chose one Reflex process (no split frontend/backend) for single-user, occasional-use scale — reasonable, but a common oversight is running compute-heavy statsmodels fits (VAR/ARIMA) synchronously inside a Reflex event handler on the same process serving the UI, which blocks the WebSocket/UI thread and makes the app feel frozen during a forecast run, especially if backtesting or refitting happens on every horizon change rather than being precomputed/cached.

**Why it happens:**
It's the simplest code to write: horizon dropdown changes → event handler calls the forecasting function directly → returns results to State. Works fine in local dev with fast toy fits; only becomes noticeable once real VAR fits with proper diagnostics run inline.

**How to avoid:**
- Fit models once when the underlying actuals table changes (new row added), not on every horizon-change click; horizon changes should just re-slice/re-project an already-fit model's forecast, which is cheap.
- If model fitting is genuinely slow, use Reflex's background task support (`rx.background`) rather than blocking the main event handler.

**Warning signs:**
- The UI visibly freezes or shows no feedback for multiple seconds when the user changes the forecast horizon.
- Every horizon change re-runs the full VAR/ARIMA fit from scratch instead of reusing a cached fitted model.

**Phase to address:**
Forecast-engine integration phase (wiring the researched/backtested models into the Reflex UI) — should be designed with fit-once/reuse from the start, not retrofitted after the UI feels slow.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Global flat ± percentage for bull/bear instead of per-series, per-horizon spread | Ships v1 scenario chart fast | Misleadingly precise/imprecise bands, erodes user trust once they notice all series look equally uncertain | Never past v1 — must be replaced before scenario feature is considered "done", not just before v2 |
| Refitting VAR/ARIMA on every horizon-change click | Simple event handler code | UI feels sluggish, wastes compute on a single-user occasional-use app where it matters for perceived quality | Only acceptable in early prototyping, not in shipped v1 |
| Treating "the model ran without error" as validation | Faster to move on to next series | Ships an overfit/unstable model with confidence intervals that look precise but aren't | Never |
| Interpolating monthly data to fake weekly cadence to unblock the UI | Weekly mode "works" visually | Actively misleading forecast that looks like real data | Never — block the feature instead |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-------------------|
| Reflex + SQLite (`rx.Model`) | Treating in-memory State as durable storage for user-entered actuals | Write-through to `rx.Model`/SQLite on every edit; State reloads from DB on session start |
| Reflex schema changes during dev | Hand-editing or deleting the `.db` file when the model schema changes | Use `reflex db init` then `reflex db makemigrations` / `reflex db migrate` from the start |
| statsmodels VAR/ARIMA + Excel export (openpyxl) | Exporting only point forecasts, dropping the bull/bear spread that gives the export the same information richness as the in-app chart | Export base/bull/bear columns together, matching what's shown in the dashboard, so the .xlsx isn't a downgrade from the UI |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Refitting VAR/ARIMA synchronously on every UI interaction | Horizon dropdown feels laggy | Fit once per actuals-table change, cache fitted model, re-project cheaply per horizon | Noticeable even at single-user scale once real (non-toy) model fits are used |
| Recomputing Excel export by re-running forecasts instead of exporting already-computed/cached results | Export button slow, or exports data inconsistent with what's on screen | Export exactly what's currently displayed/cached, not a fresh recompute | Minor at this scale, but causes UI/export mismatch bugs regardless of scale |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Assuming "single local user" means no input validation needed on the in-app data entry table | Malformed/garbage rows (non-numeric prices, wrong date format) silently corrupt the SQLite table and poison future model fits | Validate row inputs (numeric ranges, date format) before writing to SQLite, even for a trusted single user — protects data integrity, not just security |
| Storing the SQLite `.db` file in a location that gets swept into version control or shared/synced folders unintentionally | Price data (potentially business-sensitive procurement figures) leaks into git history or cloud sync | Ensure `.db` file is gitignored and stored in a location the user controls; document this explicitly since the project already deals with a real Excel workbook containing business data |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|------------------|
| Bull/bear band shown without any explanation of what it means | User can't tell if "bear" means "worst realistic case" or "worst-ever-seen case" and may over/under-trust it | Add a short inline explanation/tooltip: band = historical model error, not a guarantee |
| Weekly mode toggle available in the UI before the underlying data gap is resolved | User picks weekly mode and gets a broken or silently-proxied forecast with no indication anything is different | Don't expose the weekly toggle in the UI until weekly mode is validated and scoped (per design doc §6); or clearly gray out/label unsupported series |
| Forecast chart with no indication of how much history backs each series | User can't tell that HDAN/PPAN forecasts rest on much less history (~48 months) than Diesel/FX (~78 months), so trusts them equally | Surface data recency/length (e.g., "based on 48 months of history") somewhere near each forecast |

## "Looks Done But Isn't" Checklist

- [ ] **Forecast models:** Often missing genuine out-of-sample backtest — verify holdout MAPE was computed on data not used for fitting, matching the rigor of the existing `backend_research/REPORT.md`, not just in-sample fit stats.
- [ ] **Bull/bear scenario bands:** Often missing horizon-dependent widening — verify the band is visibly wider at 12 months than at 1 month, and differs per series per their actual backtested error.
- [ ] **Data entry table:** Often missing input validation and write-through persistence — verify a browser refresh mid-edit doesn't lose data, and garbage input (e.g., text in a price field) is rejected.
- [ ] **Excel export:** Often missing scenario columns — verify exported file contains bull/base/bear, not just base, and matches on-screen numbers.
- [ ] **Weekly mode:** Often "supported" in the UI before it's actually validated — verify the Baltic AN → HDAN/PPAN proxy (or scoped-subset approach) was backtested, not just wired up.
- [ ] **Reflex SQLite migrations:** Often missing `reflex db init`/migration setup — verify schema changes go through Alembic-backed Reflex commands, not manual `.db` surgery.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|-----------------|
| Overfit VAR/ARIMA shipped to dashboard | LOW | Swap in simpler model family (already backtested as a candidate per the research-first process); no schema/UI change needed since forecast interface stays the same |
| Flat, non-horizon-scaled bull/bear bands shipped | MEDIUM | Recompute spread function to use per-horizon forecast standard errors; UI/chart code doesn't need to change, only the backend spread calculation |
| Weekly mode shipped on a bad proxy | MEDIUM | Disable/hide the weekly toggle, re-scope per design doc §6 option (b) (weekly for AN-family only), backtest before re-enabling |
| State/DB desync causing lost user edits | LOW | Refactor event handlers to write-through immediately to `rx.Model`; no data loss for future edits, only past unsaved sessions are unrecoverable |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|---------------|
| Overfit small-sample VAR/ARIMA/SARIMAX | Model research/backtest phase | Holdout MAPE reported per series, matches or improves on existing workbook's backtest rigor (12-month holdout) |
| Weekly-mode data gap shipped as broken/misleading | Dedicated weekly-mode research phase (after monthly models are done) | Proxy relationship (or scoped-subset decision) documented with its own backtest before weekly toggle is exposed in UI |
| Bull/bear bands misleadingly precise or imprecise | Scenario/band computation phase (after model research) | Band width visibly grows with horizon; band width differs per series matching their distinct backtested MAPEs |
| Reflex State/DB desync losing user edits | Data persistence / SQLite integration phase | Manual test: edit a row, refresh browser, edit persists |
| Synchronous model refit blocking UI on every horizon change | Forecast-engine integration phase | Horizon dropdown changes feel instant (no full refit per click); refit only triggered by new actuals data |

## Sources

- [statsmodels ARIMAResults.forecast docs](https://www.statsmodels.org/devel/generated/statsmodels.tsa.arima.model.ARIMAResults.forecast.html) — confidence interval / forecast API behavior (HIGH confidence, official docs)
- [MachineLearningMastery — Out-of-Sample Forecasts with ARIMA](https://machinelearningmastery.com/make-sample-forecasts-arima-python/) — MEDIUM confidence, general practitioner guidance
- WebSearch synthesis on small-sample time-series pitfalls (sample-size-to-parameter ratio, overfitting risk with <50 obs) — MEDIUM confidence, corroborated across multiple independent sources in search results
- [Reflex — Database Overview docs](https://reflex.dev/docs/database/overview/) — HIGH confidence, official docs (State/session architecture, Alembic migration workflow)
- [Reflex — Common Errors & Troubleshooting Guide](https://reflex.dev/errors/) — MEDIUM confidence, official but not deeply reviewed in this pass
- `docs/plans/2026-08-21-reflex-dashboard-design.md` (this project) — HIGH confidence, primary source for architecture/scope decisions
- `.planning/PROJECT.md` (this project) — HIGH confidence, primary source for data provenance and backtested MAPE figures

---
*Pitfalls research for: Small-scale statsmodels forecasting + Reflex dashboard*
*Researched: 2026-08-21*
