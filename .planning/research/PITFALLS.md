# Pitfalls Research

**Domain:** Retrofitting pagination, CSV import, richer forecast stats, and performance fixes onto an existing single-state Reflex dashboard
**Researched:** 2026-08-24
**Confidence:** HIGH (grounded directly in `app/app/state.py`, `app/app/validators.py`, `app/app/app.py`; MEDIUM/LOW flagged where Reflex-internals behavior is inferred rather than doc-verified)

## Critical Pitfalls

### Pitfall 1: Pagination silently breaks the `editing_key`/`pending_delete` addressing scheme

**What goes wrong:**
`editing_key` is a global string of the form `f"{row_date}:{column}"`, and `pending_delete` is a bare `row_date`. Both are matched against `self.rows` (the full unfiltered list) in `commit_edit`, `request_delete`, and `_editable_cell`'s `rx.cond(DashboardState.editing_key == key, ...)`. If pagination introduces a *second* list (e.g. `visible_rows` or `page_rows` derived/sliced from `self.rows`) and the table is re-pointed to render that instead, `editing_key`/`pending_delete` string matching still works IF row_date stays the addressing key — but if pagination is implemented by slicing `self.rows` itself (e.g. reassigning `self.rows` to only the current page and reloading full history separately), `commit_edit`'s DB lookup (`PriceRow.select().where(PriceRow.date == row_date)`) still works since it hits the DB, but `historical_chart_figure`, `forecast_results`, `_history_df`, `summary_cards`, `_latest_actual_for`, and `freshness_chips` ALL currently iterate `self.rows` as if it's the complete history. If pagination truncates `self.rows` to "recent months," every one of these computed vars silently starts operating on a partial dataset — forecasts, freshness chips, and the historical chart would all quietly go wrong with no error, because nothing here validates row-count completeness.

**Why it happens:**
`self.rows` is currently overloaded as both "what the table displays" and "the full history used for every derived computation." There is no separation between "display window" and "computation source" today. A pagination retrofit that touches `self.rows` directly (the obvious/fastest implementation) breaks this implicit contract everywhere at once, not just in the table.

**How to avoid:**
Introduce a *new* state var (e.g. `visible_rows` or `table_page_rows`) that is a `@rx.var`-derived slice/window of `self.rows`, and repoint ONLY the table's `rx.foreach` (line ~117 in `app.py`) to it. Never mutate `self.rows` itself for windowing — it must stay the full-history source of truth for `forecast_results`, `_history_df`, `historical_chart_figure`, `freshness_chips`, and `summary_cards`. `load_rows()` continues to load everything into `self.rows`; pagination is purely a read-side/display concern layered on top.

**Warning signs:**
- Forecast values or freshness "as of" dates change when the pagination window changes.
- `_history_df()` row count is less than the actual DB row count after paginating.
- Manually toggling "show all history" changes the forecast chart output.

**Phase to address:**
Pagination phase (Phase covering DATA table fix) — must be designed with an explicit `visible_rows` derived var from day one, not bolted on after.

---

### Pitfall 2: `editing_key`/`pending_delete` state persists across a pagination page change, pointing at an off-screen row

**What goes wrong:**
`editing_key` and `pending_delete` are plain scalar strings with no relationship to "is this row currently rendered." If the user opens a cell editor (`start_edit`) or arms a delete confirmation (`request_delete` first click), then changes the pagination window (switches page, or toggles "show all history") without committing/cancelling, the edit/delete state remains armed against a row_date that's no longer visible. Two related failure modes: (a) the user is confused because the visible table shows no active editor, but pressing Enter on an unrelated new edit could still route through a stale `editing_key` if the row-key logic isn't reset; (b) worse, `commit_edit`'s draft-row branch (`row_date == ""`) is keyed on `draft_rows` having exactly one entry — if pagination/page-size changes ever touch `draft_rows` indexing, `_commit_draft_cell` could write to the wrong row.

**Why it happens:**
The existing code was built and tested (per `test_state.py`) against a single always-fully-rendered table. Pagination introduces the concept of "row exists in DB but is not currently rendered," which the edit/delete/draft state machine has zero awareness of.

