# Stack Research

**Domain:** v1.3 UI polish additions to an existing Reflex 0.9.8.post1 dashboard (dark/light toggle, layout bug fix, tab nav, chart fix, date-input UX)
**Researched:** 2026-08-24
**Confidence:** HIGH (all findings verified against the installed `reflex==0.9.8.post1` package via direct introspection, plus official Reflex docs)

No new PyPI dependencies are required for any of the five v1.3 features. Everything needed
already ships inside the installed `reflex==0.9.8.post1` package (`rx.color_mode`,
`rx.tabs`, `rx.LocalStorage`, `rx.App(style=...)`/custom stylesheets, native HTML date
input) or is a pure Plotly `go.Figure.update_layout()` tuning change in the already-shipped
`plotly==6.9.0`. This is additive component/API usage on the existing stack, not a stack
change.

## Recommended Stack

### Core Technologies (unchanged — confirmed still current, no upgrade needed)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Reflex | 0.9.8.post1 (installed, confirmed via `pip show`) | Already the app framework | All five v1.3 features are covered by APIs already present in this exact installed version — verified by introspecting `rx.color_mode`, `rx.App.__init__`, and `rx.theme()` signatures directly in the venv. No version bump needed. |
| Plotly | 6.9.0 (installed, confirmed via `pip show`) | Already renders `forecast_chart_figure` | The legend/axis overlap fix (#4) is a `go.Figure.update_layout()` margin/legend-position change, not a library capability gap — 6.9.0 already supports everything needed (`legend=dict(...)`, `margin=dict(...)`, `xaxis=dict(automargin=True)`). |

### New API Surface Being Used (part of installed Reflex, not new packages)

| API | Module | Purpose | When to Use |
|-----|--------|---------|-------------|
| `rx.color_mode` (Var) + `rx.color_mode.button()` / `.switch()` / `.icon()` | `reflex` (built-in) | Reads current mode (`"light"`/`"dark"`) and provides ready-made toggle components | Feature 1 — dark/light toggle |
| `rx.toggle_color_mode` (event, compiles to `toggleColorMode`) | `reflex` (built-in) | Event handler that flips the color mode | Feature 1 — wire to a custom toggle if not using the built-in button |
| `rx.LocalStorage` | `reflex` (built-in, `reflex.state` client-storage vars) | Declares a `str`-typed state var backed by browser `localStorage`, auto-syncs both directions | Feature 1 — persisting the toggle choice across reloads, single browser/user (matches the "survives page reloads for a single browser/user" requirement exactly; no cookie/server round-trip needed) |
| `rx.tabs.root` / `.list` / `.trigger` / `.content` | `reflex.components.radix.themes` (built-in, Radix Themes wrapper) | Controlled tabs component, `value` + `on_change` bindable to state | Feature 3 — Summary/Forecast/Data Entry section switching |
| `rx.App(style=..., stylesheets=[...])` | `reflex.app` (built-in) | Global style dict (supports arbitrary CSS selectors like `"html, body"`) or a local stylesheet asset | Feature 2 — page-level background fix (see rationale below) |
| Native `<input type="date">` via `rx.input(type="date", ...)` | `reflex.components.el` / `rx.input` | Browser-native date picker with built-in format validation and visible invalid-state affordance | Feature 5 — Data Entry date cell rework |

### Supporting Libraries

None required. No new PyPI packages for any of the five features.

## Installation

```bash
# No new installs needed — reflex==0.9.8.post1 and plotly==6.9.0 already
# provide every API surface listed above. Confirm current pins are still
# in place (no action needed unless drift detected):
pip show reflex plotly
```

## Feature-by-Feature Rationale

### 1. Dark/light mode toggle with persistence

Reflex's built-in color mode system (confirmed present via `dir(rx.color_mode)` on the
installed package: `bool, button, create, equals, guess_type, icon, is_none, is_not_none,
range, switch, to, to_string`, plus top-level `rx.toggle_color_mode` which compiles to JS
`toggleColorMode`) already gives a working toggle out of the box, driven by Radix Themes'
`appearance` mechanism.

