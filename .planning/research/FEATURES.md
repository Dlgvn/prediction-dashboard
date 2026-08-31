# Feature Research

**Domain:** Single-user commodity/FX forecasting dashboard — v2.0 additions (news/sentiment scenario adjustment, weekly-granularity mode)
**Researched:** 2026-08-31
**Confidence:** MEDIUM (data-reality findings are HIGH/verified; UX pattern findings are MEDIUM, drawn from general dashboard/fintech conventions rather than a direct competitor with this exact feature set)

## Critical Finding First: The `archive/` Dataset Is Not Commodity-Specific

Before any feature design: I directly inspected every file in `archive/` (not just the README). This
materially changes what "sentiment-driven scenario adjustment" can honestly mean for this project.

- `archive/news_sentiment_raw.csv` (10,184 rows), `news_sentiment_daily.csv` (163 days,
  2020-03-16 → 2026-08-22, **sparse** — only 163 distinct days have any sentiment computed at
  all across a ~6-year span), `sentiment_market_panel.csv`, and `ml_features.csv` are a
  **generic US-equity-market financial news sentiment dataset** (NewsAPI headlines scored with
  VADER, correlated against SPY/QQQ/DIA/VIX). Its README states it's designed to "pair with"
  a US Recession Probability Tracker and Global Inflation/AI-Layoffs datasets — this reads as a
  public/Kaggle-style general-finance-education dataset, not something sourced for ammonium
  nitrate, diesel, or Mongolian tugrik markets.
- Grepping the full raw corpus: **zero** matches for "ammonium," "Mongolia," "tugrik," or word-
  boundary "MNT." **Nine** matches for "diesel," all generic retail-fuel/inflation headlines
  (e.g., US/India petrol price and CPI stories), not commodity-market or Mongolia-specific.
  Topic buckets are `markets / policy / volatility / inflation / earnings / recession / growth`
  — a macro/equity lens, not a fertilizer or Central-Asian-FX lens.
- Practical consequence: this data can plausibly serve as a **general market risk-on/risk-off
  proxy** (via `vix_regime`, `weighted_compound`, `sent_momentum`) that *might* correlate weakly
  with globally-traded inputs like Brent crude (which already feeds the Diesel-USD model) or
  general EM-FX risk appetite (relevant to USD/MNT) — but it cannot honestly be presented as
  "news about ammonium nitrate prices" or "news about the tugrik." Any UI copy, tooltip, or
  provenance panel must reflect this scope honestly, and the required research/backtest step
  (PROJECT.md constraint: "no un-backtested model ships") must test whether this generic signal
  has *any* measurable relationship to HDAN/PPAN/Diesel/FX at all before a sentiment-adjusted
  scenario ships. This is the single biggest risk to the feature's credibility with the user.

This finding shapes several Anti-Features and the MVP gate below — it is not a "nice to know,"
it's a go/no-go input the roadmap should sequence *before* any sentiment UI work, mirroring how
weekly mode is already correctly scoped as "research spike first, UI only if it clears a bar."

## Existing UI Surface (for dependency mapping)

Verified in `app/app/app.py` and `app/app/state.py` — the two new features must extend these,
not duplicate them:

- `forecast_chart()` — a single `rx.plotly` fan chart with a per-series `rx.select` dropdown
  (`DashboardState.forecast_series_label`), one series shown at a time. This is where a
  sentiment-adjusted band or a weekly-vs-monthly toggle would render.
- `forecast_summary_cards()` / `_summary_card()` — per-series cards showing base value, bull/bear
  range, and `model_name · X.X% typical error` (from a hardcoded `MODEL_INFO` map). This is the
  established precedent for showing model provenance/confidence next to a number — reuse this
  pattern for sentiment provenance and weekly-specific MAPE.
- `forecast_table()` — read-only base/bull/bear table across the horizon, with an amber
  `forecast_warning` banner pattern already used for graceful-degradation messaging (e.g.
  insufficient history). Reuse this exact banner pattern for "sentiment unavailable" /
  "weekly not supported for this series" states.
- `freshness_chips_row()` — existing staleness-indicator chips for price data. Directly reusable
  pattern for signaling sentiment-data staleness (the archive is a static export, last updated
  2026-08-22, not a live feed).
- `horizon_control()` — the existing 1-12 slider with live "N months/N month" label pluralization
  in `app.py`. The weekly toggle should extend this control's unit label, not introduce a
  separate/parallel control.
