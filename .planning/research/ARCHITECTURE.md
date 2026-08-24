# Architecture Research: v1.3 Dashboard Polish & Data-Entry Rework

**Domain:** Integration architecture for 6 features into an existing single-state-class Reflex app
**Researched:** 2026-08-24
**Confidence:** HIGH (all findings grounded in direct reads of `app/app/state.py`, `app/app/app.py`, `app/app/forecasting.py`, `app/app/theme.py`, `app/app/validators.py`, `app/rxconfig.py`, and `.planning/STATE.md`'s recorded repro)

## Existing System Overview

```
┌───────────────────────────────────────────────────────────────────┐
│ rxconfig.py — RadixThemesPlugin(theme=rx.theme(appearance="light"))│
│ (hardcoded, no toggle mechanism today)                             │
├───────────────────────────────────────────────────────────────────┤
│ app/app/app.py — ALL render/component functions, composed in       │
│ index() as one long rx.container: cards → forecast → historical →  │
│ data entry, all on one scroll, one route ("/")                     │
├───────────────────────────────────────────────────────────────────┤
│ app/app/state.py — DashboardState(rx.State), the SOLE DB boundary  │
│ (rx.session() appears only here). Holds ~20 state fields, computed │
│ @rx.var chart/table/card builders, and every event handler.        │
├───────────────────────────────────────────────────────────────────┤
│ app/app/forecasting.py — Reflex-free. forecast_all() dispatches 4  │
│ frozen, hardcoded models; MAPEs live only in docstrings/comments.  │
├───────────────────────────────────────────────────────────────────┤
│ app/app/theme.py — dependency-free design-token constants (colors, │
│ spacing, typography). No dark-mode variants exist yet.             │
├───────────────────────────────────────────────────────────────────┤
│ app/app/validators.py — pure validate_date/validate_numeric, no    │
│ Reflex import, already correct and already returns error strings.  │
└───────────────────────────────────────────────────────────────────┘
```

Single Reflex process, single `DashboardState` class, single page/route. This pattern holds for all six v1.3 features — none of them require a new state class, a new DB table (except theme persistence), or a second route (nav bar is same-page section switching, not multi-route).

## (a) Date-cell error-rendering bug — root-cause diagnosis

**Code path traced:** `_editable_cell` (app.py:41-81) is the ONE function used for both `visible_rows` and `draft_rows` (app.py:117-130, `data_table()`) — there is no structural difference between the draft-row editor and the persisted-row editor. Both render the identical `rx.vstack(rx.input(...), rx.cond(edit_error != "", rx.text(edit_error), rx.fragment()))` block, gated by the same `rx.cond(DashboardState.editing_key == key, editor, display)`.

**Key/state-machine trace for a draft row's date cell**, confirmed by reading `add_row`, `start_edit`, `commit_edit`, `_commit_draft_cell`, and `validate_date`:
1. `add_row()` sets `draft_rows = [PriceRow(date="")]`, `editing_key = ""` — the draft's date cell renders as **display mode** (empty text), not already in edit mode. User must click it first.
2. Clicking calls `start_edit(key, display_value)` where `key = row.date + ":" + attr` → `":date"` for the draft's date column (draft `date == ""`). This matches `_commit_draft_cell`'s own `editing_key.split(":", 1)` → `("", "date")` routing in `commit_edit()`. **This routing is correct — no key mismatch found.**
3. User types (`update_draft` fires per keystroke, `draft_value` updates — no validation, no DB touch, as intended).
4. Commit is triggered ONLY by `on_blur=DashboardState.commit_edit` or `on_key_down` Enter (`handle_key_down`). There is **no on_change/live validation** — this is the load-bearing fact.
5. On commit, `commit_edit()` → `row_date == ""` → `_commit_draft_cell("date")` → `validate_date(self.draft_value, ...)`. For `"08/25/2027"`, `date.fromisoformat()` raises `ValueError` → returns `(False, "", DATE_INVALID_ERROR)`. `_commit_draft_cell` sets `self.edit_error = error` and returns — **it does not touch `editing_key`, `draft_value`, or `draft_rows`.**
6. On the next render, `editing_key` is still `":date"`, so the editor still renders (correct), and `edit_error` is now `"Enter a valid date."` — the `rx.cond(DashboardState.edit_error != "", rx.text(...), ...)` block should render this text.

**Reading the code in isolation, the error-rendering wiring is structurally correct** — `edit_error` is set, and the same component that renders it for existing rows renders it for draft rows too. This rules out "draft rows use a different/broken editor" as the root cause; `_editable_cell` is shared, single-source code.

**The actual, evidence-grounded root cause (per STATE.md's confirmed live-browser repro) is a UX/trigger problem, not a broken render:** `commit_edit()` only fires on `on_blur` or Enter keydown. If a user types an invalid date and **does not blur the field or press Enter** (e.g. types, then looks at the screen, or the browser's blur event doesn't fire the way they expect), `commit_edit()` is never invoked, `edit_error` is never set, and nothing renders — because nothing ran, not because rendering is broken. This matches "value stays in the input, zero error shown anywhere" exactly: the input still shows the typed value (never touched) and no validation ever ran. Compounding factors that make this easy to hit in practice:
- No format hint anywhere near the input (raw ISO-only text field, `date.fromisoformat()` is strict — rejects `08/25/2027`, `2027-8-25`, `Aug 25 2027`, anything but `YYYY-MM-DD`).
- The error text, when it DOES render, is small (`size="1"`) red text below a narrow table-cell input — easy to miss in a dense 17-column table, especially if the user's eye is elsewhere or the row scrolled.
- `edit_error` is a single scalar (by design, per the code comment) — if the user moves to a different cell before blur/Enter fully registers, or if focus shifts unexpectedly, the error can be set-then-immediately-cleared by the next `start_edit` call (`start_edit` resets `edit_error = ""` unconditionally), making a genuinely-set error invisible if another cell-focus event races it.

**Verdict:** No code defect in the render conditional itself — `_commit_draft_cell` and `_editable_cell` are wired correctly and consistently for both draft and persisted rows. The bug is behavioral: validation is blur/Enter-gated with no live feedback, no format affordance, and an easily-missed/racily-cleared error message, on a strict ISO-only text input. **This is exactly what the milestone's "deep-research a rework of Data Entry" note is asking for** — fix direction should not be "find the broken cond," it should be (1) add on_change/live or explicit inline validation feedback, (2) replace or augment the raw text input with a real date picker (removes the format-guessing problem entirely), (3) make the error impossible to miss (persistent banner or stronger inline treatment, not just small red text that can be raced away by a subsequent `start_edit`).

## (b) New state fields / components needed

### Theme toggle (dark/light, persisted)

`rxconfig.py` currently hardcodes `rx.theme(appearance="light", ...)` at the plugin level — this is a **build-time** config, not a runtime toggle. To make it togglable at runtime you do NOT change `rxconfig.py`'s plugin (that only sets the initial/default); instead:
- Add `theme_appearance: str = "light"` to `DashboardState` (or a small dedicated `ThemeState` — see Build Order note below on why a shared state field is simpler here given the single-state-class convention already established).
- Reflex's Radix theme appearance is normally toggled via `rx.color_mode.button()`/`rx.color_mode_cond` or by binding the top-level `rx.theme`'s `appearance` prop to a state Var in `app.py` — this needs verifying against the installed Reflex 0.9.8 API (Context7/official docs) before implementation, since `rx.theme()` as used in `rxconfig.py` is the plugin-level default and the runtime override path is a different API surface (`rx.App(theme=...)` root wrapping, not the plugin). **Flag for phase-level research** — do not guess the exact Reflex 0.9.x runtime-appearance-toggle API without checking docs first.
- Persistence: two realistic options — (1) `rx.Cookie`/`rx.LocalStorage`-backed state var (Reflex has built-in browser-persisted state vars — check exact API name for 0.9.8), which needs zero new DB table and survives only per-browser; or (2) a new `AppSetting` row (the `AppSetting` model already exists and is already used for `markup_pct` — `load_markup_pct` is the existing pattern to mirror) for persistence across devices/sessions server-side. Given this is a single-user app already using `AppSetting` for one persisted preference, **mirroring `markup_pct`'s `AppSetting` pattern is the lower-risk, consistent choice** over introducing a new browser-storage primitive.
- New component: a toggle control (icon button or switch) placed in a header/nav area — new, small, e.g. `theme_toggle()` in app.py.

### html/body transparent background fix

Not a state change — a component/CSS fix. `PAGE_BG` (theme.py) is currently only applied to the inner `rx.container` in `index()` (`background=PAGE_BG` on the container, app.py:719). The `html`/`body` elements are unstyled and transparent by default in Reflex's generated app shell, so anything outside the container's box (wide viewports, dark browser/OS chrome) shows through. Fix is to set a background at the true document root — via Reflex's global style mechanism (`rx.App(style=...)` global CSS, or a `rxconfig.py`-level style/stylesheet injection targeting `html, body`) rather than another per-component `background=` prop, since the bug is specifically that per-component props never reach `html`/`body`. **This interacts with the theme toggle**: once dark mode exists, this fix must set the background dynamically (light/dark token) rather than hardcoding `PAGE_BG`, or the same bug reappears in reverse for dark mode. Build these two together (see Build Order).

### Tab/nav bar (Summary / Forecast / Data Entry)

- New state field: `active_section: str = "summary"` (or reuse a small literal enum of the three section keys) on `DashboardState`.
- New component: `nav_bar()` — three buttons/tabs bound to `DashboardState.set_active_section(section)` (new setter event handler, trivial, mirrors `select_series`'s pattern).
- Render change in `index()`: today `index()` unconditionally composes `forecast_summary_cards()`, `forecast_section()`, `historical_section()`, `data_entry_section()` in sequence. Two implementation options: (1) conditional rendering — wrap each section in `rx.cond(DashboardState.active_section == "...", section_fn(), rx.fragment())`, hiding non-active sections from the DOM; or (2) scroll-anchor navigation — keep all sections rendered (cheap here since data volume is small and nothing lazy-loads) and have nav buttons `rx.el.a(href="#section-id")` / JS scroll-into-view. Given `forecast_results` and other `@rx.var`s are computed reactively regardless of visibility, **conditional rendering (option 1) has a real benefit**: it avoids rendering (though not recomputing) the Plotly figures and tables for hidden sections, which matters given the app already had a documented performance problem at scale (STATE.md's "2,950 editable cells" hang). Recommend option 1.

### Per-series model name + backtest accuracy display

Purely additive — see (c) below for the data-flow change; the UI-facing new component is small: a caption/badge component (e.g. `_model_badge(label, mape)`) placed near each forecast summary card and/or the forecast chart/table headers, following the existing `_summary_card`/`_freshness_chip` "foreach over a list of flat string dicts" pattern already used twice in app.py (state.py's `summary_cards` and `freshness_chips`) — the codebase already has an established idiom for exactly this shape of data, so this feature should copy that idiom rather than invent a new one.

### Fan chart legend/axis-label overlap

Not a state change — a `forecast_chart_figure` (state.py:607-730) Plotly `update_layout` tuning fix. Current layout sets `legend=dict(orientation="h")` with default position and an `add_vline` annotation ("Forecast start") using `annotation_position="top left"` — these two are the likely overlap source (horizontal legend at top colliding with the top-left vline annotation, and/or the y-axis title colliding with tick labels at the given margins `margin=dict(l=40, r=16, t=16, b=40)`). Fix is purely a layout-property change (legend `y`/`yanchor` offset, or moving the vline annotation position, or increasing top margin) — no state/component structural change needed, low risk, isolated to one `@rx.var`.

## (c) Data flow: surfacing forecasting.py's hardcoded model names into the UI

**Current state:** Model names and MAPEs (HDAN SARIMAX(0,1,0)+exog 13.33%, PPAN Direct-OLS VAR-system 23.80%, Diesel-USD Naive 7.04%, FX Naive 1.72%) exist **only as free-text in docstrings/comments** inside `forecasting.py` (e.g. lines 245-246, 299, 386, 404) — there is zero machine-readable structure for this today. `forecast_all()`'s return contract is strictly the 5-key `{hdan, ppan, diesel_usd_ton, fx_rate, diesel_mnt}` dict of row-lists (D-07's locked contract, explicitly documented as `{"month", "base", "bull", "bear"}` per row) — no model-identity field flows through it, and per D-08 `forecasting.py` must stay Reflex-free.

**Required change, minimal and consistent with existing frozen-constants pattern:**
1. Add a new frozen dict in `forecasting.py` alongside the other frozen constants (`HDAN_SARIMAX_ORDER`, etc.) — e.g. `MODEL_INFO: dict[str, dict[str, str | float]]` keyed by the same 5 series keys used everywhere else (`hdan`, `ppan`, `diesel_usd_ton`, `fx_rate`, `diesel_mnt`), each holding `{"name": "SARIMAX(0,1,0)+exog", "mape": 13.33}` transcribed from the same provenance already cited in the docstrings (`02-MODEL-DECISIONS.md`). This keeps forecasting.py's "no Reflex" and "frozen constants only" constraints intact — it's just another named constant, not new logic. `diesel_mnt` has no own model (derived) — decide whether to synthesize a composite label ("Derived: Diesel-USD × FX") or omit it from the badge display; omitting is simpler and matches how `FRESHNESS_SERIES` already excludes `diesel_mnt` for the same "derived, no own date" reason (state.py:97) — **reuse that same exclusion precedent**.
2. In `state.py`, add one new `@rx.var` (e.g. `model_info_chips`) that maps `MODEL_INFO` into the same "list of flat string dicts" shape `summary_cards`/`freshness_chips` already use — this is a pure read of a new forecasting.py constant, no new DB access, no new computation, near-zero risk. It does not need to depend on `forecast_results` at all (model identity is static, not data-dependent), so it doesn't even need to be `@rx.var` if it's truly static — could be a plain module-level constant transformation, but `@rx.var` keeps it consistent with the existing chip-rendering idiom and lets it use `SERIES_LABELS`/`FORECAST_SERIES_LABELS` for display names.
3. In `app.py`, add the small badge component described in (b) and place it near `forecast_summary_cards()`/`forecast_chart()`.

This is a low-risk, additive, one-way data flow: `forecasting.py` (new constant) → `state.py` (new thin `@rx.var`) → `app.py` (new small component). No existing function signature changes, no changes to `forecast_all()`'s locked return contract.

## (d) Suggested build order

Ordered by dependency and risk, not by feature-list order:

1. **html/body background fix** — zero dependencies, isolated CSS/global-style change, immediately fixes a visible bug. Do this FIRST but write it in a way that anticipates step 2 (don't hardcode `PAGE_BG` directly into the global style if theme toggle is coming right after — parameterize or revisit).
2. **Theme toggle (persisted dark/light)** — do this second specifically because it invalidates/extends step 1's fix (a hardcoded light background at the html/body level will just reintroduce a mismatch in dark mode) and because it's the highest-unknown-risk item (needs Reflex 0.9.8 API verification for runtime appearance toggling — Context7/official docs lookup required before implementation, not assumption). Sequencing these two together avoids doing the background fix twice.
3. **Fan chart legend/axis overlap** — isolated, low-risk, single-file (`state.py`) Plotly layout change. No dependency on anything else; can technically run in parallel with 1-2 but is listed here because it's trivial and unblocks visual QA of the chart work bundled with item 4.
4. **Per-series model name + accuracy display** — additive, low-risk, no dependency on nav/theme work. Natural pairing with item 3 since both touch the forecast-chart/summary-card visual area.
5. **Tab/nav bar** — depends conceptually on knowing final section boundaries, but not on 1-4 technically; do after the visual/theme work so the nav doesn't need to be re-tested against a still-changing background/theme. This is the biggest structural `app.py` change (conditional rendering wrapping every existing section), so isolate it to reduce blast radius from the smaller fixes above.
6. **Data Entry rework (deep-research + fix)** — last, and deliberately separated from the other five: PROJECT.md explicitly calls for a "deep-research pass" before rework, this is the only item requiring genuine UX/product decisions (date-picker vs. inline-validation vs. banner), and per (a) above the fix is behavioral/UX (not a quick conditional-render bug fix), so it warrants its own dedicated research + phase rather than being bundled with the smaller polish items. Do this after nav bar so the reworked Data Entry section lands cleanly inside the new section-switching structure rather than needing to be re-integrated into it afterward.

## Anti-Patterns to Avoid

### Anti-Pattern: Introducing a second state class for the toggle/nav additions
**What people might do:** Create `ThemeState`/`NavState` as separate `rx.State` classes since the additions feel "unrelated" to DashboardState's data-entry/forecast concerns.
**Why it's wrong:** The codebase has a single, explicit, documented convention — "DashboardState is the only place in the app that opens an rx.session() or touches the ORM" (state.py's own module docstring) — and every existing feature, however unrelated in domain (CSV import, export, forecasting, editing), was added as more fields on the same class. Splitting now breaks that established pattern for no functional benefit at this app's scale and complicates cross-state coordination (e.g. nav needing to cancel in-progress edits, mirroring what `toggle_show_all_history` already does for `show_all_history`/`cancel_edit`).
**Instead:** Add `theme_appearance`, `active_section`, and their setters as more fields/methods on `DashboardState`, exactly like `show_all_history`, `selected_series`, `import_stage`, etc. were added.

### Anti-Pattern: Fixing the date-cell bug by only changing the render conditional
**What people might do:** Assume `rx.cond(DashboardState.edit_error != "", ...)` itself is broken and "fix" it by restructuring the cond, without addressing that `commit_edit` is blur/Enter-gated with no format hint.
**Why it's wrong:** Per (a) above, the cond and the state wiring are already correct on inspection — restructuring it without changing when/how validation triggers won't change user-observed behavior, since the underlying issue is that validation may simply never run for a user who doesn't blur/Enter, or whose error gets raced away by the next `start_edit` call resetting `edit_error = ""`.
**Instead:** Treat this as the UX-rework item it's scoped as in PROJECT.md — add a real date input affordance (format hint or native date picker) and/or live validation, and make `start_edit`'s unconditional `edit_error = ""` reset not clobber a genuinely-pending error from a race with a near-simultaneous blur/commit — this needs the deep-research pass called for in the milestone goal, not a one-line render fix.

## Sources

- `app/app/state.py`, `app/app/app.py`, `app/app/forecasting.py`, `app/app/theme.py`, `app/app/validators.py`, `app/rxconfig.py` — read in full, HIGH confidence, this milestone's ground truth.
- `.planning/STATE.md` (lines 28-34, 157-178) and `.planning/PROJECT.md` (lines 113-123) — recorded live-browser repro details (exact typed input `"08/25/2027"`, exact observed symptom) and prior confirmed bugs (light-appearance pin history, transparent html/body via `getComputedStyle`) — HIGH confidence, first-party project records.
- Reflex 0.9.8's exact runtime dark-mode-toggle API and global `html`/`body` style-injection mechanism were **not verified against Context7/official docs in this pass** — flagged explicitly in (b) and (d) item 2 as needing a docs lookup before implementation; do not assume `rx.color_mode`/`toggle_color_mode` API shape without checking the installed 0.9.8 version's docs first.

---
*Architecture research for: v1.3 Dashboard Polish & Data-Entry Rework*
*Researched: 2026-08-24*