**Constraint from the existing codebase:** `rxconfig.py` currently pins theme with
`rx.plugins.RadixThemesPlugin(theme=rx.theme(appearance="light", accent_color="blue"))`.
A hard-coded `appearance="light"` on the plugin's theme takes precedence over runtime
`rx.color_mode` toggling — this was the v1.2 fix for a dark-mode-inheritance bug and
**must not be reverted directly**. The correct v1.3 approach:
- Remove (or change to `appearance=rx.color_mode`) the hard-coded `appearance="light"` in
  the `RadixThemesPlugin`'s `rx.theme(...)` call, OR wrap `index()`'s returned component
  tree in an explicit `rx.theme(appearance=DashboardState.color_mode, ...)` at the page
  level so the toggle actually has an effect.
- `rx.theme()`'s installed signature confirms `color_mode: LiteralAppearance | None` is a
  valid kwarg on the theme component itself (separate from the plugin-level default),
  which is the idiomatic way to make appearance state-driven while keeping a sane default.
- For persistence, declare a `rx.LocalStorage`-backed var (e.g.
  `color_mode: str = rx.LocalStorage("light")`) rather than relying on Reflex's own
  internal (undocumented-persistence) color mode cookie — `rx.LocalStorage` is confirmed
  in official docs to auto-sync a string-typed state var with browser `localStorage`,
  which matches "survives page reloads for a single browser/user" precisely and needs no
  server-side session/cookie plumbing for a single-user app.
- Since the app already carries a `theme.py` design-token module (`PAGE_BG`, `SURFACE`,
  `BORDER`, etc. — all hard-coded light-mode hex values per the Phase 6 UI-SPEC), a real
  dark mode requires either (a) defining a parallel dark token set and switching between
  them via `rx.cond`/`rx.color_mode_cond`, or (b) descoping to "toggle only changes Radix's
  built-in light/dark chrome, not the custom design tokens." Flag this scope decision for
  the roadmap — it's a design-token workload, not just a wiring change.

Confidence: HIGH — verified directly against the installed 0.9.8.post1 package, not just
docs/training data.

### 2. Correct html/body-level background

Researched Radix Themes' actual (current, non-deprecated) background model: Radix Themes'
own docs confirm that **the background color deliberately lives on the `.radix-themes`
wrapper element via the `--color-background` CSS variable, not on `html`/`body`** — "Theme
does not set body background color automatically" is current, intentional Radix behavior,
not a bug in Reflex's integration. This matches the diagnosed root cause (`html`/`body`
computed `rgba(0,0,0,0)`, inner Radix wrapper divs carry the real background) — it's
expected Radix architecture that the app needs to explicitly compensate for at the
page-chrome level, since the content area doesn't fill the viewport width on all layouts.

**Recommended fix**, using only already-available `rx.App` capability (confirmed via
`inspect.signature(rx.App.__init__)` on the installed package — `style: ComponentStyle` and
`stylesheets: list[str]` are real, present kwargs):
- Add a small custom stylesheet asset (e.g. `assets/global.css`) with
  `html, body { background: #FAFAFA; }` (using the existing `PAGE_BG` token value, or a
  CSS variable if dark mode is added per feature 1), and register it via
  `rx.App(stylesheets=["/global.css"])` in `app.py`. This is the Reflex-documented pattern
  for styling root-level elements Reflex components can't reach directly (Reflex's own
  custom-stylesheets doc explicitly calls out `html`/`body`-level styling as a stylesheet,
  not `rx.App(style=...)` dict, use case).
- Alternative without a new file: `rx.App(style={"html, body": {"background": PAGE_BG}})`
  — the `style` dict is confirmed to support arbitrary CSS selector keys (docs: "CSS class
  styles like `.some-css-class`, and CSS ID styles like `#special-input`" — same mechanism
  extends to element selectors like `html, body`). Either approach works; the stylesheet
  file is slightly more conventional for a static, non-reactive style rule.
