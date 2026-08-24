# Pitfalls Research

**Domain:** Retrofitting theme/nav/UI features onto an existing single-page Reflex dashboard with a complex edit/delete/draft-row state machine
**Researched:** 2026-08-24
**Confidence:** HIGH (grounded directly in `app/app/state.py`, `app/app/app.py`, `app/app/theme.py`, `app/app/forecasting.py`, `app/rxconfig.py`)

## Critical Pitfalls

### Pitfall 1: Theme toggle reintroduces OS-dark-mode inheritance (the exact bug v1.2 Phase 6 fixed)

**What goes wrong:**
`rxconfig.py` currently pins `RadixThemesPlugin(theme=rx.theme(appearance="light", accent_color="blue"))` — a static, build-time config value. Radix's `appearance` prop, when set to `"inherit"` (or omitted), follows the OS/browser `prefers-color-scheme`. If a naive toggle implementation removes this static `light` pin and instead sets `appearance="inherit"` at the `rx.theme()` level, any user whose browser prefers dark mode is instantly back to the original bug: illegible text because `theme.py`'s hardcoded hex colors (`PAGE_BG = "#FAFAFA"`, `SURFACE = "#FFFFFF"`, `MUTED_TEXT = "#71717A"`, etc.) assume a light background and are never swapped by Radix's own dark palette (since none of these are Radix theme tokens — they're raw hex literals wired directly into `plot_bgcolor`, `background=`, chart colors, etc.).

**Why it happens:**
Radix Themes' idiomatic dark-mode pattern is `appearance="inherit"` + a `<Theme.Panel>`/CSS-variable driven design system. But this app doesn't use Radix CSS variables for its custom tokens — `theme.py` is a *parallel* hardcoded color system (explicitly built as "no scattered literals," single source of truth, but only for one appearance). Naively wiring a toggle to Radix's `appearance` prop without also branching `theme.py`'s constants creates a mismatch: Radix chrome (buttons, inputs, table borders) goes dark, but every custom `SURFACE`/`PAGE_BG`/Plotly `font.color` stays light-colored — the same "light text/background assumptions violated" failure class as before, just triggered by a user click instead of OS inheritance.

**How to avoid:**
- Make `appearance` a controlled value driven by *persisted app state*, never `"inherit"`. The toggle should explicitly set `"light"` or `"dark"` — OS preference should never be consulted as a fallback for anything currently visible on load.
- `theme.py`'s constants must become theme-aware (either two token dicts selected by mode, or restructure so components/figures read from a state-derived color at render time). Every one of `PAGE_BG`, `SURFACE`, `BORDER`, `MUTED_TEXT`, `NEUTRAL_LINE`, `ACCENT`, `ACCENT_FILL`, `UP`/`DOWN`, `DESTRUCTIVE` needs a dark-mode counterpart — including the Plotly figure builders in `state.py` (`historical_chart_figure`, `forecast_chart_figure`) which currently hardcode `plot_bgcolor="rgba(0,0,0,0)"` + `font=dict(color=MUTED_TEXT)`, so a light MUTED_TEXT on a dark Radix background is invisible even if the *page* background is fixed.
- Persist the choice server-side (SQLite `AppSetting`, same pattern as `markup_pct`) and set it via `on_mount`, so a returning user never sees a flash of the wrong theme or an OS-driven default.

**Warning signs:**
- Any use of `appearance="inherit"` anywhere in the diff.
- `theme.py` constants referenced without going through a mode-aware lookup.
- Plotly `font=dict(color=MUTED_TEXT)` / `plot_bgcolor` left unconditional in `historical_chart_figure` / `forecast_chart_figure` after the toggle ships.

**Phase to address:**
Theme toggle phase — must be scoped to include a `theme.py` rework (dual token sets) and a Plotly figure color audit, not just an `rxconfig.py`/`rx.color_mode` change.

---

### Pitfall 2: Page-background fix (html/body transparency) collides with the card/surface system's transparent-canvas trick