**How to avoid:**
On every pagination boundary event (page change, "show all" toggle, page-size change), explicitly call `cancel_edit()` and `cancel_pending_delete()` as part of that event handler — never let stale `editing_key`/`pending_delete` survive a visibility change. Since `draft_rows` is a single-slot mechanism unrelated to pagination (drafts are always unsaved, never paginated), leave `draft_rows` handling untouched, but make sure the paginated table still renders the draft row (likely by always appending `draft_rows` to whatever page/window is shown, matching current `app.py` behavior of two separate `rx.foreach` calls at lines 117 and 124).

**Warning signs:**
- Edit/delete confirmation UI appears "stuck" after switching pages.
- Automated test: start edit → switch page → assert `editing_key == ""`.

**Phase to address:**
Pagination phase — add explicit edit/delete-state reset to the page-change/toggle event handlers as an acceptance criterion, not an afterthought.

---

### Pitfall 3: `rx.foreach` key stability breaks under pagination/reordering, causing edit state to attach to the wrong row after a page change

**What goes wrong:**
Reflex's `rx.foreach` (like React) needs stable per-item identity to correctly diff and preserve component state across re-renders. The current implementation builds the cell key as a Var-level string concatenation of `row.date` + column (per the `app.py` comment at line 44), which is stable because `self.rows` is always the same full ordered list. If pagination reorders, slices, or the "show all history" toggle swaps between two differently-sized lists rendered by the same `rx.foreach` call, and Reflex/React is not given an explicit `key=` per item (or reuses positional index by default), item-level UI state (e.g. any local hover/focus state, or subtle Radix component state) can get attached to the wrong physical row when the underlying list changes. Reflex does not always require an explicit key on `rx.foreach`, but relying on implicit positional keys is fragile once the list is no longer stable/append-only.

**Why it happens:**
The existing table was designed for one never-reordered, monotonically-growing list. Pagination introduces list swaps (page 1 → page 2, "recent" → "all") that are exactly the case where implicit/positional keying breaks down.

**How to avoid:**
When implementing pagination, explicitly verify (via Reflex docs/Context7, not assumption) whether `rx.foreach` needs an explicit stable key for the paginated list, and if so use `row.date` (already unique per row) as that key rather than positional index. Since all cell-editing state already keys off `row.date` via `editing_key`, this is a natural, low-risk pairing.

**Warning signs:**
- After switching pages, a cell editor or hover state appears on the wrong row.
- Visual "jump"/flicker on page change beyond expected data change.

**Phase to address:**
Pagination phase — verify `rx.foreach` keying behavior via Context7/official docs before shipping, since this is exactly the kind of Reflex-specific correctness detail training data may be stale or wrong on.

---

### Pitfall 4: CSV import reuses cell-level validators in a way that produces confusing errors, or worse, silently skips them

**What goes wrong:**
Today's only validation path is `validate_numeric`/`validate_date` in `validators.py`, invoked ONE CELL AT A TIME with immediate UI feedback (`edit_error` scalar) and a hard block on commit. CSV import is fundamentally different: it's N rows × M columns arriving at once, and the natural implementation temptation is either (a) writing a parallel, hastily-built validation path that doesn't reuse `validate_numeric`/`validate_date` — causing CSV-imported data to be accepted under different rules than manually-entered data (e.g. CSV import might not enforce "no negative values" or duplicate-month rejection the same way), or (b) reusing the validators correctly per-cell but only surfacing a single `edit_error`-style scalar, which is useless for a 167-row import (user has no way to know WHICH of 2,950 cells failed).

**Why it happens:**
`edit_error: str` is a single scalar by explicit design (documented in `state.py`'s comment: "editing_key already guarantees at most one cell is in edit mode at a time"). CSV import breaks that invariant — many cells are being validated simultaneously — but the design pattern (one shared error string) is the obvious thing to copy without noticing it no longer holds.

**How to avoid:**
Reuse `validate_numeric`/`validate_date` as the single source of truth per-cell (do not fork new validation logic), but design a NEW error-reporting shape for import specifically: a list of `{row, column, error}` dicts (mirroring the `freshness_chips`/`summary_cards` list-of-flat-dicts pattern already established in this codebase), surfaced as a pre-commit "N rows will import, M rows have errors" preview before any DB write. Import should also enforce `validate_date`'s duplicate-month rule across the *entire incoming batch*, not just against existing DB rows — two CSV rows for the same month must be caught too (this is a case `validate_date` doesn't currently need to handle, since `_commit_draft_cell` only ever adds one row at a time).

