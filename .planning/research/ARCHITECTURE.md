# Architecture Research

**Domain:** Integrating a news/sentiment scenario-adjustment layer and a weekly-forecast research spike into an existing single-process Reflex forecasting dashboard
**Researched:** 2026-08-31
**Confidence:** HIGH (grounded in direct reads of `app/app/forecasting.py`, `app/app/state.py`, `app/app/models.py`, `app/app/app.py`, `app/app/seed.py`, `backend_research/REPORT.md`, `backend_research/REPORT-PHASE2.md`, `archive/README.md`) — MEDIUM on the sentiment data's actual predictive relevance, which is an open research question this document surfaces rather than resolves.

## Standard Architecture

### System Overview — current state (verified)

```
┌───────────────────────────────────────────────────────────────────────┐
│                         Reflex process (single)                       │
├───────────────────────────────────────────────────────────────────────┤
│  app/app/app.py                                                       │
│    index() → rx.match(active_section, "summary"/"forecast"/           │
│    "data_entry" → {historical_section, data_entry_section})           │
│    Renders DashboardState vars/components; NEVER opens rx.session().  │
├───────────────────────────────┬───────────────────────────────────────┤
│  app/app/state.py (DashboardState — SOLE rx.session() call site)      │
│    - load_rows / commit_edit / request_delete / confirm_import        │
│    - forecast_results (@rx.var) → single call site for forecast_all() │
│    - _history_df() → PriceRow rows → plain pd.DataFrame (16 cols)     │
│    - SERIES_ATTRS / SERIES_LABELS / FORECAST_SERIES_LABELS = single   │
│      sources of truth for the 16-series schema + 5-series forecast    │
│      dispatch                                                         │
├───────────────────────────────┬───────────────────────────────────────┤
│  app/app/forecasting.py (ZERO reflex import — pure pandas/numpy)      │
│    forecast_all(history, horizon, markup_pct) → single dispatcher     │
│      → forecast_hdan (SARIMAX+exog, frozen GARCH sigma spread)        │
│      → forecast_ppan_var_system (Direct-OLS VAR-system, ARIMA-SE      │
│        spread)                                                        │
│      → forecast_diesel_usd / forecast_fx (Naive, ARIMA-SE spread)     │
│      → diesel_mnt_forecast (derived: diesel_usd × fx × markup)        │
│    MODEL_INFO = frozen {series: (model_name, mape_pct)} provenance    │
│    All model choices hard-coded from backend_research/ backtest       │
│    output — MODEL_INFO/HDAN_SARIMAX_ORDER/etc. are never re-derived   │
│    at runtime (D-06/D-08 "no un-backtested model ships").             │
├───────────────────────────────┬───────────────────────────────────────┤
│  app/app/models.py (rx.Model/SQLModel — SQLite)                       │
│    PriceRow: one row per MONTH, wide 16-series schema, date unique    │
│    AppSetting: key/value (markup_pct)                                 │
├───────────────────────────────┴───────────────────────────────────────┤
│  app/app/seed.py — standalone offline script (NOT wired into app      │
│  startup, opens its OWN sqlmodel session) that bulk-loads CSVs into   │
│  PriceRow. This is the app's one pre-existing exception to "state.py  │
│  is the sole session boundary" — an established, deliberate pattern   │
│  ("never wired into app startup — standalone script").                │
└───────────────────────────────────────────────────────────────────────┘

Offline/out-of-band, NOT part of the running app:
  backend_research/  — walk-forward backtest harness (walk_forward.py,
    run_*_candidates.py, results/*.json, REPORT.md/REPORT-PHASE2.md).
    This is where EVERY winning model in forecasting.py was proven before
    being hard-coded. New models (sentiment adjustment, weekly cadence)
    must go through an equivalent step here BEFORE touching app/.

  archive/  — NOT yet wired to anything. Contains US-equity-market news/
    sentiment data (see Pitfall below), not commodity-specific sentiment.
```

### Component Responsibilities (existing, verified by file read)

