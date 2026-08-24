# Project Research Summary

**Project:** Prediction Dashboard — v1.3 (Dashboard Polish & Data-Entry Rework)
**Domain:** Internal financial forecasting dashboard retrofit (Reflex, single-user, six UI/UX fixes on an existing app)
**Researched:** 2026-08-24
**Confidence:** HIGH

## Executive Summary

This milestone is a targeted UI/UX retrofit — not new-product research — on an already-working Reflex 0.9.8.post1 dashboard (`app/app/state.py`, `app.py`, `forecasting.py`, `theme.py`). Six concrete feedback items drive the scope: a transparent-background "black margins" bug, a missing dark/light toggle, missing tab navigation across Summary/Forecast/Data Entry, missing per-forecast model provenance, a fan-chart legend/axis overlap, and a silently-failing free-text date entry field. All required capability already exists in the installed stack (`reflex==0.9.8.post1`, `plotly==6.9.0`) — zero new PyPI dependencies are needed; this is entirely additive use of built-in Reflex APIs (`rx.color_mode`, `rx.tabs`, `rx.App(style=...)`, native `rx.input(type="date")`) and Plotly layout tuning.

The recommended approach is architecturally conservative: keep the single `DashboardState` class and single-route/single-page structure that the codebase already commits to, rather than introducing new state classes or multi-route navigation. Two features are far riskier than their surface complexity suggests: (1) the dark/light toggle, because the app has a *parallel*, non-Radix hardcoded hex color system (`theme.py`) that a naive `appearance="inherit"`/toggle wiring will not re-color, silently reintroducing the exact illegibility bug a prior phase (v1.2 Phase 6) already fixed; and (2) the Data Entry date-field fix, because root-cause investigation shows the bug is *not* a broken render conditional but a blur/Enter-gated validation race interacting with a hand-rolled `editing_key`/`draft_rows`/`edit_error` state machine already shared by three prior features (windowing toggle, CSV import). Both need dedicated phases rather than being treated as quick fixes.

Key mitigations: sequence the background-fix and theme-toggle work together against one shared color-token source (never hardcode a single-appearance background); source model name/MAPE metadata from new constants in `forecasting.py` (not hand-typed literals in `state.py`/`app.py`) to avoid a second, driftable source of truth; and treat the date-entry fix as its own research-heavy phase with an explicit state-transition audit and regression tests against windowing and CSV import, per PROJECT.md's own "deep research" flag on that item.

## Key Findings

### Recommended Stack

No new stack decisions are required — keep `reflex==0.9.8.post1` and `plotly==6.9.0` as-is and consume already-shipped API surface.

**Core technologies:**
- Reflex 0.9.8.post1 — already the app framework; `rx.color_mode`, `rx.tabs`, `rx.App(style=...)`, native `rx.input(type="date")` all verified present via direct introspection of the installed package
- Plotly 6.9.0 (via `rx.plotly`) — legend/axis-overlap fix is a pure `go.Figure.update_layout()` change, no capability gap
- `rx.LocalStorage` — for persisting the theme toggle choice client-side (single-browser/user fit)

### Expected Features

**Must have (table stakes, all six map 1:1 to explicit user feedback — P1 for v1.3):**
- Fix transparent `html`/`body` background (root cause of "black margins")
- Dark/light mode toggle, persisted, using `rx.color_mode` primitives
- Tab/nav bar (Summary / Forecast / Data Entry) via `rx.tabs`
- Fan chart legend/axis-label overlap fix (Plotly layout only)
- Per-series model name + backtest MAPE shown in plain language near each forecast
- Structured date entry (`rx.input(type="date")`) replacing free-text, with visible validation

**Should have (differentiators, defer if time-constrained):**
- Plain-language accuracy framing (e.g. "typically within ±13% of actual")
- System-preference-aware default color mode (verify if already default in 0.9.8)

**Defer (v2+):**
- Inline model-comparison tooltip showing all candidate models' backtest scores
- Deeper model diagnostics (AIC/BIC, residual plots) — explicitly an anti-feature for this non-technical audience

**Anti-features to actively avoid:** freeform/fuzzy date parsing instead of a native date input; a full branded theming overhaul while adding dark mode; exposing raw statsmodels diagnostics; a multi-route nav instead of in-page tabs.

### Architecture Approach

Single Reflex process, single `DashboardState` class, single page/route — none of the six features require a new state class, a new DB table (except theme persistence), or a new route. Tabs should be implemented as client-side section switching (conditional rendering within the existing `index()`), not separate Reflex routes, to avoid `on_mount` duplication and in-flight draft/edit state loss.

