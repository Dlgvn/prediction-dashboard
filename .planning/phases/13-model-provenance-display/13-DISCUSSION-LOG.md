# Phase 13: Model Provenance Display - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 13-model-provenance-display
**Areas discussed:** Diesel MNT label, placement, accuracy wording

---

## Diesel MNT label

| Option | Description | Selected |
|--------|-------------|----------|
| "Derived (Diesel USD × FX)" | Honest about being computed, not fitted | ✓ |
| Show underlying models combined ("Naive + Naive") | Technically accurate but redundant/confusing | |

**User's choice:** "Derived (Diesel USD × FX)".

---

## Placement

| Option | Description | Selected |
|--------|-------------|----------|
| New line on existing summary cards | Consistent with Phase 8's high/low and YoY pattern | ✓ |
| Near the fan chart instead | Caption for the currently-selected series | |

**User's choice:** New line on summary cards.

---

## Accuracy wording

| Option | Description | Selected |
|--------|-------------|----------|
| Plain MAPE percentage | Simple, matches existing numeric-first style | ✓ |
| Qualitative label ("High confidence") | Avoids "MAPE" but needs new tier definitions | |

**User's choice:** Plain MAPE percentage.

---

## Claude's Discretion

- Exact copy wording and line ordering.
- Where in the card stack the new line sits (append at end, after YoY).

## Deferred Ideas

- AI-generated "drivers" explanation — already out of scope per v1.2 REQUIREMENTS.md.
- Full model diagnostics (AIC/BIC, residuals) — anti-feature per research.