| Component | File | Responsibility | Reflex-coupled? |
|-----------|------|-----------------|------------------|
| `forecasting.py` | `app/app/forecasting.py` | Pure forecast math: 4 hard-coded per-series models + derived diesel_mnt + frozen `MODEL_INFO` provenance constant | No — zero `import reflex`, unit-tested directly (`tests/test_forecasting.py`) |
| `models.py` | `app/app/models.py` | SQLite schema: `PriceRow` (monthly wide table), `AppSetting` (k/v) | Yes (`rx.Model`) but only imported, never queried outside state.py |
| `state.py` | `app/app/state.py` | Sole DB read/write boundary (`rx.session()`); computed vars (`forecast_results`, `summary_cards`, chart figures); event handlers for edit/delete/import | Yes — this is the Reflex boundary |
| `app.py` | `app/app/app.py` | Component tree, `rx.match(active_section, ...)` tab switching | Yes — pure rendering |
| `seed.py` | `app/app/seed.py` | Standalone, manually-run, offline CSV → `PriceRow` bulk loader with its own session | Yes (imports `rx.Model` via `app.models`) but architecturally exempt from the "state.py only" rule because it never runs inside the live app process |
| `backend_research/` | `backend_research/*.py` | Offline walk-forward backtest harness that produced every constant now frozen in `forecasting.py` | No |

## Recommended Project Structure — additions for v2.0

```
backend_research/
├── sentiment/                      # NEW — research/backtest phase for the
│   │                                 sentiment-adjustment feature. Mirrors
│   │                                 the existing run_*_candidates.py /
│   │                                 walk_forward.py pattern.
│   ├── sentiment_data_loader.py    # NEW — loads archive/*.csv, aligns
│   │                                 sentiment dates to PriceRow's monthly
│   │                                 cadence (resample/aggregate daily→
│   │                                 monthly, mirroring data_loader.py's
│   │                                 existing resample patterns)
│   ├── run_sentiment_backtest.py   # NEW — tests whether a sentiment
│   │                                 signal, added as an adjustment to the
│   │                                 EXISTING base/bull/bear bands, reduces
│   │                                 error or improves interval coverage
│   │                                 vs. the current statistical-spread-only
│   │                                 baseline (same walk_forward.py harness)
│   └── results/sentiment_backtest.json   # NEW — frozen output, mirrors
│                                            results/wf_*.json convention
├── run_weekly_candidates.py        # EXISTS — extend, don't replace, per
│                                      REPORT.md's own "before revisiting
│                                      this" follow-ups (SARIMAX/ETS at
│                                      weekly cadence; Baltic AN dedup check)
└── results/weekly_candidates.json  # EXISTS — append new weekly-SARIMAX
                                       results here on the same schema

app/app/
├── forecasting.py                  # MODIFY (additive only) — add
│                                      MODEL_INFO-style frozen provenance
│                                      constant for the sentiment adjustment
│                                      once backtested; existing 4 model
│                                      functions untouched
├── sentiment.py                    # NEW — pure Python, mirrors
│                                      forecasting.py's zero-Reflex-import
│                                      contract exactly. Composes with (does
│                                      NOT replace) the existing
│                                      base/bull/bear dict shape.
├── models.py                       # MODIFY (additive) — new
│                                      SentimentDaily/SentimentMonthly
│                                      rx.Model table (see Data Flow below)
├── seed_sentiment.py                # NEW — standalone offline loader for
│                                      archive/*.csv → new sentiment table,
│                                      following seed.py's exact precedent
│                                      (own session, "never wired into app
│                                      startup")
├── state.py                        # MODIFY (additive) — new computed
│                                      var(s) that call sentiment.py
│                                      functions against forecast_results'
│                                      existing output; NO changes to
│                                      forecast_results itself (composition,
│                                      not replacement — see Pattern 1)
└── app.py                          # MODIFY (additive) — render the
                                       sentiment-adjusted band + provenance
                                       text in forecast_section()

app/alembic/versions/
└── <new>_add_sentiment_table.py    # NEW — via `reflex db migrate`, per
                                       models.py's existing SQLModel
                                       convention; do NOT hand-write SQL
```

### Structure Rationale

