# Feature Research

**Domain:** Mixed-cadence (weekly + monthly) financial/commodity forecast dashboard UI
**Researched:** 2026-09-01
**Confidence:** MEDIUM (project-specific reasoning HIGH; general mixed-cadence dashboard UX patterns MEDIUM — thin authoritative literature on this exact niche, corroborated by one Qlik community pattern and general dashboard-cadence guidance)

## Context

This is a narrow, well-scoped addition: a **granularity toggle** (Monthly/Weekly) on an existing, already-shipped Forecast tab and Summary cards. The backend work is done and validated (`backend_research/REPORT-WEEKLY.md`, go verdict, HDAN 7.25%/PPAN 6.96% weekly MAPE vs 9.49%/10.08% monthly benchmark; FX weekly source confirmed available via `FX Data.csv`'s Weekly column). This milestone is forecast-**viewing** only — no new weekly data-entry UI. Scope is deliberately small: 3 of 5 series (HDAN, PPAN, FX) get weekly; 2 (Diesel-USD, derived Diesel-MNT) stay monthly-only, permanently, because no weekly source data exists for them.

General industry guidance on cadence toggles (from research) reinforces one core principle directly applicable here: **don't mix cadences within a single reading — pick the dominant tempo per view and be explicit about what's shown.** ("The classic mistake is mixing the modes on one screen... forces two reading speeds at once, and neither gets served well.") This directly informs the recommendation below on how to handle the 2 monthly-only series inside an otherwise weekly view, and on the horizon-units question.

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist once a granularity toggle exists at all. Missing these makes the toggle feel broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Monthly/Weekly toggle control on the Forecast tab, applying to both the fan chart and Summary cards together | A toggle that only half-applies (e.g., chart switches but cards don't) breaks the mental model that "granularity" is one dashboard-wide state, not two independent settings | LOW | Single `rx.State` var (e.g. `granularity: str = "monthly"`) read by both Forecast tab and Summary cards; existing tab-nav pattern (v1.3) already establishes cross-component shared state conventions to extend |
| Toggle state persists for the session (and ideally across reloads, matching the existing dark/light persistence pattern) | User picked weekly once, expects it to stay weekly while navigating; re-picking every page load is friction the app has already trained users out of via the persisted theme toggle | LOW | Reuse the exact persistence mechanism already built for the dark/light toggle (v1.3) — same pattern, different key |
| Explicit "monthly only" state for Diesel-USD and Diesel-MNT when Weekly is selected — never hidden, never silently showing stale/faked weekly-looking data | Silently dropping 2 of 5 cards when switching modes reads as a bug ("where did diesel go?"); faking a weekly number by resampling/interpolating monthly data would misrepresent model confidence the project has been explicit about maintaining (provenance/MAPE display is already a shipped feature) | LOW-MEDIUM | Render the card in a disabled/muted state with a clear label ("Monthly only — no weekly data source") rather than omitting it from the grid; keeps card count/layout stable across toggle switches |
| Model provenance line (name + backtested MAPE) updates to reflect the currently-selected granularity's model, not a stale monthly figure shown under a weekly toggle | The provenance feature exists specifically for trust/transparency (v1.3 decision); showing monthly MAPE next to weekly forecast values would be actively misleading, worse than not having provenance at all | LOW | Provenance already reads from a per-series model-metadata source; add a granularity key to that lookup (e.g. `{HDAN: {monthly: {...}, weekly: {...}}}`) rather than a parallel code path |
| Horizon control adapts its unit/range to the selected granularity (weeks when Weekly is selected, not a re-labeled month picker) | A "1-12" horizon slider that silently means "months" in one mode and "weeks" in another (without changing its label/scale) will produce forecasts 4x shorter or longer than the user intends when they don't notice the mode switch | LOW-MEDIUM | See dedicated discussion below (horizon expressed in weeks vs month-equivalent) — this is the one design question genuinely worth deciding deliberately, not just building |
| Chart x-axis and fan-chart date labeling reflect true weekly dates (not monthly labels relabeled) when in Weekly mode | Users comparing the chart to real calendar weeks (e.g. "is that the forecast for the week of the 15th?") need real week-ending dates, not synthetic labels | LOW | Existing fan chart already takes a date-indexed series; feed it the weekly date index instead of monthly when in Weekly mode — no new charting capability needed, same Plotly component |

### Differentiators (Competitive Advantage)

Not required for this milestone to feel complete, but add real value within the existing scope. None of these should block the core toggle ship.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side accuracy callout when switching to Weekly ("Weekly model: 7.25% MAPE vs Monthly: 9.49% MAPE — weekly is more accurate for HDAN") | Directly answers the "why would I ever pick weekly over monthly" question with the exact number the backend research already produced; turns an obscure backtest result into a user-facing selling point for the new mode | LOW | Purely presentational — the numbers already exist in `REPORT-WEEKLY.md`/the model-metadata table; this is a copy/formatting decision, not new computation. Recommended: fold into the provenance line itself (see provenance section below) rather than a separate callout component, to avoid clutter |
| Deep-link/URL query param for granularity (e.g. `?granularity=weekly`) so the toggle state is shareable/bookmarkable | Nice for a power user who always wants weekly HDAN pulled up; low cost given Reflex's routing supports this | LOW | Purely additive; skip if it doesn't fit Reflex's existing routing conventions cheaply — not worth introducing a new pattern just for this milestone |
| Per-series granularity override within Weekly mode is explicitly NOT this — see anti-features. Listed here only to note what a "richer" version could look like if ever revisited | — | — | Deliberately not recommending for this milestone |

### Anti-Features (Commonly Requested, Often Problematic)

Features that would seem like natural extensions of "add weekly mode" but should be avoided this milestone.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Per-series granularity picker (e.g. HDAN weekly, PPAN monthly, FX weekly, mixed within one view) | Feels flexible — "let the user choose per card" | Reintroduces exactly the "two reading speeds on one screen" problem general dashboard-cadence guidance warns against; also multiplies state combinations (2^3 for the weekly-eligible series alone) for a single-user app where a global toggle already satisfies the actual need | One global Monthly/Weekly toggle affecting all cards at once; monthly-only series (Diesel-USD, Diesel-MNT) show their honest "monthly only" state regardless of the global toggle |
| Faking/deriving a synthetic weekly Diesel-USD or Diesel-MNT forecast via naive interpolation of the monthly curve, to make the weekly view "feel complete" (all 5 cards populated) | Surface appeal: symmetric UI, no empty/disabled cards, "looks more finished" | Directly violates the project's core discipline established since v1 ("no un-backtested model ships to the dashboard") — an interpolated curve is not a backtested forecast and would carry a fabricated confidence implication; also, backend research explicitly found no weekly Diesel/FX proxy relationship worth trusting for Diesel in earlier spikes | Show the "monthly only" disabled/muted card state (table stakes above); if a weekly Diesel/FX data source is ever found, that's new backend research, not a UI workaround |
| New weekly-cadence Data Entry UI/table for manually entering weekly actuals, added opportunistically since the Weekly toggle is already being built | Feels like the natural companion to a weekly forecast view ("if I can view weekly, I should be able to enter weekly") | Explicitly out of scope per the milestone definition; existing monthly Data Entry tab already works and weekly actuals ingestion is an unscoped, separately-sized problem (would need its own CSV/import research, validation rules, etc.) — scope creep risk is high and directly contradicts the stated milestone boundary | Leave Data Entry tab monthly-only this milestone, exactly as scoped; revisit as its own milestone if ever needed |
| Auto-switching or defaulting to Weekly mode for HDAN/PPAN/FX because "it's more accurate" | Seems like doing the user a favor by defaulting to the objectively lower-MAPE model | Removes user agency/predictability — a returning user (matching this app's monthly, occasional-use pattern) expects the view they last used, not a silently different default state per series; also the "more accurate" framing is horizon-dependent (weekly MAPE is measured at h=4/5 weeks, not directly comparable to a 12-month monthly horizon pick) | Default to Monthly (matches existing shipped behavior, zero surprise for existing users), let the user opt into Weekly; use the persisted-toggle pattern (table stakes) so their choice sticks |
| Independent weekly horizon slider range (e.g. 1-52 weeks) mirroring the monthly 1-12 range 1:1 | Symmetric-feeling UI parity with the existing monthly horizon control | Weekly models were only backtested out to h=4/5 weeks (~1 month) per `REPORT-WEEKLY.md` — extending the horizon control far beyond the validated range invites the user to request forecasts with no backtested accuracy basis, silently violating "no un-backtested model ships" | Cap the weekly horizon control at a validated range (see horizon-units discussion below); if a longer horizon is wanted later, that requires new backtesting first |

## Feature Dependencies

```
Weekly granularity toggle (Forecast tab + Summary cards)
    └──requires──> Existing tab/shared-state pattern (v1.3 tab-nav + persisted dark/light toggle)
    └──requires──> Weekly model metadata (model name, MAPE) per series, keyed by granularity
                       └──requires──> backend_research/REPORT-WEEKLY.md validated weekly models (HDAN, PPAN)
                       └──requires──> Weekly FX model (net-new this milestone; validated against FX Data.csv Weekly column)
    └──requires──> Weekly-dated fan chart rendering
                       └──requires──> Existing Plotly fan-chart component (v1 build) — reused, not rebuilt

"Monthly only" honest state for Diesel-USD / Diesel-MNT
    └──requires──> Weekly granularity toggle (state to react to)
    └──enhances──> User trust / provenance discipline (already established, v1.3)

Provenance line granularity-awareness
    └──requires──> Weekly granularity toggle
    └──requires──> Weekly model metadata (see above)
    └──enhances──> Weekly toggle's value proposition (shows *why* weekly might be picked)

Horizon control unit adaptation (weeks vs months)
    └──requires──> Weekly granularity toggle
    └──conflicts with──> Symmetric 1-12 unit range reuse (see anti-feature: capped range instead)
```

### Dependency Notes

- **Weekly toggle requires existing shared-state/persistence pattern:** the dark/light theme toggle (v1.3) already solved "one persisted UI-mode setting affecting multiple components" — this is the same shape of problem at a different key, not a new pattern to invent.
- **Weekly toggle requires per-series weekly model metadata:** HDAN and PPAN are already validated (`REPORT-WEEKLY.md`, go verdict). FX weekly is *not yet backtested* — the milestone's own scope note flags a new FX weekly model as required work before the toggle can honestly include FX. This is a real sequencing dependency: the weekly-FX backtest must land before (or in the same phase as) the FX weekly card ships, not after.
- **"Monthly only" state enhances (doesn't block) the toggle:** the toggle can ship its core 3-series behavior with Diesel-USD/Diesel-MNT cards simply always rendering in their existing monthly form, disabled-styled when Weekly is globally selected. This is a small additive layer on top of the toggle, not a separate feature with its own critical path.
- **Horizon unit adaptation conflicts with naive range reuse:** don't let "just reuse the 1-12 slider" ship silently reinterpreted as weeks — this needs an explicit decision (see below), otherwise it's a a footgun disguised as reuse.

## Design Decisions for This Milestone's Open Questions

The prompt asked four specific design questions. Answering each directly, since they gate implementation choices more than a generic table-stakes/differentiator list does:

### (a) Granularity toggle affecting Forecast tab + Summary cards
**Recommendation: single global toggle, not per-card.** Table stakes as listed above. One `rx.State` boolean/enum drives both the Forecast tab's model selection/chart and the Summary cards' displayed values and provenance. This matches the general dashboard-cadence guidance found in research (pick one dominant tempo per screen) and avoids the combinatorial-state anti-feature (per-series granularity picker).

### (b) Honest "monthly only" representation for Diesel-USD / Diesel-MNT
**Recommendation: always-visible, disabled/muted card state with explicit label, never hidden and never faked.** This is table stakes, not optional polish — it's a direct extension of the project's existing "no un-backtested model ships" discipline (already enforced for sentiment in v2.0's Phase 16 no-go, correctly *not* shipped in degraded form). Concretely: keep both Diesel cards in the Summary grid at all times; when Weekly is selected, style them muted/disabled with a one-line explanation ("Monthly data only — no weekly source exists for Diesel-USD"), continuing to show their last-known *monthly* forecast value rather than blanking them, so the user isn't confused about whether the card broke. Grid layout stays stable (5 cards, always), which also avoids a layout-reflow bug class.

### (c) Weekly horizon expressed in weeks vs. month-equivalent
**Recommendation: weeks, not a converted month-ish range — but cap the range to match the validated backtest horizon (~4-5 weeks / roughly 1 month), not a full 1-52 mirror of the monthly 1-12 control.** Rationale: `REPORT-WEEKLY.md`'s validated results are h=4 (primary) and h=5 (sensitivity) — i.e., roughly one month out. Presenting a 12-week or 52-week horizon option would imply backtested confidence the project doesn't have yet, directly against the established "no un-backtested model ships" rule. Converting the horizon to a "month-ish" label (e.g., "~1 month (4 weeks)") is reasonable as a *secondary* clarifying label next to a weeks-denominated control, but the primary unit and stored value should be weeks — that's what the model backtest is actually indexed on, and it avoids a lossy/ambiguous unit conversion layer between the UI and the forecasting module. If/when a longer weekly horizon is backtested in a future milestone, the range can simply be extended — no redesign needed.

### (d) Whether/how the provenance line changes for weekly mode
**Recommendation: yes, it must change, and it should actively surface the accuracy delta as a value proposition, not just silently swap the number.** The provenance line already exists specifically to build trust via "which model, its backtested MAPE" (v1.3 decision) — showing a stale monthly MAPE under a weekly forecast would be a regression in the exact feature designed to prevent this kind of misrepresentation. Concretely:
- Provenance line reads from a granularity-keyed model-metadata source (`{series: {monthly: {model, mape}, weekly: {model, mape}}}`), not a single flat lookup — this is a small backend/data-shape change, not a new UI capability.
- Because weekly MAPE numbers are meaningfully *better* for HDAN (7.25% vs 9.49%) and PPAN (6.96% vs 10.08%), the provenance line is also the natural (and only necessary) place to fold in the differentiator listed above — e.g. "SARIMAX(0,1,0)+BalticAN — 7.25% MAPE (weekly; monthly model: 9.49%)" — rather than adding a separate comparison widget. This keeps the accuracy story in the one place users already look for it, without new UI real estate.
- Do not claim "weekly is simply more accurate" as a blanket statement in copy — the comparison is horizon-matched (h=4/5 weeks ≈ 1 month) per the backtest methodology; if copy implies weekly beats monthly at all horizons, that overstates the validated claim. Keep the comparison framed as "at the ~1-month horizon" if any comparative language is used at all.

## MVP Definition

### Launch With (this milestone)

- [ ] Global Monthly/Weekly toggle on Forecast tab, shared state with Summary cards — core requested capability
- [ ] Weekly-cadence fan chart + card values for HDAN, PPAN, FX (all three backed by validated/to-be-validated weekly models)
- [ ] Weekly FX model research/backtest (net-new this milestone per PROJECT.md scope — FX Data.csv Weekly column)
- [ ] "Monthly only" honest disabled-state cards for Diesel-USD and Diesel-MNT when Weekly selected
- [ ] Granularity-aware provenance line (model name + MAPE) for all 5 series, including the weekly-vs-monthly MAPE contrast for HDAN/PPAN/FX
- [ ] Weeks-denominated horizon control when Weekly is selected, capped to the validated ~4-5 week backtest range
- [ ] Toggle state persisted (reuse dark/light toggle's existing persistence mechanism)

### Add After Validation (future, if requested)

- [ ] Shareable/bookmarkable granularity via URL query param — nice-to-have, low cost, not required for launch
- [ ] Extended weekly horizon range, if a future backtest validates beyond ~5 weeks

### Future Consideration (explicitly deferred, not this milestone)

- [ ] Weekly-cadence Data Entry UI for manual weekly actuals — explicitly out of scope per milestone definition; would need its own CSV import/validation research
- [ ] Per-series granularity mixing within one view — anti-feature, not planned
- [ ] Weekly Diesel-USD/Diesel-MNT forecasting — blocked indefinitely on a weekly Diesel/FX-adjacent data source that doesn't currently exist; not a UI problem to solve

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Global Monthly/Weekly toggle (Forecast tab + Summary cards) | HIGH | LOW | P1 |
| Weekly HDAN/PPAN forecast display (chart + cards) | HIGH | LOW (models already validated) | P1 |
| Weekly FX forecast display (chart + cards) | HIGH | MEDIUM (model not yet backtested — new research this milestone) | P1 |
| "Monthly only" disabled-state cards for Diesel-USD/Diesel-MNT | HIGH (trust/honesty) | LOW | P1 |
| Granularity-aware provenance line with weekly-vs-monthly MAPE contrast | MEDIUM-HIGH (justifies the whole feature) | LOW | P1 |
| Weeks-denominated, capped horizon control | HIGH (prevents silent misuse of un-backtested horizons) | LOW-MEDIUM | P1 |
| Toggle persistence | MEDIUM | LOW (pattern reuse) | P2 |
| URL query param deep-link for granularity | LOW | LOW | P3 |
| Weekly Data Entry UI | N/A this milestone | HIGH | Out of scope |

**Priority key:**
- P1: Must have for this milestone's launch
- P2: Should have, add when convenient within the milestone
- P3: Nice to have, defer without concern

## Sources

- `.planning/PROJECT.md` — milestone scope, existing shipped features, key decisions history (HIGH confidence, primary source)
- `.planning/milestones/v2.0-ROADMAP.md` — Phase 16/17 research spike outcomes and their "no-go = don't ship degraded" precedent, directly informing the anti-features on faking data (HIGH confidence)
- `backend_research/REPORT-WEEKLY.md` — validated weekly HDAN/PPAN model MAPE figures (7.25%/6.96% weekly vs 9.49%/10.08% monthly benchmark), horizon-matched methodology (h=4/5 weeks) — HIGH confidence, primary source for the horizon-cap and provenance recommendations
- CLAUDE.md project stack/architecture notes — confirms Reflex `rx.State` shared-state pattern already used for dark/light toggle, reused for granularity toggle recommendation (HIGH confidence)
- [Forecast Cadence | Revspire](https://www.revspire.io/resources/blogs/the-complete-2026-guide-to-forecast-cadence-for-revenue-leaders) — general forecast-cadence guidance (MEDIUM confidence, general B2B revenue-ops context, not commodity-forecasting-specific)
- [How do dashboards visualize forecasts? | Pedowitz Group](https://www.pedowitzgroup.com/how-do-dashboards-visualize-forecasts) — general dashboard forecast-visualization patterns (MEDIUM confidence)
- [community.qlik.com — showing monthly/weekly/daily views dynamically](https://community.qlik.com/t5/QlikView-App-Dev/How-to-show-monthly-weekly-and-daily-views-dynamically-in/td-p/104708) — corroborates the single-toggle, dominant-tempo-per-screen pattern with per-mode default date ranges (MEDIUM confidence, community forum not official docs, but concrete implementation precedent)
- [DataCult — Weekly Decision Cadence dashboards](https://www.datacult.ai/2026/02/28/resources-weekly-decision-cadence-dashboards/) — source of the "classic mistake is mixing modes on one screen" principle directly applied to the anti-features section (MEDIUM confidence)

---
*Feature research for: mixed-cadence (weekly + monthly) financial/commodity forecast dashboard, v2.1 Weekly Forecast UI milestone*
*Researched: 2026-09-01*
