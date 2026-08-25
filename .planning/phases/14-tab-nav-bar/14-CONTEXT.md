# Phase 14: Tab/Nav Bar — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a tab/nav bar letting the user switch between Summary, Forecast, and Data Entry sections without a full page reload and without losing in-progress state (an edit in progress, an armed delete, a CSV import preview). Root architecture already decided by v1.3 milestone research: client-side section toggling within the existing single page/route (`index()`), NOT separate Reflex routes — routes would duplicate `on_mount` data loading and risk losing `DashboardState`'s in-memory edit/import state on navigation.

In scope: a new `active_section` state field, a tab bar component, conditional rendering of the 4 existing sections (`forecast_summary_cards()`, `forecast_section()`, `historical_section()`, `data_entry_section()`) grouped into 3 tabs.
Out of scope: any change to the sections' internal content/behavior, any change to the edit/delete/draft-row/CSV-import state machine itself (only how it's rendered/hidden), routing/URL changes.
</domain>

<decisions>
## Implementation Decisions

### Tab mapping
- **D-01:** 3 tabs, not 4: "Summary" = `forecast_summary_cards()`, "Forecast" = `forecast_section()`, "Data Entry" = `historical_section()` + `data_entry_section()` combined (historical chart grouped with the editable table since both concern raw actuals).

### Tab bar placement and behavior
- **D-02:** Sticky tab bar positioned below the header (title + theme toggle), always visible. Clicking a tab shows ONLY that tab's section content (conditional render/hide, not just a scroll-to anchor with everything still stacked) and scrolls the page to top — behaves like a real tabbed interface, not an in-page jump-link nav.

### Default tab
- **D-03:** "Summary" is the active tab on first page load — matches the Phase 6 "answer in 10-20 seconds" design goal; user sees the forecast summary cards immediately without clicking anything.

### Claude's Discretion
- Exact tab bar component (Reflex's `rx.tabs.root`/`.list`/`.trigger`/`.content` vs. a custom `rx.hstack` of buttons driven by `active_section` + `rx.cond`) — research confirmed `rx.tabs` is available and documented in the installed Reflex version; use whichever cleanly supports controlled `value`/`on_change` wiring to `DashboardState.active_section`.
- Exact tab label text (likely "Summary" / "Forecast" / "Data Entry" verbatim, matching D-01's names).
- Whether `active_section` persists across reloads (localStorage, like `theme_mode`) or always resets to "Summary" on fresh load — default to always-resets-to-Summary unless there's a clear reason to persist, since D-03 already establishes Summary as the natural landing tab.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/app.py` — `index()` (line ~724, the composition point being restructured), `forecast_summary_cards()` (line ~497), `forecast_section()` (line ~514), `historical_section()` (line ~537), `data_entry_section()` (line ~676) — the 4 existing top-level sections, each already carrying `role="region"` + `aria_label` landmarks that must be preserved
- `app/app/state.py` — `DashboardState.editing_key`, `draft_value`, `edit_error`, `pending_delete`, `draft_rows` (the edit/delete state machine), `import_stage`, `_staged_import_rows` (the CSV import state machine) — these must NOT be reset or lost when switching tabs away from Data Entry and back
- `app/app/theme.py` — no new tokens needed; reuse existing spacing/typography/color tokens for the tab bar styling

### v1.3 milestone research (MANDATORY)
- `.planning/research/SUMMARY.md` — Phase 4 (this phase): "`rx.tabs.root`/`.list`/`.trigger`/`.content` directly confirmed against current Reflex docs with working example"; "client-side vs. multi-route already resolved in favor of client-side"
- `.planning/research/PITFALLS.md` — Pitfall 3: tab/nav retrofit must not break `index()`'s single `on_mount=[load_rows, load_markup_pct]` (must fire exactly once, not per-tab-switch) or lose in-flight draft/CSV state; explicitly test "switch tabs mid-edit" and "mid-CSV-preview" scenarios
- `.planning/research/ARCHITECTURE.md` — confirms new `active_section` state field + `nav_bar()` component, `rx.tabs`-based or `rx.cond`-based client-side section switching within the existing single route

### Prior phase precedent
- `.planning/phases/11-background-fix-theme-toggle/` — established the pattern of a header-area control (`theme_toggle()`) wired to a `DashboardState` field with an event handler; the new tab bar follows the same "small control component next to the title" placement precedent
- `.planning/phases/06-ux-ui-redesign/06-CONTEXT.md` — the locked page order (Summary → Forecast → Historical → Data Entry) that D-01's tab grouping is built from, not replacing

### Project-level
- `.planning/REQUIREMENTS.md` — NAV-01
- `.planning/ROADMAP.md` — Phase 14 entry

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `theme_toggle()` (Phase 11) — the precedent for "a small interactive control living in the header hstack alongside the title" — the tab bar likely sits in a new row directly below this same header hstack.

### Established Patterns
- Every top-level section already has `role="region"` + `aria_label` — conditional rendering must preserve these landmarks (only the currently-visible section's landmark is in the DOM, which is standard/acceptable a11y behavior for tabbed interfaces, unlike hiding via `display:none` which would keep the landmark in the accessibility tree).
- `on_mount=[DashboardState.load_rows, DashboardState.load_markup_pct]` lives on the single `rx.container` root in `index()` — this must NOT be duplicated per-tab; it fires once on initial page load regardless of which tab conditional rendering shows.

### Integration Points
- New `active_section: str = "summary"` field (or similar) on `DashboardState`, plus a `set_active_section` (or reuse `rx.tabs`'s built-in `on_change`) event handler.
- `index()` restructured to render the tab bar once, then conditionally render each of the 3 tab-groups based on `active_section` (via `rx.match` / `rx.cond` chain, or `rx.tabs.content` per-tab if using the built-in component).
- Data Entry tab specifically must keep `historical_section()` and `data_entry_section()` mounted/rendered together as one unit whenever that tab is active.

</code_context>

<specifics>
## Specific Ideas

No new visual references — the tab bar should look like a natural extension of the existing Phase 6 header area, calm and understated (not a colorful pill-tab SaaS style).

</specifics>

<deferred>
## Deferred Ideas

None — phase scope is fully covered by the decisions above.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-tab-nav-bar*
*Context gathered: 2026-08-24*
