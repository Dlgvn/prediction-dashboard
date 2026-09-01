# Phase 16: Sentiment Data Sufficiency & Causality Screen — Research Report

Generated deterministically by `backend_research/sentiment/run_sentiment_causality_screen.py` from `backend_research/results/sentiment_causality_screen.json`. This is SENT-01/SENT-02's deliverable: a per-series go/no-go verdict for whether monthly news sentiment Granger-causes each tracked price series, with the effective monthly sample size stated explicitly. A "no-go" verdict is a complete and valid outcome of this screen, not a failure to fix.

## Go/No-Go at a glance

| Series | Verdict | Max effective monthly N | Floor (MIN_GRANGER_N) | Qualifying predictors |
|---|---|---|---|---|
| HDAN | no-go | 14 | 24 | — |
| PPAN | no-go | 14 | 24 | — |
| Diesel-USD | no-go | 19 | 24 | — |
| FX rate | no-go | 19 | 24 | — |

Diesel-MNT has no row above because it is a derived series (Diesel-USD x FX rate x markup) whose sentiment status follows from the Diesel-USD and FX rate rows, per D-04 — it is never screened as its own go/no-go target.

## Effective monthly sample size

| Series | Effective monthly N | Floor | Clears floor? |
|---|---|---|---|
| HDAN | 14 | 24 | no |
| PPAN | 14 | 24 | no |
| Diesel-USD | 19 | 24 | no |
| FX rate | 19 | 24 | no |

Coverage context (NOT sample size): the underlying sentiment archive covers 20 distinct months with 8410 total articles. This raw article/month count is context only and must not be read as the effective monthly sample size — the number that actually matters for a monthly Granger test is the overlap between sentiment coverage and each target's price history after the lag shift, reported in the table above.

## Methodology

- **Targets (D-04)**: the four live `PriceRow` series — HDAN, PPAN, Diesel-USD, FX rate — loaded via `db_loader.load_price_history()` and percent-changed via `db_loader.pct_change_frame()` for stationarity. Never equities.
- **Sentiment predictors as levels**: the five sentiment predictors enter as monthly LEVELS and are deliberately NOT percent-changed — `weighted_compound` is bounded in [-1, 1] and crosses zero, so a percent-change transform on it produces sign flips and `inf` values.
- **UTC+8 correction**: the monthly `weighted_compound` series is rebuilt from `archive/news_sentiment_raw.csv`'s raw `published_at` article timestamps, corrected to Mongolia local time (UTC+8), because `archive/news_sentiment_daily.csv`'s date-only column has already been bucketed to a UTC calendar day and cannot be timezone-corrected after the fact.
- **Month-unit EMAs**: `sent_ema3`, `sent_ema10` and `sent_momentum` are EMAs computed on the monthly `weighted_compound` series itself (month-unit spans) and therefore intentionally do NOT match a naive resample of the archive's day-unit EMA columns.
- **vix_regime_code**: the numeric `vix_regime_code` column is used, never the string `vix_regime` column, and is bucketed on its own US trading-day calendar with no UTC+8 shift applied (it is not article-publication-timestamped data).
- **Zero-article months (D-06)**: months with zero articles are dropped from the sentiment frame, never forward-filled or interpolated.
- **Monthly aggregation**: the monthly `weighted_compound` value is a source-credibility-weighted mean per the archive's documented formula.
- **Statistical bar (D-01, D-05)**: the p<0.05 / p<0.10 tiers and the `MIN_GRANGER_N = 24` floor are imported unchanged from `causality_screen.py` — never redefined here — so the sentiment screen's bar is identical to every other predictor's bar.
- **Best-lag qualification (D-02, D-03)**: a predictor qualifies at its single best (lowest-p) lag among 1-3, with no directional or sign filter applied — tier alone decides.
- **Insufficient overlap (D-07)**: below-`MIN_GRANGER_N` combinations are recorded with `note: "insufficient overlap"` and the F-test is not run, as a branch computed on the measured effective monthly N.

## Per-series detail

### HDAN — Go/No-Go: no-go

insufficient sample size (max effective monthly N = 14, floor MIN_GRANGER_N = 24).

| Predictor | Lag | N | p-value | Tier | Note |
|---|---|---|---|---|---|
| sent_ema10 | 1 | 14 | — | ns | insufficient overlap |
| sent_ema10 | 2 | 13 | — | ns | insufficient overlap |
| sent_ema10 | 3 | 12 | — | ns | insufficient overlap |
| sent_ema3 | 1 | 14 | — | ns | insufficient overlap |
| sent_ema3 | 2 | 13 | — | ns | insufficient overlap |
| sent_ema3 | 3 | 12 | — | ns | insufficient overlap |
| sent_momentum | 1 | 14 | — | ns | insufficient overlap |
| sent_momentum | 2 | 13 | — | ns | insufficient overlap |
| sent_momentum | 3 | 12 | — | ns | insufficient overlap |
| vix_regime_code | 1 | 14 | — | ns | insufficient overlap |
| vix_regime_code | 2 | 13 | — | ns | insufficient overlap |
| vix_regime_code | 3 | 12 | — | ns | insufficient overlap |
| weighted_compound | 1 | 14 | — | ns | insufficient overlap |
| weighted_compound | 2 | 13 | — | ns | insufficient overlap |
| weighted_compound | 3 | 12 | — | ns | insufficient overlap |