- **`backend_research/sentiment/`** as a subfolder (not new top-level files) — keeps the sentiment backtest visually and organizationally subordinate to the existing `backend_research/` harness it depends on (`walk_forward.py`, `model_harness.py`), the same way `run_weekly_candidates.py`'s weekly section reused the existing harness rather than forking a parallel one.
- **`app/app/sentiment.py` as a sibling to `forecasting.py`, not a submodule of it** — the project's zero-Reflex-import contract (D-08) is a per-file property enforced by `tests/test_forecasting.py`-style import assertions; a new file makes it trivial to write an equivalent `tests/test_sentiment.py` that asserts `sentiment.py` never imports `reflex`, without touching the existing frozen file.
- **`seed_sentiment.py` as its own file, not folded into `seed.py`** — `seed.py`'s docstring is explicit about its column mapping being scoped to the three price CSVs; sentiment data has a different cadence (daily) and a different target table, so keeping it separate avoids overloading one script's CLI argument contract (`python -m app.seed "<an data path>" "<an weekly path>" "<diesel path>"`).

## Architectural Patterns

### Pattern 1: Sentiment adjustment composes with, never replaces, the existing spread

**What:** `sentiment.py` exports a pure function with a signature like `apply_sentiment_adjustment(scenario: dict, sentiment_signal: float, horizon: int) -> dict`, where `scenario` is exactly the `{"base": [...], "bull": [...], "bear": [...]}` shape every `forecast_*` function in `forecasting.py` already returns. It **takes an already-computed statistical scenario dict as input** and returns a new dict of the same shape — it never fits its own point forecast and never touches `base`.

**When to use:** Every call site that today reads `forecast_results[key]` (chart, table, summary cards) can optionally read a second, sentiment-adjusted dict instead — additive, not a replacement of the existing spread mechanism. This mirrors the exact discipline `_apply_garch_spread` / `_apply_se_spread` already use in `forecasting.py`: a small pure function that widens/shifts `bull`/`bear` around an untouched `base`.