- `forecasting.py` — bull/bear are currently produced by `_apply_se_spread()` /
  `_apply_garch_spread()` as `base ± backtested statistical spread`, a documented invariant
  ("no un-backtested model ships... never be silently improved back into an unbacktested model").
  A sentiment adjustment must not mutate this existing band — see Anti-Features.

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Sentiment-adjusted scenario shown in the *same* fan chart as base/bull/bear, not a separate page | Existing forecast_chart() is the single source of truth for scenarios; a second disconnected sentiment view would feel bolted-on | LOW-MED | Extend `forecast_chart_figure` builder in state.py; add a distinguishable line/band style (e.g. dashed) for the sentiment-adjusted variant |
| Clear labeling that separates "statistical spread" bull/bear from "sentiment-adjusted" bull/bear | Users must never confuse a backtested band with a heuristic overlay — conflating them breaks the trust the MAPE-display precedent already established | LOW | Toggle/legend label change; mirrors existing `forecast_series_label` select pattern |
| Basic provenance line (date range covered, article count, mean/weighted sentiment score) near the chart | Matches the existing MAPE-next-to-forecast precedent (`_summary_card`) — the app already trains users to expect "here's the number, here's how trustworthy it is" | LOW-MED | Reuse `_summary_card` styling; source fields directly available in `news_sentiment_daily.csv` (`article_count`, `weighted_compound`) |
| Staleness/coverage warning when sentiment data doesn't cover the requested period, or is old | Archive is a static, non-live export (last row 2026-08-22); silently showing a stale score as current is misleading | LOW | Reuse `freshness_chips_row()` pattern verbatim |
| Graceful empty state when no sentiment adjustment applies (e.g. backtest says "no signal" for a series) | Matches existing `forecast_table()`'s amber `forecast_warning` banner precedent for degraded states | LOW | Reuse existing banner component |
| Weekly/Monthly control that defaults to Monthly and is always visible | Monthly is the validated, shipped mode; weekly must not silently become default before its own backtest clears | LOW | Extends `horizon_control()`; default `granularity="monthly"` |
| Explicit per-series disabled state (not silent fallback) when a series doesn't support weekly | Diesel/FX have zero weekly source data (confirmed in PROJECT.md context) — silently falling back to monthly without telling the user is a trust-breaking surprise | LOW | Standard "disabled control + tooltip explaining why" pattern (verified as a common, accessible dashboard convention below) |
| Unit relabeling when granularity changes (chart axis, table "Month" column header, horizon slider label) | A granularity toggle that changes the model but not the labels is a well-documented dashboard usability complaint (e.g. GA4 users flag exactly this inconsistency) | LOW-MED | Extend existing `"month"` / `" months"` string logic in `horizon_control()` and `forecast_table()` column header |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-scenario "why" list — top 3-5 headlines by absolute sentiment score behind the adjustment | Concrete, auditable provenance beats a black-box "+2% because sentiment" — matches academic/industry pattern of source attribution being the key trust element in financial sentiment tools | MEDIUM | No LLM/summarization needed — just sort `news_sentiment_raw.csv` rows by `abs(compound)` for the window and list title+source+link. Keeps the "no live API, no new LLM dependency" scope this milestone implies |
| Sample-size / confidence flag on the sentiment score (e.g. "low sample — 1 article" badge) | Prevents over-trusting a single-headline day; the daily file shows many days with `article_count == 1` | LOW | Simple threshold on `article_count`; mirrors the MAPE-as-trust-signal precedent |
| Sentiment trend mini-chart (`sent_ema3`/`sent_ema10`/`sent_momentum`) alongside the price fan chart | Lets the user see sentiment *regime*, not just a point score — closer to how the app already frames statistical spread as a range, not a point | MEDIUM | New `rx.plotly` component reusing the existing charting pattern |
| Explicit statistical-only vs statistical+sentiment view switch | Reassures the user the sentiment layer is additive/optional, not a silent replacement of the backtested model — directly supports the project's "no un-backtested model ships" trust posture | LOW-MED | Reuse the existing `rx.select`/toggle pattern already used for series selection |
| Per-series weekly capability badge ("Weekly available" / "Monthly only") shown on the series selector and summary cards | Lets the user know before switching, rather than discovering via a disabled toggle later; especially useful since coverage will likely be partial (HDAN/PPAN candidate, Diesel/FX/Diesel-MNT confirmed monthly-only) | MEDIUM | New state field per series; small badge element added to existing `_summary_card` |
| Weekly-specific MAPE shown distinctly from the monthly MAPE, if/when weekly passes backtest | Lets the user directly compare confidence between granularities using the exact display convention already established for monthly | LOW | Extends existing `MODEL_INFO`/`_summary_card` pattern with a second entry keyed by granularity |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Live/auto-refreshing news polling for sentiment | Feels more "real-time" and impressive | Mismatched with single-user, roughly-monthly usage cadence; adds a scheduler, API keys, rate-limit handling, and ongoing cost for a dashboard opened a few times a month — exactly the "real-time everything" trap the app has already avoided elsewhere (e.g. no live price API) | Batch-refresh the archive CSVs manually, following the same pattern as the existing CSV bulk-import feature for price data |
| SHAP/attribution-style explainability UI for the sentiment adjustment | Sounds rigorous, aligns with "explainable AI" trend seen in academic literature | Overkill for a small, auditable statsmodels-based app; adding a black-box explainability layer on top of a heuristic sentiment overlay contradicts the project's own "no un-backtested model ships" simplicity ethos, and is disproportionate engineering for a single user | Simple, auditable transparency instead: article count, date range, mean/weighted score, and top headlines — no attribution plots |
| Presenting the archive's generic US-equity sentiment as commodity-specific "AN/Diesel/MNT news" | Feature was scoped around this exact dataset, so it's tempting to imply direct relevance | **Verified false** — zero ammonium/Mongolia/tugrik/MNT mentions in 10,184 raw articles; this would actively mislead the user about what's driving a price band shift, undermining the tool's core trust proposition (procurement/budgeting decisions) | Label explicitly as a "general market risk sentiment" overlay (macro risk-on/risk-off proxy); gate the feature entirely on the required research/backtest step confirming *some* measurable relationship exists before shipping any UI |
| In-app full article reader / news browser | Feels feature-rich, "why not show the whole article" | Bloomberg-terminal-style feature bloat for an occasional-use procurement tool; large UI surface for low marginal value | Top-3 headline snippets with outbound links only |
| Sentiment silently widening/narrowing the *existing* backtested statistical bull/bear band | Simplest to implement — just adjust the existing spread number | Violates the documented invariant in `forecasting.py` that bull/bear = base ± backtested statistical spread; mixes an unvalidated heuristic into a validated number, making both harder to trust or debug | Sentiment adjustment must be a clearly separate, additive third band/line — never a mutation of the existing statistical band |
| All-or-nothing weekly mode (blocked globally because 2 of 5 values can't support it) | Simpler binary toggle to build | Throws away real value — HDAN/PPAN have genuine weekly source data per PROJECT.md context even though Diesel/FX don't | Per-series/partial weekly availability, not a single global gate |
| Auto-interpolating synthetic weekly points for Diesel/FX/Diesel-MNT to fake parity with HDAN/PPAN | Makes the UI "feel" consistent across all 5 tracked values | Manufactures false precision; an interpolated point is not a forecast and directly violates "no un-backtested model ships" | Explicitly gray out and label Diesel/FX/Diesel-MNT as monthly-only; no synthetic data |
| Shipping weekly UI in parallel with the unresolved re-research backtest | Feels efficient to build UI and research simultaneously | Directly contradicts the Key Decision already logged in PROJECT.md: weekly mode is "a research spike... not a committed build" until it beats the prior no-go (10.35%/16.01% weekly VAR vs 9.49%/10.08% monthly MAPE) | Strict sequencing: backtest result first, UI only if/when it clears the bar |
| Open-ended granularity picker (daily/weekly/biweekly/monthly/quarterly) | "More options" sounds more flexible | Over-engineered for a budgeting/procurement tool; PROJECT.md only ever specifies monthly (1-12) or weekly | Keep it a simple two-state Monthly/Weekly toggle |

## Feature Dependencies

```
Sentiment-adjusted scenario display
    └──requires──> Sentiment/backtest research step
                       (does the generic archive sentiment measurably relate to
                        HDAN/PPAN/Diesel/FX at all? — currently unverified/unlikely
                        to be commodity-specific; must be an honest go/no-go call,
                        same posture as weekly mode)

Sentiment provenance panel (headlines / date range / article count)
    └──requires──> Sentiment-adjusted scenario display
                       (nothing to show provenance for without an adjustment existing)

Sentiment trend mini-chart
    └──enhances──> Sentiment-adjusted scenario display

Weekly forecast mode UI (toggle + relabeled axes/table)
    └──requires──> Weekly re-research backtest passing, per series
                       (HDAN/PPAN = candidate; Diesel/FX = confirmed no-go on data
                        availability per PROJECT.md)

Per-series weekly capability badge
    └──enhances──> Weekly forecast mode UI

Diesel-MNT weekly value
    └──requires──> Diesel-USD weekly AND FX weekly
                       (derived series — diesel_mnt_forecast() multiplies the two
                        inputs; inherits the weaker/no-go status of either one,
                        so it cannot go weekly unless both underlying series do)

Sentiment-adjusted band ──conflicts with──> mutating the existing statistical bull/bear band
    (must render as a separate, additive line/band — never overwrite _apply_se_spread()/
     _apply_garch_spread() output)
```

### Dependency Notes

- **Sentiment display requires the research step:** Given the verified data mismatch (generic
  US-equity sentiment vs. Mongolian fertilizer/diesel/FX markets), this is not a formality —
  the backtest may well come back "no defensible signal," in which case this becomes a
  research-only artifact rather than a shipped UI feature, exactly like weekly mode's prior
  no-go.
- **Diesel-MNT inherits its inputs' weekly status:** because it's computed as
  `diesel_usd.bull * fx.bull * multiplier` (per `diesel_mnt_forecast()`), it cannot be "weekly"
  unless both Diesel-USD and FX independently clear a weekly backtest — currently expected to
  remain monthly-only regardless of HDAN/PPAN's outcome.
- **Provenance conflicts with silent mutation:** the sentiment layer's credibility depends on
  it being visibly separate from the backtested statistical band; combining them into one
  number would make the existing MAPE trust signal meaningless (the MAPE describes the
  statistical model only, not a heuristic sentiment tweak).

## MVP Definition

### Launch With (v1 of this milestone) — gated on research

- [ ] **Sentiment:** backtest/research step first — determine whether the archive's generic
      sentiment data has *any* measurable, defensible relationship to HDAN/PPAN/Diesel/FX.
      No UI work starts until this returns a result.
- [ ] **If sentiment research is a go:** a single additive sentiment-adjusted band/line on the
      existing fan chart, clearly distinguished from the statistical band, with a basic
      provenance line (article count, date range, mean/weighted score) honestly labeled as
      "general market sentiment," not commodity-specific news.
- [ ] **Weekly:** backtest/research step first, per series — HDAN/PPAN as the primary
      candidates; confirm Diesel/FX remain no-go given the known absence of weekly source data.
- [ ] **If weekly research is a go for any series:** a Monthly/Weekly toggle scoped to only the
      series that pass, with explicit disabled+tooltip state for the ones that don't (Diesel,
      FX, and derived Diesel-MNT expected to stay monthly-only).