**Warning signs:**
- CSV import accepts negative prices or malformed dates that manual entry would reject.
- Two CSV rows for the same month both get inserted (duplicate-month check doesn't catch same-batch duplicates).
- Import either fully succeeds or fully fails with no per-row detail on which rows had problems.

**Phase to address:**
CSV import phase — validator reuse + batch-duplicate-check + structured multi-row error reporting should be explicit acceptance criteria.

---

### Pitfall 5: CSV import bypasses the row-level DB write pattern and violates the "state.py is the sole DB path" architecture rule

**What goes wrong:**
Per the module docstring, `DashboardState` is documented as "the only place in the app that opens an `rx.session()` or touches the ORM." A CSV import feature needs to do bulk inserts/updates, which is a very different code shape from the current one-row-at-a-time `session.add(PriceRow(**kwargs)); session.commit()` pattern used in `_commit_draft_cell` and `commit_edit`. It's tempting to write a separate `import.py` module with its own `rx.session()` calls for performance/testability reasons (bulk insert helpers are easier to unit test standalone) — but that silently violates the established single-DB-path architecture rule, creating two independent places that can drift out of sync on schema/session handling.

**Why it happens:**
Bulk import genuinely benefits from being pulled into a plain, testable function (mirroring how `forecast_all`/`_export_bytes` are kept as plain methods/functions per the docstring's own reasoning) — but "testable helper function" and "opens its own DB session outside state.py" are two different things, and it's easy to conflate them.

**How to avoid:**
Write the CSV parsing + row-validation logic as a pure function (no Reflex, no ORM) similar to `validators.py`'s existing dependency-free design — parse rows, validate, return a list of validated dicts + a list of errors. Then have a `DashboardState` event handler own the actual `rx.session()` bulk-write step, keeping the "sole DB path" rule intact. This also makes the parsing/validation testable exactly like `test_validators.py` already does, without needing Reflex's state/event machinery in tests.

**Warning signs:**
- A new module opens `rx.session()` outside `state.py`.
- CSV import and manual-entry code paths use different SQLAlchemy session patterns.

**Phase to address:**
CSV import phase — architecture review checkpoint before implementation, referencing the existing `state.py` docstring rule explicitly.

---

### Pitfall 6: New computed stats (historical high/low, % change) get derived from `self.rows` instead of reusing `_latest_actual_for`/`forecast_results`, causing drift from `summary_cards`

**What goes wrong:**
`summary_cards`' delta_text/% change logic (lines ~384-401 in `state.py`) already computes "% change vs. latest actual" for each of the 4 SUMMARY_CARD_SERIES, using `_latest_actual_for(key)` — which has special-cased logic for `diesel_mnt` (multiplying `diesel_usd_ton * fx_rate * (1 + markup_pct/100)`, only from rows where BOTH fields are non-None). If "richer forecast context" adds a NEW computed var for historical high/low or a differently-scoped % change (e.g. "since data start" instead of "vs latest actual"), and that new var re-implements its own loop over `self.rows` without reusing `_latest_actual_for`'s `diesel_mnt` derivation convention, the two numbers can disagree for diesel — e.g. summary_cards' delta uses the markup-adjusted latest actual, but a naively-added "% change" stat might use raw `diesel_usd_ton` history without the FX/markup multiplier, producing a % change badge that contradicts the summary card's arrow/delta on the same page.

**Why it happens:**
`diesel_mnt` isn't a stored column — it's always derived on the fly, and that derivation logic currently lives in three near-duplicate places already (`_latest_actual_for`, `forecast_chart_figure`'s historical segment, and `_export_bytes`/`_history_df` don't touch it but forecast_results computation does via `forecasting.py`). Adding a 4th ad-hoc reimplementation for a new stat is the path of least resistance and the most likely drift source.

**How to avoid:**
Extract the `diesel_mnt` derivation (the `if row.diesel_usd_ton is not None and row.fx_rate is not None: value = row.diesel_usd_ton * row.fx_rate * multiplier` pattern) into a single private helper (e.g. `_diesel_mnt_series(self) -> list[tuple[str, float]]`) and have `_latest_actual_for`, `forecast_chart_figure`, and any new historical-high/low/%-change var all call it, rather than each hand-rolling the loop. New computed vars must be built as `@rx.var` properties that call `_latest_actual_for`/`_diesel_mnt_series` rather than reading `self.rows` raw whenever the series involves `diesel_mnt`.

**Warning signs:**
- A "% change" or "52-week high/low" badge shows a number that doesn't reconcile with the existing summary card's arrow direction for Diesel MNT specifically (the other 3 series — hdan, ppan, fx_rate — are plain columns and much less likely to drift since they're direct `getattr` reads).
- Code review finds a new `for row in self.rows: if row.diesel_usd_ton is not None and row.fx_rate is not None` loop that isn't calling an existing helper.

**Phase to address:**
Forecast-context enrichment phase — refactor the `diesel_mnt` derivation into one shared helper as a prerequisite/first task before adding new stats on top of it.

---

### Pitfall 7: New computed vars re-run expensive work (forecast_all, DataFrame construction) on every access instead of reading cached `forecast_results`

**What goes wrong:**
The codebase has an explicit, repeatedly-documented rule ("Pitfall 2 guard — exactly one call site app-wide") that `forecast_all()` must only be invoked from `forecast_results`, and every other var (`summary_cards`, `forecast_chart_figure`, `forecast_table_rows`) reads `self.forecast_results` rather than recomputing. This is called out three separate times in comments, meaning it was a real, already-encountered pitfall in this exact codebase. A naive implementation of "historical high/low" or "% change" that needs forecast data (e.g. "% change vs. forecast base" rather than vs. latest actual) is at high risk of re-deriving forecast values independently instead of reading the cached `forecast_results` dict, especially if the new stat is computed in a different file/module than `state.py` and doesn't inherit awareness of this convention.

**Why it happens:**
`forecast_results` is an `@rx.var`, and Reflex computed vars look like plain properties — it's easy for a new contributor (or an AI agent) to call `forecast_all(...)` directly again "just for this one stat" without realizing it duplicates an expensive statsmodels fit and violates the established single-call-site rule, especially since `forecast_all`/`forecasting.py` isn't shown in this research pass but is imported directly into `state.py`.

**How to avoid:**
Any new stat that needs forecast output must be implemented as an `@rx.var` (or plain method) that reads `self.forecast_results`, never importing/calling `forecast_all` a second time. Add this as an explicit code-review checklist item for the forecast-enrichment phase, mirroring the existing in-code comments.

**Warning signs:**
- `grep -n "forecast_all(" app/app/state.py` returns more than one call site.
- New feature noticeably slows down forecast horizon changes (statsmodels fit is not free; re-running it per new stat access would be a visible perf regression).

**Phase to address:**
Forecast-context enrichment phase — enforce via code review / grep check as an explicit gate before merge.

---

### Pitfall 8: Historical high/low over ALL history silently becomes O(n) per render as data grows, compounding with existing per-render loops

**What goes wrong:**
`historical_chart_figure`, `_export_bytes`, `_history_df`, `freshness_chips`, and `summary_cards` (via `_latest_actual_for`) already each do a full O(n) pass over `self.rows` on every recompute — this is fine at 167 rows but is a pattern that's about to be repeated again for high/low and % change stats. None of this is currently disastrous, but it means "performance" work in this milestone has two distinct problems that must not be conflated: (1) the *table rendering* problem (2,950 `<td>` DOM nodes — the actual reported bug), which pagination fixes, and (2) *computed-var recomputation cost*, which pagination does NOT fix, because `forecast_results`, `summary_cards`, `historical_chart_figure` etc. all read `self.rows` (full history), not the paginated window. If new high/low/%-change vars are added without noticing this distinction, there's a risk of assuming pagination "solved performance" and then adding more full-history loops unconcerned about cost, when the real fix for computed-var cost (if it ever matters at this data scale) is Reflex's var-caching (`@rx.var` already caches until dependencies change) — which is already correctly used, but every new var must depend only on what actually changed, or it will recompute more often than necessary.

**Why it happens:**
"Performance" in the milestone framing conflates a DOM-rendering bug (2,950 cells) with computed-var cost, but they need different fixes: pagination for the former, careful `@rx.var` dependency scoping for the latter. At 167 rows monthly-cadence data, O(n) Python loops (167 iterations) are not a real performance risk today — but the milestone explicitly asks for "general performance patterns... as data grows," so this distinction should be documented even though it's not urgent yet.

**How to avoid:**
Treat pagination (DOM node count) and computed-var recomputation cost as two separate concerns in planning. Don't assume fixing the table pagination bug also "fixes performance" broadly. For new high/low/%-change vars, keep them as separate small `@rx.var`s (not embedded inside `summary_cards`) so Reflex's dependency tracking only recomputes what actually changed (e.g. changing `horizon_months` shouldn't force recomputation of a historical-high/low var that only depends on `self.rows`, since Reflex caches `@rx.var`s per-dependency).

**Warning signs:**
- A new stat is computed inline inside `summary_cards` or `forecast_results` rather than as its own `@rx.var`, forcing it to recompute whenever those vars' unrelated dependencies change.
- Perf profiling later shows `self.rows` being iterated redundantly many times per single user interaction (e.g. once for `historical_chart_figure`, once for `freshness_chips`, once for a new high/low var, once for `_latest_actual_for` — each doing its own separate pass).

**Phase to address:**
Performance-patterns research/phase — document the pagination-vs-computed-var distinction explicitly in that phase's scope, and split new stats into independent `@rx.var`s.

---

### Pitfall 9: Reflex full-state re-render storms from high-frequency events colliding with paginated table + new import UI

**What goes wrong:**
Reflex ships the entire state delta to the client on every event by default (unless using more granular state substates), and `update_draft`'s own comment already flags this exact concern ("Fires on every keystroke — never touch the DB or reload here"). Pagination introduces new candidate high-frequency events: a page-size input, a "jump to page N" control, or (worse) a live-filter/search box for the table. If any of these are implemented naively — e.g. calling `load_rows()` or recomputing `forecast_results`-dependent vars on every keystroke of a page-jump input, the way `update_draft` deliberately avoids — this reintroduces exactly the kind of full-recompute-per-event cost the codebase has so far been careful to avoid. CSV import adds another high-risk case: a large file upload progress/preview UI that updates state on every parsed row rather than in one batch.

**Why it happens:**
Reflex's whole-state-per-event model (`DashboardState` is a single monolithic state class here, not split into substates) means ANY event handler mutation triggers a full re-send/re-render of everything bound to that state, including expensive computed vars like `forecast_results`/`forecast_chart_figure` if they're on the same page. This is already implicitly acknowledged by the existing `update_draft` comment but hasn't been tested against a paginated table or a bulk-import UI yet.

**How to avoid:**
Keep the existing discipline: pagination controls and CSV import progress should mutate lightweight scalar/list vars only, and defer any DB read (`load_rows()`) or heavy computed-var-triggering mutation to an explicit "commit" action (mirroring how cell edits already separate `update_draft` — cheap, per-keystroke — from `commit_edit` — DB write + reload). For CSV import specifically, parse the whole file client-side-adjacent in one event handler call (not row-by-row state updates) and only update state once with the full parsed preview.

**Warning signs:**
- UI lag/jank when typing in a new pagination or CSV-related input field.
- Network tab shows large state-delta payloads firing on every keystroke of a new control.

**Phase to address:**
Both pagination phase and CSV import phase — apply the existing `update_draft` cheap-mutation pattern to any new high-frequency input.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Slice `self.rows` directly for pagination instead of adding a separate `visible_rows` var | Less code, faster to ship | Breaks every other computed var that assumes `self.rows` is full history (Pitfall 1) | Never |
| Fork a new validation path for CSV import instead of reusing `validate_numeric`/`validate_date` | Faster to write in isolation | Manual entry and CSV import silently enforce different rules (Pitfall 4) | Never |
| Compute new stats inline inside `summary_cards` rather than as separate `@rx.var`s | Less boilerplate, one function to read | Forces unrelated recomputation, harder to test independently (Pitfall 8) | Only for a genuinely tiny, cheap addition with no independent test need |
| Single scalar error string for CSV import errors (copy `edit_error` pattern) | Reuses existing UI pattern | Useless for multi-row import — user can't see which of N rows failed (Pitfall 4) | Never for import; fine to keep for single-cell edit |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|--------------|------------------|-------------------|
| CSV import → SQLite/`rx.Model` | Bulk `session.add_all()` without checking for duplicate months within the batch itself | Validate batch-internal duplicates using `validate_date`'s existing month-uniqueness logic extended to check against both DB rows AND previously-validated rows in the same import batch |
| CSV import → existing `_editable_cell`/`edit_error` UI pattern | Reusing the single-scalar `edit_error` var for import errors | New list-of-dict error shape (mirrors `freshness_chips`/`summary_cards` pattern already in this codebase) |
| Excel export polish → `openpyxl`/pandas | Adding new export columns (e.g. forecast data) directly into `_export_bytes` without checking the D-08 constraint documented in the code ("the actuals table only, never forecast output") | Confirm scope with `.planning/PROJECT.md`/prior decisions before adding forecast columns to export; if forecast export is now in scope, build it as a clearly separate export function, not a silent extension of `_export_bytes` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Rendering full `self.rows` via `rx.foreach` in the table (existing bug) | Browser hang, 2,952 `<td>` DOM nodes at 167 rows | Windowed `visible_rows` derived var, default to recent N months | Already broken today at 167 rows/17 cols |
| O(n) Python loops over `self.rows` repeated across many separate computed vars (`historical_chart_figure`, `freshness_chips`, `_latest_actual_for`, future high/low stat) | Slower page interactions as row count grows into the thousands | Consolidate repeated full-history scans into shared helpers where reasonable; rely on Reflex's `@rx.var` caching to avoid redundant recompute per single event | Not urgent at current ~167-row monthly scale; becomes worth optimizing only if row count grows an order of magnitude or weekly-cadence mode ships |
| CSV import synchronously parsing + validating a large file in one blocking event handler | UI freezes during import of a large file | Keep parse+validate as a fast pure function (pandas read_csv is fast for hundreds of rows); if file sizes grow much larger, consider chunked/background processing — not needed at this project's current data scale | Only a concern if import files grow beyond low thousands of rows; not a v1.2 blocker given documented ~167-row dataset |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| CSV import trusting file content without the same validation as manual entry | Negative prices, malformed dates, or nonsense values silently persisted to SQLite, corrupting forecast input for a single-user app where no one else will catch it | Route all import cell values through `validate_numeric`/`validate_date` before any DB write, exactly like manual entry (Pitfall 4) |
| CSV import accepting arbitrarily large files without a size/row-count sanity check | A malformed or huge file could hang the single Reflex process for the one user, or explode memory in `pandas.read_csv` | Add a basic row-count sanity cap (e.g. reject files with more rows than plausible for monthly data) as defense-in-depth, even for a trusted single-user context |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Pagination default window too small/large without checking real data recency | User has to click into "show all" every session just to see recent months, or misses that older months exist | Default window should match the milestone's stated intent ("recent months") — confirm exact N (e.g. last 12 or 24 months) against how the user actually works, not an arbitrary guess |
| CSV import with no dry-run/preview before committing | User accidentally overwrites/duplicates months with no ability to review before commit, given SQLite has no UI-level undo | Always show a "N rows will be added, M rows have errors, review before import" preview step, mirroring the two-click delete confirmation pattern (`pending_delete`) already used elsewhere in this app for other risky one-way actions |
| New forecast stats (high/low, % change) added without matching the existing card visual language (arrows/direction/caption pattern in `summary_cards`) | Inconsistent, harder-to-parse dashboard | Reuse the existing flat-dict-list-of-cards rendering pattern (`SUMMARY_CARD_SERIES`/`summary_cards`) for new stats rather than inventing a new visual pattern |

## "Looks Done But Isn't" Checklist

- [ ] **Pagination:** Often missing — verify `forecast_results`/`summary_cards`/`freshness_chips`/`historical_chart_figure` still operate on FULL history, not the paginated window, after the change.
- [ ] **Pagination:** Often missing — verify edit/delete state (`editing_key`, `pending_delete`) is explicitly reset on every page-change/toggle event.
- [ ] **CSV import:** Often missing — verify batch-internal duplicate-month detection (two rows in the same CSV for the same month), not just duplicate-vs-DB detection.
- [ ] **CSV import:** Often missing — verify import goes through the SAME `validate_numeric`/`validate_date` functions as manual cell edit, not a reimplementation.
- [ ] **New forecast stats (high/low, % change):** Often missing — verify the `diesel_mnt` derivation (usd × fx × markup) is reused via a shared helper, not reimplemented, to avoid drift with `summary_cards`.
- [ ] **New forecast stats:** Often missing — verify no new call site to `forecast_all()` was added; must read cached `self.forecast_results`.
- [ ] **Excel export polish:** Often missing — verify any scope change (e.g. adding forecast data to export) doesn't silently violate the documented D-08 "actuals table only" constraint without an explicit decision to change it.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Pagination breaks computed vars by slicing `self.rows` (Pitfall 1) | LOW | Revert the slice; introduce `visible_rows` as a separate `@rx.var`; repoint only the table's `rx.foreach` |
| CSV import used a forked/weaker validation path (Pitfall 4) | MEDIUM | Re-run all previously-imported rows through `validate_numeric`/`validate_date`; flag and surface any rows that would now fail; requires a data-quality pass over already-committed SQLite rows |
| New stat drifted from `summary_cards` due to duplicated `diesel_mnt` logic (Pitfall 6) | LOW | Extract shared helper retroactively; both call sites converge once helper lands; low risk since it's a pure-function refactor with existing test coverage patterns (`test_state.py`) to lean on |
| Double `forecast_all()` call site introduced (Pitfall 7) | LOW | `grep` for the second call site, replace with a read of `self.forecast_results` |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Pagination breaks full-history computed vars (Pitfall 1) | Pagination phase | Code review: `grep -n "self.rows" app/app/state.py` confirms no pagination-window var is aliased into it; forecast/chart/freshness vars unaffected by page changes in manual test |
| Stale edit/delete state across page changes (Pitfall 2) | Pagination phase | Test: start edit → change page/toggle → assert `editing_key == "" ` and `pending_delete == ""` |
| `rx.foreach` key stability under pagination (Pitfall 3) | Pagination phase | Confirm via Context7/official Reflex docs whether explicit `key=row.date` is needed for the paginated foreach; manual test of page-switch behavior for visual glitches |
| CSV import validation drift from manual entry (Pitfall 4) | CSV import phase | Unit test: same malformed CSV cell rejected by both `validate_numeric`/`validate_date` directly and by the import pipeline |
| CSV import violates single-DB-path architecture rule (Pitfall 5) | CSV import phase | Code review: `grep -n "rx.session()" app/app/*.py` shows only `state.py` |
| `diesel_mnt` derivation drift in new stats (Pitfall 6) | Forecast-enrichment phase | Code review: new high/low/%-change vars call a shared `_diesel_mnt_series`/`_latest_actual_for` helper, not a raw loop |
| Duplicate `forecast_all()` call site (Pitfall 7) | Forecast-enrichment phase | `grep -n "forecast_all(" app/app/state.py` returns exactly 1 result |
| Conflating pagination fix with computed-var perf fix (Pitfall 8) | Performance-patterns phase | Explicit scope note in phase plan distinguishing DOM-node reduction (pagination) from `@rx.var` recomputation cost |
| Re-render storms from new high-frequency inputs (Pitfall 9) | Pagination + CSV import phases | Manual test: typing/interacting with new pagination/import controls doesn't trigger `load_rows()` or forecast recomputation per keystroke |

## Sources

- Direct code reads: `app/app/state.py`, `app/app/validators.py`, `app/app/app.py` (grep), `.planning/PROJECT.md` — HIGH confidence, these are the actual system being modified
- Reflex `rx.foreach` key-stability behavior — MEDIUM/LOW confidence, inferred from general React/Reflex diffing conventions and the existing in-code comment about Var-level key construction; NOT independently re-verified against current Reflex 0.9.8 docs in this pass — flagged in Pitfall 3 as needing Context7/official-doc verification before the pagination phase ships
- Reflex whole-state-per-event model and `@rx.var` caching-by-dependency behavior — MEDIUM confidence, consistent with Reflex's documented state/event architecture and with this codebase's own in-code comments (`update_draft`'s "never touch the DB or reload here" note), but not independently re-verified via Context7 in this pass

---
*Pitfalls research for: Prediction Dashboard v1.2 (Data Entry Fix & Forecast Enrichment)*
*Researched: 2026-08-24*