**Trade-offs:** Pro — this cannot silently corrupt the already-backtested statistical bands (v1's core promise). Con — if a real, validated sentiment signal only naturally wants to shift `base` (e.g., "bearish news should shift the whole expected price down, not just widen bear"), that decision needs to be made explicit and named for the user, not layered in as a hidden implementation detail. Recommend v2 land the adjustment on `bull`/`bear` only first (the same choice the existing GARCH/SE spread pattern makes), and treat "should sentiment also tilt `base`" as an open question for the backtest to answer.

**Example (illustrative, matches `_apply_se_spread`'s existing shape discipline):**
```python
# app/app/sentiment.py — mirrors forecasting.py's zero-Reflex-import contract
def apply_sentiment_adjustment(
    scenario: dict, sentiment_signal: float, horizon: int
) -> dict:
    """Tilt bull/bear (never base) by a backtested sentiment multiplier.

    `scenario` is the exact {"base": [...], "bull": [...], "bear": [...]}
    shape every forecast_* function in forecasting.py returns. This
    function never re-fits a point forecast and never mutates `base` —
    it composes with the statistical spread, per D-0X (sentiment is v2's
    Scenario-planning/Delphi-style mechanism REQUIREMENTS.md already
    reserved, explicitly deferred from Phase 2's backtestable-methods
    scope in REPORT.md).
    """
    ...
```

### Pattern 2: Sentiment data storage stays a separate table at its native cadence, never merged into `PriceRow`

**What:** `PriceRow` is a wide table with exactly one row per tracked **month** (`date` unique, `SERIES_ATTRS` = 16 price columns). Sentiment data in `archive/` is **daily** (`news_sentiment_daily.csv`, `sentiment_market_panel.csv`) and covers a different, broader set of columns (VADER compound scores, EMAs, momentum, market-panel returns) that have nothing to do with commodity prices. Do not add sentiment columns to `PriceRow` — instead add a new table, e.g. `SentimentDaily` (or pre-aggregated `SentimentMonthly` if the backtest settles on monthly-only granularity), following `models.py`'s existing `rx.Model, table=True` + `sqlmodel.Field` convention, with its own `reflex db migrate` revision.

**When to use:** Any time ingested data has a different natural cadence or schema shape than the existing 16-series monthly contract. This is the same reasoning `AppSetting` already applies for `markup_pct` (D-04: "global markup lives on `AppSetting`, NOT as a per-row column on `PriceRow`") — cadence/shape mismatches get their own table, not a bolt-on column.

**Trade-offs:** Pro — keeps `SERIES_ATTRS`/`SERIES_LABELS` (the 16-series single source of truth `state.py`, `seed.py`, and export code all share) completely unperturbed; zero risk of an accidental column-count drift bug. Con — `state.py`'s `_history_df()` builder (which currently just does `{attr: getattr(row, attr) for attr in SERIES_ATTRS}`) needs a second, parallel builder for sentiment history, joined by date at the point `sentiment.py` is called, not baked into the existing DataFrame.

### Pattern 3: Weekly-cadence work stays entirely inside `backend_research/` until it clears a real backtest bar — zero `app/` changes during the spike

**What:** Per `PROJECT.md`'s explicit v2 key decision ("v2 weekly-forecast-mode work is a research spike... not a committed build") and the "no un-backtested model ships to the dashboard" constraint, the weekly spike should extend `backend_research/run_weekly_candidates.py` (which already has `load_an_weekly()`, `load_weekly_drivers()`, `merged_weekly()` and a working weekly-vs-monthly horizon-matched evaluation methodology per `REPORT.md`'s "Weekly cadence" section) — not touch `forecasting.py`/`state.py`/`models.py` at all.

**When to use:** For this milestone specifically. `REPORT.md`'s own prior no-go finding names two concrete untried follow-ups: (a) test SARIMAX/exponential-smoothing at weekly cadence (only VAR/OLS were tried before), (b) resolve whether `AN price weekly.csv`'s own Baltic AN series duplicates `AN Data.csv`'s. Do both before touching app code.

**Trade-offs:** Pro — a failed or inconclusive weekly backtest costs nothing in app-layer complexity or migration risk. Con — if the spike DOES clear the bar, the schema/dispatcher changes required are substantial (see below), so budget that as a distinct follow-on scope, not a small addition to this milestone.

## Data Flow

### Sentiment feature: archive CSVs → adjustment value (new)

```
archive/news_sentiment_daily.csv        (date, weighted_compound, sent_ema3,
archive/sentiment_market_panel.csv       sent_ema10, sent_momentum, article_count,
archive/ml_features.csv                  + SPY/QQQ/DIA/VIX-derived columns)
        │
        ▼  (OFFLINE — backend_research/sentiment/sentiment_data_loader.py)
Resample/aggregate daily sentiment → monthly, aligned to PriceRow's date
grid (same cadence problem seed.py's D-06b "average, don't take-last"
convention already solved for AN/weekly-driver CSVs — reuse that pattern)
        │
        ▼  (OFFLINE — backend_research/sentiment/run_sentiment_backtest.py,
             same walk_forward.py harness as every existing model)
Backtest: does a sentiment-derived adjustment measurably improve interval
coverage or reduce error vs. the CURRENT statistical-spread-only baseline,
for HDAN/PPAN/Diesel-USD/FX specifically? Frozen result → results/
sentiment_backtest.json + a REPORT-SENTIMENT.md (mirrors REPORT.md format)
        │
        ▼  GATE: only proceed past this point if the backtest shows a real,
             honestly-reported improvement (mirrors the Phase 2 "leakage
             red flag" discipline already applied to HDAN/PPAN/Diesel/FX)
        │
        ▼  (ONE-TIME/PERIODIC — app/app/seed_sentiment.py, own session,
             mirrors seed.py precedent, never wired into app startup)
archive CSVs → new SentimentDaily/SentimentMonthly rx.Model table (SQLite)
        │
        ▼  (RUNTIME — app/app/state.py, the sole live rx.session() site)
DashboardState reads SentimentDaily/Monthly rows the same way load_rows()
reads PriceRow, converts to a plain DataFrame/scalar (mirrors _history_df())
        │
        ▼  (RUNTIME — app/app/sentiment.py, zero-Reflex pure function,
             called from a NEW state.py computed var, e.g.
             sentiment_adjusted_forecast_results, that wraps the EXISTING
             forecast_results output — never re-invokes forecast_all)
apply_sentiment_adjustment(scenario_dict, sentiment_signal, horizon)
  → same {"base","bull","bear"} shape, bull/bear tilted
        │
        ▼  (RUNTIME — app/app/app.py, forecast_section())
Rendered as an additional band/toggle on the existing forecast_chart_figure,
plus a provenance line (mirrors summary_cards' existing MODEL_INFO-sourced
"Model" line) naming what's driving the adjustment
```

### Weekly spike: data → go/no-go decision (research-only, no runtime flow yet)

```
AN Data.csv (native weekly, HDAN/PPAN)  ─┐
AN price weekly.csv (weekly drivers)     ├─► backend_research/run_weekly_candidates.py
                                          │     (EXTEND: add SARIMAX/ETS candidates,
                                          │      dedupe Baltic AN source)
                                          ▼
                              results/weekly_candidates.json
                                          │
                                          ▼  GATE: horizon-matched (4-week-ahead)
                                             MAPE must beat the existing monthly
                                             VAR's 9.49%/10.08%, per REPORT.md's
                                             own comparison methodology
                                          │
                        ┌─────────────────┴─────────────────┐
                        ▼ NO-GO (prior result)               ▼ GO (hypothetical)
              Spike ends here. Zero app/         Second, SEPARATE milestone:
              changes. Update PROJECT.md          new PriceRowWeekly table,
              Key Decisions with the new           cadence-aware forecast_all_weekly()
              result and rationale.                dispatcher, cadence toggle in
                                                     state.py/app.py — scoped only to
                                                     HDAN/PPAN (no weekly Diesel/FX
                                                     data exists at all, confirmed
                                                     unchanged in REPORT.md).
```

## Anti-Patterns

### Anti-Pattern 1: Assuming `archive/`'s sentiment data is already about the right market

**What people do:** Treat `PROJECT.md`'s Key Decision ("v2 news/sentiment scenario feature builds on the existing `archive/` dataset... rather than researching a provider from scratch") as license to skip validating relevance, and wire `weighted_compound`/`sent_momentum` straight into a scenario adjustment for HDAN/PPAN/Diesel/FX.

**Why it's wrong:** Verified by reading `archive/README.md` and the CSVs directly: this dataset is **US equity-market sentiment** — VADER scores on NewsAPI headlines about `markets/policy/volatility/inflation/earnings/recession/growth`, correlated against **SPY/QQQ/DIA/VIX**, explicitly designed as a next-day S&P-500-return predictor (`spy_return_next1d` is literally the regression target in `ml_features.csv`). It contains zero fertilizer/ammonium-nitrate/urea/diesel/crude/Mongolian-tögrög-specific content. There is no established or backtested reason to believe US equity-market fear/greed sentiment moves HDAN/PPAN/Diesel/USD-MNT prices, and the tracked series are already known (per `REPORT-PHASE2.md`'s causality screen) to respond to specific fundamentals (urea/ammonia/Baltic AN/gas benchmarks/Brent/Urals), not broad market risk appetite.