### Add After Validation

- [ ] Top-N headline drill-down for sentiment provenance — once the basic adjustment is live and
      trusted
- [ ] Weekly-specific MAPE chip shown alongside the monthly one — once weekly mode ships for at
      least one series
- [ ] Sentiment trend mini-chart — once the point-in-time score display is validated as useful

### Future Consideration (defer)

- [ ] Live/polling news API integration — explicitly out of step with single-user, roughly-
      monthly usage; also flagged in prior-milestone STACK.md as deliberately unresearched/
      deferred pending its own future research pass
- [ ] SHAP or other formal explainability tooling — disproportionate for this scale and model
      complexity
- [ ] Full in-app article reader — feature bloat for an occasional-use procurement tool
- [ ] Open-ended multi-granularity picker beyond Monthly/Weekly — no stated need beyond these two

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| Sentiment/backtest research step (go/no-go) | HIGH | MEDIUM | P1 |
| Weekly re-research backtest, per series (go/no-go) | HIGH | MEDIUM | P1 |
| Sentiment-adjusted band + basic provenance (if go) | HIGH | MEDIUM | P1 (conditional) |
| Weekly toggle + per-series disabled state (if go) | HIGH | MEDIUM | P1 (conditional) |
| Sentiment staleness/coverage warning | MEDIUM | LOW | P1 (conditional, ships with the band) |
| Per-series weekly capability badge | MEDIUM | MEDIUM | P2 |
| Top-N headline provenance drill-down | MEDIUM | MEDIUM | P2 |
| Weekly-specific MAPE display | MEDIUM | LOW | P2 |
| Sentiment trend mini-chart | LOW-MEDIUM | MEDIUM | P3 |
| Statistical-only vs statistical+sentiment view switch | MEDIUM | LOW-MEDIUM | P2 |
| Live news polling | LOW (for this usage pattern) | HIGH | Reject/defer |
| SHAP-style explainability | LOW (for this scale) | HIGH | Reject/defer |
| Full article reader | LOW | MEDIUM-HIGH | Reject/defer |

