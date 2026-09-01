# Phase 22: Weekly Granularity Toggle & UI - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Source:** Direct user Q&A (2 targeted questions on the open UI decisions research flagged)
plus milestone-level research (FEATURES.md/PITFALLS.md) for everything else. This is a UI
phase (`UI hint: yes` in ROADMAP.md), so unlike Phases 19-21 this one did involve user
input on the genuinely open visual/placement decisions.

<domain>
## Phase Boundary

The final phase of v2.1. Depends on Phase 21 (weekly forecasting module) — this phase
cannot be planned in full/executed until Phase 21's exact function signatures
(`forecast_all_weekly`, `WEEKLY_MODEL_INFO`) land, though context-gathering and research
can proceed in parallel. Delivers the user-facing granularity toggle, wiring Phase 21's
weekly forecasts into the existing Summary/Forecast tabs alongside the current monthly
view — never replacing it.
</domain>

<decisions>
## User-decided (this session)

- **Toggle placement**: Next to the existing horizon selector, in the Forecast tab —
  `horizon_control()` in `app/app/app.py` (lines ~277-308) is the existing component to
  extend/sit beside. The horizon control and granularity toggle are closely related
  (horizon *range* changes depending on granularity — 1-12 months vs. up to 5 weeks per
  Phase 21's `MAX_HORIZON_WEEKLY`), so they belong together, not scattered across tabs.
- **Diesel-USD/Diesel-MNT weekly-mode treatment**: Grayed-out/dimmed card stays in its
  normal grid position, showing the last-known monthly forecast values visually muted, with
  a small badge/label explaining "Monthly data only" (or similar wording). NOT a blank
  placeholder with no numbers, and NOT hidden entirely — the card's presence and its
  (dimmed) monthly numbers make clear this series simply doesn't have weekly granularity,
  rather than looking broken or making the user wonder where it went.

## Locked from milestone-level research (FEATURES.md, PITFALLS.md, SUMMARY.md)

- Single **global** Monthly/Weekly toggle — one state var drives both the Forecast tab
  chart AND the Summary tab cards together. No per-series toggles (explicitly an
  anti-feature — "two reading speeds on one screen").
- Toggle **persists** across reload/visit — reuse the exact mechanism `DashboardState`
  already uses for `theme_mode` persistence (its own localStorage-style key, per Phase 11's
  precedent — check `state.py` for the exact pattern: likely `rx.Cookie` or a
  `LocalStorage`-backed Var, or an `AppSetting` DB row like `markup_pct`).
- Default stays **Monthly** — Weekly is opt-in, never auto-selected even though some weekly
  models are more accurate than their monthly counterparts (explicit anti-feature per
  FEATURES.md: "Auto-defaulting to Weekly mode 'because it's more accurate' removes user
  agency").
- Weekly horizon is denominated in **weeks**, capped to whatever Phase 21's
  `MAX_HORIZON_WEEKLY` constant turns out to be (research flagged this as validated up to
  5 weeks, per the backtest's `horizon=5` — confirm the actual constant name/value from
  Phase 21's finished code before wiring the slider's max).
- Each weekly-capable series' (HDAN/PPAN/FX) summary card must show the **correct weekly
  model name + MAPE** when in Weekly mode — read from Phase 21's `WEEKLY_MODEL_INFO`, not
  a stale monthly `MODEL_INFO` figure. This is the same card component already showing
  `MODEL_INFO`-derived text for monthly (see `summary_cards()`/wherever the existing
  provenance line renders) — branch its data source on the granularity state var, don't
  build a parallel card component.
- Weekly forecast chart/table dates must be **real week-ending dates**, not monthly ticks
  relabeled — the x-axis/date column should come from the actual `WeeklyPriceRow`/weekly
  forecast index, which already carries real dates (Phase 19/21 produce genuinely
  weekly-dated data, so this should fall out naturally from correctly wiring the data
  source rather than needing special date-formatting logic — but verify the existing chart
  component doesn't hardcode a monthly date-format assumption anywhere).
- Should-have (not required, but cheap and recommended if time allows): fold the
  weekly-vs-monthly MAPE delta into the provenance line itself (e.g.
  "7.25% MAPE weekly · 9.49% monthly") rather than a separate comparison widget — the
  numbers already exist in `WEEKLY_MODEL_INFO`/`MODEL_INFO`, this is a string-formatting
  choice, not new data plumbing.

## Non-goals (explicit, per REQUIREMENTS.md v2.1+ Deferred section)

- No weekly Data Entry UI — the existing monthly Data Entry tab is completely unaffected
  and unchanged by this phase.
- No per-series granularity override.
- No horizon extension beyond what Phase 21 actually validated.
- No changes to the existing monthly Forecast/Summary rendering when Monthly is selected —
  this phase is additive; Monthly mode's current behavior must be pixel-identical to today
  post-implementation (regression risk to watch).

## Claude's Discretion

- Exact Reflex component choice for the toggle itself (`rx.segmented_control`, `rx.switch`,
  `rx.tabs`, or a styled `rx.hstack` of two buttons) — match the existing design system's
  established look (check `app/app/theme.py`'s tokens and how the existing dark/light
  toggle or tab bar is implemented, for visual consistency).
- Exact wording of the Diesel "Monthly data only" badge — keep it short, non-alarming (this
  is expected behavior, not an error state).
- Whether granularity state lives as a new `DashboardState` var or is grouped with the
  existing `horizon_months`/theme-mode vars — executor's call on organization, but must
  follow whatever persistence pattern `theme_mode` already established (per the locked
  decision above).
- Exact grid/layout mechanics for keeping Diesel's card in its normal position while dimmed
  — CSS opacity/color-token approach, informed by `theme.py`'s existing muted/disabled
  token vocabulary if one exists.

## Deferred Ideas

None raised beyond what's already tracked in REQUIREMENTS.md's v2.1+ Deferred section.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` (Phase 22 section) — goal, success criteria, WKUI-03..08
- `.planning/REQUIREMENTS.md` (WKUI-03 through WKUI-08) — requirement text
- `.planning/research/FEATURES.md` — table stakes/anti-features for the toggle, honest
  Diesel state, horizon units, provenance behavior (all four of this phase's open design
  questions were already answered there at the milestone level; this session's user Q&A
  covered only the two items FEATURES.md left as implementation-level, not design-level,
  open — toggle placement and Diesel's exact visual treatment)
- `.planning/research/PITFALLS.md` — Pitfall 5 (monthly-only series mis-rendering — the
  single most consequential pitfall for this phase)
- `.planning/research/SUMMARY.md` — Phase D synthesis
- `app/app/app.py` — `horizon_control()` (lines ~277-308, the component this phase extends
  alongside), wherever `summary_cards()`/forecast chart/table rendering lives — read the
  full file before planning
- `app/app/state.py` — `DashboardState`, existing `theme_mode` persistence pattern to mirror
  for the new granularity state var, existing `horizon_months`/`set_horizon`
- `app/app/theme.py` — design tokens, muted/disabled color vocabulary if one exists
- Phase 21's finished `app/app/forecasting.py` additions (once complete) —
  `forecast_all_weekly`, `WEEKLY_MODEL_INFO`, `MAX_HORIZON_WEEKLY` — this phase's plan
  cannot be finalized against exact signatures until Phase 21 lands
</canonical_refs>