**Major components:**
1. `state.py` (`DashboardState`) — sole DB/session boundary; gains `theme_appearance`, `active_section` fields plus setters, following the existing single-state-class convention
2. `theme.py` — currently light-only hardcoded hex tokens; must become dual-tokenized (light/dark) before/alongside the toggle, including Plotly figure `font`/`plot_bgcolor` colors
3. `forecasting.py` — Reflex-free; gains a new frozen `MODEL_INFO`/metadata constant (name + MAPE per series) consumed through the existing single `forecast_all()` call site, no signature changes to its locked return contract
4. `app.py` — render/component layer; gains `theme_toggle()`, `nav_bar()`, a small model-info badge component, and Plotly layout tweaks in `state.py`'s figure builders

**Suggested build order (from ARCHITECTURE.md):** background fix → theme toggle (same/adjacent phase, shared color-token source) → fan chart legend fix → model provenance display → tab/nav bar → Data Entry rework (last, most research-heavy).

### Critical Pitfalls

1. **Theme toggle reintroduces OS-dark-mode inheritance / un-tokenized colors** — never use `appearance="inherit"`; drive appearance from persisted state only, and dual-tokenize every `theme.py` constant plus Plotly `font.color`/`plot_bgcolor` before shipping the toggle.
2. **Background fix hardcodes one appearance, colliding with the theme toggle** — set `html`/`body` background from the same mode-aware token source as `PAGE_BG`/`SURFACE`, not a separate hardcoded CSS rule; verify at 3 viewports × 2 appearances.
3. **Tab/nav retrofit breaks `on_mount` loading or loses in-flight draft/CSV state** — implement as client-side section toggling within the existing single page/route, not separate routes; explicitly test "switch tabs mid-edit" and "mid-CSV-preview."
4. **Model metadata becomes a second, driftable source of truth** — add name/MAPE as real constants in `forecasting.py`, consumed via the existing single `forecast_all()` call site; never hand-type MAPE literals into `state.py`/`app.py`.
5. **Fan chart legend fix collides with the "Forecast start" vline annotation** — reposition both together, apply consistently to both `historical_chart_figure` and `forecast_chart_figure`, and leave `aria_label` props in `app.py` untouched.
6. **Date-entry fix regresses the windowing toggle or CSV import's shared state machine** — root cause is a blur/Enter-gated validation race in `_editable_cell`/`commit_edit`, not a broken `rx.cond`; write a full state-transition table for `editing_key`/`draft_value`/`edit_error`/`draft_rows`/`pending_delete` before changing control flow, reuse the existing scalar `edit_error` field, and regression-test against windowing toggle and CSV import (which has its own separate, un-audited date-validation path in `csv_import.py`).

## Implications for Roadmap

Suggested phase structure (six features, sequenced by dependency/risk rather than feedback-list order):

### Phase 1: Background Fix + Theme Toggle
**Rationale:** These two are architecturally coupled — a background fix done in isolation with a hardcoded light value must be redone once dark mode ships; PITFALLS.md explicitly recommends treating them as one phase (or tightly sequenced) with one shared color-token source.
**Delivers:** Dual-tokenized `theme.py` (light/dark), mode-aware `html`/`body` background via `rx.App(style=...)`, persisted toggle (`rx.LocalStorage` or `AppSetting`, mirroring the existing `markup_pct` pattern), Plotly figure colors made mode-aware.
**Addresses:** Feedback items #1 (dark/light toggle) and the "black margins" root cause.
**Avoids:** Pitfall 1 (OS-inheritance/un-tokenized colors) and Pitfall 2 (hardcoded single-appearance background).

### Phase 2: Fan Chart Legend/Axis Fix
**Rationale:** Isolated, low-risk, single-file (`state.py`) Plotly layout change with no dependency on theme/nav work; cheap to sequence early to unblock visual QA of adjacent chart work.
**Delivers:** Repositioned legend + adjusted `add_vline` annotation position + margin tuning, applied identically to both `historical_chart_figure` and `forecast_chart_figure`.
**Uses:** Plotly 6.9.0 `update_layout()` (no new stack elements).
**Avoids:** Pitfall 5 (legend/annotation collision, `aria_label` regression).

### Phase 3: Model Provenance Display
**Rationale:** Additive, no dependency on theme/nav work; natural pairing with Phase 2 since both touch the forecast-chart/summary-card visual area; requires new `forecasting.py` constants as a prerequisite.
**Delivers:** `MODEL_INFO`-style frozen constants in `forecasting.py`, a thin `@rx.var` in `state.py`, and a small badge component in `app.py` showing plain-language model name + accuracy.
**Implements:** The "one-way data flow" — `forecasting.py` → `state.py` → `app.py`, through the existing single `forecast_all()` call site.
**Addresses:** Feedback item #4.
**Avoids:** Pitfall 4 (second source of truth / drift).

### Phase 4: Tab/Nav Bar (Summary / Forecast / Data Entry)
**Rationale:** Biggest structural change to `app.py` (conditional rendering wrapping every existing section); do after visual/theme work lands so nav doesn't need re-testing against a still-changing background/theme.
**Delivers:** `active_section` state field, `nav_bar()` component, `rx.tabs`-based (or `rx.cond`-based) client-side section switching within the existing single route.
**Addresses:** Feedback item #3.
**Avoids:** Pitfall 3 (on_mount duplication, lost draft/edit state on switch).