**Priority key:**
- P1: Must clear before anything else — the two research/backtest steps are the actual v2.0
  deliverable in the "spike" sense; conditional P1s only apply if their gate returns a go
- P2: Should have, add once the conditional P1 ships and is validated with the user
- P3: Nice to have, future consideration

## Competitor Feature Analysis

No direct competitor exists for this exact niche (single-user Mongolian ammonium
nitrate/diesel/FX procurement forecasting). Patterns below are drawn from adjacent domains
(general fintech/market dashboards, BI tools) rather than a like-for-like competitor, and are
weighted accordingly (MEDIUM confidence, several independent sources agree on the general shape
even without a perfect analog).

| Feature | General fintech dashboards (e.g. market-sentiment trackers, BI tools) | Our Approach |
|---------|--------------------------------------------------------------------|--------------|
| Sentiment provenance/transparency | Source attribution (which outlets/headlines), confidence values, sentiment-by-source breakdowns are the recurring pattern across financial sentiment tooling and BI/UX literature | Reuse this pattern but scale it down to fit a single-user tool: article count + top headlines + explicit "general market, not commodity-specific" label, no dashboard-wide source-mix visualizations |
| Granularity toggles with partial support | BI tools (Metabase, GA4, Qlik) routinely surface granularity options that aren't valid for every view/series, and users consistently flag it as confusing when the toggle doesn't clearly explain *why* something is unavailable | Explicit per-series disabled state + tooltip, not a silent fallback or a generic error, addressing the exact complaint pattern found in BI-tool user reports |
| Disabled/unsupported control signaling | Standard convention: disabled control + tooltip explaining why + accessible focus handling (not a plain disabled attribute, which blocks keyboard focus) | Matches the app's own recent a11y precedent (keyboard-accessible data-entry cells, aria-live feedback) — apply the same care to the weekly-mode disabled state |

