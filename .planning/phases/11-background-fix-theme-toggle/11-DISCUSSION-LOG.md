# Phase 11: Background Fix + Theme Toggle - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-24
**Phase:** 11-background-fix-theme-toggle
**Areas discussed:** Persistence mechanism, default appearance, dark palette approach, toggle placement

---

## Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Browser localStorage | Simple, client-side, no DB schema change | ✓ |
| Server-side AppSetting DB row | Mirrors markup_pct pattern, survives cross-machine | |

**User's choice:** Browser localStorage.

---

## Default appearance

| Option | Description | Selected |
|--------|-------------|----------|
| Always default to light | Predictable, avoids reintroducing the OS-inheritance bug | ✓ |
| Respect OS preference on first load | Nicer first-run UX, more risk if detection is wrong | |

**User's choice:** Always default to light.

---

## Dark palette approach

| Option | Description | Selected |
|--------|-------------|----------|
| Bespoke dark palette, kept minimal | Hand-picked colors, restrained like the light system | ✓ |
| Mechanical inversion of existing tokens | Faster, but may need separate contrast tuning anyway | |

**User's choice:** Bespoke minimal dark palette.

---

## Toggle placement

| Option | Description | Selected |
|--------|-------------|----------|
| Top of the page, near the title | Standard convention, always visible | ✓ |
| Somewhere else | Not specified | |

**User's choice:** Header, near the title.

---

## Claude's Discretion

- Exact dark hex values, WCAG-verified per Phase 6's contrast measurement discipline.
- Toggle control's icon/visual treatment.
- Exact Reflex 0.9.8 runtime appearance-toggle API — verify during research, don't assume.

## Deferred Ideas

None beyond phase boundary (nav bar is Phase 14).