- Do **not** attempt to fix this by adding more `background=SURFACE`/`background=PAGE_BG`
  props to `rx.container`/`rx.box` wrappers in `app.py` — that's the pattern already in use
  (confirmed by grep: `SURFACE`/`PAGE_BG` background props appear ~9 times across
  `app.py`) and is precisely what produces the "inner wrapper has background, html/body
  doesn't" symptom. The fix has to target `html`/`body` directly via stylesheet/global
  style, not another wrapper-level prop.

Confidence: HIGH for the Reflex/Radix mechanism (official Radix docs + `rx.App` signature
introspection); MEDIUM on "exact CSS value to use if dark mode ships in the same
milestone" since that depends on the feature-1 scope decision above.

### 3. Tab/nav bar for section switching

`rx.tabs` (Radix Themes primitive, already bundled — no new package) is the idiomatic
choice over a hand-rolled `rx.cond`-based show/hide toggle, confirmed via official docs
(`reflex.dev/docs/library/disclosure/tabs/`):
- `rx.tabs.root(rx.tabs.list(rx.tabs.trigger(...), ...), rx.tabs.content(..., value=...),
  value=State.active_tab, on_change=State.set_active_tab)` is the controlled pattern —
  directly reusable for a `DashboardState.active_section: str` var with values
  `"summary"`/`"forecast"`/`"data_entry"`.