## Sources

- **Direct file inspection (HIGH confidence, primary verification):** `archive/README.md`,
  `archive/news_sentiment_daily.csv`, `archive/news_sentiment_raw.csv`,
  `archive/sentiment_market_panel.csv`, `archive/ml_features.csv`, `archive/market_prices.csv` —
  confirmed dataset scope, date coverage/sparsity, and absence of commodity-specific content via
  direct grep/inspection, not a third-party claim.
- **Direct code inspection (HIGH confidence):** `app/app/app.py`, `app/app/state.py`,
  `app/app/forecasting.py` — confirmed existing chart/summary-card/table component structure and
  the documented bull/bear-band invariant.
- `.planning/PROJECT.md` — authoritative source for the weekly-mode prior no-go backtest numbers
  and the "research spike, not committed build" framing this document mirrors for sentiment.
- Academic/industry sentiment-forecasting research (MEDIUM confidence, WebSearch, not verified
  against this project's specific series): [Does sentiment analysis bring more responsive
  commodity price forecasting? (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0275531926001686),
  [Crude oil price forecasting incorporating news sentiment (Springer)](https://link.springer.com/article/10.1007/s44443-025-00289-8),
  [News Sentiment and Commodity Futures Investing (Wiley)](https://onlinelibrary.wiley.com/doi/10.1002/fut.70019),
  [Explainable stock price prediction from financial news (NCBI/PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7924447/)
  — used only to confirm sentiment *can* have measurable forecasting power for oil/crude-adjacent
  commodities in the literature, which is why the research/backtest gate (rather than an outright
  rejection) is the right posture for this feature, not evidence that it will work for this
  project's specific series or data source.
- Dashboard/UX pattern research (MEDIUM confidence, WebSearch, general conventions not
  project-specific): [Disabled Buttons UX — Smart Interface Design
  Patterns](https://smart-interface-design-patterns.com/articles/disabled-buttons/),
  general BI-tool granularity-toggle discussions (Metabase, GA4, Qlik community threads) —
  used to confirm the disabled+tooltip and partial-granularity-support conventions referenced
  above.

---
*Feature research for: Prediction Dashboard v2.0 (news/sentiment scenario adjustment + weekly
forecast mode research spike)*
*Researched: 2026-08-31*
