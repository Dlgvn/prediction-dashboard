# Phase 11: Background Fix + Theme Toggle - Research

**Researched:** 2026-08-24
**Domain:** Reflex 0.9.8.post1 runtime color-mode/appearance API, Radix Themes background model, dual-token design systems
**Confidence:** HIGH (all core mechanism claims verified by reading the actual installed package source, not docs/training data)

## Summary

The phase's central open question — "what is the exact Reflex 0.9.8.post1 API for toggling
Radix Themes' `appearance` at runtime?" — is answered directly by reading the installed
`reflex_base`/`reflex_components_radix` source (`app/.venv/lib/python3.12/site-packages/...`).

Three load-bearing facts, all `[VERIFIED: source]`:

1. **`rx.Config(default_color_mode=...)`** (a top-level `rxconfig.py` kwarg, NOT nested
   inside `RadixThemesPlugin`/`rx.theme(...)`) is what controls the app's color mode on a
   fresh browser with no stored preference. It defaults to `"system"` when unset — **this
   is almost certainly why the OS-inheritance bug existed in the first place**, since
   `rxconfig.py` today never sets it.
2. **`rx.theme(appearance="light", ...)`'s `appearance` prop is stripped from the rendered
   output** by `Theme._render()` (`.remove_props("appearance")`) in the installed
   `reflex_components_radix` package. It has **no effect on the actual DOM** in this
   installed version. The current build-time pin in `rxconfig.py` is very likely a
   no-op for the mechanism that actually paints the page (see Pitfall 1 below for why the
   original v1.2 fix probably worked anyway, and why it can't be trusted to keep working).
3. Radix's actual light/dark DOM class (`.radix-themes.light` / `.radix-themes.dark`) is
   set by an **always-injected** `RadixThemesColorModeProvider` component (auto-added via
   `RadixThemesComponent._get_app_wrap_components()`, priority 45 — present automatically
   whenever `RadixThemesPlugin` is used, no explicit wiring required) that reads
   `resolvedTheme` from React's `ColorModeContext` and applies it as a class on
   `document.querySelector('.radix-themes[data-is-root-theme="true"]')`.

`ColorModeContext` itself (`react-theme.js`, installed template, read directly) already
implements exactly what D-01/D-03 ask for: it reads/writes `localStorage.getItem("theme")`
automatically, needs no extra `rx.LocalStorage` var for the *page chrome* concern, and its
initial value (before any localStorage entry exists) is the compiled `defaultColorMode`
constant, which comes straight from `default_color_mode` in `rx.Config`.

**Primary recommendation:** Set `default_color_mode="light"` in `rx.Config(...)`
(rxconfig.py). Wire the toggle to Reflex's built-in `rx.toggle_color_mode` /
`rx.color_mode.switch()`/`.button()` for the Radix-chrome half of the problem (satisfies
THEME-02/THEME-03 practically for free). Because the *custom* `theme.py` tokens and the
server-computed Plotly figures cannot read the JS-only `ColorModeContext` from Python
`@rx.var` code, introduce **one** backend-readable source of truth — a
`rx.LocalStorage`-backed state var (its own key, e.g. `"pd_theme_mode"`) — and toggle it in
the *same* event chain as `rx.toggle_color_mode`, so both stay in lockstep. Do not rely on
`appearance="inherit"` or on the config's `"system"` default anywhere in the diff (D-02).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Radix chrome light/dark (buttons, inputs, borders) | Browser / Client (React context) | — | `RadixThemesColorModeProvider` + `ColorModeContext` swap DOM classes client-side; no backend round-trip needed or possible |
| Custom design tokens (`theme.py` PAGE_BG/SURFACE/etc.) selection | Frontend Server (Reflex backend state, computed at render) | Browser (localStorage persistence) | These are raw hex literals fed into Python-rendered props/Plotly figures — must be resolved server-side via a backend-readable state var, not the JS-only ColorModeContext |
| Plotly figure colors (`font.color`, `plot_bgcolor`→ font only, since bgcolor stays transparent) | Frontend Server (`@rx.var` figure builders in `state.py`) | — | Figures are built as Python `go.Figure` objects in `DashboardState`; must read the same backend mode var as `theme.py` token selection |
| `html`/`body` background | Browser / Client (global CSS / `rx.App` style) | Frontend Server (must reference the correct mode-aware token at compile/render time) | Radix explicitly does not set `html`/`body` background — confirmed by architecture (background lives on `.radix-themes` wrapper via `--color-background`); app must inject its own CSS reaching `html`/`body` |
| Theme preference persistence | Browser / Client (localStorage) | — | D-01 explicitly rules out server-side `AppSetting` DB storage; localStorage is also what Reflex's own `ColorModeContext` already uses |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| reflex | 0.9.8.post1 (installed, confirmed via `.venv` introspection) | Framework already in use | No new dependency — all needed APIs (`rx.Config.default_color_mode`, `rx.color_mode`, `rx.toggle_color_mode`, `rx.set_color_mode`, `rx.LocalStorage`, `rx.color_mode_cond`) ship in the exact installed version, verified by reading source, not just `pip show` |

No new packages are installed by this phase. **Package Legitimacy Audit is not applicable** — nothing new is added to `requirements`/`pyproject`.

## Package Legitimacy Audit

Not applicable — this phase installs no new external packages. All APIs used are part of
the already-installed `reflex==0.9.8.post1` distribution (confirmed via direct
introspection of `app/.venv/lib/python3.12/site-packages/reflex_base` and
`reflex_components_radix`).

## Architecture Patterns

### System Architecture Diagram

```
Browser (first load, no localStorage["theme"])
   │
   ▼
compiled `defaultColorMode` constant  <───── rx.Config(default_color_mode="light")  [rxconfig.py, NEW]
   │
   ▼
ThemeProvider (react-theme.js, built into Reflex)
   │  reads localStorage["theme"] if present, else uses defaultColorMode
   │  exposes: color_mode (raw) / resolved_color_mode ("light"|"dark") / toggle_color_mode (event)
   ▼
ColorModeContext (React context, always mounted)
   │
   ├──► RadixThemesColorModeProvider (auto-injected by RadixThemesPlugin)
   │        swaps `.radix-themes` DOM class light/dark  ─────► Radix chrome (buttons, inputs, panel borders)
   │
   └──► rx.color_mode.switch()/.button() UI control (header toggle, D-04)
            on click → fires `rx.toggle_color_mode` (flips ColorModeContext + localStorage["theme"])
            SAME on_click ALSO fires DashboardState.toggle_theme_mode
                 │
                 ▼
       DashboardState.theme_mode: str = rx.LocalStorage("light", name="pd_theme_mode")  [NEW backend var]
                 │  backend-readable, own localStorage key, kept in lockstep with the toggle click
                 ▼
       ┌─────────────────────────────────────────────────────────┐
       │ Frontend Server (Reflex backend, Python)                  │
       │  - theme.py dual-token lookup keyed by DashboardState.theme_mode │
       │  - historical_chart_figure / forecast_chart_figure         │
       │    read DashboardState.theme_mode to pick font/line colors │
       │  - app.py background=/border= props resolve mode-aware     │
       │    token via DashboardState.theme_mode                     │
       └─────────────────────────────────────────────────────────┘
                 │
                 ▼
       rx.App(style={"html, body": {"background": <token>}})  ─────► html/body background (THEME-01)
       (must be Var-driven off DashboardState.theme_mode, not a static hex)
```

### Recommended Project Structure
```
app/app/
├── theme.py       # dual-tokenized: LIGHT = {...}, DARK = {...} dict, or *_LIGHT/*_DARK constant pairs
├── state.py        # DashboardState.theme_mode (rx.LocalStorage), toggle_theme_mode() event, figure builders read it
├── app.py           # header toggle control (D-04), background props resolve via DashboardState.theme_mode
└── rxconfig.py       # default_color_mode="light" added to rx.Config(...)
```

### Pattern 1: Config-level default (not theme-plugin-level)
**What:** Set the app's pre-first-visit color mode via `rx.Config(default_color_mode="light")`.
**When to use:** Always, for this app — never leave it at the framework default (`"system"`).
**Example:**
```python
# Source: app/.venv/lib/python3.12/site-packages/reflex_base/config.py:258
# (installed package source, read directly)
import reflex as rx

config = rx.Config(
    app_name="app",
    db_url="sqlite:///reflex.db",
    default_color_mode="light",   # NEW — was implicitly "system" (unset)
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(accent_color="blue")  # appearance= removed — it is a no-op
        ),
    ],
)
```

### Pattern 2: Dual-write toggle (Radix chrome + backend token var, kept in lockstep)
**What:** One click handler fires two things together: Reflex's built-in
`rx.toggle_color_mode` (drives Radix chrome via ColorModeContext) AND a backend
`rx.LocalStorage`-backed state var (drives Python-computed colors: `theme.py` token
selection, Plotly figure colors, `html`/`body` background).
**When to use:** Any time server-rendered content (not just Radix's own components) needs
to be mode-aware — this app has both (custom hex tokens in `theme.py`, Plotly `go.Figure`
objects built in Python).
**Example:**
```python
# state.py
class DashboardState(rx.State):
    # Own localStorage key — deliberately NOT the same key Reflex's built-in
    # ColorModeContext uses ("theme"), to avoid the two mechanisms fighting
    # over one key's value/format.
    theme_mode: str = rx.LocalStorage("light", name="pd_theme_mode")

    def toggle_theme_mode(self) -> None:
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"

# app.py
rx.el.button(
    rx.color_mode.icon(),
    on_click=[DashboardState.toggle_theme_mode, rx.toggle_color_mode],
    aria_label="Toggle dark mode",
)
```

### Pattern 3: `theme.py` dual-token lookup
**What:** Replace flat constants with a mode-keyed lookup, resolved by
`DashboardState.theme_mode` at render/compute time — not `rx.color_mode_cond` for the
Plotly figure builders (which run in plain Python, not JSX), though `rx.color_mode_cond`
remains valid for purely presentational `app.py` component props if desired for the Radix
chrome.
**Example:**
```python
# theme.py — keep dependency-free; add a lookup function instead of plain module constants
LIGHT = {
    "PAGE_BG": "#FAFAFA", "SURFACE": "#FFFFFF", "BORDER": "#8E9096",
    "ACCENT": "#2563EB", "ACCENT_FILL": "rgba(37,99,235,0.15)",
    "DESTRUCTIVE": "#DC2626", "NEUTRAL_LINE": "#697177",
    "UP": "#15803D", "DOWN": "#DC2626", "MUTED_TEXT": "#71717A",
}
DARK = {
    "PAGE_BG": "#18181B", "SURFACE": "#27272A", "BORDER": "#52525B",
    # ... measure and record contrast ratios per the existing amendment-comment convention
}

def tokens(mode: str) -> dict:
    return DARK if mode == "dark" else LIGHT
```
```python
# state.py figure builder — reads DashboardState.theme_mode, resolves tokens() once
from app.theme import tokens

@rx.var
def historical_chart_figure(self) -> go.Figure:
    t = tokens(self.theme_mode)
    ...
    font=dict(size=14, color=t["MUTED_TEXT"]),
```

### Anti-Patterns to Avoid
- **Setting `appearance="inherit"` anywhere** (Theme kwarg, `rx.theme(color_mode=...)`, or
  raw prop) — reintroduces OS-inheritance exactly as PITFALLS.md Pitfall 1 describes.
- **Trusting `rx.theme(appearance="light")` to do anything at runtime** — verified it is
  stripped from render output by `Theme._render()` in the installed package. Relying on it
  as the "already fixed" mechanism (as CONTEXT.md's canonical refs imply v1.2 did) is not
  safe going forward.
- **Adding a second, independent theme-mode state var that isn't synced with
  `rx.toggle_color_mode`'s click** — creates exactly the "Radix chrome went dark but custom
  surfaces stayed light" bug class Pitfall 1 describes, just via a new code path instead of
  the old `appearance="inherit"` path.
- **Using `rx.Cookie` or a DB-backed `AppSetting` row for theme persistence** — explicitly
  ruled out by CONTEXT.md D-01.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Detecting/persisting the toggle choice across reloads for Radix's own chrome | A custom cookie/localStorage read-write hook | Reflex's built-in `ColorModeContext` (`rx.toggle_color_mode`, `rx.color_mode`, `rx.set_color_mode`) | Already ships in the installed package, already handles first-render/localStorage race conditions (`isInitialized` guard in `react-theme.js`), already exposed as `rx.color_mode.switch()`/`.button()` ready-made components |
| A light/dark icon toggle button | Hand-rolled icon + conditional | `rx.color_mode.icon()` / `rx.color_mode.button()` | Pre-built, pre-wired to `toggle_color_mode`, ARIA-safe defaults |

**Key insight:** Reflex's color-mode system already solves persistence and the Radix-chrome
half of this phase completely — the only genuinely new engineering work is (1) turning on
`default_color_mode="light"` (currently unset → defaults to the exact bug class this phase
must prevent), and (2) bridging that client-only mechanism to the app's Python-computed
custom tokens/Plotly colors, since the backend cannot read `ColorModeContext` directly.

## Common Pitfalls

### Pitfall 1: Assuming the current `appearance="light"` pin is what protects against OS-inheritance
**What goes wrong:** STATE.md's decision log and PITFALLS.md both describe the v1.2 fix as
"pinned Radix theme to appearance=light in rxconfig.py plugins." Reading the installed
`Theme._render()` source shows `appearance` is `.remove_props("appearance")`-stripped from
the rendered tag — it cannot be what's currently preventing OS-dark-mode inheritance in
production. The actual protection today, if any exists at all, would have to come from
`rx.Config.default_color_mode`, which is **not set** anywhere in the current `rxconfig.py`
(confirmed by reading the file — only `app_name`, `db_url`, `plugins` are set), meaning it
silently defaults to `"system"`.
**Why it happens:** `Theme._render()`'s prop-stripping behavior is an internal
implementation detail not documented in the Theme component's own docstring (which still
describes `appearance` as "Override light or dark mode theme") — easy for a contributor
(or a prior AI-assisted session) to reasonably believe the plugin-level prop was load-bearing.
**How to avoid:** Do not re-verify this fix by reading `rx.theme()`'s docstring alone — the
plan MUST include actually setting `default_color_mode="light"` in `rx.Config(...)`, and a
verification step that reproduces the original bug scenario (OS/browser set to prefers-dark,
localStorage cleared, fresh load) to confirm the page renders light, not just that
`appearance="light"` is present in the source diff.
**Warning signs:** A diff that only touches `rx.theme(appearance=...)` without also adding
`default_color_mode` to `rx.Config(...)`.

### Pitfall 2: Backend Python code can't read `resolved_color_mode`
**What goes wrong:** `resolved_color_mode`/`color_mode`/`toggle_color_mode` are all special
`Var` objects that resolve via `useContext(ColorModeContext)` in the browser — they have no
Python-side value a `@rx.var` (like `historical_chart_figure`) can read at compute time.
Attempting `if self.resolved_color_mode == "dark":` inside a backend method will fail (no
such backend attribute exists) or silently do the wrong thing if someone tries to smuggle
the Var itself into Python control flow.
**Why it happens:** The naming (`rx.color_mode`) suggests a normal readable state field;
it's actually closer to a template-only expression.
**How to avoid:** Use Pattern 2 above — a dedicated `rx.LocalStorage`-backed backend state
var (`DashboardState.theme_mode`) as the one source of truth Python code can read, kept in
lockstep with the built-in toggle via a combined event chain on every click.
**Warning signs:** Any `state.py` code referencing `rx.color_mode`, `resolved_color_mode`,
or `rx.toggle_color_mode` outside of `app.py` component wiring.

### Pitfall 3 (carried from PITFALLS.md, re-confirmed against source): Un-tokenized Plotly figures
See PITFALLS.md Pitfall 1's Plotly-specific note — `historical_chart_figure` and
`forecast_chart_figure` in `state.py` currently hardcode `font=dict(color=MUTED_TEXT)`
(imported directly from `theme.py`, not mode-aware). Confirmed still true by direct read of
`state.py` in this research pass (lines 248, 271, 637, 727 all reference the flat
`MUTED_TEXT` import). Must switch to `tokens(self.theme_mode)["MUTED_TEXT"]` per Pattern 3.

### Pitfall 4 (carried from PITFALLS.md Pitfall 2, re-confirmed): `html`/`body` background must be mode-aware from day one
Since the background fix and the toggle ship in the same phase (per CONTEXT.md's explicit
bundling rationale), the `rx.App(style={"html, body": {...}})` (or stylesheet) fix must
reference `DashboardState.theme_mode`-driven token from the start — a static hex here
becomes an immediate half-fixed bug the moment dark mode is reachable via the toggle.
Confirmed `rx.App.__init__` accepts `style: ComponentStyle` (dict) which supports Var
values, so `style={"html, body": {"background": DashboardState.theme_mode_page_bg}}` type
wiring (via a computed `@rx.var` returning the resolved hex) is the correct mechanism —
plain stylesheets (`assets/global.css`) cannot reference backend state and should NOT be
used here (this rules out one of the two options STACK.md's Alternatives table offered,
now that dark mode is confirmed in-scope for the same phase).

## Code Examples

### `rx.App` background bound to backend state
```python
# Source: inspect.signature(rx.App.__init__) on installed reflex==0.9.8.post1 —
# confirms `style: ComponentStyle` accepts arbitrary CSS selector keys, including
# element selectors, and that values may be Vars (per reflex_base/style.py's
# convert()/Style handling of Var values).
app = rx.App(
    style={"html, body": {"background": DashboardState.page_bg}},
)
```
Where `DashboardState.page_bg` is a small `@rx.var` (`return tokens(self.theme_mode)["PAGE_BG"]`).

### Built-in toggle button wired to both mechanisms
```python
# app.py, near the "Prediction Dashboard" heading per D-04
rx.hstack(
    rx.heading("Prediction Dashboard", size="9", as_="h1"),
    rx.color_mode.button(
        allow_system=False,   # D-02: never expose a "system" option
        on_click=DashboardState.toggle_theme_mode,  # fires alongside toggle_color_mode internally
    ),
    align="center",
    justify="between",
    width="100%",
)
```
Note: `ColorModeIconButton.create()` (source read directly,
`reflex_components_radix/themes/color_mode.py`) already wires `on_click=toggle_color_mode`
internally and supports `allow_system=True/False` (default `False` — confirmed already
matches D-02's "toggle only, no system option" requirement out of the box). Passing an
*additional* `on_click=DashboardState.toggle_theme_mode` requires verifying Reflex merges
multiple `on_click` sources into one event chain rather than one overriding the other — if
`ColorModeIconButton` doesn't accept an extra `on_click` prop cleanly (it may not, since its
`create()` hardcodes `on_click=toggle_color_mode` and doesn't expose an "additional events"
param), the safer implementation is a **plain custom button** (not `rx.color_mode.button()`)
built from `rx.icon_button(rx.color_mode.icon(), on_click=[DashboardState.toggle_theme_mode, rx.toggle_color_mode])`,
giving explicit control over the event chain. **Flagging this as an implementation detail
the planner/implementer must verify against the actual `IconButton`/IconButton.create prop
merging behavior before committing to `rx.color_mode.button()` verbatim** — the custom
`rx.icon_button` + explicit two-item `on_click` list is the safer, more certain path.

## State of the Art

| Old Approach (CONTEXT.md/STACK.md's initial guess) | Actual Verified Mechanism | When Discovered | Impact |
|--------------------------------------------------|---------------------------|------------------|--------|
| "Remove/override `appearance=\"light\"` at the theme-plugin level to enable runtime toggling" | `appearance` is stripped from render entirely; irrelevant to runtime behavior | This research pass (source read) | Planner must not spend effort reconciling `rx.theme(appearance=...)` with the toggle — it's a dead prop for this purpose. Real lever is `rx.Config.default_color_mode` |
| "Use a single `rx.LocalStorage`-backed `color_mode` var to drive both Radix appearance and custom tokens" (STACK.md) | Radix appearance is driven by Reflex's own built-in `ColorModeContext`/`localStorage["theme"]`, entirely separate from any custom state var; a custom `rx.LocalStorage` var is still needed, but only for the *custom* Python-side tokens, and must be kept in lockstep via a combined event, not treated as the single source Radix itself reads | This research pass (source read) | Two localStorage keys will exist (Reflex's own `"theme"` + the app's custom key) — both must always be toggled together; document this explicitly so a future phase doesn't "simplify" by removing one |

**Deprecated/outdated:** N/A — no version changes involved, this is a correction of the
prior research pass's inference (STACK.md/PITFALLS.md), not an ecosystem change.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | The original v1.2 Phase 6 "appearance=light pin" fix actually worked in production despite `appearance` being stripped from render (i.e., some other mechanism, e.g. `default_color_mode` implicitly resolving to a browser default, or the bug report predates this exact installed package version's stripping behavior) | Pitfall 1 | If wrong, the historical bug's true root cause is still not fully understood — recommend the plan include an explicit before/after manual repro (OS set to dark, clear localStorage, load page) rather than trusting either this research's or the prior session's narrative |
| A2 | `rx.icon_button` cleanly accepts a two-item `on_click=[StateEvent, rx.toggle_color_mode]` list and fires both in order | Code Examples | If wrong, the toggle could silently only flip one of the two tracked states, reintroducing the Radix-chrome/custom-token mismatch (Pitfall 1's core failure mode) — planner should have the implementer manually verify this in a running dev server before treating it as done |
| A3 | Exact dark-mode hex values are not yet determined — CONTEXT.md D-03 leaves them to discretion, contrast-measured during implementation | Pattern 3 example | Low — explicitly flagged as placeholder/example values, not a locked palette |

## Open Questions

1. **Does `ColorModeIconButton`/`rx.color_mode.button()` support merging an extra `on_click` handler, or does it override?**
   - What we know: `ColorModeIconButton.create()` source (read directly) hardcodes
     `on_click=toggle_color_mode` inside `IconButton.create(ColorModeIcon.create(), on_click=toggle_color_mode, **props)` and doesn't `props.setdefault("on_click", ...)` — meaning passing `on_click=` in `**props` from a caller (e.g. `rx.color_mode.button(on_click=DashboardState.toggle_theme_mode)`) would raise a `TypeError` (duplicate keyword) rather than merge.
   - What's unclear: Whether Reflex's Component `**props` machinery might reconcile a duplicate before reaching `IconButton.create`.
   - Recommendation: Skip `rx.color_mode.button()` for the dual-write requirement; use a plain `rx.icon_button(rx.color_mode.icon(), on_click=[DashboardState.toggle_theme_mode, rx.toggle_color_mode])` instead, which is unambiguous and directly testable.

2. **Exact CSS variable Radix uses for its own background (`--color-background`) — should `html`/`body`'s background token be identical to `SURFACE`'s dark value, or a separate darker "page" shade?**
   - What we know: light mode already distinguishes `PAGE_BG` (#FAFAFA) from `SURFACE`
     (#FFFFFF) — a subtle page-vs-card contrast.
   - What's unclear: Whether Radix's own dark-mode `--color-background` (driven by the
     `.dark` class) matches a suitable `PAGE_BG_DARK` automatically, or if a custom value
     independent of Radix's palette is needed to preserve the light mode's page/card
     distinction.
   - Recommendation: During implementation, inspect Radix's computed `--color-background`
     in dark mode via devtools and decide whether to reuse it or hand-pick per D-03's
     "small, hand-picked bespoke palette" instruction (D-03 already leans toward hand-picking).

## Environment Availability

Not applicable — this phase has no external service/tool dependencies beyond the already
verified local Python venv (`app/.venv`) and the already-installed `reflex` package.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed in `app/.venv`, used by prior phases per STATE.md's plan history, e.g. Phase 6/10 test files) |
| Config file | none found in `app/` root during this pass — assume pytest defaults (`app/tests/` or colocated `test_*.py`); implementer should confirm actual layout at plan time |
| Quick run command | `cd app && ./.venv/bin/pytest -k theme or -k color_mode -x` (once tests are added) |
| Full suite command | `cd app && ./.venv/bin/pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|-------------|
| THEME-01 | html/body renders a mode-aware color, no transparent margins | manual/browser (`getComputedStyle`) + unit test on `DashboardState.page_bg` value per mode | `pytest -k page_bg` | Wave 0 — new test |
| THEME-02 | User can toggle light/dark from UI | manual browser click-through (Reflex UI interaction not unit-testable without a browser harness) | manual | N/A |
| THEME-03 | Theme persists across reload | manual browser (reload, verify localStorage + rendered class) | manual | N/A |
| THEME-04 | Every color token has a dark counterpart, WCAG AA | unit test asserting `tokens("dark")` has the same key set as `tokens("light")`, plus a contrast-ratio check per existing Phase 6 pattern | `pytest -k theme_tokens` | Wave 0 — extend existing WCAG test from Phase 6 if present |

### Sampling Rate
- **Per task commit:** targeted `pytest -k theme`
- **Per wave merge:** full suite
- **Phase gate:** full suite green + a manual browser check (OS set to dark, localStorage
  cleared, fresh load must render light; toggle must flip both Radix chrome and custom
  surfaces/Plotly text together; reload must preserve the choice) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_theme_tokens.py` (or equivalent existing test file extension) — covers
  THEME-04's key-parity + contrast-ratio assertions for the new `DARK` token dict
- [ ] No test harness currently exercises `rx.Config`/compiled JS behavior (`default_color_mode`,
  localStorage race) — this is inherently a manual/browser verification, not automatable
  with pytest; document this explicitly as a human checkpoint task in the plan

## Project Constraints (from CLAUDE.md)

- Tech stack constraint: Reflex (Python-only), SQLite via `rx.Model`. This phase adds no
  new dependency, consistent with the constraint.
- GSD workflow enforcement: file-changing work must go through a GSD command
  (`/gsd-execute-phase` etc.) — not directly relevant to research output, noted for the
  planner/implementer.
- Data cadence / model provenance constraints (weekly forecasting, backtest-before-ship) are
  unrelated to this phase's scope.

## Sources

### Primary (HIGH confidence — direct read of installed package source)
- `app/.venv/lib/python3.12/site-packages/reflex_base/config.py` (lines ~180, ~258, ~418) — `default_color_mode` field, default `"system"`
- `app/.venv/lib/python3.12/site-packages/reflex_base/style.py` (full file read) — `color_mode`/`resolved_color_mode`/`toggle_color_mode`/`set_color_mode` Var definitions, `ColorModeContext` wiring
- `app/.venv/lib/python3.12/site-packages/reflex_base/.templates/web/utils/react-theme.js` (full file read) — `ThemeProvider` implementation: localStorage read/write ("theme" key), `defaultColorMode` fallback, `toggleColorMode` semantics
- `app/.venv/lib/python3.12/site-packages/reflex_base/.templates/web/components/reflex/radix_themes_color_mode_provider.js` (full file read) — confirms `.radix-themes` root DOM class swap driven by `resolvedTheme`
- `app/.venv/lib/python3.12/site-packages/reflex_components_radix/themes/base.py` (full file read) — `Theme` component: `appearance` prop **stripped** in `_render()`, `_get_app_wrap_components()` auto-injecting the color mode provider
- `app/.venv/lib/python3.12/site-packages/reflex_components_radix/themes/color_mode.py` (full file read) — `ColorModeIconButton`/`ColorModeSwitch`/`ColorModeIcon` implementations, `allow_system` default `False`
- `app/.venv/lib/python3.12/site-packages/reflex_base/compiler/templates.py` (grepped) — confirms `defaultColorMode` is compiled from `default_color_mode` config into the JS `ThemeProvider` wrapper

### Secondary (project files, HIGH confidence, read directly)
- `.planning/phases/11-background-fix-theme-toggle/11-CONTEXT.md` — locked decisions D-01..D-04
- `.planning/REQUIREMENTS.md` — THEME-01..04 definitions
- `.planning/STATE.md` — v1.2 Phase 6 decision log entry describing the (now-shown-to-be-non-functional) `appearance="light"` pin
- `.planning/research/STACK.md`, `.planning/research/PITFALLS.md` — milestone-level research, cross-referenced and corrected where installed-source evidence contradicted their inferences
- `app/rxconfig.py`, `app/app/theme.py`, `app/app/app.py`, `app/app/state.py` — read in full

### Tertiary (LOW confidence)
- None used — this research deliberately relied on direct source inspection over
  WebSearch/training-data claims, given the phase's explicit instruction to verify against
  actual installed behavior rather than assumptions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all APIs confirmed present in installed version
- Architecture (runtime color-mode mechanism): HIGH — verified by reading actual source of
  the exact installed package, not docs or training data
- Pitfalls: HIGH for the corrected/re-verified mechanism claims; MEDIUM for Assumption A1
  (why the original v1.2 fix "worked") since that requires historical/runtime forensics
  outside this research's scope
- Dark palette exact hex values: NOT researched (explicitly CONTEXT.md's discretion —
  measure during implementation per D-03, following Phase 6's WCAG methodology)

**Research date:** 2026-08-24
**Valid until:** Tied to the exact installed `reflex`/`reflex_base`/`reflex_components_radix`
versions in `app/.venv` — re-verify `Theme._render()`'s prop-stripping behavior if Reflex is
ever upgraded, since this is unusual, version-specific internal behavior, not documented
public API guaranteed to persist.