**What goes wrong:**
`historical_chart_figure` and `forecast_chart_figure` both explicitly set `plot_bgcolor="rgba(0,0,0,0)"` and `paper_bgcolor="rgba(0,0,0,0)"` — the chart canvas is *intentionally transparent* so it inherits the `SURFACE` (`#FFFFFF`) card background it sits inside (`rx.box(..., background=SURFACE, ...)` in `historical_chart()`/`forecast_chart()`). The reported bug — black margins from a transparent `html`/`body` — is almost certainly the *same transparency mechanism* operating one level up: Reflex/Radix's root `html`/`body` has no explicit background set, so it falls through to the browser default (black in dark-mode browsers, or just "whatever's behind it" on wide viewports where `rx.container`'s max-width leaves gutters). A fix applied carelessly (e.g. "just set `background: white` on `html`/`body` globally via raw CSS") will hardcode a light color at the *browser root*, which directly conflicts with the theme toggle work (Pitfall 1) — the moment dark mode is added, that hardcoded root background becomes the new black-margin bug's dark-mode twin (a permanently-white flash margin outside a dark page).

**Why it happens:**
Reflex apps get their `html`/`body` styling from `rx.App`'s stylesheet configuration or global CSS, which is easy to patch in isolation from the Radix theme system and from `theme.py`, since neither file currently touches `html`/`body`. Fixing this "in isolation" (pure CSS reset) without coordinating with the theme toggle phase means doing the background-color work twice, or shipping a fix that only covers one mode.
</br>
**How to avoid:**
- Set the `html`/`body` background using the same mode-aware source of truth as `PAGE_BG`/`SURFACE` (Pitfall 1's dual-token system), not a separate hardcoded value. In Reflex this is typically done via `rx.App(style=...)` or a global stylesheet that reads the same `PAGE_BG` token, or by relying on Radix's own `appearance`-driven root background instead of a custom override.
- Sequence this fix together with (or after) the theme toggle work, even though PROJECT.md lists them as separate bullets — doing the background fix first with a hardcoded light value creates rework once the toggle lands.
- Verify at three viewport widths (narrow, `rx.container`'s max-width, and ultra-wide) and both appearances — the "black margins" report specifically calls out wide viewports, meaning `rx.container`'s side gutters are the visible surface, distinct from the page's own scrollable background.

**Warning signs:**
- A raw `background: white` or `background: #FAFAFA` CSS rule added outside `theme.py`'s token system.
- Fix verified only in light mode / only at one viewport width.

**Phase to address:**
Should be the SAME phase as the theme toggle, or explicitly sequenced immediately after it with the same token source — not a fully independent phase, despite being listed as a separate bullet in PROJECT.md.

---

### Pitfall 3: Tab/nav retrofit breaks `on_mount` data loading or creates duplicate/stale loads per section

**What goes wrong:**
`index()` currently has a single `on_mount=[DashboardState.load_rows, DashboardState.load_markup_pct]` at the page/container level, and `DashboardState.rows` is the shared full-history source of truth read by `visible_rows`, `historical_chart_figure`, `forecast_results`, `summary_cards`, `_export_bytes`, etc. — i.e., every "section" (Summary/Forecast/Data Entry) depends on the SAME state that's currently loaded exactly once, at mount, for the whole page. If tabs are implemented as separate Reflex *pages* (separate routes, e.g. `/forecast`, `/data-entry`) rather than client-side show/hide of one page's sections, `on_mount` will fire independently per route, and naive per-route wiring can either (a) forget to load `load_markup_pct`/`load_rows` on a newly-added route, leaving that tab showing stale/empty state, or (b) reload on every tab switch, discarding in-progress edit/draft state (`editing_key`, `draft_rows`, `pending_delete`, CSV `import_stage`) since `load_rows()` reassigns `self.rows` but does NOT touch `draft_rows`/`editing_key` — however if a naive nav switch triggers a full state reset instead of a targeted reload, unsaved draft rows would silently vanish when switching from Data Entry to Summary and back.

**Why it happens:**
Reflex `on_mount` semantics differ between "conditionally rendered sections within one page" (mount fires once) and "separate routed pages" (mount fires on every navigation to that route). The existing codebase's single-page architecture means every prior phase assumed `self.rows`/`self.markup_pct` are loaded once and stay fresh via targeted mutations (`load_rows()` after every write). A tab/nav retrofit is the first time this assumption gets tested against navigation.

**How to avoid:**
- Prefer client-side section switching (single route, `rx.tabs` or conditional rendering driven by a `active_tab` state var) over multiple Reflex routes — this preserves the existing single `on_mount` and avoids re-triggering data loads or losing in-flight edit state on tab switch. This is the lower-risk option given the existing architecture.
- If separate routes are used instead, each route's `on_mount` must call the same load list, AND draft/edit state (`editing_key`, `draft_rows`, `pending_delete`, `import_stage`) must be either preserved (since `DashboardState` is a single app-wide state class, it should persist across route navigation within the same session) or explicitly and intentionally reset — verify via `rx.State` scoping that state does not get discarded on route change.
- Explicitly test: start an edit or an in-progress CSV import preview, switch tabs, switch back — draft/import state must survive.

**Warning signs:**
- New `rx.App().add_page(...)` calls with separate routes and separate `on_mount` lists that don't mirror `index()`'s.
- Any test plan that doesn't include "switch tabs mid-edit" or "switch tabs mid-CSV-preview."

**Phase to address:**
Tab/nav phase — should explicitly decide (and document as a design decision) client-side sections vs. multi-route before implementation, given the state-persistence stakes above.

---

### Pitfall 4: Surfacing model name/MAPE creates a second source of truth that drifts from `forecast_all()`'s actual dispatch

**What goes wrong:**
`forecasting.py` currently encodes model identity and backtest accuracy ONLY as prose in docstrings and code comments — e.g. `forecast_hdan`'s docstring says "Model: SARIMAX(0,1,0)+exog, backtested mean 1-12 MAPE of 13.33%", `forecast_ppan`'s says "Direct-OLS VAR-system(h=1..12) ... backtested mean 1-12 MAPE of 23.80%", and the two Naive-model docstrings give 7.04% and 1.72%. None of this is a Python constant, let alone something `forecast_all()` returns. If the UI work is done by simply copy-pasting these strings into a new dict in `state.py` (mirroring the `SERIES_LABELS`-style "single source of truth" pattern the codebase already uses elsewhere), that copy becomes a SECOND, independently-editable copy of facts that already live in `forecasting.py` — any future change to `HDAN_SARIMAX_ORDER`, the PPAN VAR system members, or a re-backtest that changes MAPE will silently desync the UI from the actual dispatch logic, since nothing enforces the two stay equal.

**Why it happens:**
`forecasting.py`'s module docstring explicitly states model choices must not be re-derived/touched here (PROJECT.md constraint: "forecasting models must go through a research/backtest step... before being used"), which correctly discourages touching the *modeling* code, but doesn't by itself prevent someone from duplicating the *display strings* describing those models elsewhere. The path of least resistance — hand-typing "SARIMAX — 13.3% MAPE" into a UI string — looks safe because it doesn't touch modeling logic, but it does create drift risk on the *label*.

**How to avoid:**
- Add model-identity metadata (name string + backtest MAPE) as actual Python constants co-located with each model's implementation in `forecasting.py` (e.g. `HDAN_MODEL_NAME = "SARIMAX(0,1,0)+exog"`, `HDAN_BACKTEST_MAPE = 13.33`), then have `forecast_all()` (the "single dispatcher... orchestrating all four winning models," per its own docstring at line 488-489) include this metadata in its returned dict — OR expose a small `MODEL_METADATA` dict/function in `forecasting.py` keyed by the same series keys `forecast_all()` already dispatches on (`hdan`, `ppan`, `diesel_usd_ton`/`diesel_mnt`, `fx_rate`).
- `state.py` should read this metadata from `forecasting.py` at the SAME call site as the existing `forecast_all(history, ...)` call in `forecast_results` (the codebase already enforces "Pitfall 2 guard — exactly one call site app-wide" for `forecast_all`; extend that discipline to model metadata) — never hand-copy the MAPE numbers into `state.py` or `app.py` as literals.
- If MAPE constants must live separately from the docstrings (since docstrings aren't machine-readable), update the docstrings to reference the constant name rather than repeating the number, so there's exactly one numeric literal per model.

**Warning signs:**
- A new dict/constant in `state.py` (not `forecasting.py`) containing model names or MAPE percentages as literals.
- Any PR that changes a MAPE number in only one of `forecasting.py`'s docstrings or the new UI-facing constant.

**Phase to address:**
Model-metadata-surfacing phase — should require the metadata constants to be added to `forecasting.py` (not `state.py`) as its first task, then consumed via `forecast_all()`'s existing single-call-site pattern.

---

### Pitfall 5: Plotly legend/margin fix breaks the "Forecast start" `add_vline` annotation or the chart's `aria_label`

**What goes wrong:**
`forecast_chart_figure` in `state.py` currently: (a) sets `legend=dict(orientation="h")` with no explicit `x`/`y`/anchor, letting Plotly auto-place the horizontal legend (the likely source of the reported overlap with axis labels since `margin=dict(l=40, r=16, t=16, b=40)` leaves very little top margin — `t=16` — for a legend that may render above the plot area); (b) adds a `Forecast start` vertical line via `figure.add_vline(..., annotation_text="Forecast start", annotation_position="top left")`, which is ALSO positioned relative to the plot area's top and will collide with whatever legend-repositioning fix is applied if both end up anchored near the top-left; (c) the containing `rx.box` around `rx.plotly(...)` carries `aria_label="Fan chart of forecast base value with expected range"` at the `rx.box` level, not on the Plotly figure itself — a naive fix that adds accessibility attributes directly to the `go.Figure()` layout (e.g. Plotly's own `layout.meta` or embedding ARIA via `config`) would be redundant/conflicting with the existing box-level `aria_label`, and if the fix mistakenly moves or removes the `rx.box` wrapper to restructure the chart, that `aria_label` (and `historical_chart`'s equivalent) is lost silently since nothing tests for it.

**Why it happens:**
Plotly's `t` margin, legend position, and `add_vline`'s annotation are three independent layout mechanisms that share the same visual real estate (top of the plot) without any of them being aware of the other's footprint — a common Plotly gotcha when increasing top margin for a legend without also checking whether an existing vline annotation is still positioned sensibly relative to it.

**How to avoid:**
- When repositioning the legend (e.g. moving to `legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)` or moving it below the plot with `y=-0.2`), increase `margin.t` (or `margin.b` if moving legend below) to match, and re-check `add_vline`'s `annotation_position` doesn't now overlap the new legend location — consider changing `annotation_position` (e.g. to `"top"` without `"left"`, or `"bottom left"`) as part of the same change, not as an afterthought.
- Do NOT touch the `aria_label` props on the wrapping `rx.box` in `historical_chart()`/`forecast_chart()` in `app.py` when editing figure layout in `state.py`'s `forecast_chart_figure`/`historical_chart_figure` — these are two different files/layers; a layout-only fix should only touch `state.py`.
- Apply the exact same margin/legend treatment to BOTH `historical_chart_figure` and `forecast_chart_figure` if the fix is meant to be a general "chart polish" — right now both duplicate nearly identical layout blocks (margin, plot_bgcolor, font), so an inconsistent fix (legend/margin changed on one but not the other) would look like a regression on whichever chart wasn't touched, even if that chart didn't have the reported bug.
- Preserve `hovermode="x unified"` and the existing `NEUTRAL_LINE`/`ACCENT`/`ACCENT_FILL`/`BORDER` color tokens from `theme.py` untouched — this pitfall is scoped to layout geometry (legend position, margins), not color; do not fold this work into the theme-toggle color rework (Pitfall 1) accidentally.

**Warning signs:**
- A diff that changes `margin` or `legend` in `state.py` without also touching `add_vline`'s `annotation_position`.
- A diff that removes or edits `aria_label=` in `app.py`'s `historical_chart()`/`forecast_chart()`.
- Only one of the two chart figures updated when both share near-identical layout code.

**Phase to address:**
Fan chart legend/axis-overlap phase — scope explicitly to `state.py` layout dict changes in both figure builders; include a manual check of the vline annotation position and a diff-review step confirming `aria_label` props in `app.py` are untouched.

---

### Pitfall 6: Draft-row date-validation fix regresses the windowing toggle or CSV-import's shared use of `editing_key`/`draft_rows`

**What goes wrong:**
The diagnosed root cause (PROJECT.md) is that the new-row date field "silently rejects invalid input with zero user-facing error feedback." Looking at the actual code: `_commit_draft_cell` DOES call `validate_date(...)` and DOES set `self.edit_error = error` on failure (lines 899-906) — so error state is technically being set. The likely real bug is in `app.py`'s `_editable_cell`: the error text is only rendered inside the `editor` vstack (`rx.cond(DashboardState.edit_error != "", rx.text(...)))`, which is only shown while `DashboardState.editing_key == key` is true. If the input's `on_blur=DashboardState.commit_edit` fires and `commit_edit` returns early after setting `edit_error` (validation failure keeps `editing_key` unchanged in `_commit_draft_cell` — it only clears `editing_key`/`draft_value` on the SUCCESS path), then the cell should stay in edit mode with the error visible... but `on_blur` firing means the browser has already moved focus away, and Radix/browser blur-triggered re-renders combined with `auto_focus=True` on the input can cause a race where the editor unmounts before the `rx.cond` re-render with the error text is visible, OR the `on_blur` fires and calls `commit_edit` which fails validation and returns, leaving `editing_key` set — but if the user's mouse/tab action was a genuine "click away" the input may already be visually gone from focus-loss styling even though `rx.cond` should still be showing it. This exact `editing_key`/`draft_value`/`edit_error` triad is shared identically between the ORIGINAL single-cell edit flow (v1 Phase 4), the windowing toggle's `cancel_edit()` call inside `toggle_show_all_history` (v1.2 Phase 7), and indirectly by CSV import which bypasses this flow entirely but shares `self.rows`/`load_rows()` (v1.2 Phase 10). A fix that changes `commit_edit`/`_commit_draft_cell`'s control flow (e.g. adding a new state field for "date field has a pending error" separate from `edit_error`, or changing `on_blur` handling to not call `commit_edit`) risks: (a) `toggle_show_all_history`'s `self.cancel_edit()` call no longer clearing whatever new error-tracking field is added, leaving a stale error visible after the window toggle changes which rows are shown; (b) CSV import's `confirm_import()` / `handle_csv_upload()` writing directly to `PriceRow` via `session.add()` without going through `_commit_draft_cell` at all — if the date-validation fix consolidates validation logic assuming ALL new rows flow through `_commit_draft_cell`, CSV import's separate `parse_import_csv` validation path (in `csv_import.py`, not read here but referenced in `state.py`) will NOT pick up the fix, silently leaving two divergent date-validation implementations for two different entry methods.

**Why it happens:**
`editing_key`, `draft_value`, `edit_error`, `pending_delete`, and `draft_rows` form a small hand-rolled state machine with implicit invariants documented only in comments ("editing_key format...", "edit_error is a plain scalar... because editing_key already guarantees at most one cell is in edit mode"). Three prior phases have each added a new interaction that touches this machine (windowing's `cancel_edit()`+`cancel_pending_delete()` call inside `toggle_show_all_history`; CSV import's entirely separate `_staged_import_rows`/`import_stage` machine that deliberately does NOT reuse `edit_error` per the comment at line 172-178) — the invariants are easy to violate when adding a fourth interaction (better date-error UX) without re-reading all the comments describing why the scalar (not dict) `edit_error` design and the `""` empty-date sentinel matter.

**How to avoid:**
- Before changing `commit_edit`/`_commit_draft_cell`, write out (in the plan) the full state-transition table for `editing_key`/`draft_value`/`edit_error`/`draft_rows`/`pending_delete` across: normal cell edit, draft-row date entry, draft-row non-date entry, Escape, blur, window toggle, and delete-arm — and verify the fix's new behavior is added as a new column/case in that table, not a parallel mechanism.
- Reuse `edit_error` (the existing scalar) for the improved date-error display rather than introducing a new field — the existing design comment explicitly says a scalar is safe because only one cell can be in edit mode at a time; that invariant still holds for this fix.
- If the actual bug is a blur/focus race (not a missing error-set call), the fix likely belongs in `app.py`'s `_editable_cell` (e.g. don't rely solely on `on_blur` to commit — consider keeping the editor open and only committing on Enter/explicit action while showing the error live via `update_draft`-triggered client-side validation, or ensure `on_blur` firing after a validation failure re-focuses the input rather than fully losing it), not necessarily in `state.py`'s validation logic itself, since `edit_error` IS already being set correctly server-side.
- Explicitly regression-test after the fix: (1) toggle "show all history" while a draft row has an active date error — error and draft must both survive the toggle per the existing `draft_rows` untouched guarantee; (2) run a CSV import while a draft row is mid-entry with an error — the two flows are state-independent (`_staged_import_rows` vs `draft_rows`) but both call `load_rows()`, so confirm a CSV import commit doesn't clobber `self.rows` in a way that orphans an unrelated in-progress draft-row's displayed position; (3) verify `csv_import.py`'s own date validation (separate code path) either already has proper error surfacing or is explicitly out of scope for this fix (don't assume fixing `state.py`'s draft-row path also fixes CSV import's UX).

**Warning signs:**
- A new state field added for date-specific errors instead of reusing `edit_error`.
- `toggle_show_all_history`'s `cancel_edit()`/`cancel_pending_delete()` calls not updated to also reset any new field.
- No test/verification step covering "error + window toggle" or "error + CSV import" interaction, only the isolated draft-row-date-entry case.
- Fix applied only in `state.py` when the root cause is actually a client-side blur/render-timing issue in `app.py`.

**Phase to address:**
Data Entry rework phase — should explicitly include a state-transition audit of `editing_key`/`draft_value`/`edit_error`/`draft_rows`/`pending_delete` as a pre-implementation step, and regression checks against both the windowing toggle and CSV import flows as acceptance criteria, given three prior phases already share this machine.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Toggling `appearance` via `rx.color_mode` without dual-tokenizing `theme.py` | Ships a visible toggle fast | Reintroduces the exact light-text-on-dark / dark-text-on-light illegibility bug v1.2 Phase 6 fixed | Never |
| Hardcoding model name/MAPE strings directly in `app.py`/`state.py` instead of `forecasting.py` constants | Faster to ship the UI card | Silent drift from actual dispatch logic on next re-backtest | Never — PROJECT.md's "no un-backtested model ships" provenance rule implies label accuracy matters too |
| Implementing tabs as separate Reflex routes instead of client-side section toggling | Feels more "standard web nav" (URLs per section) | Duplicates/complicates `on_mount` data loading and risks losing in-flight draft/edit state on navigation | Only if draft/edit state is proven (via test) to persist across routes in this Reflex version |
| Adding a new state field for date-error display instead of reusing `edit_error` | Slightly clearer naming for the new feature | Breaks the documented "at most one cell in edit mode" scalar-safety invariant relied on elsewhere | Never without updating `toggle_show_all_history` and re-verifying the invariant |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| Radix `RadixThemesPlugin` + custom `theme.py` hex tokens | Assuming Radix's `appearance` toggle automatically re-colors custom hex literals | Dual-tokenize `theme.py` explicitly; Radix only re-colors its own component chrome, not raw hex values passed to `background=`/Plotly |
| Plotly figures rendered via `rx.plotly` inside themed cards | Setting `plot_bgcolor`/`paper_bgcolor` to a fixed color instead of transparent, breaking the "inherit card surface" trick both charts currently rely on | Keep `rgba(0,0,0,0)` backgrounds; make `font.color` (currently `MUTED_TEXT`) mode-aware instead |
| `forecast_all()` single-dispatcher pattern | Adding a second call site or a parallel metadata source for model name/MAPE outside `forecasting.py` | Extend `forecast_all()`'s return shape or add a co-located metadata accessor in `forecasting.py`, consumed from the existing single call site in `state.py`'s `forecast_results` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Re-rendering both Plotly figures (`historical_chart_figure`, `forecast_chart_figure`) on every tab switch if tabs are implemented as always-mounted-but-hidden sections | Sluggish tab switching despite no new data | If using client-side tab visibility (recommended, Pitfall 3), consider `rx.cond` unmounting inactive sections rather than CSS-hiding them, OR accept the cost since dataset is small (single-user, monthly cadence) | Unlikely to matter at this app's scale (hundreds of rows), but worth a conscious choice, not an accident |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Theme toggle with no persistence (resets to light every reload) | User has to re-toggle every session, defeating the point of PROJECT.md's "Persisted dark/light mode toggle" requirement | Store in `AppSetting` (same table/pattern as `markup_pct`), load via `on_mount` |
| Tabs that reset scroll position or lose the currently-selected chart series (`selected_series`/`forecast_series`) on switch | Feels broken, loses user's place | Since these are already state vars independent of tab implementation, verify they're untouched by whatever tab-switching mechanism is chosen |
| Fixing date-field errors by making failures louder without explaining the expected format | User still can't figure out valid input, just sees more red text | Error message + inline format hint (existing `validate_date` already returns an `error` string — verify it currently is descriptive; the CONTEXT block's diagnosis is "zero user-facing error feedback," so check its actual copy is human-readable, not just present) |

