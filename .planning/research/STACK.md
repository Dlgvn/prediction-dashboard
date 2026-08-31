# Stack Research — v2.0 Sentiment Scenarios & Weekly Forecast Research

**Domain:** Additive research/stack for (a) news/sentiment-driven bull/bear scenario
adjustment and (b) a weekly-cadence forecasting re-research spike, layered onto an
existing Reflex + statsmodels + pandas monolith.
**Researched:** 2026-08-31
**Confidence:** MEDIUM-HIGH (library versions verified via PyPI; data-sufficiency findings
verified by direct inspection of the actual archive/ files, not assumed)

## Headline Finding — Read Before Anything Else

**The `archive/` dataset is a generic Kaggle-style "financial news sentiment vs US
equities" dataset. It is not about ammonium nitrate, diesel, crude, or MNT/USD FX, and
its dense daily coverage is only ~2 months long.** This changes what "build the sentiment
feature" means for v2. Full detail in "Archive Data Sufficiency Audit" below. In short:

- `news_sentiment_daily.csv` / `sentiment_market_panel.csv` / `ml_features.csv` are keyed
  to **SPY/QQQ/DIA/VIX** (US equity indices), not commodities or EM FX. Topics are
  `markets / policy / inflation / volatility / earnings / recession / growth` — general
  macro-financial news, zero ammonium nitrate/urea/diesel/crude/Mongolia-specific content.
- `news_sentiment_daily.csv` has only **163 rows** spanning 2020-03-16 to 2026-08-22, but
  **148 of those 163 rows (91%) fall in the last ~28 days** (late July–August 2026). The
  gaps before that are up to 414 days apart — isolated one-off historical pulls, not a
  continuous series. This is a direct artifact of **NewsAPI's free-tier "last 30 days
  only"** restriction (confirmed via web search below), not a data-quality bug in the prep
  work.
- `News_Category_Dataset_v3.json` (87MB) is the well-known public HuffPost News Category
  dataset (2012–2022): categories are POLITICS/COMEDY/WORLD NEWS/ENTERTAINMENT/etc. It has
  no financial or commodity signal at all and is not a useful input for this feature.

**Practical consequence:** there is no way to *backtest* a sentiment→HDAN/PPAN/Diesel/FX
adjustment against multi-year monthly history using this data, because the only densely
covered window is ~2 months (call it 1–2 monthly observations after resampling) — nowhere
near enough for a regression with any statistical power. Recommendations below are shaped
around that constraint: reuse the *methodology* the archive already encodes (VADER scoring,
lag/EMA/rolling feature engineering, panel-merge pattern), but scope v2 research as "build
the pipeline mechanics + an honest correlation/data-sufficiency check," not "ship a
backtested sentiment coefficient." This is consistent with PROJECT.md's own constraint that
"no un-backtested model ships to the dashboard" — the honest research finding may legitimately
be "insufficient data yet; ship an experimental/capped nudge with a visible caveat" rather
than a fitted regression.

## Recommended Stack

