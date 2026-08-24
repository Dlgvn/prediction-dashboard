# Feature Research

**Domain:** Internal financial forecasting dashboard (single/small user group, procurement/finance staff) — UI polish + data-entry fix milestone
**Researched:** 2026-08-24
**Confidence:** HIGH (Reflex-specific mechanics), MEDIUM (general dashboard UX conventions, sourced from NN/g and established design-pattern sites)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist on any modern dashboard. Missing these makes the app feel broken or unprofessional — directly matches this milestone's feedback items.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Full-width responsive layout (no dead margins) | Any web app rendered on a laptop/desktop is expected to use the viewport; unstyled/black margins read as a rendering bug, not a design choice | LOW | Root cause is almost certainly a missing `background-color` on `html`/`body` (they stay transparent, so the OS/browser chrome or a themed `<html>` shows through) plus a max-width container that isn't set to fill viewport. Fix at the `rx.app` / global stylesheet level (`style={"background": rx.color("gray", 1)}` or set `_html`/`body` in the theme), not per-page. |
| Dark/light mode toggle | Standard on virtually all professional SaaS/dashboard tools since ~2020; users increasingly expect it, and its *absence* combined with a transparent-background bug is very likely what's producing the "black margins" complaint in dark-mode browsers specifically | LOW | Reflex ships this as a first-class primitive: `rx.color_mode.button()` / `rx.color_mode.switch()` plus `rx.color_mode_cond()` for conditional rendering, all driven by `rx.theme(appearance="...")`. State (user's last choice) persists automatically via Reflex's built-in `color_mode` local-storage var — no custom state model needed. This is the "just use the framework's built-in recipe" case, not a build-from-scratch feature. |
| Tab/section navigation (Summary / Forecast / Data Entry) | Once a dashboard has 3+ logically distinct sections, users expect navigation instead of one continuous scroll — this is the default pattern on every BI tool (Tableau, PowerBI, Metabase, Looker) and even simple internal tools | LOW-MEDIUM | Reflex's `rx.tabs.root` / `rx.tabs.list` / `rx.tabs.trigger` / `rx.tabs.content` is a direct fit — controlled via `value` + `on_change` bound to a state var if the active tab needs to persist across reload, or `default_value` if not. Low complexity to wire up; the only real cost is restructuring the current single-scroll page into three content blocks. |
| Legible, non-overlapping chart labels/legend | A chart where the axis label and legend visually collide is read as broken, not stylistic — this is a correctness bug more than a "feature" | LOW | Plotly (`rx.plotly`) exposes `legend=dict(orientation="h", y=-0.2, ...)` and margin/axis-title positioning directly in the figure's `layout`; typical fix is moving the legend below the plot area (horizontal orientation) or into the right margin with adequate `margin=dict(r=...)`, combined with `xaxis_title_standoff`/`yaxis_title_standoff` padding. No new library needed — it's a `go.Figure.update_layout()` tweak. |
| Structured (non-free-text) date entry | Free-text date fields silently failing (accepting garbage or a non-ISO format with no error) is a textbook, well-documented UX failure (NN/g: "Date-Input Form Fields") — the standard fix in every modern web form is to remove the free-text failure mode entirely, not to add better error messages on top of it | LOW-MEDIUM | See dedicated analysis below — this is the deep-research item (#6). |
| Visible per-forecast model provenance ("which model, how accurate") | Once a user has been burned by (or is scrutinizing) a forecast for procurement decisions, "why should I trust this number" becomes a real question — showing model name + backtest accuracy is a standard trust-building pattern in any tool presenting a statistical estimate (weather apps show confidence, financial estimate tools show source/methodology) | LOW | This is additive to the existing summary cards — a small caption/badge, not a new page. See dedicated analysis below — this is feedback item #4. |

### Differentiators (Competitive Advantage)

Not required by users, but meaningfully improve this specific app given its audience (non-technical procurement staff who don't want to think about statistics).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Plain-language accuracy framing next to MAPE (e.g. "SARIMAX — typically within ±13% of actual") | Non-technical procurement/finance users don't intuitively know what "13.3% MAPE" means; translating it into "how wrong has this model been historically" builds trust without requiring a stats background | LOW | Purely a string-formatting/copy decision on top of the number already being computed in `backend_research/`-style backtests — no new computation. |
| System-preference-aware default color mode (respect OS light/dark setting on first visit, remember explicit override after) | Slightly better first-run experience than defaulting to a fixed mode; matches what users already expect from every modern app (browser, OS, VS Code, etc.) | LOW | Reflex's `rx.color_mode` already defaults to system preference via `prefers-color-scheme` unless a stored override exists — verify this is the default behavior in the installed 0.9.8 version rather than assuming; if not default, it's a one-line config (`appearance="inherit"` vs a fixed value in `rx.theme`). |
| Inline model-comparison tooltip (hover to see all candidate models' backtest scores, not just the winner) | Gives an interested/skeptical user a path to "why this model and not another" without cluttering the default view | MEDIUM | Nice-to-have; requires surfacing the full backtest table (already exists in `backend_research/REPORT.md`-style output) into the UI as a hover/expand affordance. Reasonable v1.4+ candidate, not required for this milestone's stated ask. |

### Anti-Features (Commonly Requested, Often Problematic)

Things that look like reasonable "fixes" for this feedback but would create more problems than they solve for this specific app and user base.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Freeform date text field + smarter regex/fuzzy-date parsing ("accept any format the user types") | Seems like a lower-effort fix than changing the input control — "just parse it better" | Fuzzy date parsing (e.g. trying to guess "03/04/25" as MM/DD or DD/MM) is exactly the failure mode already hurting this user — ambiguous formats silently resolve to the *wrong* date rather than erroring, which is worse than a visible rejection. Also adds an ongoing maintenance burden (new edge cases forever) instead of eliminating the class of bug. | Native `rx.input(type="date")` (HTML5 date input) — eliminates free-text parsing entirely; the browser renders a calendar picker and always returns an unambiguous ISO value. This is the standard, zero-parsing-code fix and directly targets the diagnosed root cause. |
| Full custom-branded design system / theming overhaul while adding dark mode | "As long as we're touching colors, let's redesign" scope creep | This is a single-user/small-team internal tool, not a customer-facing product — a bespoke design system is disproportionate effort for the audience size and doesn't address any of the 6 reported issues | Use Reflex's built-in `rx.theme` + Radix-based component defaults; only override where the transparent-background bug and legend-overlap bug require it. |
| Exposing raw statsmodels diagnostics (AIC/BIC, residual plots, ACF/PACF charts) next to the forecast, in the name of "transparency" | Feels like the maximally-transparent version of feature #4 | This audience is explicitly non-technical procurement/finance staff — raw model diagnostics are noise to them and undermine the actual goal (quick trust signal), reintroducing the same "overwhelming for non-technical user" problem the milestone question explicitly warns against | Single plain-language line: model family name + one accuracy number, phrased in real-world terms (see differentiator above). Keep deeper diagnostics, if ever needed, in `backend_research/` artifacts, not the live UI. |
| A full multi-page router (distinct URL routes per section) instead of tabs on one page | Tabs vs. routes can look like a similar ask ("navigation between sections") | This is a single-process, single/small-user internal tool with no need for deep-linking, bookmarking a specific section, or SEO; a full router adds Reflex page/route complexity (`app.add_page` per section, cross-page state sharing concerns) for no user-facing benefit over an in-page `rx.tabs` component, which keeps all existing state wiring simpler | `rx.tabs.root` on a single page/route, as already identified in Table Stakes. |

## Feature Dependencies

```
Fix transparent html/body background bug
    └──requires──> (none — independent CSS/theme-config fix, do first)

Dark/light mode toggle
    └──enhances──> Fix transparent html/body background bug
                       (the black-margin bug is most visible/severe specifically in dark mode;
                        fixing background transparency first makes the toggle's dark state look correct)

Tab/nav bar (Summary / Forecast / Data Entry)
    └──requires──> Existing page content already exists as separable blocks
                       (already true — Summary cards, Forecast chart+table, Data Entry table
                        are already distinct sections per PROJECT.md; this is a restructuring,
                        not new content)

Per-series model name + backtest accuracy display
    └──requires──> Backtest accuracy numbers already computed (already true — HDAN 9.4% MAPE,
                    PPAN 10.0%, Diesel-USD 3.4%, FX 0.25% exist per PROJECT.md "Validated" section)
    └──enhances──> Forecast tab content (natural home once tabs exist, though not a hard blocker
                    — could ship independently of the tab restructuring)

Fan chart legend/axis-label fix
    └──requires──> (none — independent Plotly layout fix)

Structured date-entry (rx.input type=date) rework
    └──requires──> (none technically — but should be scoped and shipped together with clear
                    inline validation messaging, since the milestone explicitly calls this out
                    as needing "deep research", i.e. don't treat it as a one-line prop swap
                    without checking downstream effects: CSV bulk-import date parsing,
                    existing stored-date format in SQLite, edit-in-place row behavior)
    └──conflicts with──> Freeform text date entry (mutually exclusive — pick one, per Anti-Features)
```

### Dependency Notes

- **Dark/light mode toggle enhances the background-margin fix (not vice versa):** doing the background fix first means the dark-mode toggle "just works" visually instead of exposing the same margin bug in a new state. Sequence: background fix → dark mode toggle.
- **Tab/nav bar requires no new content, only restructuring:** all three target sections (Summary, Forecast, Data Entry) already exist as of v1.2; this is UI reorganization risk (state scoping, conditional rendering cost when a tab is hidden), not a data/backend dependency.
- **Model provenance display requires no new computation:** the backtest MAPE numbers are already validated and stored per PROJECT.md's "Validated" requirements section — this is purely a display/formatting task, which keeps its complexity LOW despite sounding like a "ML feature."
- **Date-entry rework has the widest blast radius of the six items:** unlike the others, it touches the SQLite-backed `rx.Model` row-add/edit flow, the CSV bulk-import date-parsing path added in v1.2, and whatever validation currently exists on the Data Entry table's new-row form. This is why the milestone explicitly flagged it for deep research rather than a quick fix — recommend scoping it as its own phase, not bundled with the four cosmetic UI fixes.

## MVP Definition (for this milestone, v1.3)

### Launch With (v1.3)

- [ ] Fix transparent `html`/`body` background — root cause of black-margin complaint; must ship regardless of dark mode, since it also affects wide-viewport light mode
- [ ] Dark/light mode toggle using Reflex's built-in `rx.color_mode` primitives, with persisted user choice — directly requested (#1), low complexity, framework-native
- [ ] Tab/nav bar (Summary / Forecast / Data Entry) using `rx.tabs` — directly requested (#3), restructures existing content only
- [ ] Fan chart legend/axis-label overlap fix via Plotly layout config — directly requested (#5), isolated bug fix
- [ ] Per-series model name + backtest MAPE shown near each forecast, in plain-language framing — directly requested (#4), no new computation needed
- [ ] Replace free-text date entry with `rx.input(type="date")` (or equivalent structured/native date picker), with explicit inline validation feedback if any edge case still allows an invalid state — directly requested (#6), root cause already diagnosed; this is the deep-research item and should get its own scoping pass given it touches CSV import and stored-date formatting too

### Add After Validation (v1.4+)

- [ ] Inline model-comparison tooltip showing all candidate models' backtest scores, not just the winner — useful once the basic provenance display is validated with real users
- [ ] System-preference-aware default color mode (if not already default behavior in the installed Reflex version) — polish, not user-blocking

### Future Consideration (v2+)

- [ ] Deeper model diagnostics view (AIC/BIC, residual plots) — explicitly deferred; this audience doesn't need it and it risks re-introducing the "overwhelming for non-technical user" problem this milestone is trying to avoid

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Fix transparent background (black margins) | HIGH | LOW | P1 |
| Dark/light mode toggle | HIGH | LOW | P1 |
| Tab/nav bar | HIGH | LOW-MEDIUM | P1 |
| Fan chart legend/axis fix | MEDIUM | LOW | P1 |
| Model name + backtest accuracy display | MEDIUM-HIGH | LOW | P1 |
| Structured date-entry rework | HIGH (blocks core Data Entry workflow entirely for affected users) | MEDIUM (deep-research flagged) | P1 |
| Model-comparison tooltip | LOW-MEDIUM | MEDIUM | P3 |
| System-preference-aware default mode | LOW | LOW | P3 |
| Raw statsmodels diagnostics in UI | LOW (for this audience) | MEDIUM | Anti-feature — do not build |

**Priority key:**
- P1: Must have for this milestone (v1.3) — all six correspond directly to explicit user feedback items
- P3: Nice to have, defer to a later milestone

## Detailed Analysis: The Four Focus Questions

### (1) Dark/light mode toggles on financial/internal dashboards

Standard expectation, not a differentiator, on any tool built in the last several years — Reflex treats this as a built-in "recipe" (`rx.color_mode.button()`/`.switch()`/`.icon()`, `rx.color_mode_cond()` for conditional styling, driven by `rx.theme(appearance=...)`), with color-mode state and persistence handled by the framework rather than custom app state. The correct sequencing for this app specifically is to fix the transparent `html`/`body` background *before or alongside* adding the toggle, since the reported "black margins" symptom is consistent with a transparent background showing through in dark-mode/wide-viewport conditions — the toggle and the margin bug are very likely two views of the same root cause. (Confidence: HIGH — Reflex's own docs/recipes confirm `rx.color_mode` as the documented, current pattern.)

### (3) Tab-based section navigation on single-page dashboards

Standard pattern once a dashboard has 3+ distinct logical sections (this one has exactly three: Summary, Forecast, Data Entry) — every mainstream BI/dashboard tool defaults to tab or sidebar-section navigation over one long scroll at this content volume. Reflex's `rx.tabs.root`/`rx.tabs.list`/`rx.tabs.trigger`/`rx.tabs.content` (Radix-based) is the direct, low-complexity fit; `default_value` is enough if tab state doesn't need to survive a reload, `value` + `on_change` bound to state if it does. No new content needs to be created — this is a restructuring of existing sections, which keeps risk low. (Confidence: HIGH — confirmed against Reflex's current tabs documentation.)

### (4) Model provenance/confidence without overwhelming a non-technical user

The standard pattern across domains that show non-experts a statistical estimate (weather forecast confidence, price-estimate tools) is: **one model name + one accuracy number, translated into plain language**, not a diagnostics panel. For this app: a small caption near each forecast reading e.g. "SARIMAX — typically within ±13% of actual" accomplishes the ask (#4) without requiring the user to understand ARIMA orders, MAPE definitions, or backtest methodology. This is purely additive display work — the backtest MAPE values already exist per PROJECT.md's validated forecasting requirements (HDAN 9.4%, PPAN 10.0%, Diesel-USD 3.4%, FX 0.25%), so there's no new computation, only formatting/placement. Deeper diagnostics (AIC/BIC, residual plots, candidate-model comparison) should explicitly be treated as an anti-feature for the default view — that level of detail is for `backend_research/` artifacts, not the live dashboard, given the explicitly non-technical procurement/finance audience.

### (6) Date-entry UX fix for the diagnosed silent-validation-error bug

This is a well-documented, well-solved UX problem class (Nielsen Norman Group's "Date-Input Form Fields" guidance and current date-input pattern libraries agree): **free-text date fields are inherently error-prone for exactly the failure mode already diagnosed here** — a user types a plausible-looking date in an unexpected format, and the field either silently rejects it or (worse) silently misinterprets it. The standard, best-practice fix for a non-technical user in a monthly-cadence entry table is to **remove the free-text failure mode entirely** rather than improve error messaging on top of it:

- **Primary fix:** use a native/structured date input — Reflex's `rx.input(type="date")` renders the browser's built-in HTML5 date input, which provides a calendar-picker widget and always returns an unambiguous, correctly-formatted date value. This eliminates format-guessing and silent rejection by construction, not by better validation messages.
- **Secondary/defense-in-depth:** if any path still allows manual text entry (e.g. a fallback for browsers/environments where the native picker renders as plain text, or a paste path), add explicit, specific inline error messaging per NN/g guidance ("Invalid date format, use YYYY-MM-DD" rather than a generic "Invalid input"), and never silently discard user input.
- **Scope note:** flagged in the milestone as needing "deep research" because the blast radius extends beyond the single input field — the same date-parsing assumptions likely exist in the CSV bulk-import path added in v1.2 and in however dates are currently stored/round-tripped through the SQLite `rx.Model`. Recommend treating this as its own phase with an explicit audit of every date-parsing entry point (manual add-row, manual edit-row, CSV import, Excel export round-trip) rather than a single-field prop swap.

(Confidence: HIGH for the general UX pattern — NN/g and current date-input-pattern references agree closely; HIGH for Reflex's `rx.input(type="date")` existing and wrapping the native HTML5 date input, though the exact current-version prop surface should be double-checked against the installed Reflex 0.9.8 docs during implementation rather than assumed from general web search results.)

## Sources

- https://reflex.dev/docs/recipes/others/dark-mode-toggle/ — Reflex's official dark-mode-toggle recipe — HIGH confidence
- https://reflex.dev/docs/styling/theming/ — `rx.theme`, `appearance` prop, color-mode mechanics — HIGH confidence
- https://reflex.dev/docs/library/disclosure/tabs/ — `rx.tabs.root`/`list`/`trigger`/`content` API — HIGH confidence
- https://www.nngroup.com/articles/date-input/ — Nielsen Norman Group, "Date-Input Form Fields: UX Design Guidelines" — HIGH confidence (authoritative UX research org)
- https://uxpatterns.dev/patterns/forms/date-input — current date-input pattern reference (masks, native pickers, error messaging) — MEDIUM confidence
- General web search on native HTML5 date input as the standard fix for free-text date parsing failures — MEDIUM confidence (framework-specific `rx.input(type="date")` prop surface not directly confirmed against a Reflex-specific doc page in this pass; verify against installed 0.9.8 docs before implementation)
- .planning/PROJECT.md — existing validated backtest MAPE figures, existing feature inventory (Summary/Forecast/Data Entry sections, CSV bulk import, Excel export), milestone feedback list — HIGH confidence (primary project source)

---
*Feature research for: Prediction Dashboard v1.3 (Dashboard Polish & Data-Entry Rework)*
*Researched: 2026-08-24*
