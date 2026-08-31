# Phase 16: Sentiment Data Sufficiency & Causality Research - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-31
**Phase:** 16-Sentiment Data Sufficiency & Causality Research
**Areas discussed:** Go/no-go strictness, Small-N floor, Sentiment feature scope

---

## Go/no-go strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Stricter than existing pipeline | Require p<0.05 only, given domain-mismatch risk | |
| Same bar as existing predictors | Reuse p<0.10 exactly as causality_screen.py does | ✓ |
| Require corroboration beyond p-value | p<0.05 AND multiple lags/features | |

**User's choice:** Same bar as existing predictors (p<0.05/p<0.10 tiers, unchanged).

| Option | Description | Selected |
|--------|-------------|----------|
| Per-series | Report go/no-go independently for HDAN/PPAN/Diesel-USD/FX | ✓ |
| Global (any series) | Single go/no-go across all four | |

**User's choice:** Per-series.

| Option | Description | Selected |
|--------|-------------|----------|
| Single lag is enough | Matches shortlist_for()'s best-lag pattern | ✓ |
| Require 2+ lags | More robust, more implementation work | |

**User's choice:** Single lag is enough.

| Option | Description | Selected |
|--------|-------------|----------|
| P-value alone is sufficient | No sign/directional check, matches existing pipeline | ✓ |
| Require a directionally sensible sign | Extra sanity check given sentiment's noise risk | |

**User's choice:** P-value alone is sufficient.

| Option | Description | Selected |
|--------|-------------|----------|
| Out of scope | Diesel-MNT follows Diesel-USD/FX results, no separate test | ✓ |
| Report it separately too | Explicit Diesel-MNT row for completeness | |

**User's choice:** Out of scope (matches forecasting.py's existing derived-series pattern).

**Notes:** User accepted all recommended options for this area — no deviation from the
existing causality_screen.py pipeline's established conventions.

---

## Small-N floor

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse MIN_GRANGER_N=24 | One consistent floor across the whole pipeline | ✓ |
| Stricter floor for sentiment specifically | e.g. 36, given known thin coverage | |

**User's choice:** Reuse MIN_GRANGER_N=24.

| Option | Description | Selected |
|--------|-------------|----------|
| Drop zero-article months | Honest reflection of sparsity, shrinks effective N | ✓ |
| Forward-fill from last known score | Keeps series continuous, risks staleness/leakage | |

**User's choice:** Drop zero-article months.

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate no-go, skip the test | Matches causality_screen.py's "insufficient overlap" skip | ✓ |
| Run it anyway, flag as unreliable | More raw information, risk of over-trusting a flagged number | |

**User's choice:** Immediate no-go, skip the test.

**Notes:** User accepted all recommended options — consistent with keeping the sentiment
screen mechanically identical to the existing predictor screen wherever possible.

---

## Sentiment feature scope

| Option | Description | Selected |
|--------|-------------|----------|
| Raw/weighted sentiment score | weighted_compound | ✓ |
| Sentiment trend/momentum | sent_ema3, sent_ema10, sent_momentum | ✓ |
| VIX-derived macro risk regime | vix_regime | ✓ |

**User's choice:** All three feature families (multiSelect).

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, exclude them | rolling_corr_60d and equity return-target columns are archive-purpose artifacts | ✓ |
| Include them too | Test everything, let the screen decide relevance | |

**User's choice:** Yes, exclude them.

**Notes:** None.

---

## Claude's Discretion

- Exact daily-to-monthly resampling method (mean vs. median) — mean chosen as the
  standard default, to be noted explicitly in the phase's research output.
- Report file naming/location — follows the existing `backend_research/REPORT*.md` +
  `results/*.json` convention.
- Timezone handling (UTC `published_at` vs. Mongolia UTC+8) — a correctness detail
  handled per PITFALLS.md guidance (extend `walk_forward.py`'s `LeakageError` guard),
  not surfaced as a product decision.

## Deferred Ideas

None — discussion stayed within phase scope.