- Since this remains a single-route app (per the milestone framing — "no routing needed,
  just conditional rendering"), each `rx.tabs.content(...)` panel simply wraps the existing
  `forecast_summary_cards()`, `forecast_section()`, and `data_entry_section()` component
  calls already defined in `app.py` — this is a layout reorganization of `index()`, not new
  component logic.
- `rx.tabs` supports `orientation="horizontal"` (default, matches "tab bar") and
  `color_scheme` for matching the existing `ACCENT` token.

Confidence: HIGH — confirmed against official docs with a working code example.

### 4. Fan chart legend/axis overlap

No new dependency — `plotly==6.9.0` (already installed and used in `state.py`'s
`forecast_chart_figure`) fully supports the fix. The current `update_layout()` call (seen
at `app/app/state.py:629-648` for the empty-state path) already uses `margin=dict(l=40,
r=16, t=16, b=40)`; the populated-chart path (further down the same method, past line 690)
needs the equivalent treatment plus explicit legend placement. Concretely, for the
populated-series branch:
- Set `legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)` (or
  `y=-0.2` below the plot) to move the legend off the plot area entirely rather than
  Plotly's default overlapping top-right inset legend — this is almost certainly the
  overlap source given 4 traces (Historical, Bear, Bull-band fill, Base) sharing the
  default legend position.
- Add `xaxis=dict(automargin=True)` and `yaxis=dict(automargin=True, tickformat=
  NUMBER_FORMAT)` so long date/number tick labels don't get clipped or overlap the axis
  title — `automargin` is a stable, long-standing Plotly layout option, confirmed present
  in `go.Layout` for the pinned 6.9.0 install (no version gate).
- Increase `margin=dict(l=48, r=16, t=48, b=56)` (top/bottom bumped from the empty-state
  values) to make room once the legend and axis titles both need space.

Confidence: HIGH — this is standard, version-stable Plotly `go.Figure` layout API, not
Reflex-specific; no external verification needed beyond confirming 6.9.0 is what's
installed (done).

### 5. Data Entry date-input UX rework

Recommend native `rx.input(type="date", ...)` over the current custom
text-field-with-silent-validation-failure approach:
- Native `<input type="date">` (Reflex exposes this via `rx.input(type="date")`, which maps
  straight to the underlying HTML element) gives the browser's own date picker UI and — critically
  for the diagnosed root cause — the browser enforces a strict `YYYY-MM-DD` format at the
  input level, so malformed entries can't even be typed into a state var in the first
  place, unlike a free-text field that silently fails a Python-side regex/`datetime.strptime`
  check with no visible feedback.
- For any values still needing custom Python-side validation (e.g. "date not in the
  future", "date not already in the table" duplicate-check reused from the CSV-import
  duplicate-skip logic shipped in v1.2), pair the native date input with an
  `rx.cond(State.date_error != "", rx.text(State.date_error, color=DESTRUCTIVE), ...)`
  inline error message directly under the cell — using the existing `DESTRUCTIVE` token
  already defined in `theme.py` — so failures are visible rather than silent. This directly
  targets the diagnosed root cause ("draft-row date cell validation failure renders no
  visible error").
- No new package needed; this is a component-choice + inline-error-rendering pattern using
  only already-installed `reflex` and the existing `theme.py` tokens.

Confidence: MEDIUM — the native-date-input recommendation is a well-established web
pattern (not Reflex-specific), and `rx.input(type=...)` passing through to native HTML
input types is standard Reflex behavior, but the exact current Data Entry table cell
editor implementation wasn't read in full during this stack-focused pass — the phase
implementer should confirm the current draft-row cell component before swapping input
type (this is a UI-pattern/UX decision the roadmap should flag for a components-level look,
not a stack gap).

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `rx.LocalStorage` for color-mode persistence | `rx.Cookie` | Only if the toggle preference needs to be readable server-side on initial page load (e.g. to server-render the correct theme before JS hydrates) — not needed here since this is a single-user, single-process, client-rendered SPA-style app; `rx.LocalStorage` is simpler and matches the stated requirement exactly. |
| Stylesheet asset (`assets/global.css` + `rx.App(stylesheets=[...])`) for html/body background | `rx.App(style={"html, body": {...}})` inline dict | Use the inline `style` dict instead if the background needs to be *dynamically* state-driven (e.g. changes live with the dark-mode toggle) rather than a static CSS rule — a plain stylesheet can't reference Reflex state. If feature 1 and feature 2 ship together and the bg must follow color mode, prefer the inline `style` dict (or a `--color-background`-driven CSS variable already following Radix's own color-mode switching) over a static stylesheet. |
| `rx.tabs` (Radix Themes) | `rx.segmented_control` | If the "tab bar" should look more like a pill/segmented toggle (iOS-style) rather than traditional underlined tabs — same underlying controlled-value pattern (`value`/`on_change`), purely a visual choice. Radix `rx.tabs` was chosen here because it also natively supports `rx.tabs.content` panel semantics (ARIA `tabpanel` roles), which `rx.segmented_control` does not provide out of the box — better accessibility default for a nav bar that's actually swapping content, not just picking a value. |
| Native `rx.input(type="date")` | Custom masked text input (e.g. a JS date-mask library) | Only if the product needs a custom date format not supported by native date inputs (e.g. non-ISO display format) — adds a real new dependency and complexity the diagnosed bug doesn't require; native input directly fixes the silent-failure root cause with zero new dependencies. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| A new component library (e.g. `react-datepicker`, custom npm date-picker package) for feature 5 | Reflex is Python-only per project constraints; pulling in a bespoke JS component adds build complexity and violates the "no JS build tooling" constraint already established in the validated stack (see project STACK.md's "What NOT to Use" for the split-frontend prohibition) | Native `rx.input(type="date")`, already covered by Reflex's HTML element passthrough |
| Editing only `rx.box`/`rx.container` `background=` props to fix the html/body bug | This is the exact pattern already present ~9 times in `app.py` and is what produces the bug (inner-wrapper-only background, `html`/`body` still transparent) — adding more of the same prop doesn't reach the `html`/`body` elements at all | Global stylesheet or `rx.App(style={"html, body": {...}})`, which targets the actual transparent elements |
| Reverting `RadixThemesPlugin(theme=rx.theme(appearance="light", ...))` back to a fully dynamic/system-detected appearance without a persisted override | This plugin-level pin was the deliberate v1.2 fix for a dark-mode-inheritance bug (per CLAUDE.md) — removing it outright without adding the `rx.LocalStorage`-backed override in its place would very likely reintroduce that regression | Keep a light default at the plugin level, but make it override-able by binding `appearance=` on a page-level `rx.theme(...)` to the persisted `color_mode` state var (see feature 1 rationale) |
| Plotly's default auto-positioned legend for a 3-4 trace fan chart | Confirmed the likely direct cause of the reported axis-label/legend overlap — Plotly's implicit legend defaults to an inset top-right position that collides with plot content/axis labels once multiple traces and tight `margin` values (already `t=16` in the empty-state branch) are combined | Explicit `legend=dict(orientation="h", y=1.02, ...)` placement plus `automargin=True` on both axes |

