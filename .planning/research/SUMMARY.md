# Project Research Summary

**Project:** Prediction Dashboard v2.0 -- News/Sentiment Scenario Adjustment & Weekly Forecast Research Spike
**Domain:** Additive research/build for a single-user Reflex commodity/FX forecasting dashboard -- layering a sentiment-driven scenario adjustment and a weekly-cadence forecasting spike onto an already-shipped, backtested v1 monolith
**Researched:** 2026-08-31
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is not a greenfield build -- it's two gated research spikes layered onto a mature, already-shipped Reflex + statsmodels dashboard (`app/app/forecasting.py`, `state.py`, `models.py`) whose v1 bull/bear bands are already backtested and frozen (D-06/D-08: "no un-backtested model ships"). Both v2.0 features must go through the same offline `backend_research/` backtest discipline that produced every existing model constant before anything touches `app/`. No new core stack is needed -- pandas/statsmodels/scikit-learn/scipy are already pinned and sufficient; the only net-new libraries are `vaderSentiment` (only if scoring new text) and `pmdarima` (research-phase convenience for weekly order search), both research-only, never runtime dependencies.

The single most important research finding, confirmed independently by all four researchers via direct file inspection (not assumption): the `archive/` dataset provided as the sentiment feature's starting point is a generic US-equity-market (SPY/QQQ/DIA/VIX) financial-news sentiment dataset with **zero** ammonium nitrate/diesel/Mongolia/tugrik content, and its dense daily coverage is only ~2 months wide (a NewsAPI free-tier artifact), not the 6-year span its date range implies. This means the sentiment feature cannot honestly be built as "ship a fitted sentiment coefficient" -- the correct scope is "build the pipeline/methodology, run a rigorous causality/correlation check against the app's actual four series, and honestly report go/no-go," mirroring how weekly mode is already scoped as a research spike, not a committed build. The weekly spike itself has a documented prior no-go (10.35%/16.01% weekly MAPE vs 9.49%/10.08% monthly, R2=0.03-0.04) with two specific untried follow-ups (SARIMAX/ETS at weekly cadence, Baltic-AN dedup) -- re-running the same VAR/proxy-variable combination would just reproduce the same failure.

Key risks, consistently flagged across STACK/FEATURES/ARCHITECTURE/PITFALLS: (1) treating domain-mismatched or sparse data as sufficient for a backtest (small-N illusion, correlation-with-equities conflated with predictive signal); (2) look-ahead/leakage bugs in the daily-sentiment-to-monthly-price merge, especially UTC vs Mongolia-local timezone boundaries; (3) an unbounded sentiment adjustment silently destabilizing the already-calibrated statistical bull/bear spread; (4) partial weekly coverage (only HDAN/PPAN can ever go weekly -- Diesel/FX/Diesel-MNT have no weekly source data at all) creating a confusing, inconsistent UI if not designed as per-series-aware from the start. Mitigation is the same pattern throughout: reuse the existing `walk_forward.py` harness and `causality_screen.py` methodology rather than inventing parallel ad hoc paths, treat sentiment as a strictly additive/capped layer on `bull`/`bear` that never touches `base` or the existing `MODEL_INFO` provenance, and gate all UI work behind an explicit backtest pass/fail -- never build UI speculatively ahead of a validated result.

## Key Findings

### Recommended Stack

No new core technologies are needed -- this milestone extends the existing Reflex/SQLite/pandas/statsmodels/scikit-learn/scipy/arch stack that already shipped v1's forecasting. All additions are research-phase-only conveniences, mirroring the project's existing rule that research-phase tools (e.g. `pmdarima`) never become runtime dependencies.