### Phase 5: Data Entry Rework (Date-Entry Fix)
**Rationale:** Deliberately last and separated from the other five — PROJECT.md explicitly flags this as needing a "deep research" pass; the fix is behavioral/UX (blur/Enter-gated validation race in a hand-rolled state machine already shared by 3 prior features), not a quick conditional-render bug fix.
**Delivers:** Native `rx.input(type="date")` (or equivalent structured picker) replacing free-text entry, reworked/louder inline validation reusing the existing `edit_error` scalar, and an explicit audit of every date-parsing entry point (manual add-row, manual edit-row, CSV import, Excel export round-trip).
**Addresses:** Feedback item #6.
**Avoids:** Pitfall 6 (regression of windowing toggle / CSV import's shared `editing_key`/`draft_rows`/`edit_error` machine).

### Phase Ordering Rationale

- Theme/background work sequenced first: highest-coupling pair (fixing one without the other creates rework); subsequent phases render inside whatever background/color system Phase 1 establishes.
- Chart and model-provenance work (Phases 2-3): low-risk, isolated, additive — grouped as "safe middle" phases.
- Nav (Phase 4): sequenced after visual work so it isn't tested against a moving target, before Data Entry rework so the reworked section lands inside the final page structure.
- Data Entry rework (Phase 5): last and isolated — only item touching a complex, multi-feature-shared hand-rolled state machine, highest regression risk (HIGH recovery cost), and the only item PROJECT.md flags for deep research.

### Research Flags

Needs deeper research during planning:
- **Phase 1 (Theme toggle):** Reflex 0.9.8's exact runtime appearance-toggle API (`rx.color_mode` vs. `rx.App(theme=...)` root wrapping) not verified against Context7/official docs in the architecture pass — confirm exact API shape before implementation.
- **Phase 5 (Data Entry rework):** Requires a pre-implementation state-transition table for `editing_key`/`draft_value`/`edit_error`/`draft_rows`/`pending_delete`, plus an audit of `csv_import.py`'s separate date-validation path.

Standard patterns (skip deep research):
- **Phase 2 (Fan chart fix):** Well-documented Plotly layout API, isolated single-file change.
- **Phase 3 (Model provenance):** Codebase already has an established idiom (`summary_cards`/`freshness_chips` "list of flat string dicts") to copy directly.
- **Phase 4 (Tab/nav bar):** `rx.tabs.root`/`.list`/`.trigger`/`.content` directly confirmed against current Reflex docs; client-side vs. multi-route already resolved in favor of client-side.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified via direct introspection of installed `reflex==0.9.8.post1`; no new dependencies needed |
| Features | HIGH/MEDIUM | HIGH for Reflex-specific mechanics; MEDIUM for general dashboard UX conventions (NN/g, pattern libraries) |
| Architecture | HIGH | Grounded in direct reads of all relevant source files and `.planning/STATE.md`'s recorded repro |
| Pitfalls | HIGH | Same direct-source-read grounding; pitfalls trace to specific line-level code behavior |

**Overall confidence:** HIGH

### Gaps to Address

- Exact Reflex 0.9.8 runtime API for toggling `rx.theme`'s `appearance` prop at runtime (vs. build-time `rxconfig.py` plugin config) — needs docs/Context7 lookup before Phase 1 implementation.
- Whether `rx.color_mode` already defaults to system preference in installed 0.9.8, or needs explicit `appearance="inherit"` config.
- `csv_import.py`'s own date-validation implementation was referenced but not directly read — must be audited as part of Phase 5.
- Persistence mechanism for the theme toggle (`rx.LocalStorage` vs. `AppSetting` DB row) — decide during Phase 1 planning based on whether cross-device persistence matters.

## Sources

### Primary (HIGH confidence)
- Direct reads: `app/app/state.py`, `app/app/app.py`, `app/app/forecasting.py`, `app/app/theme.py`, `app/app/validators.py`, `app/rxconfig.py`
- `pip show reflex plotly` introspection of installed `reflex==0.9.8.post1`, `plotly==6.9.0`
- https://reflex.dev/docs/recipes/others/dark-mode-toggle/, https://reflex.dev/docs/styling/theming/, https://reflex.dev/docs/library/disclosure/tabs/
- `.planning/PROJECT.md`, `.planning/STATE.md`

### Secondary (MEDIUM confidence)
- https://www.nngroup.com/articles/date-input/
- https://uxpatterns.dev/patterns/forms/date-input

### Tertiary (LOW confidence)
- General web search on `rx.input(type="date")` prop surface — not directly confirmed against a Reflex-specific doc page

---
*Research completed: 2026-08-24*
*Ready for roadmap: yes*