## Stack Patterns by Variant

**If dark mode's design tokens are scoped into v1.3 (not deferred):**
- Extend `theme.py` with a parallel dark-mode token set (e.g. `PAGE_BG_DARK`,
  `SURFACE_DARK`, etc.) and switch between them in `app.py` via `rx.color_mode_cond(light,
  dark)` per token, rather than hard-coding a second theme module — keeps a single source
  of truth per the existing `theme.py` docstring's stated design ("no scattered literals").
- Because the file's own docstring states changing a constant is "a design-contract change,
  not a routine code edit" — this should go through the UI-SPEC contract process the phase
  already established (06-UI-SPEC.md pattern), not an ad hoc addition.

**If dark mode's design tokens are explicitly deferred (toggle affects Radix chrome only):**
- Wire `rx.color_mode` + `rx.LocalStorage` per feature 1, but leave `theme.py`'s hard-coded
  hex values untouched — document this as a known limitation ("toggle changes Radix
  primitives' light/dark styling; custom card/chart surfaces remain light-themed") so it's
  an explicit scope decision, not a bug discovered post-ship.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| reflex==0.9.8.post1 | `rx.color_mode`, `rx.tabs`, `rx.LocalStorage`, `rx.App(style=/stylesheets=)` | All confirmed present via direct introspection (`inspect.signature`, `dir()`) of the installed package on 2026-08-24 — no upgrade needed for any v1.3 feature. |
| plotly==6.9.0 | `go.Layout(legend=..., margin=..., xaxis=dict(automargin=True))` | Standard, long-stable Plotly layout API; no version gate for any option used in the feature-4 fix. |
| RadixThemesPlugin(theme=rx.theme(appearance="light")) | Runtime `rx.color_mode` toggling | These two currently conflict (plugin-level pin overrides runtime toggle) — feature 1 implementation must explicitly reconcile them per the rationale above, not just add a toggle button and assume it works. |

## Sources

- Direct introspection of installed `reflex==0.9.8.post1` package (`pip show`, `dir(rx.color_mode)`, `inspect.signature(rx.App.__init__)`, `inspect.signature(rx.theme)`) — HIGH confidence, ground truth for this exact project's environment
- https://reflex.dev/docs/client-storage/overview/ — confirmed `rx.LocalStorage`/`rx.Cookie` string-var sync behavior — HIGH confidence
- https://reflex.dev/docs/library/disclosure/tabs/ — confirmed `rx.tabs.root/list/trigger/content` controlled-value pattern with code example — HIGH confidence
- https://reflex.dev/docs/styling/custom-stylesheets.md (GitHub source) and `rx.App.__init__` signature — confirmed `stylesheets=[...]` and `style={...}` support arbitrary CSS selectors including element selectors like `html, body` — HIGH confidence
- https://www.radix-ui.com/themes/docs/overview/releases — confirmed current Radix Themes background-color model (`.radix-themes` wrapper via `--color-background`, not `html`/`body` by design; `hasBackground`/`appearance` interaction) — MEDIUM-HIGH confidence (official Radix docs, cross-referenced with the project's own diagnosed symptom)
- Existing project files read directly: `app/rxconfig.py`, `app/app/theme.py`, `app/app/state.py` (lines 585-690), `app/app/app.py` (lines 160-727) — HIGH confidence, ground truth for integration points
- `.planning/PROJECT.md` — milestone scope and constraints — HIGH confidence

---
*Stack research for: Prediction Dashboard v1.3 (Dashboard Polish & Data-Entry Rework)*
*Researched: 2026-08-24*