**Core technologies (additions):**
- `pandas` (already pinned) -- resample daily sentiment to monthly cadence and merge onto the existing price dataframe; no new dependency needed.
- `statsmodels` (already pinned `0.14.6`) -- `QuantReg` for asymmetric bull/bear quantile bands as a function of sentiment + horizon; optionally add sentiment as an `exog` regressor only if validated.
- `scikit-learn` (pin `1.7.2`, not the v1 STACK.md's stale `1.9.0` figure -- confirmed drift via `backend_research/ENV.md`) -- small Ridge/ElasticNet regression of sentiment features against forecast residuals to derive a bounded adjustment coefficient.
- `scipy` (transitive) -- `pearsonr`/`spearmanr` for the mandatory correlation/sufficiency check that must run before any sentiment adjustment is trusted.
- `arch` (already pinned `8.0.0`) -- reuse the existing GARCH(1,1) horizon-widening pattern; a sentiment adjustment should plug in as a second factor on top of this, not a parallel band system.
- `vaderSentiment==3.3.2` -- only if scoring any new/curated commodity-relevant text; matches the archive's own existing scoring methodology.
- `pmdarima==2.1.1` -- weekly SARIMAX/seasonal order-search convenience only, research-phase, never shipped.

**What NOT to use:** live NewsAPI or any live news API as a v2 runtime dependency (free tier only returns trailing ~30 days -- doesn't solve the historical-backtest gap and adds an external network dependency this single-process app deliberately avoids); any LLM API for sentiment scoring (cost, latency, non-determinism vs. VADER's free/deterministic/offline precedent); `transformers`/FinBERT (heavy compiled dependency, overkill for a few-hundred-row dataset); `News_Category_Dataset_v3.json` (unrelated HuffPost topic-classification corpus, zero financial/commodity signal).

### Expected Features

Both features are conditionally scoped: nothing ships to the UI until its research/backtest gate returns a "go." This mirrors the project's existing "no un-backtested model ships" discipline.

**Must have (table stakes, if each gate clears):**
- Sentiment-adjusted band rendered in the *same* existing fan chart, clearly distinguished (e.g. dashed line) from the statistical band -- never a second disconnected view.
- Explicit labeling that separates "statistical spread" from "sentiment-adjusted" bands -- never conflate a backtested number with a heuristic overlay.
- Basic provenance line (date range, article count, mean/weighted sentiment score) honestly labeled "general market sentiment," not commodity-specific.
- Staleness/coverage warning reusing the existing `freshness_chips_row()` pattern.
- Weekly/Monthly toggle defaulting to Monthly, with explicit per-series disabled state (not silent fallback) for series lacking weekly data (Diesel/FX/Diesel-MNT).
- Unit relabeling (chart axis, table column header, horizon slider label) whenever granularity changes.

**Should have (differentiators, add after validation):**
- Top-3-5 headline "why" list behind a sentiment adjustment (auditable provenance, no LLM needed).
- Sample-size/confidence flag on the sentiment score (e.g. "low sample -- 1 article").
- Per-series weekly capability badge and weekly-specific MAPE display, once weekly ships for at least one series.
- Sentiment trend mini-chart, once the point-in-time score display is validated as useful.

**Defer (v2+/reject):**
- Live/auto-refreshing news polling -- mismatched with single-user, roughly-monthly usage.
- SHAP-style explainability -- disproportionate for this scale.
- Full in-app article reader -- feature bloat.
- Open-ended multi-granularity picker beyond Monthly/Weekly.
- Auto-interpolating synthetic weekly points for series without weekly data -- manufactures false precision.

### Architecture Approach

The existing codebase already establishes the exact discipline both features must follow: `forecasting.py` is a pure, zero-Reflex-import module whose model choices are hard-coded from completed `backend_research/` backtests, and `state.py` is the sole `rx.session()` boundary. New work should be strictly additive -- a new sibling `sentiment.py` module (same zero-Reflex-import contract), a new `SentimentDaily`/`SentimentMonthly` table (never merged into the existing wide `PriceRow` schema, mirroring how `AppSetting` already handles cadence/shape mismatches), and a `backend_research/sentiment/` subfolder that reuses the existing `walk_forward.py` harness rather than forking a parallel merge/backtest path. The weekly spike stays entirely inside `backend_research/run_weekly_candidates.py` with zero `app/` changes until a real backtest clears the bar.

**Major components:**
1. `backend_research/sentiment/` (new) -- offline sentiment data loader + backtest harness, extending `walk_forward.py`; produces a frozen `results/sentiment_backtest.json` and go/no-go report before any app code changes.
2. `app/app/sentiment.py` (new, conditional on backtest pass) -- pure function `apply_sentiment_adjustment(scenario, sentiment_signal, horizon)` that takes the existing `{"base","bull","bear"}` dict and returns a new dict of the same shape, tilting `bull`/`bear` only, never `base` -- composes with, never replaces, `forecasting.py`'s output.
3. `app/app/models.py` (modify, additive) -- new `SentimentDaily`/`SentimentMonthly` `rx.Model` table at its native cadence, separate from `PriceRow`.
4. `backend_research/run_weekly_candidates.py` (extend, research-only) -- add SARIMAX/ExponentialSmoothing weekly candidates and resolve the Baltic-AN dedup question named as follow-ups in the prior no-go report; zero `app/` changes during this spike.

### Critical Pitfalls

1. **Archive sentiment data is for a different prediction problem (US equities, not commodities)** -- before any backtest, run a fresh Granger-causality/correlation screen (reusing `causality_screen.py`'s pattern) against HDAN/PPAN/Diesel-USD/FX specifically, not SPY; treat "does this data relate to our series at all" as an unproven hypothesis, not a given.
2. **Sparse coverage creates a small-N illusion** -- 91% of the sentiment daily file's rows fall in the last ~28 days; report effective monthly sample size explicitly and apply the project's existing thin-sample exclusion rule (`MIN_ML_ORIGINS`) rather than treating raw row counts as sample size.
3. **Look-ahead/leakage in the daily-to-monthly merge** -- UTC vs Mongolia-local (UTC+8) timezone mismatch and windowed-statistic columns can leak future information into a monthly resample; extend `walk_forward.py`'s existing `LeakageError` guard rather than writing a parallel merge path.
4. **Sentiment adjustment silently destabilizing the calibrated statistical spread** -- cap/bound the adjustment's influence and backtest empirical coverage of the *combined* band against the unadjusted band; never ship an unbounded multiplier as a "UI tweak" exempt from the backtest gate.
5. **Repeating the same failed weekly VAR/proxy-variable combination** -- the prior spike's root cause was weak input variables (R2=0.03-0.04), not model family; run a causality screen on genuinely new candidate weekly variables before refitting, and always compare against the prior spike's exact 9.49%/10.08% vs 10.35%/16.01% figures using the same walk-forward, horizon-matched methodology.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Sentiment Data Sufficiency & Causality Research
**Rationale:** This is the actual v2.0 deliverable in the "spike" sense -- everything downstream is conditional on this result, and the domain-mismatch/sparsity findings mean it is very likely to return a "no" or "not yet" for a fitted coefficient.
**Delivers:** `backend_research/sentiment/sentiment_data_loader.py`, `run_sentiment_backtest.py`, frozen `results/sentiment_backtest.json`, honest go/no-go report (Granger/correlation screen against HDAN/PPAN/Diesel/FX, effective monthly sample-size statement, timezone-aware leakage-checked merge).
**Addresses:** the P1 "Sentiment/backtest research step" from FEATURES.md.
**Avoids:** Pitfalls 1-4 (domain mismatch, small-N illusion, look-ahead leakage, correlation/predictive-signal conflation).

### Phase 2: Weekly Forecast Re-Research Spike
**Rationale:** Independent of Phase 1, can run in parallel; has a well-defined prior baseline (9.49%/10.08% monthly MAPE) and two named untried follow-ups, so this is a bounded, well-scoped research task rather than open-ended exploration.
**Delivers:** Extended `backend_research/run_weekly_candidates.py` with SARIMAX/ExponentialSmoothing candidates and Baltic-AN dedup resolution, updated `results/weekly_candidates.json`, a REPORT-WEEKLY-2.md with a side-by-side comparison against the prior spike's exact figures.
**Addresses:** the P1 "Weekly re-research backtest, per series" from FEATURES.md.
**Avoids:** Pitfalls 7-8 (repeating the same failed model family, non-comparable backtest window/horizon).

### Phase 3: Sentiment-Adjusted Scenario UI (conditional on Phase 1 go)
**Rationale:** Only build if Phase 1 clears a real significance bar -- building this speculatively ahead of a validated result directly contradicts the project's "no un-backtested model ships" rule.
**Delivers:** `app/app/sentiment.py` (pure adjustment function + `SENTIMENT_ADJUSTMENT_INFO` provenance constant), new `SentimentDaily`/`SentimentMonthly` table + migration, `seed_sentiment.py` offline loader, additive fan-chart band + provenance line + staleness timestamp in `app.py`/`state.py`.
**Uses:** `statsmodels.QuantReg` or a bounded multiplier per Phase 1's winning approach; the existing `arch`-based GARCH widening pattern as the base spread to layer on top of.
**Implements:** Architecture Pattern 1 (compose, never replace, `base`) and Pattern 2 (separate table, never merged into `PriceRow`).

### Phase 4: Weekly Forecast Mode UI (conditional on Phase 2 go, separate follow-on milestone)
**Rationale:** Only build if Phase 2 clears the horizon-matched MAPE bar; architecture research explicitly flags this as substantial enough (new `PriceRowWeekly` table, cadence-aware dispatcher, per-series UI) to warrant its own planning cycle rather than folding into this milestone.
**Delivers:** Per-series-aware granularity toggle (Monthly default, Weekly enabled only for series that passed), explicit disabled+tooltip state for Diesel/FX/Diesel-MNT, relabeled axes/table/horizon-slider units.
**Addresses:** the P1 "Weekly toggle + per-series disabled state" from FEATURES.md.
**Avoids:** Pitfall 9 (partial-coverage UI inconsistency, all-or-nothing gating).

### Phase Ordering Rationale

- Both research spikes (Phase 1, Phase 2) must complete and produce documented go/no-go findings before any corresponding UI phase starts -- this is the same "research/backtest before app changes" discipline the existing codebase already enforces for every shipped model.
- Sentiment and weekly research are independent of each other (different data, different code paths) and can be sequenced in parallel or either order; UI phases (3, 4) are strictly downstream of their respective research phase and should not be started speculatively.
- If either research phase returns a clear no-go, its corresponding UI phase should be dropped from the roadmap entirely (documented as a closed research finding) rather than built in a degraded form -- mirrors PROJECT.md's own framing that a negative result is a valid, complete milestone outcome.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Sentiment Data Sufficiency):** Needs research -- the causality-screen methodology and leakage-safe merge logic must be designed carefully against `walk_forward.py`'s existing harness; high risk of subtle timezone/small-N mistakes if rushed.
- **Phase 2 (Weekly Re-Research Spike):** Needs research -- must design genuinely new candidate variables (not just a new model family) to avoid reproducing the prior no-go; requires careful methodology matching to stay comparable to the prior spike's figures.

Phases with standard patterns (skip deep research-phase):
- **Phase 3 (Sentiment UI, if go):** Standard pattern -- directly mirrors existing `_summary_card`/`forecast_chart`/`freshness_chips_row` components already built for v1; mostly extension work once the backtest constant exists.
- **Phase 4 (Weekly UI, if go):** Mostly standard pattern (extends `horizon_control()`), though the per-series-aware disabled-state design needs explicit UX spec work per Pitfall 9.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Library versions verified via PyPI; data-sufficiency findings verified by direct inspection of `archive/` files, not assumed. Some version drift found between v1's original STACK.md and the actually-installed `backend_research` environment (scikit-learn 1.7.2 vs 1.9.0, pandas 2.2.3 vs 3.0 pin) -- flagged, not yet reconciled. |
| Features | MEDIUM | Data-reality findings (archive scope/sparsity) are HIGH/verified via direct file inspection; UX pattern findings (disabled-state conventions, granularity-toggle UX) are MEDIUM, drawn from general dashboard/fintech conventions rather than a direct competitor with this exact feature set. |
| Architecture | HIGH | Grounded in direct reads of `forecasting.py`, `state.py`, `models.py`, `app.py`, `seed.py`, `REPORT.md`, `REPORT-PHASE2.md`, `archive/README.md`. MEDIUM specifically on the sentiment data's actual predictive relevance, which is an open research question this document surfaces rather than resolves. |
| Pitfalls | HIGH | Grounded in direct inspection of `archive/*.csv`, `backend_research/REPORT.md`, and the prior weekly-backtest quick-task result -- not generic ML folklore. One MEDIUM sub-point: NewsAPI free-tier limits and the HuffPost dataset's provenance are corroborated by in-repo evidence but not independently re-verified against NewsAPI's current live terms in this session. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Sentiment relevance is genuinely unresolved:** all four researchers independently concluded the archive data is very likely insufficient for a validated commodity/FX sentiment adjustment (domain mismatch + ~2-month dense coverage). Roadmap should treat "ship a validated sentiment adjustment" as a possible-but-unlikely outcome, and explicitly plan for "document an honest no-go" as a legitimate, complete Phase 1 result -- not a blocker to closing the milestone.
- **Version drift between the original v1 STACK.md and actually-installed environment** (scikit-learn 1.7.2 vs 1.9.0, pandas 2.2.3 vs the `~=3.0` pin): should be reconciled/re-confirmed at the start of implementation, since new sentiment-pipeline code needs to know which pandas behavior (copy-on-write defaults, etc.) it will actually run under.
- **Weekly re-research's realistic upside is small:** with only ~1.5 weeks of additional data since the prior spike, the untried variable/model-family combinations are the main lever, not new data volume -- roadmap should set expectations that this spike may simply reconfirm the prior no-go, which is still a valid, budgeted outcome.
- **Mixed-granularity UI design (Phase 4) has no existing precedent in this codebase** to extend from (the current toggle is a single global control) -- this needs explicit UX design work during planning, not just component reuse, if Phase 2 returns a go.

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `archive/README.md`, `archive/news_sentiment_daily.csv`, `archive/news_sentiment_raw.csv`, `archive/sentiment_market_panel.csv`, `archive/ml_features.csv`, `archive/market_prices.csv`, `archive/News_Category_Dataset_v3.json` -- row counts, date ranges, column schemas, content sampling.
- Direct code inspection: `app/app/forecasting.py`, `app/app/state.py`, `app/app/models.py`, `app/app/app.py`, `app/app/seed.py`.
- `backend_research/REPORT.md`, `backend_research/REPORT-PHASE2.md`, `.planning/quick/20260821-weekly-an-backtest/SUMMARY.md`, `.planning/STATE.md`, `.planning/PROJECT.md` -- prior backtest figures, model provenance, key decisions.
- PyPI JSON API (`pypi.org/pypi/<package>/json`) -- live version lookups for vaderSentiment, arch, pmdarima, scipy, scikit-learn.

### Secondary (MEDIUM confidence)
- Web search on NewsAPI.org free-tier historical article limits (corroborates but doesn't independently re-verify the in-repo README's stated 28-day limit).
- Academic/industry sentiment-forecasting literature (ScienceDirect, Springer, Wiley, NCBI) -- confirms sentiment *can* have measurable forecasting power for oil/crude-adjacent commodities in general, not specific to this project's data.
- Dashboard/UX pattern research (Smart Interface Design Patterns, Metabase/GA4/Qlik community threads) -- general disabled-control and granularity-toggle conventions, not project-specific.

### Tertiary (LOW confidence)
- None flagged -- all findings in this synthesis trace to at least MEDIUM-confidence sources above.

---
*Research completed: 2026-08-31*
*Ready for roadmap: yes*