## "Looks Done But Isn't" Checklist

- [ ] **Theme toggle:** Often missing dark-mode colors for Plotly figure `font`/hover text — verify `historical_chart_figure`/`forecast_chart_figure` render legibly in dark mode, not just page chrome.
- [ ] **Background fix:** Often verified only in light mode / only at container max-width — verify at narrow, container-max, and ultra-wide viewports in BOTH appearances.
- [ ] **Tab/nav:** Often missing a check that in-progress edits/drafts/CSV-import-preview survive a tab switch — verify explicitly, don't assume.
- [ ] **Model metadata surfacing:** Often implemented as a UI-layer literal copy — verify the displayed MAPE/model name traces back to a `forecasting.py` constant via `forecast_all()`, not a hand-typed string.
- [ ] **Fan chart fix:** Often fixes legend overlap but leaves the "Forecast start" annotation now colliding with the relocated legend — verify visually with real data at multiple horizon lengths (short horizon = annotation near legend; long horizon = annotation far from legend).
- [ ] **Data Entry rework:** Often fixes the reported symptom (silent rejection) without checking CSV import's separate validation path (`csv_import.py`) has the same UX quality — verify both entry methods, not just manual draft-row entry.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Theme toggle ships with un-tokenized `theme.py` | MEDIUM | Revert toggle to a state-only no-op (force `"light"`) while `theme.py` dual-tokenizing is completed as a follow-up; don't leave `appearance="inherit"` live in the interim |
| Tabs implemented as routes lose draft state on switch | MEDIUM | Convert to client-side section toggling within the existing single `index()` page/route; low risk since `DashboardState` doesn't need to change, only `app.py`'s render structure |
| Model metadata drifts (UI shows stale MAPE after a re-backtest) | LOW | Since metadata should be sourced from `forecasting.py` constants per Pitfall 4's prevention, a drift means the wiring was done wrong — fix by pointing the UI read back to the constant, not by manually correcting the displayed number |
| Data Entry fix regresses windowing or CSV import | HIGH | Requires re-tracing the full `editing_key`/`draft_rows`/`pending_delete` state table (see Pitfall 6); recommend reverting to pre-fix behavior and re-implementing with the state-transition table written first, given three prior phases' worth of accumulated interaction surface |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| OS-dark-mode reintroduction via `appearance="inherit"` | Theme toggle phase | Grep diff for `"inherit"`; manually test with OS set to dark while app toggle is set to light — page must stay light |
| Black margins fix hardcodes one appearance | Theme toggle phase (combined with or immediately following background fix) | Test html/body background in both light and dark app-toggle states, at 3 viewport widths |
| Tab/nav breaks `on_mount` or loses draft state | Tab/nav phase | Manual test: start draft row edit or CSV preview, switch tabs, switch back — state must persist |
| Model metadata second source of truth | Model-metadata-surfacing phase | Code review: confirm displayed MAPE/name value traces to a `forecasting.py` constant referenced through `forecast_all()`, not a literal in `state.py`/`app.py` |
| Fan chart legend fix collides with vline annotation or breaks `aria_label` | Fan chart fix phase | Visual check across short/long horizons; diff review confirming `aria_label` props in `app.py` untouched |
| Data Entry date-fix regresses windowing/CSV-import | Data Entry rework phase | Full state-transition table written pre-implementation; regression test matrix covering windowing toggle + CSV import interaction with the fix |

## Sources

- `app/app/state.py` (read directly) — `editing_key`/`draft_rows`/`edit_error`/`show_all_history`/CSV import state machine, `forecast_results` single-call-site pattern, Plotly figure builders
- `app/app/app.py` (read directly) — `index()`'s single `on_mount`, `_editable_cell`'s blur/error rendering, `aria_label` placement on `rx.box` wrappers
- `app/app/theme.py` (read directly) — hardcoded hex color tokens with no dark-mode variants, comments documenting WCAG-contrast amendments (light-mode-specific)
- `app/rxconfig.py` (read directly) — `RadixThemesPlugin(theme=rx.theme(appearance="light", ...))` pinning
- `app/app/forecasting.py` (grepped directly) — model docstrings containing MAPE/model-name prose only, `forecast_all()` as documented single dispatcher (line 488-489)
- `.planning/PROJECT.md` (read directly) — v1.3 milestone scope, v1.2 Phase 6's light-only pin as a deliberate prior bug fix, Data Entry root-cause diagnosis

---
*Pitfalls research for: Reflex dashboard v1.3 feature retrofit (theme, nav, model metadata, chart fix, data-entry rework)*
*Researched: 2026-08-24*