### Core Technologies (additions to existing stack — no changes to Reflex/SQLite/rx.Model)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pandas | already pinned (`~=3.0` in `app/requirements.txt`; `2.2.3` actually installed per `backend_research/ENV.md` — see Version Compatibility) | Resample daily sentiment (`news_sentiment_daily.csv`) to monthly/weekly cadence to match forecast frequency; merge sentiment panel onto the existing price history dataframe | Already the project's data-handling library; no new dependency needed for the resample/merge step, which is 90% of the sentiment-pipeline plumbing |
| statsmodels | already pinned `0.14.6` | (1) `statsmodels.regression.quantile_regression.QuantReg` to fit asymmetric bull/bear quantiles as a function of sentiment + horizon, instead of a symmetric ± spread; (2) optionally add sentiment as an `exog` regressor to the existing SARIMAX(HDAN) call if/when a validated relationship is found | Already in the stack; `QuantReg` gives a principled way to produce *asymmetric* bands (bear widens more than bull on negative sentiment, or vice versa) without hand-rolling a new statistical framework — no new library required for this |
| scikit-learn | `1.7.2` (already pinned in `backend_research/requirements-research.txt`, NOT `1.9.0` — see Version Compatibility) | Small `Ridge`/`ElasticNet` regression of sentiment features against realized forecast error (residual), to derive a bounded scenario-widening/skewing coefficient; `sklearn.linear_model.QuantileRegressor` as an alternative to `QuantReg` if you want L1-penalized quantile fits | Already an approved research-phase dependency per the project's existing tech stack doc; reuse rather than add a competing regression library |
| scipy | already a transitive dependency of statsmodels/scikit-learn (`1.18.0` installed per `backend_research` env check) | `scipy.stats.pearsonr` / `spearmanr` for the mandatory correlation/sufficiency check *before* any sentiment-driven adjustment is trusted | This is the single most important step given the Headline Finding above — validate before modeling, don't assume the relationship exists. No new install needed; it rides in with statsmodels/scikit-learn already |
| arch | `8.0.0` (already pinned in `backend_research/requirements-research.txt`, used by `run_garch.py` for GARCH(1,1) horizon-widening of the existing statistical spread) | Reuse the *same* horizon-widening architecture already built for the statistical-spread bands — a sentiment adjustment should plug in as a second multiplicative/additive factor on top of the GARCH-or-backtest-error spread that already exists, not a parallel band-computation system | This is not a new recommendation — it's flagging that the project already solved "how do bull/bear bands widen with horizon" via `arch`, and the sentiment feature should extend that pattern (see Integration Point below) rather than reinventing band math |
| vaderSentiment | `3.3.2` (current PyPI, released 2020-05-22 — mature, stable, no breaking changes since; confirmed via PyPI JSON API) | Only needed if/when new text (beyond what's already pre-scored in `news_sentiment_daily.csv`) is scored — e.g. manually curated commodity/diesel/FX headlines added during the research phase | The archive's own README documents VADER as the scoring method already used to produce every sentiment column in the archive files. If any new text is scored, use the same tool for methodological consistency (an article scored with a different sentiment model isn't comparable to the archive's `compound` scores) |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pmdarima | `2.1.1` (confirmed current; supports `statsmodels>=0.14.5`, `python>=3.10` — compatible with this project's pinned statsmodels `0.14.6`) | Speed up weekly SARIMAX/seasonal-order search (REPORT.md's own follow-up (a): "test SARIMAX/exponential-smoothing at weekly cadence... wasn't repeated" in the prior weekly backtest) | Research-phase only — same rule as the existing STACK.md's treatment of pmdarima: use to auto-search weekly `(p,d,q)(P,D,Q,s)` orders faster than manual grid search, then hard-code the winning order if it ships. Do not add as a runtime dependency |
| `statsmodels.tsa.holtwinters.ExponentialSmoothing` | included in statsmodels 0.14.6, no new install | Exponential-smoothing candidate at weekly cadence, per REPORT.md's explicit follow-up recommendation | Weekly re-research spike only — add alongside the existing weekly VAR/OLS candidates already coded in `run_weekly_candidates.py` |

### Development Tools

No new dev tooling needed. Continue using `pytest` (already pinned `~8.0`) for unit tests
of any new sentiment-feature or weekly-model functions — keep them as plain Python
functions callable from tests, per the project's existing pattern of not burying logic in
`rx.State` methods.

## Installation

```bash
# Already installed (app/requirements.txt) — no action needed:
# reflex[db]~=0.9.8, sqlmodel~=0.0.39, pandas~=3.0, statsmodels~=0.14.6, openpyxl~=3.1, plotly~=6.9

# Research-phase additions (mirror backend_research/requirements-research.txt pattern —
# do NOT add these to app/requirements.txt unless a backtest explicitly wins and the
# feature ships):
pip install vaderSentiment==3.3.2   # only if scoring any new/curated text
pip install pmdarima==2.1.1         # weekly SARIMAX order search convenience only

# Already present in backend_research/requirements-research.txt, reuse as-is:
# arch==8.0.0, scikit-learn==1.7.2
```

## Archive Data Sufficiency Audit

Direct inspection of `archive/` (row counts, date ranges, column schemas — not assumed
from the README alone):

| File | Rows | Date range | What it actually covers |
|------|------|------------|--------------------------|
| `news_sentiment_raw.csv` | 8,410 | 2020-03-16 → 2026-08-22 | Individual articles, VADER-scored, topics = markets/policy/inflation/volatility/earnings/recession/growth. Sources are general financial media (Business Insider, TheStreet, CNBC, Crypto Briefing, Yahoo Entertainment, etc.) — no commodity or Mongolia trade press |
| `news_sentiment_daily.csv` | 163 | 2020-03-16 → 2026-08-22 | Daily aggregates, but 148/163 rows (91%) are in the last ~28 days; older rows are single isolated days up to 414 days apart |
| `market_prices.csv` | 1,670 | 2020-01-02 → 2026-08-21 (dense, daily trading days) | SPY/QQQ/DIA OHLCV + VIX — US equities, unrelated instrument universe to HDAN/PPAN/Diesel/FX |
| `sentiment_market_panel.csv` | 119 | same sparse-then-dense pattern as `news_sentiment_daily.csv` | Sentiment merged onto SPY/QQQ/DIA, target = `spy_return_next1d` |
| `ml_features.csv` | 117 | same pattern | ML-ready panel: lag/EMA/rolling/interaction features on the same US-equity target |
| `News_Category_Dataset_v3.json` | ~210K articles (est.) | 2012–2022 | Public HuffPost dataset (POLITICS/COMEDY/WORLD NEWS/etc.) — general news categorization, no financial/commodity signal |

**Why the dense window is only ~2 months:** the README documents the source as "NewsAPI
(newsapi.org)... last 28 days per run, 8 queries." NewsAPI's free developer tier restricts
the `/everything` endpoint to roughly the last month of articles (confirmed via web search
— see Sources). The older, sparse rows in the daily file are leftovers from earlier one-off
runs before the pipeline was run repeatedly/scheduled — they are not a continuous 6-year
history.

**What this means for the v2 sentiment feature:**
1. **Do not attempt a rigorous statistical backtest of sentiment→price-band adjustment
   against 2020–2025 history using this data** — the overlap is too thin (effectively a
   handful of days, not enough monthly/weekly observations after resampling).
2. **The methodology is reusable even though the data isn't domain-matched.** The
   VADER-scoring approach, the `sent_ema3`/`sent_ema10`/`sent_momentum` (MACD-style) feature
   engineering, the lag-1..5 + rolling-5/10/20 pattern in `ml_features.csv`, and the
   `rolling_corr_60d`/`sent_quantile_60d` panel columns are all a legitimate, working template
   for "how do I turn scored news into model-ready features" — reapply this pattern to
   whatever commodity/FX-relevant news gets collected going forward, rather than
   re-designing feature engineering from scratch.
3. **A defensible, honest scope for the v2 research phase** given this constraint:
   (a) build the pandas resample/merge/feature-engineering pipeline using the archive as a
   working example/fixture, (b) run the mandatory `scipy.stats` correlation check between
   whatever overlapping sentiment signal exists and HDAN/PPAN/Diesel/FX forecast residuals,
   (c) **document the finding honestly** — if correlation is not statistically distinguishable
   from noise (extremely likely given the ~2-month overlap), the research conclusion is "not
   enough data to fit a validated adjustment yet," not "ship a fitted coefficient anyway."
   That finding is itself valid research output per PROJECT.md's "no un-backtested model
   ships" constraint.
4. **If the project wants a real backtest eventually**, it needs commodity/FX-relevant news
   (fertilizer/urea/ammonia trade press, Brent/diesel crack spread coverage, Mongolia/EM-FX
   coverage) collected continuously over enough months to build real history — that is future
   work, explicitly out of scope for what currently exists in `archive/`.

## Integration Point: How Sentiment Plugs Into the Existing Fan Chart (Without Replacing It)

The existing v1 pattern (per PROJECT.md and `backend_research/run_garch.py`) is:
`bull/base/bear = base ± (statistical spread that widens with horizon, sourced from GARCH(1,1)
conditional volatility or backtest error/analytic SE as fallback)`.

**Recommended pattern for sentiment:** treat sentiment as a *second, capped multiplier/skew*
applied to the existing spread — not a parallel model, not a change to the base forecast:

```
adjusted_spread_bull = base_spread * (1 + k_bull * sentiment_signal)
adjusted_spread_bear = base_spread * (1 + k_bear * sentiment_signal)
```

where `sentiment_signal` is a bounded, monthly-resampled aggregate (e.g. `weighted_compound`
or `sent_momentum` clipped to [-1, 1]) and `k_bull`/`k_bear` are small coefficients derived
from the `scikit-learn`/`statsmodels` correlation step above — **and set to 0 (feature
disabled / band unchanged) if the correlation check doesn't clear a significance bar**, rather
than defaulting to some arbitrary nonzero weight. This keeps the base SARIMAX/VAR/Naive point
forecast completely untouched (satisfies "layered on top of," not "replacing") and reuses the
horizon-widening machinery that already exists via `arch`, rather than adding a second,
independent band-computation code path.

`QuantReg` (statsmodels) is a good alternative/complement to the multiplier approach if the
research phase wants genuinely asymmetric, directly-estimated quantile bands (10th/90th
percentile as a function of sentiment + horizon) instead of scaling a symmetric spread — no
new dependency either way.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| VADER (`vaderSentiment`) for any new text scoring | FinBERT / other transformer-based financial sentiment models (via HuggingFace `transformers`) | Only if the research phase concludes VADER's rule-based scoring is measurably too coarse for commodity/trade-press language (jargon-heavy, different from the retail-finance headlines VADER was tuned on) — but this adds `torch`/`transformers` (large, compiled, GPU-optional-but-slow-on-CPU) to a single-user, single-process, occasional-use app. Don't reach for this without first showing VADER's ceiling is actually the blocker |
| `arch`'s existing GARCH(1,1) widening + a sentiment multiplier on top | A dedicated sentiment-conditional volatility model (e.g. GARCH-X with sentiment as an external regressor) | Only worth the added complexity if the correlation check finds a genuinely strong, stable sentiment→volatility relationship — unlikely to be resolvable with the current ~2-month data window regardless of technique |
| `statsmodels.QuantReg` / `sklearn.QuantileRegressor` for asymmetric bands | Bootstrapped/simulation-based scenario bands (e.g. Monte Carlo resampling of historical shocks weighted by sentiment) | If quantile regression's linear-in-features assumption looks too crude once real data exists — Monte Carlo resampling needs no new dependency either (`numpy.random`, already transitive), just more research-phase design work; not needed at current data scale |
| pandas resample + statsmodels `exog` for weekly re-research | A dedicated time-series feature library (e.g. `tsfresh`, `sktime`) | Only if weekly re-research needs dozens of engineered candidate features searched automatically — given the prior weekly backtest already found the new weekly drivers add real but weak signal (R²=0.031–0.044, per REPORT.md), a heavier auto-feature-engineering library is unlikely to change the go/no-go conclusion and adds a large, rarely-needed dependency |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| Live NewsAPI (or any live news-API) as a v2 runtime dependency | (1) PROJECT.md's own Key Decisions table says v2 sentiment builds on the existing `archive/` prep work, not a from-scratch provider search; (2) NewsAPI's free tier only ever returns the last ~30 days (confirmed above) — a live feed doesn't solve the historical-backtest gap, it just extends the same "last month only" problem forward instead of backward; (3) introducing a network call at request/forecast time is a real architectural change for a project whose whole design point is a single local process with no external service dependency | Treat `archive/`'s pre-scored data as the research fixture for now; if commodity-specific live news is wanted later, that is genuinely a new milestone requiring its own provider research (as PROJECT.md's constraints doc already anticipated for the separate, explicitly-deferred "connect to a data API" idea) |
| An LLM API (OpenAI/Anthropic/etc.) for sentiment scoring | Adds cost-per-call, network latency, and non-determinism to a single-user, occasional-use app where the existing precedent (VADER, already used to build every sentiment column in `archive/`) is free, deterministic, and runs fully offline/in-process — completely consistent with the "single Reflex process, no external service" architecture already chosen for this project | `vaderSentiment` (already the archive's own methodology) |
| `transformers`/FinBERT/any HuggingFace model | Heavy compiled dependency (`torch`), slow CPU inference, massive overkill for a dataset this size (currently: a few hundred rows once resampled) and a single-user app that runs "roughly monthly" per PROJECT.md | VADER, as above; revisit only if VADER is empirically shown inadequate on real commodity-press text |
| Treating `News_Category_Dataset_v3.json` as a v2 input | It is the public HuffPost News Category dataset (2012–2022) — general news categorization (POLITICS/COMEDY/WORLD NEWS/etc.), not financial or commodity-relevant, and has no price/market columns to merge against at all | Ignore this file for the sentiment-adjustment feature; if a large ad-hoc text corpus is ever needed for a different purpose, note that it's this data before using it |
| Fitting a sentiment regression coefficient on the current archive data and shipping it as if backtested | The dense-coverage window is ~2 months (91% of daily rows), which resamples to roughly 1–2 monthly data points — statistically meaningless for a regression, and would violate PROJECT.md's own "no un-backtested model ships" constraint if presented as validated | Run the correlation/sufficiency check, document an honest "insufficient data" finding if that's what it shows, and ship (if anything) a clearly-labeled experimental/capped nudge rather than a fitted coefficient presented as validated |

## Stack Patterns by Variant

**If the correlation/sufficiency check finds no usable signal in the current archive data
(the likely outcome given the ~2-month dense window):**
- Ship nothing model-driven for v2; document the finding in the research phase and treat
  "collect continuous commodity/FX-relevant news for N more months" as a follow-up decision,
  not a blocker to closing this milestone.
- No new stack dependency needed for this outcome — it's a research conclusion, not a build.

**If the weekly re-research spike (per REPORT.md's own stated follow-ups) finds SARIMAX or
ExponentialSmoothing at weekly cadence beats the prior VAR/OLS weekly results and clears the
existing monthly VAR's 9.49%/10.08% MAPE bar on a horizon-matched (4-week) basis:**
- Use `pmdarima` only during the order-search step, then hard-code the winning
  `(p,d,q)(P,D,Q,s)` order in the shipped weekly model — mirrors the project's existing rule
  for `pmdarima` (research-phase convenience only, never a runtime dependency).
- Consider testing `arch`'s GARCH(1,1) at weekly cadence too — REPORT.md's monthly GARCH
  work already established the pattern (`run_garch.py`), and weekly data has ~4x more
  observations per unit time, which may make volatility clustering easier to detect than
  at monthly cadence.
- Diesel/FX remain permanently monthly-only regardless of this outcome — no weekly source
  data exists for them at all (confirmed in PROJECT.md context), so no stack change is
  possible or needed there.

**If the weekly re-research spike reconfirms the prior no-go (weekly-native underperforms
monthly on a horizon-matched basis):**
- No new stack dependency needed — this closes the spike with a "confirmed no-go, don't
  build weekly UI" finding, exactly the kind of honest negative result PROJECT.md's Key
  Decisions table already anticipated as a valid outcome.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `arch==8.0.0` | `statsmodels==0.14.6`, `numpy`/`scipy` as resolved by pip | Already verified working in this repo — `backend_research/run_garch.py` uses it in production-of-research-results today. No new compatibility risk. |
| `scikit-learn` | pinned `1.7.2` in `backend_research/requirements-research.txt`, **not** the `1.9.0` figure in the original `.planning/research/STACK.md` from the v1 milestone | `backend_research/ENV.md` explicitly records this drift ("scikit-learn: 1.7.2 installed vs 1.9.0 STACK.md pin — No"). Use `1.7.2` as the actual research-phase pin going forward for consistency with the already-installed environment; re-verify before bumping. |
| `pandas` | `~=3.0` pinned in `app/requirements.txt`, but `2.2.3` actually installed in the `backend_research/` environment per `ENV.md` | Same drift pattern — `backend_research/ENV.md` warns not to rely on pandas-3.0-only copy-on-write defaults when writing research scripts, since the installed research environment is still 2.2.3. Confirm which pandas version the sentiment-pipeline code will actually run under (`app/.venv` vs `backend_research/`) before relying on pandas 3.x-only behavior. |
| `pmdarima==2.1.1` | `statsmodels>=0.14.5` (project has `0.14.6`), `python>=3.10` (project targets 3.11/3.12) | Confirmed via PyPI `requires_dist` — compatible with the current pins, no version conflict. |
| `vaderSentiment==3.3.2` | No hard pin on numpy/pandas/statsmodels — it's a standalone lexicon-based scorer with minimal dependencies | Last released 2020-05-22 but stable/mature (rule-based lexicon scoring, not a model that goes stale) — safe to add without version-compat concerns. |

## Sources

- Direct file inspection: `archive/README.md`, `archive/news_sentiment_daily.csv`,
  `archive/news_sentiment_raw.csv`, `archive/sentiment_market_panel.csv`,
  `archive/ml_features.csv`, `archive/market_prices.csv`, `archive/News_Category_Dataset_v3.json`
  — row counts, date ranges, and column schemas verified directly (not assumed from README
  prose alone) — HIGH confidence
- `backend_research/REPORT.md` ("Weekly cadence (Phase 1 follow-up, 2026-08-21)" section) —
  source of the 9.49%/10.08% monthly VAR baseline, the 10.35%/16.01% weekly-rolled comparison,
  and the explicit "test SARIMAX/exponential-smoothing at weekly cadence" follow-up
  recommendation this research builds on — HIGH confidence (primary project artifact)
- `backend_research/run_garch.py`, `backend_research/requirements-research.txt`,
  `backend_research/ENV.md` — confirmed `arch==8.0.0` and `scikit-learn==1.7.2` are already
  live, working research-phase dependencies, and confirmed the pandas/scikit-learn
  version-pin drift vs the original STACK.md — HIGH confidence (primary project artifact)
- PyPI JSON API (`pypi.org/pypi/<package>/json`) — live version lookups for `vaderSentiment`
  (3.3.2), `arch` (8.0.0), `pmdarima` (2.1.1), `newsapi-python` (0.2.7, not recommended),
  `scipy` (1.18.1 latest / 1.18.0 installed) — HIGH confidence, checked 2026-08-31
- Web search on NewsAPI.org free-tier historical article limits — confirmed "development
  use only," ~30-day historical window on the free `/everything` endpoint, corroborating
  the sparse-then-dense pattern observed directly in `news_sentiment_daily.csv` — MEDIUM
  confidence (aggregated secondary sources, not NewsAPI's own pricing page directly, but
  consistent with and explains the file's own observed date distribution)

---
*Stack research for: Prediction Dashboard v2.0 (News/Sentiment Scenarios & Weekly Forecast Research)*
*Researched: 2026-08-31*