**Do this instead:** Treat this as the sentiment feature's central open research question, not a solved input. In `backend_research/sentiment/`, explicitly test whether `weighted_compound`/`vix_regime`/`sent_momentum` (as a generic "risk-off" proxy) has ANY measurable relationship to HDAN/PPAN/Diesel-USD/FX via the same causality-screen methodology `REPORT-PHASE2.md` already used for fundamental predictors (Granger/lag p-value screen). If it clears no bar (plausible, given the domain mismatch), report that honestly — the "no un-backtested model ships" rule applies here just as strictly as it did to the ML baselines that were rejected in Phase 2. Do not silently swap in different, more-relevant data sources without telling the user that the originally-scoped `archive/` dataset didn't pan out.

### Anti-Pattern 2: Widening the sentiment adjustment's scope to touch `base`, `forecast_all`'s dispatcher, or `MODEL_INFO` directly

**What people do:** Once a sentiment signal is validated, it's tempting to fold it directly into `forecast_hdan`/`forecast_ppan_var_system`/etc. as a new exogenous predictor, or to have it silently overwrite `MODEL_INFO`'s backtested MAPE numbers with a "new, improved" figure.

**Why it's wrong:** `forecast_all`'s docstring is explicit that D-06 forbids caching/refitting drift and that `MODEL_INFO`'s values are "transcribed verbatim from the forecast_* docstrings... themselves sourced from `02-MODEL-DECISIONS.md`" — i.e., every number there traces to one specific, already-completed backtest. Silently changing what `base` means, or overwriting those provenance numbers with different-methodology sentiment-adjusted figures, breaks the "displayed model line is honest about what actually produced this number" contract the whole app currently guarantees (VIS-05).

