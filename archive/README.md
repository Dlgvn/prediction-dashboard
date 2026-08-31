
# Financial News Sentiment vs Markets
Daily NLP sentiment scores from NewsAPI headlines correlated against S&P 500, NASDAQ, and VIX.
Updated: 2026-08-23

## Sentiment Scoring Methodology
Each article is scored with VADER on `title + description`. Compound range: −1.0 (most negative) to +1.0.
High-credibility sources (Reuters, Bloomberg, WSJ, FT, CNBC) receive a 1.5× source weight
in the `weighted_compound` daily aggregate.

| Threshold | Category |
|-----------|----------|
| compound ≥ 0.05 | positive |
| compound ≤ −0.05 | negative |
| else | neutral |

## Files

### news_sentiment_raw.csv
| Column | Type | Description |
|--------|------|-------------|
| date | date | Publication date (YYYY-MM-DD) |
| published_at | datetime | Raw UTC timestamp |
| source | str | News outlet name |
| topic | str | Query category: markets / policy / volatility / inflation / earnings / recession / growth |
| title | str | Article headline |
| description | str | Article lede |
| url | str | Direct link |
| compound | float | VADER compound score (−1.0 to 1.0) |
| pos | float | VADER positive ratio |
| neg | float | VADER negative ratio |
| neu | float | VADER neutral ratio |
| sentiment_cat | str | positive / negative / neutral |
| source_weight | float | 1.5 for high-credibility sources, 1.0 otherwise |

### news_sentiment_daily.csv
| Column | Type | Description |
|--------|------|-------------|
| date | date | Trading date |
| article_count | int | Number of articles that day |
| mean_compound | float | Simple mean VADER compound score |
| median_compound | float | Median compound score |
| std_compound | float | Standard deviation of compound |
| min_compound / max_compound | float | Min/max compound scores |
| pct_negative / pct_positive | float | Fraction of articles in each category |
| weighted_compound | float | Source-credibility weighted compound score |
| sent_ema3 / sent_ema10 | float | 3- and 10-day exponential moving averages |
| sent_momentum | float | sent_ema3 − sent_ema10 (MACD-style signal) |
| dominant_sentiment | str | positive / negative / neutral |

### market_prices.csv
| Column | Type | Description |
|--------|------|-------------|
| date | date | Trading date |
| spy_open/high/low/close | float | SPY adjusted OHLC prices |
| spy_volume | int | SPY daily volume |
| spy_return_1d | float | SPY daily % return |
| spy_gap_pct | float | Overnight gap vs prior close, % |
| spy_range_pct | float | High-low range as % of prior close |
| spy_return_5d / spy_return_20d | float | 5-day and 20-day rolling % returns |
| [same columns for qqq_, dia_] | | |
| vix_close | float | VIX daily close |
| vix_pct_chg | float | VIX daily % change |
| market_direction | int | +1 up day, −1 down day, 0 flat (based on SPY) |

### sentiment_market_panel.csv
Primary analysis file — all sentiment + market columns merged by date.
Additional columns:
| Column | Type | Description |
|--------|------|-------------|
| spy_return_next1d | float | SPY T+1 % return (primary target) |
| spy_up_next1d | int | 1 if SPY up on T+1, else 0 |
| vix_regime | str | low / normal / elevated / extreme |
| sent_quantile_60d | float | Percentile rank in trailing 60-day sentiment dist |
| rolling_corr_60d | float | Rolling 60-day Pearson r between sentiment and SPY |

### ml_features.csv
ML-ready version of the panel with engineered features and targets.
Key added columns:
| Column | Type | Description |
|--------|------|-------------|
| sent_compound_L1–L5 | float | Lagged mean_compound, 1–5 days |
| sent_neg_pct_L1–L5 | float | Lagged pct_negative, 1–5 days |
| sent_momentum_L1–L5 | float | Lagged sent_momentum, 1–5 days |
| sent_rolling_mean_5/10/20d | float | Rolling mean compound |
| sent_rolling_std_5/10/20d | float | Rolling std of compound |
| neg_pct_rolling_5/10/20d | float | Rolling mean of pct_negative |
| spy_return_L1/L2/L3 | float | Lagged SPY daily returns |
| vix_L1 / vix_change_1d | float | Lagged VIX and daily change |
| vix_regime_code | int | Numeric encoding: 0=low 1=normal 2=elevated 3=extreme |
| sent_x_vix | float | Interaction: sentiment × VIX (fear-amplified) |
| sent_x_article_count | float | Interaction: sentiment × article volume |
| article_count_zscore | float | Article count z-score vs trailing 20-day mean |
| day_of_week | int | 0=Monday … 4=Friday |
| sent_sign_change | int | 1 if sentiment flipped direction vs prior day |
| spy_return_next1d | float | **Regression target**: next-day SPY % return |
| spy_up_next1d | int | **Classification target**: 1 if SPY up next day |

## Sources
- **NewsAPI** (newsapi.org): financial and economic headlines, last 28 days per run, 8 queries
- **Yahoo Finance** (via yfinance): SPY, QQQ, DIA adjusted OHLCV; VIX close — 2020–present
- **VADER**: Hutto & Gilbert (2014) rule-based sentiment for social/news text — vaderSentiment library

## Complements
Designed to pair with:
- US Recession Probability Tracker dataset
- Global Inflation vs Interest Rates dataset
- Global AI Layoffs & Job Market dataset

## License
CC0 — Public Domain
