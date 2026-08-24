# Phase 11: Background Fix + Theme Toggle — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the transparent `html`/`body` background bug (real users report "black spaces on the two sides" at wide viewports/dark-mode browsers) and add a persisted light/dark theme toggle, bundled into one phase because they are architecturally coupled — a background fix using a single hardcoded appearance would need to be redone once dark mode ships.

In scope: mode-aware page-level background, a runtime-togglable Radix appearance (replacing the current build-time `appearance="light"` pin in `rxconfig.py`), a dual-tokenized `theme.py` (light + dark variants of every color constant), a toggle control in the header, localStorage persistence, and dark-mode-aware Plotly figure colors (`font.color`, `plot_bgcolor` currently hardcode light-only values).
Out of scope: any change to spacing/typography tokens (unaffected by theme), any change to the accent color's role/reservation rules from Phase 6, any new page section or nav bar (that's Phase 14).
</domain>

<decisions>
## Implementation Decisions

### Persistence
- **D-01:** Theme preference persists via browser localStorage (client-side only), not a server-side `AppSetting` DB row. No DB schema change for this phase.

### Default appearance
- **D-02:** First-time page load (no stored preference) always defaults to light, regardless of OS/browser `prefers-color-scheme`. Do NOT wire `appearance="inherit"` or any OS-preference detection — this is the exact bug class v1.2 Phase 6 already fixed once (silent OS-dark-mode inheritance against hardcoded light backgrounds). The toggle is the only way to enter dark mode.

### Dark palette
- **D-03:** Dark mode gets a small, hand-picked bespoke palette (not a mechanical color-invert of the light tokens) — dark page background, dark card surface, light text, the same single accent hue (adjusted for contrast against the dark surface if needed), same UP/DOWN semantic colors (adjusted for contrast if needed). Keep it as minimal/restrained as the existing light system — same number of tokens, not a larger set.

### Toggle placement
- **D-04:** The toggle control sits in the header area near the page title ("Prediction Dashboard"), always visible regardless of scroll position (not deep in a settings panel).

### Claude's Discretion
- Exact dark hex values — must pass the same WCAG AA thresholds already established and measured for the light palette in `theme.py`'s amendment comments (4.5:1 normal text, 3:1 non-text boundaries); document any measured ratio the way Phase 6 did.
- Toggle control's exact visual treatment (icon choice, size) — follow existing header/button patterns in `app.py`.
- Whether the runtime appearance toggle uses Reflex's `rx.color_mode`/`rx.toggle_color_mode` primitives or a different mechanism — resolve via the exact Reflex 0.9.8 API check flagged as an open gap in `.planning/research/SUMMARY.md` (verify before implementation, don't assume the API shape).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/theme.py` — every light-mode color constant (PAGE_BG, SURFACE, BORDER, ACCENT, ACCENT_FILL, DESTRUCTIVE, NEUTRAL_LINE, UP, DOWN, MUTED_TEXT) — each needs a dark-mode counterpart. Note the existing amendment-comment convention (documents WHY a value was changed and its measured contrast ratio) — follow it for new dark tokens too.
- `app/rxconfig.py` — currently pins `rx.plugins.RadixThemesPlugin(theme=rx.theme(appearance="light", accent_color="blue"))` at build time. This build-time pin is exactly what must become runtime-togglable.
- `app/app/app.py` — `index()`'s root container currently sets `background=PAGE_BG` (hardcoded light) at the bottom of the function (~line before `app = rx.App()`); this and every other `background=SURFACE`/`background=PAGE_BG` prop throughout the file (used in `historical_chart()`, `empty_state()`, card components, etc.) must become mode-aware.
- `app/app/state.py` — `historical_chart_figure` and `forecast_chart_figure` Plotly figure builders hardcode `font=dict(size=14, color=MUTED_TEXT)` and `plot_bgcolor="rgba(0,0,0,0)"` (transparent, relying on the card's light `SURFACE` showing through) — these must become mode-aware too, or dark-mode charts will show light-mode text color on a dark card.

### v1.3 milestone research (MANDATORY — this phase's specific risk analysis)
- `.planning/research/PITFALLS.md` — Pitfall 1 (theme toggle reintroducing OS-inheritance / un-tokenized colors) and Pitfall 2 (background fix colliding with the toggle if done independently) — both directly address this phase.
- `.planning/research/STACK.md` — confirms `rx.color_mode` + `rx.toggle_color_mode` + `rx.LocalStorage` are already present in the installed `reflex==0.9.8.post1` package (verified via direct introspection), and that the background fix should use `rx.App(style=...)` or equivalent global style injection, not more `background=` props on inner boxes (the pattern already used ~9x, which is the actual root cause of the symptom per Stack research's Radix-architecture explanation — background is expected to live on the `.radix-themes` wrapper by Radix's own design, but wasn't propagated to `html`/`body`).
- `.planning/research/ARCHITECTURE.md` — recommends background-fix and theme-toggle land in the same phase/sequence against one shared color-token source; flags the exact Reflex 0.9.8 runtime-appearance-toggle API as unverified and needing a docs check before implementation (not to be assumed).
- `.planning/research/SUMMARY.md` — "Gaps to Address": exact Reflex 0.9.8 runtime API for toggling `rx.theme`'s `appearance` prop at runtime (vs. build-time plugin config) needs a docs/Context7 lookup before implementation.

### Prior phase precedent
- `.planning/phases/06-ux-ui-redesign/06-UI-SPEC.md` — the original light-only design contract and its WCAG contrast measurement discipline (to be mirrored for dark tokens)
- STATE.md decision log: "Pinned Radix theme to appearance=light in rxconfig.py plugins — App silently inherited OS dark-mode preference, breaking text legibility while custom light backgrounds stayed hardcoded; found during [Phase 6] Task 3 human verification" — this is the exact bug class D-02 exists to prevent recurring.

### Project-level
- `.planning/REQUIREMENTS.md` — THEME-01, THEME-02, THEME-03, THEME-04
- `.planning/ROADMAP.md` — Phase 11 entry

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `theme.py`'s existing amendment-comment pattern (cites which task changed a value, why, and the measured contrast ratio) — reuse exactly for new dark-mode tokens.
- Existing WCAG contrast test in the test suite (from Phase 6's responsive/a11y pass) — likely extendable to also check dark-mode pairings.

### Established Patterns
- All color/spacing/typography values resolve from `theme.py` — no scattered literals in `app.py`/`state.py`. This discipline must extend to dark-mode values too (no ad-hoc dark hex literals outside `theme.py`).
- `theme.py` is dependency-free by design (no Reflex import) — if theme-mode-aware constants require knowing the *current* mode at render time (not just two static palettes), this may need a different mechanism than a plain module constant (e.g. Reflex `rx.color_mode_cond` or a computed var) — flag this as a design decision for the planner, since `theme.py`'s current "plain constant" pattern may not directly support runtime switching.

### Integration Points
- `rxconfig.py`'s theme plugin config is the build-time entry point that currently forces light-only.
- `index()`'s root container background prop, plus every other `background=` prop across `app.py`, are the render-time integration points.
- `historical_chart_figure`/`forecast_chart_figure` in `state.py` are the chart-specific integration points needing mode-aware Plotly colors.

</code_context>

<specifics>
## Specific Ideas

No new visual references — dark palette should feel like a natural "night mode" of the existing calm, light, single-accent Phase 6 design system, not a different visual identity.

</specifics>

<deferred>
## Deferred Ideas

None beyond what's already out of scope for this phase (nav bar is Phase 14, spacing/typography unchanged).

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-background-fix-theme-toggle*
*Context gathered: 2026-08-24*