### PPAN — Go/No-Go: no-go

insufficient sample size (max effective monthly N = 14, floor MIN_GRANGER_N = 24).

| Predictor | Lag | N | p-value | Tier | Note |
|---|---|---|---|---|---|
| sent_ema10 | 1 | 14 | — | ns | insufficient overlap |
| sent_ema10 | 2 | 13 | — | ns | insufficient overlap |
| sent_ema10 | 3 | 12 | — | ns | insufficient overlap |
| sent_ema3 | 1 | 14 | — | ns | insufficient overlap |
| sent_ema3 | 2 | 13 | — | ns | insufficient overlap |
| sent_ema3 | 3 | 12 | — | ns | insufficient overlap |
| sent_momentum | 1 | 14 | — | ns | insufficient overlap |
| sent_momentum | 2 | 13 | — | ns | insufficient overlap |
| sent_momentum | 3 | 12 | — | ns | insufficient overlap |
| vix_regime_code | 1 | 14 | — | ns | insufficient overlap |
| vix_regime_code | 2 | 13 | — | ns | insufficient overlap |
| vix_regime_code | 3 | 12 | — | ns | insufficient overlap |
| weighted_compound | 1 | 14 | — | ns | insufficient overlap |
| weighted_compound | 2 | 13 | — | ns | insufficient overlap |
| weighted_compound | 3 | 12 | — | ns | insufficient overlap |

### Diesel-USD — Go/No-Go: no-go

insufficient sample size (max effective monthly N = 19, floor MIN_GRANGER_N = 24).

| Predictor | Lag | N | p-value | Tier | Note |
|---|---|---|---|---|---|
| sent_ema10 | 1 | 19 | — | ns | insufficient overlap |
| sent_ema10 | 2 | 18 | — | ns | insufficient overlap |
| sent_ema10 | 3 | 17 | — | ns | insufficient overlap |
| sent_ema3 | 1 | 19 | — | ns | insufficient overlap |
| sent_ema3 | 2 | 18 | — | ns | insufficient overlap |
| sent_ema3 | 3 | 17 | — | ns | insufficient overlap |
| sent_momentum | 1 | 19 | — | ns | insufficient overlap |
| sent_momentum | 2 | 18 | — | ns | insufficient overlap |
| sent_momentum | 3 | 17 | — | ns | insufficient overlap |
| vix_regime_code | 1 | 19 | — | ns | insufficient overlap |
| vix_regime_code | 2 | 18 | — | ns | insufficient overlap |
| vix_regime_code | 3 | 17 | — | ns | insufficient overlap |
| weighted_compound | 1 | 19 | — | ns | insufficient overlap |
| weighted_compound | 2 | 18 | — | ns | insufficient overlap |
| weighted_compound | 3 | 17 | — | ns | insufficient overlap |

### FX rate — Go/No-Go: no-go

insufficient sample size (max effective monthly N = 19, floor MIN_GRANGER_N = 24).

| Predictor | Lag | N | p-value | Tier | Note |
|---|---|---|---|---|---|
| sent_ema10 | 1 | 19 | — | ns | insufficient overlap |
| sent_ema10 | 2 | 18 | — | ns | insufficient overlap |
| sent_ema10 | 3 | 17 | — | ns | insufficient overlap |
| sent_ema3 | 1 | 19 | — | ns | insufficient overlap |
| sent_ema3 | 2 | 18 | — | ns | insufficient overlap |
| sent_ema3 | 3 | 17 | — | ns | insufficient overlap |
| sent_momentum | 1 | 19 | — | ns | insufficient overlap |
| sent_momentum | 2 | 18 | — | ns | insufficient overlap |
| sent_momentum | 3 | 17 | — | ns | insufficient overlap |
| vix_regime_code | 1 | 19 | — | ns | insufficient overlap |
| vix_regime_code | 2 | 18 | — | ns | insufficient overlap |
| vix_regime_code | 3 | 17 | — | ns | insufficient overlap |
| weighted_compound | 1 | 19 | — | ns | insufficient overlap |
| weighted_compound | 2 | 18 | — | ns | insufficient overlap |
| weighted_compound | 3 | 17 | — | ns | insufficient overlap |

## What would change this result

Reaching a real (non-`ns`) tier for any target would require continuous, commodity/FX-relevant sentiment coverage spanning at least 24 overlapping months with each target's price history — substantially denser and longer than the current archive. Building that additional data collection pipeline is out of scope for v2.0. Re-running `run_sentiment_causality_screen.py` after any future archive refresh recomputes every verdict above automatically, so a denser archive would surface a real finding without any code change.