**Do this instead:** Keep sentiment strictly a post-hoc, clearly-labeled adjustment layer (Pattern 1) with its OWN frozen provenance constant (mirroring `MODEL_INFO`'s shape but named separately, e.g. `SENTIMENT_ADJUSTMENT_INFO`), rendered as an additional, explicitly-labeled line/toggle — never merged into or overwriting the existing four models' identity.

### Anti-Pattern 3: Pre-building the weekly UI/schema before the spike's backtest gate passes

**What people do:** Start adding a `cadence` toggle to `state.py`, a `PriceRowWeekly` table, or a weekly branch in `forecast_all` "so it's ready" while the research spike is still running.

**Why it's wrong:** `PROJECT.md`'s Key Decisions table is explicit that this is "a research spike (re-research before shipping), not a committed build" — the prior backtest was a documented no-go (10.35%/16.01% weekly-rolled MAPE vs. 9.49%/10.08% monthly-native), and even the two named follow-up experiments (SARIMAX/ETS at weekly cadence, Baltic-AN-source dedup) are unproven. Building schema/UI first inverts the project's own "research/backtest step before any model touches the UI" rule and risks a second unused table (`PriceRowWeekly`) sitting alongside `PriceRow` if the spike is another no-go.

**Do this instead:** Everything for this milestone stays inside `backend_research/run_weekly_candidates.py` and `results/weekly_candidates.json`. Only after a documented GO decision should a second, separate planning cycle scope the `PriceRowWeekly` table / dispatcher / UI work — and even then, note structurally that weekly mode can only ever cover HDAN/PPAN (no weekly Diesel/FX data exists at all, confirmed unchanged in `REPORT.md`), which breaks the existing "all 4 series forecast together" assumption baked into `forecast_all`'s single dispatcher, `SUMMARY_CARD_SERIES` (4 cards), and `FORECAST_SERIES_LABELS` (5 keys) — that's a UX decision to surface explicitly to the user before any weekly UI ships, not something to paper over.

## Integration Points

### Sentiment feature

| File | New or Modified | What changes |
|------|------------------|---------------|
| `backend_research/sentiment/sentiment_data_loader.py` | NEW | Loads/aligns `archive/*.csv` to monthly cadence |
| `backend_research/sentiment/run_sentiment_backtest.py` | NEW | Backtests adjustment value using existing `walk_forward.py` harness |
| `backend_research/sentiment/results/sentiment_backtest.json` | NEW | Frozen backtest output (source of truth for any constant later hard-coded into `app/`) |
| `app/app/sentiment.py` | NEW | Pure, zero-Reflex adjustment function(s) + `SENTIMENT_ADJUSTMENT_INFO` provenance constant — gated on the backtest above existing |
| `app/app/models.py` | MODIFY (additive) | New `SentimentDaily`/`SentimentMonthly` `rx.Model` table |
| `app/alembic/versions/` | NEW | Migration for the new table, via `reflex db migrate` |
| `app/app/seed_sentiment.py` | NEW | Standalone offline loader, mirrors `seed.py`'s own-session/never-wired-into-startup pattern |
| `app/app/state.py` | MODIFY (additive) | New computed var wrapping `forecast_results` + `sentiment.py`; new `load_sentiment_data()` read method alongside `load_rows()`; NO changes to existing `forecast_results`, `SERIES_ATTRS`, or `_history_df()` |
| `app/app/app.py` | MODIFY (additive) | New provenance line/toggle in `forecast_section()`, mirrors the existing `MODEL_INFO`-sourced model line in `summary_cards` |
| `app/app/forecasting.py` | UNTOUCHED | No changes — sentiment composes on the outside of `forecast_all`'s output, per Pattern 1 |

### Weekly research spike (this milestone)

| File | New or Modified | What changes |
|------|------------------|---------------|
| `backend_research/run_weekly_candidates.py` | MODIFY (extend) | Add SARIMAX/ETS weekly candidates per `REPORT.md`'s own named follow-up |
| `backend_research/results/weekly_candidates.json` | MODIFY (append) | New candidate results, same schema |
| `backend_research/REPORT.md` (or a new `REPORT-WEEKLY-2.md`) | MODIFY/NEW | Updated go/no-go recommendation |
| `app/app/forecasting.py`, `app/app/state.py`, `app/app/models.py`, `app/app/app.py` | UNTOUCHED | Zero changes during the spike, per Pattern 3 and Anti-Pattern 3 |

## Scaling Considerations

Not meaningfully applicable at this project's stated scale (single local user, occasional/roughly-monthly use — confirmed in `PROJECT.md`'s Context section). The relevant "scaling" axis for this milestone is data-volume/backtest-rigor, not concurrent users:

| Concern | This milestone | If ever multi-user/cloud (explicitly out of scope) |
|---------|-----------------|------------------------------------------------------|
| Sentiment table size | `news_sentiment_daily.csv` is 164 rows, `sentiment_market_panel.csv` 119 rows — trivial for SQLite | N/A |
| Backtest compute | Walk-forward re-fitting on ~200-row monthly series is seconds-scale, matches existing `backend_research/` runtime | N/A |
| Weekly cadence row count | `AN Data.csv` native-weekly rows (~7-day spacing) roughly 4x monthly row count — still trivial for SQLite/pandas | N/A |

## Integration Points — External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| None (this milestone) | `archive/` is a static, already-downloaded CSV snapshot (NewsAPI + yfinance, per `archive/README.md`), not a live API | Live news/API ingestion is explicitly out of scope per `PROJECT.md` ("Automatic API data-fetch from external price sources... is a future milestone, not v1") — this milestone works from the static archive only |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `sentiment.py` ↔ `forecasting.py` | `sentiment.py` imports `forecasting.py`'s output SHAPE convention only (the `{"base","bull","bear"}` dict) — no import of `forecasting.py`'s internals, no reverse dependency | Keeps `forecasting.py` frozen/untouched, satisfies Pattern 1 |
| `sentiment.py` ↔ `state.py` | `state.py` calls `sentiment.py` functions the same way it calls `forecast_all` — plain function call, plain DataFrame/dict in, plain dict out | Mirrors the existing `forecasting.py` ↔ `state.py` boundary exactly (D-08's zero-Reflex-in-forecasting.py contract) |
| `backend_research/sentiment/` ↔ `app/app/sentiment.py` | One-way, offline → frozen constant. Backtest code is NEVER imported by `app/` (mirrors `forecasting.py`'s existing relationship to `backend_research/`) | `arch`-style "SUS flag was a false positive but still isolated to research" precedent (see STATE.md) — keep research-only deps (if any, e.g. a VADER re-score) out of `app/requirements.txt` |
| `seed_sentiment.py` ↔ SQLite | Own `sqlmodel`/`rx.Model` session, run manually, never during app boot | Mirrors `seed.py`'s exact precedent — the one pre-existing exception to "state.py is the sole session boundary," not a new violation |

## Sources

- `app/app/forecasting.py` (read in full) — HIGH confidence, current source of truth for all model/provenance/spread logic
- `app/app/state.py` (read in full) — HIGH confidence, current source of truth for the DB boundary, computed vars, and dispatch pattern
- `app/app/models.py`, `app/app/seed.py` (read) — HIGH confidence, schema and offline-ingestion precedent
- `app/app/app.py` (partial read, `forecast_section`/`historical_section`/tab-match structure) — HIGH confidence on the tab-switching pattern new UI must slot into
- `.planning/PROJECT.md` — HIGH confidence, authoritative milestone scope/constraints/key-decisions source
- `backend_research/REPORT.md` (Weekly cadence section, full text) — HIGH confidence, verified prior weekly no-go backtest numbers (10.35%/16.01% vs. 9.49%/10.08% MAPE) and the two named follow-up experiments
- `backend_research/REPORT-PHASE2.md` — HIGH confidence, verified the causality-screen methodology to reuse for sentiment relevance testing, and confirmed sentiment/Delphi-style methods were explicitly out of Phase 2's backtestable scope ("This is the mechanism REQUIREMENTS.md already reserves for v2's live news/sentiment-driven bull/bear adjustment")
- `archive/README.md` + direct CSV header/row inspection (`news_sentiment_daily.csv`, `sentiment_market_panel.csv`, `ml_features.csv`, `market_prices.csv`) — HIGH confidence finding: this dataset is US-equity-market (SPY/QQQ/DIA/VIX) sentiment, not commodity/FX-specific — the single most important finding for scoping the sentiment research phase correctly
- `.planning/STATE.md` (tail) — HIGH confidence, confirmed no sentiment/weekly implementation has started yet in this milestone, and confirmed the `arch` package precedent for isolating research-only dependencies

---
*Architecture research for: Prediction Dashboard v2.0 (News/Sentiment Scenarios & Weekly Forecast Research)*
*Researched: 2026-08-31*
