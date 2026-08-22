# Phase 4: Data Entry UI & Historical View - Research

**Researched:** 2026-08-22
**Domain:** Reflex (Python full-stack) editable table UI + rx.plotly single-series historical chart
**Confidence:** MEDIUM-HIGH (Reflex event/state mechanics are officially documented and stable; exact prop names cross-checked against docs; no Context7 MCP tool was available in this environment, so verification is via WebFetch of official reflex.dev pages, not a live SDK query)

## Summary

This phase turns Phase 1's read-only `data_table()` into an editable spreadsheet-like grid
(click-to-edit cells, add-row, two-click delete) and adds one `rx.plotly` line chart with a
series-selector dropdown. Nothing in this phase requires new dependencies — Reflex core
components (`rx.table`, `rx.input`, `rx.select`, `rx.icon`, `rx.plotly`) plus `plotly.express`
(already pinned per STACK.md) cover the entire UI surface. The hard part is not the widgets,
it's the **state design**: Reflex tables render via `rx.foreach` over a list State var, and
`rx.foreach` items are opaque `Var` proxies inside the loop body — you cannot do
`if row.date == editing_row_id` in Python because `row` is a Var, not a real object at
render time. The standard pattern is to key edit/delete/pending state by a stable row
identifier (the row's `date` string, since D-02 already enforces it's unique) stored in
*separate* State dicts (`editing_cell: dict[str, str]`, `pending_delete: str | None`), not by
mutating flags on the `PriceRow` model objects themselves.

The DB-is-source-of-truth pattern (PITFALLS.md Pitfall 4) governs every write: cell edits,
new rows, and deletes must call `rx.session()` and commit before `self.rows` is
reloaded/updated — never let `self.rows` (the in-memory State list) diverge from SQLite even
transiently across a page refresh. The one deliberate exception, explicitly required by D-06,
is the new "Add row" row: it lives in `self.rows`-adjacent client state without a DB write
until its Date cell passes D-02 validation (valid + non-duplicate month) — this needs a
second, distinct in-memory list (e.g. `draft_rows`) rather than jamming an unsaved row into
`self.rows`, so the "reload from DB" path never risks reloading over an unsaved draft.

**Primary recommendation:** Model state as three additions to `DashboardState`: (1) a
`dict[str, str]` keyed by `f"{row_date}:{column}"` tracking which single cell is currently in
edit mode plus its draft value, (2) a `str | None` for the one row currently in delete-confirm
state, (3) a small list of not-yet-persisted draft rows for D-06. Keep all SQLite writes as
plain `with rx.session() as session:` blocks inside `DashboardState` event handlers (no new
DB access points), matching Phase 1's established boundary.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cell edit UI (input rendering, focus, key handling) | Frontend Server (Reflex State/compiled component) | — | Reflex compiles Python State + components to a single reactive frontend; there is no separate browser-only JS tier in this stack |
| Cell validation (numeric/date rules, D-01/D-02) | API/Backend (Reflex event handler, Python) | — | Validation must run server-side in the Reflex event handler before any `session.add`/`commit` — Reflex event handlers execute in the backend process even though they feel like client code; this is the only place that can safely gate a SQLite write |
| Row persistence (add/edit/delete) | Database/Storage (SQLite via `rx.Model`) | API/Backend (`rx.session()` call site) | Matches Phase 1's established pattern: `DashboardState` is the sole `rx.session()` call site (STATE.md decision log) |
| Historical chart rendering | Frontend Server (Reflex `rx.plotly` + computed `@rx.var`) | — | Chart figure is built server-side from `self.rows` + `self.selected_series` inside a computed var, then serialized to the frontend for Plotly.js to render — no separate charting service |
| Series selector state | Frontend Server (Reflex State var `selected_series`) | — | Simple reactive dropdown binding, no DB round-trip needed (chart recomputes from already-loaded `self.rows`) |

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Numeric validation uniform across all 16 series columns: reject non-numeric,
  reject negative, allow blank/null. No series-specific range checks.
- **D-02:** Date must be a valid date AND must not duplicate an existing row's calendar
  month. Adding a row for an existing month is rejected (edit existing row instead).
- **D-03:** Historical chart covers all 16 series columns (full parity with the table), not
  just the 4 headline series.
- **D-04:** One chart with a series selector/toggle — not 16 mini-charts, not one overlaid
  mega-chart. Each series shown one at a time (implicit per-series y-axis scale).
- **D-05:** Click-to-edit per cell; blur or Enter commits. No per-row edit-mode toggle, no
  separate Save/Cancel buttons.
- **D-06:** "Add row" button appends a blank row at the bottom, cells behave like existing
  cells. New row's Date cell must satisfy D-02 before the row is persisted to SQLite — not
  written with no date.
- **D-07:** Click-delete-again-to-confirm: first click relabels/recolors to a confirm state,
  second click within that state deletes. No modal.

### Claude's Discretion
None flagged this round — all four presented gray areas were explicitly decided.

### Deferred Ideas (OUT OF SCOPE)
None raised outside phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Add a new row of monthly actuals in the dashboard | "Add-Row-With-Deferred-Persist" pattern below; `draft_rows` State list + D-02 gate before `session.add` |
| DATA-02 | Edit existing row inline, no modal/form | "Click-to-Edit Cell" pattern below; per-cell edit-state dict keyed by row date + column |
| DATA-03 | Delete a row with a confirm step | "Delete-Confirm State Machine" pattern below; single `pending_delete: str \| None` State var |
| DATA-04 | Validate on save (numeric reject non-numeric/negative; D-01) | Server-side validation inside the commit event handler, before `session.add`/`commit`; UI-SPEC copy variants mapped to validation branches |
| DATA-05 | All writes persist in SQLite, survive restart/refresh | Every commit path calls `rx.session()` + `session.commit()`; `self.rows` reloaded via `load_rows()` after each write (never trust in-memory mutation alone) |
| VIS-01 | Historical chart of actuals (no forecast), per series | `rx.plotly` + `plotly.express.line` computed var pattern below; series selector `rx.select` bound to `selected_series` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| reflex | 0.9.8.post1 (per STACK.md, already installed) | `rx.table`, `rx.input`, `rx.select`, `rx.icon`, `rx.plotly`, State/event system | Already the project's locked framework; no new dependency needed for this phase |
| plotly | 6.9.0 (per STACK.md, already installed) | `plotly.express.line` to build the historical chart figure server-side | `rx.plotly` renders any `plotly.graph_objects.Figure`; `plotly.express` is the standard high-level API for a single-series time-series line chart |

No new packages are required for this phase. `[CITED: .planning/research/STACK.md]`

### Supporting
None beyond what STACK.md already pins.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `rx.plotly` + `plotly.express.line` | `rx.recharts.line_chart` | Recharts is lighter and matches Reflex's default aesthetic more closely, but STACK.md already locked `rx.plotly` for this project's charting needs (bull/bear band rendering in Phase 5 needs Plotly-specific shaded-region support); staying consistent avoids maintaining two charting idioms across Phase 4 and Phase 5 |
| Per-cell edit-state dict | A boolean `is_editing` flag added directly to a mutable Python dataclass mirroring `PriceRow` | Rejected: `rx.foreach` iterates `self.rows: list[PriceRow]`, and `PriceRow` is an `rx.Model`/SQLModel instance — adding transient UI-only fields to the ORM model conflates persistence schema with UI state and risks Reflex trying to serialize/diff those fields as part of the model's reactive Var tracking |

**Installation:**
No install step required — dependencies already present per STACK.md.

## Package Legitimacy Audit

Not applicable — this phase adds zero new external packages. Both `reflex` and `plotly` were
already audited/pinned in the Phase 1-era STACK.md research.

## Architecture Patterns

### System Architecture Diagram

```
Browser (compiled Reflex frontend, React under the hood)
   |
   |  click cell -> on_click sets editing_cell[key] = current_value
   |  type -> on_change updates draft value (debounced)
   |  blur / Enter -> on_blur / on_key_down("Enter") fires commit_cell(row_date, column)
   v
Reflex Backend (DashboardState event handlers, Python process)
   |
   |  commit_cell(row_date, column, value):
   |    1. validate value (D-01 numeric rule, or D-02 date rule if column == "date")
   |    2. if invalid -> set validation_error[key] = <copy from UI-SPEC>, stay in edit mode, DO NOT touch DB
   |    3. if valid -> rx.session(): fetch PriceRow by date, setattr, session.commit()
   |    4. self.load_rows()  # reload self.rows from DB, source-of-truth reassert
   |    5. clear editing_cell[key]
   v
SQLite (price_row table, unique index on date)
   |
   v
DashboardState.rows (list[PriceRow], reloaded post-write)
   |
   v
data_table() re-renders via rx.foreach(DashboardState.rows, ...)
historical_chart() re-renders via @rx.var line_chart_figure(self) built from self.rows + self.selected_series
```

Add-row path branches before step 3 above: while `draft_rows` entries lack a valid,
non-duplicate date, edits to non-date cells on that row update the draft list only (no
`session.add`); once the date cell passes validation, the draft row is promoted — inserted
into SQLite and removed from `draft_rows`, then `self.rows` reload picks it up naturally.

### Recommended Project Structure
No new files needed — this phase extends existing modules:
```
app/app/
├── models.py    # unchanged (PriceRow, AppSetting already defined in Phase 1)
├── state.py     # DashboardState gains: editing_cell, validation_error, pending_delete,
│                #   draft_rows vars + add_row/commit_cell/delete_row/cancel_edit/select_series
│                #   event handlers, plus a computed @rx.var for the chart figure
└── app.py       # data_table() cells become conditional (rx.cond edit vs display),
                 #   add "Add row" button, add historical_chart() component + rx.select
```

### Pattern 1: Click-to-Edit Cell
**What:** Each table cell renders either static text or an `rx.input`, switching based on
whether `f"{row.date}:{column}"` is the currently-tracked edit key in State.
**When to use:** Every editable cell in `data_table()` (DATA-02, D-05).
**Example:**
```python
# Source: reflex.dev/docs/library/forms/input/ (on_blur, on_key_down, value/on_change)
#         reflex.dev/docs/getting-started/basics/ (rx.cond conditional rendering)
class DashboardState(rx.State):
    rows: list[PriceRow] = []
    editing_key: str = ""          # f"{date}:{column}", "" means nothing is being edited
    draft_value: str = ""
    error_by_key: dict[str, str] = {}

    def start_edit(self, key: str, current_value: str):
        self.editing_key = key
        self.draft_value = current_value or ""
        self.error_by_key.pop(key, None)

    def update_draft(self, value: str):
        self.draft_value = value

    def cancel_edit(self):
        self.editing_key = ""
        self.draft_value = ""

    def commit_edit(self):
        key = self.editing_key
        if not key:
            return
        row_date, column = key.split(":", 1)
        ok, error_or_value = self._validate(column, self.draft_value)
        if not ok:
            self.error_by_key[key] = error_or_value
            return  # stay in edit mode, do not write to DB
        with rx.session() as session:
            row = session.exec(PriceRow.select().where(PriceRow.date == row_date)).first()
            setattr(row, column, error_or_value)
            session.add(row)
            session.commit()
        self.error_by_key.pop(key, None)
        self.editing_key = ""
        self.load_rows()

    def handle_key_down(self, key: str):
        if key == "Enter":
            self.commit_edit()
        elif key == "Escape":
            self.cancel_edit()


def _editable_cell(row: PriceRow, attr: str) -> rx.Component:
    key = row.date + ":" + attr  # Var-level string concat, valid inside rx.foreach
    value = getattr(row, attr)
    display = rx.cond(value != None, value, "")
    return rx.table.cell(
        rx.cond(
            DashboardState.editing_key == key,
            rx.vstack(
                rx.input(
                    value=DashboardState.draft_value,
                    on_change=DashboardState.update_draft,
                    on_blur=lambda: DashboardState.commit_edit,
                    on_key_down=DashboardState.handle_key_down,
                    auto_focus=True,
                ),
                rx.cond(
                    DashboardState.error_by_key.contains(key),
                    rx.text(DashboardState.error_by_key[key], color="red", size="1"),
                ),
            ),
            rx.text(display, on_click=lambda: DashboardState.start_edit(key, display)),
        )
    )
```
**Confidence:** MEDIUM. `on_blur`/`on_key_down`/`value`/`on_change` prop names verified via
official docs fetch. The exact combination of `rx.cond` + `rx.foreach` + per-cell dict lookup
(`error_by_key.contains(key)` / `error_by_key[key]`) is a standard Reflex idiom for dict Vars
but was not run/tested in this environment — the planner should treat the precise Var
indexing syntax (`dict_var[key]` vs `dict_var.get(key)`) as needing a quick spike/smoke test
during execution, since Reflex's Var-proxy operator overloading has had version-to-version
differences.

### Pattern 2: Add-Row-With-Deferred-Persist (D-06)
**What:** "Add row" appends a client-only draft row; the row is only written to SQLite once
its date cell passes D-02 validation.
**When to use:** The "Add row" button and the resulting blank row's cells (DATA-01, D-06).
**Example:**
```python
class DashboardState(rx.State):
    rows: list[PriceRow] = []
    draft_rows: list[PriceRow] = []   # unsaved, date not yet valid/persisted

    def add_row(self):
        self.draft_rows.append(PriceRow(date=""))  # unsaved sentinel: empty date

    def commit_edit(self):
        key = self.editing_key
        row_date, column = key.split(":", 1)
        # Distinguish draft vs. persisted target by checking draft_rows first.
        draft = next((r for r in self.draft_rows if r.date == row_date or (row_date == "" and column != "date")), None)
        if column == "date":
            ok, value_or_error = self._validate_date(self.draft_value)
            if not ok:
                self.error_by_key[key] = value_or_error
                return
            if draft is not None:
                # Promote: this draft row now has a valid, non-duplicate date -> persist it.
                draft.date = value_or_error
                with rx.session() as session:
                    session.add(draft)
                    session.commit()
                self.draft_rows.remove(draft)
                self.load_rows()
                self.editing_key = ""
                return
            # else: editing the date on an already-persisted row (rename month) -- normal path
        # ... numeric column path as in Pattern 1, but if `draft is not None`,
        #     mutate the draft_rows entry in place instead of writing to SQLite,
        #     since a draft row with no valid date must never reach session.add().
```
**Key insight:** the row identity problem (how do you find "the" blank row among possibly
multiple in-progress drafts before it has a date) means D-06 as decided only guarantees
correctness for a single in-flight draft row at a time — RESEARCH flags this as an open
question below (only one blank row should be addable/editable until it's saved, or drafts
need a synthetic client-side UUID key instead of `date`). Recommend gating the "Add row"
button to be disabled (or replacing the newest draft) while any `draft_rows` entry still has
an empty date, to sidestep the multi-draft identity problem entirely — this is the simplest
approach consistent with D-06's spirit ("no separate add-row form UI") and avoids needing a
synthetic ID system.
**Confidence:** MEDIUM — the general "hold unsaved state separately, promote on validation"
pattern is standard Reflex practice (PITFALLS.md Pitfall 4 already establishes DB-as-source-
of-truth), but the specific single-draft-at-a-time constraint is this research's own design
decision to resolve an ambiguity D-06 doesn't fully specify (see Open Questions).

### Pattern 3: Delete-Confirm State Machine (D-07)
**What:** One State var tracks which single row (by date) is in "confirm delete" state.
**When to use:** The trash-icon delete control in each row (DATA-03, D-07).
**Example:**
```python
class DashboardState(rx.State):
    pending_delete: str = ""  # row date currently in confirm state, "" = none

    def request_delete(self, row_date: str):
        if self.pending_delete == row_date:
            # second click: actually delete
            with rx.session() as session:
                row = session.exec(PriceRow.select().where(PriceRow.date == row_date)).first()
                if row:
                    session.delete(row)
                    session.commit()
            self.pending_delete = ""
            self.load_rows()
        else:
            self.pending_delete = row_date

    def cancel_pending_delete(self):
        self.pending_delete = ""


def _delete_cell(row: PriceRow) -> rx.Component:
    return rx.table.cell(
        rx.cond(
            DashboardState.pending_delete == row.date,
            rx.button(
                "Confirm delete?",
                color_scheme="red",
                on_click=lambda: DashboardState.request_delete(row.date),
                on_blur=DashboardState.cancel_pending_delete,  # UI-SPEC: revert on blur/click-away
            ),
            rx.icon_button(
                rx.icon("trash-2"),
                variant="ghost",
                color_scheme="red",
                on_click=lambda: DashboardState.request_delete(row.date),
            ),
        )
    )
```
Because `pending_delete` is a single scalar (not a dict), only one row can be in confirm
state at a time — clicking a different row's delete icon while another is pending silently
overwrites `pending_delete` to the new row (never triggers accidental delete of the old one,
since the second click always compares against the *current* `pending_delete` value). This is
consistent with UI-SPEC's "revert on blur/click-away" discretion note.
**Confidence:** HIGH — this is a straightforward scalar State var pattern with no Reflex-
specific gotchas.

### Pattern 4: Series-Selector-Driven Single Chart (D-03/D-04, VIS-01)
**What:** One `rx.plotly` chart whose figure is a computed `@rx.var` (or plain `@rx.event`-
free property) rebuilt from `self.rows` + `self.selected_series`, driven by an `rx.select`.
**When to use:** The historical chart block (VIS-01).
**Example:**
```python
# Source: reflex.dev/docs/library/graphing/other-charts/plotly/
import plotly.express as px
import plotly.graph_objects as go

_SERIES_OPTIONS = [(label, attr) for label, attr in _COLUMNS if attr != "date"]

class DashboardState(rx.State):
    rows: list[PriceRow] = []
    selected_series: str = "hdan"  # default: HDAN, first headline series per UI-SPEC

    def select_series(self, attr: str):
        self.selected_series = attr

    @rx.var
    def historical_chart_figure(self) -> go.Figure:
        dates = [r.date for r in self.rows]
        values = [getattr(r, self.selected_series) for r in self.rows]
        fig = px.line(x=dates, y=values, markers=True)
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title=dict(_SERIES_OPTIONS).get(self.selected_series, self.selected_series),
            showlegend=False,
        )
        fig.update_traces(line_color="#697177")  # UI-SPEC: neutral gray, no accent, single series
        return fig


def historical_chart() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Series", weight="bold"),
            rx.select(
                [label for label, _ in _SERIES_OPTIONS],
                value=<label for current selected_series>,  # map attr<->label both ways
                on_change=lambda label: DashboardState.select_series(<label_to_attr(label)>),
            ),
        ),
        rx.plotly(data=DashboardState.historical_chart_figure, width="100%"),
    )
```
**Important:** because `historical_chart_figure` is a computed `@rx.var`, it recalculates
automatically whenever `self.rows` or `self.selected_series` changes — no re-query of SQLite
happens on selector change (`self.rows` is already loaded in memory from `load_rows()`), which
directly satisfies the "without re-querying the DB on every selector change" requirement in
the downstream consumer brief. `rx.select` takes a list of string options; since `_COLUMNS`
pairs are `(label, attr)`, the planner should build a label->attr and attr->label lookup
(plain Python dicts at module scope, not State) to translate between the dropdown's
human-readable value and the internal column attr name.
**Confidence:** HIGH for the `@rx.var` + `rx.plotly` recompute-on-state-change mechanism
(explicitly documented: "If the figure is set as a state var, it can be updated during run
time" `[CITED: reflex.dev/docs/library/graphing/other-charts/plotly/]`). MEDIUM for the exact
`rx.select` value-binding signature — verify current prop name (`value` vs `default_value`)
against installed Reflex version's docstring/`help(rx.select.root)` before writing the task,
since Reflex's Radix-based `rx.select` has a slightly different API from the legacy `rx.select`
single-function convenience wrapper across versions.

### Anti-Patterns to Avoid
- **Storing unsaved draft-row data as fields bolted onto `PriceRow` instances directly:**
  `PriceRow` is the ORM model; conflating "not yet in the DB" with "an ORM object not yet
  added to a session" is fine (SQLModel instances can exist unattached to a session), but do
  NOT add ad-hoc non-schema attributes to it for edit-tracking (e.g. `row._is_editing = True`)
  — Reflex's Var diffing/serialization for `list[PriceRow]` State vars expects the model's
  declared fields only; extra dynamic attributes are a source of subtle serialization bugs.
- **Re-querying the whole table on every keystroke:** `on_change` fires per keystroke (subject
  to Reflex's built-in debouncing per the Input docs); only `commit_edit` (on blur/Enter)
  should touch `rx.session()`. Don't call `self.load_rows()` inside `update_draft`.
- **Validating only client-side (JS-only) and skipping server-side re-validation:** Reflex
  event handlers run in the Python backend process regardless of where the trigger originated
  in the browser — there is no meaningful "client-side only" validation layer to lean on
  in this architecture. All D-01/D-02 checks belong in the `commit_edit`/`add_row` event
  handler in `state.py`, not scattered into component render logic.
- **One overlaid multi-line chart or 16 mini-charts:** explicitly rejected by D-04 — do not
  let "just show everything" scope-creep back in during implementation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounced text input while typing | Custom `setTimeout`/JS debounce logic | Reflex's built-in `rx.input` debouncing (documented behavior) | Reflex already debounces `on_change` for you so backend State updates don't lag the user's typing; reimplementing this in a custom component is unnecessary complexity for zero benefit |
| Date parsing/validation | Hand-rolled regex date validator | Python stdlib `datetime.strptime`/`date.fromisoformat` wrapped in a try/except inside the event handler | Stdlib date parsing already handles the edge cases (leap years, invalid day-of-month) that a regex would get wrong; D-02 only needs "valid date" + "no duplicate month", both trivial with stdlib |
| Chart line rendering | Hand-rolled SVG/canvas chart | `plotly.express.line` + `rx.plotly` (already the project's locked charting stack per STACK.md) | Re-deriving hover tooltips, axis scaling, and responsive sizing from scratch when Plotly already provides all of it for free is pure waste |

**Key insight:** This phase's complexity is entirely in State design (identity/keying of
in-progress edits, drafts, and pending deletes), not in the widgets themselves — every
individual Reflex component used here (`rx.input`, `rx.select`, `rx.plotly`, `rx.icon_button`)
is a thin, well-documented wrapper. Resist the urge to build custom debouncing, custom date
parsing, or a custom charting solution; none of that is where this phase's real risk lives.

## Common Pitfalls

### Pitfall 1: Losing edits on page refresh because they were never actually committed to SQLite
**What goes wrong:** A cell shows the edited value locally (State updated) but the developer
forgets to call `session.commit()`, or commits without reassigning/reloading `self.rows`
afterward, so a refresh shows stale data even though the UI briefly looked correct.
**Why it happens:** It's easy to update `self.draft_value` and clear `self.editing_key`
without actually writing through to the DB — the UI looks "done" because State re-renders,
masking the missing persistence step.
**How to avoid:** Every commit path (`commit_edit`, `add_row` promotion, `request_delete`)
must both `session.commit()` AND call `self.load_rows()` afterward, per PITFALLS.md's
established "State reflects DB" pattern from Phase 1.
**Warning signs:** An edit "sticks" during the session but disappears after a manual browser
refresh — the classic symptom this project's own PITFALLS.md already names for Phase 1/4.

### Pitfall 2: `rx.foreach` closures capturing the wrong row (stale closure / index reuse)
**What goes wrong:** Using a plain Python `for` loop or lambda that captures a mutable loop
variable when building `rx.foreach` children can cause every row's click handler to reference
the same (last) row, because `rx.foreach`'s callback receives a `Var` proxy per item, not a
concrete Python object at loop-definition time.
**Why it happens:** Developers coming from other frameworks assume `lambda: State.fn(row.date)`
captures `row` by value like a normal Python closure; inside `rx.foreach`, `row` is itself a
Var, and the lambda is fine as long as it's defined *inside* the `rx.foreach` callback (which
Reflex handles correctly) — the bug appears if code tries to precompute a Python list of
`row.date` values outside the foreach callback and index into it by position instead.
**How to avoid:** Always build the per-row component (including its `on_click=lambda: ...`)
inside the function passed to `rx.foreach(DashboardState.rows, render_row)` — never try to
zip/enumerate `self.rows` in plain Python at component-definition time, since `self.rows` is
also just a Var reference outside of event handlers.
**Warning signs:** Every row's delete/edit button appears to operate on the same (usually
last) row regardless of which row was clicked.

### Pitfall 3: Add-row identity collision with multiple unsaved drafts (D-06 edge case)
**What goes wrong:** If the "Add row" button is clickable multiple times before the first
draft gets a valid date, `draft_rows` could contain 2+ rows all with `date == ""`, and the
`commit_edit` lookup-by-date logic in Pattern 2 above cannot disambiguate which draft a given
cell edit belongs to.
**Why it happens:** D-06 doesn't specify what happens if "Add row" is clicked twice in a row;
naive implementation treats each draft symmetrically and breaks on the second one.
**How to avoid:** Disable (or make idempotent — clicking again just re-focuses the existing
undated draft's date cell rather than adding a second one) the "Add row" button while any
`draft_rows` entry still has an empty/unvalidated date. Documented as an Open Question below
since it's not explicitly decided in CONTEXT.md.
**Warning signs:** Typing into the second blank row's cells silently edits the first blank
row's data, or raises a `next()` StopIteration in the lookup logic from Pattern 2.

### Pitfall 4: Validating negative-but-numeric FX/price values inconsistently with D-01
**What goes wrong:** D-01 says reject negative values uniformly across ALL 16 columns — it
would be tempting (and was explicitly rejected during discuss-phase) to special-case FX rate
with a plausibility ceiling or Diesel with a different threshold. A too-clever validator that
adds per-column business rules violates D-01's explicit "no tighter series-specific checks"
instruction.
**Why it happens:** Domain intuition ("FX rate should never exceed X") tempts over-engineering.
**How to avoid:** Implement exactly one shared numeric validator function used for all 16
series columns: `reject if not parseable as float; reject if < 0; accept blank/None`. Do not
branch on column name inside the numeric validator.
**Warning signs:** A validator function has an `if column == "fx_rate":` branch — that's a
direct D-01 violation.

## Code Examples

### Numeric and date validators (D-01/D-02)
```python
# Source: Python stdlib (datetime), applying D-01/D-02 rules from CONTEXT.md verbatim
from datetime import date

def validate_numeric(raw: str) -> tuple[bool, float | str]:
    """D-01: reject non-numeric, reject negative, allow blank/null."""
    if raw.strip() == "":
        return True, None
    try:
        value = float(raw)
    except ValueError:
        return False, "Enter a positive number or leave blank."  # UI-SPEC copy
    if value < 0:
        return False, "Enter a positive number or leave blank."  # UI-SPEC copy
    return True, value


def validate_date(raw: str, existing_dates: list[str], own_original_date: str | None) -> tuple[bool, str]:
    """D-02: must be a valid date AND must not duplicate an existing row's calendar month."""
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        return False, "Enter a valid date."  # UI-SPEC copy
    month_key = parsed.strftime("%Y-%m")
    other_months = {
        d[:7] for d in existing_dates if d != own_original_date
    }
    if month_key in other_months:
        return False, "This month already has a row — edit it instead."  # UI-SPEC copy
    return True, parsed.isoformat()
```
**Confidence:** HIGH — pure Python/stdlib, no framework-specific risk. Copy strings pulled
verbatim from `04-UI-SPEC.md` Copywriting Contract.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| N/A | N/A | — | This phase uses no deprecated APIs; Reflex 0.9.8.post1 is current per STACK.md and its `rx.input`/`rx.select`/`rx.plotly`/`rx.cond`/`rx.foreach` surface used here is stable core API, not a recently-changed area |

**Deprecated/outdated:** None identified for this phase's scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rx.select` accepts a plain list of string labels with `value=`/`on_change=` binding in the currently-installed Reflex version, and this is the correct component (vs. a deprecated `rx.select.root`/legacy split) | Pattern 4 | Low — if the prop name differs (e.g. requires `rx.select.root(rx.select.trigger(...), rx.select.content(...))` composition instead of the flat convenience form), the planner needs one extra task step to check `help(rx.select)` in the installed environment before writing the exact component tree; does not change the overall state design |
| A2 | `dict_var[key]` / `dict_var.contains(key)` Var-indexing syntax works as shown for `error_by_key` inside `rx.cond` | Pattern 1 | Medium — if this Var indexing syntax is wrong for the installed Reflex version, the error-display sub-pattern needs adjustment (e.g. using a computed `@rx.var` method instead of raw dict indexing in the component tree), but the surrounding edit/commit state machine is unaffected |
| A3 | A single scalar `pending_delete: str` (not a dict) is sufficient because only one row's delete-confirm state needs to be visible at a time | Pattern 3 | Low — this is a design choice, not a factual claim; if the planner wants simultaneous multi-row pending-delete support (not requested by D-07), this would need to become a `set[str]`, but nothing in CONTEXT.md asks for that |
| A4 | The recommended resolution to the "multiple unsaved draft rows" edge case (disable/reuse "Add row" while one draft is unvalidated) is the right interpretation of D-06, since D-06 itself doesn't address this case | Pattern 2 / Pitfall 3 | Medium — this is genuinely undecided in CONTEXT.md; flagged explicitly in Open Questions below for planner/user confirmation rather than silently assumed as locked |

## Open Questions

1. **What happens if "Add row" is clicked twice before the first draft row gets a valid date?**
   - What we know: D-06 specifies the single-draft happy path (blank row appended, cells
     click-to-edit, not persisted until date is valid/non-duplicate).
   - What's unclear: CONTEXT.md's discussion never raised the double-click case explicitly.
   - Recommendation: Disable the "Add row" button (or make repeated clicks a no-op / refocus
     the existing draft's date cell) while any draft row lacks a valid date. This is the
     simplest interpretation consistent with D-06's "no separate add-row form UI" spirit and
     avoids needing a synthetic client-side row-ID scheme. Flag for the planner to confirm
     this is acceptable, or route back through discuss-phase if a stricter answer is wanted.

2. **Exact `rx.select` value-binding API for the currently-installed Reflex version.**
   - What we know: `rx.select` is a documented, stable Reflex component; STACK.md pins
     Reflex 0.9.8.post1.
   - What's unclear: this research could not execute `help(rx.select)` against a live install
     in this sandboxed research pass (no reflex package was found/importable in this
     environment — see Environment Availability below) to confirm the exact prop signature
     matches the WebFetch-sourced docs verbatim for this pinned version.
   - Recommendation: the first execution task touching `historical_chart()` should do a quick
     `python -c "import reflex as rx; help(rx.select)"` spike (or check the installed venv's
     Reflex docs/source) before finalizing the component tree, and adjust Pattern 4's example
     if the signature differs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| reflex (Python package) | All patterns in this phase | ✗ (not importable in this research sandbox) | STACK.md pins 0.9.8.post1 | Verify actual installed version in the execution environment (`pip show reflex`) before implementation; component API details in this research (especially `rx.select`, Pattern 4) should be spot-checked against the real installed version at execution time |
| plotly (Python package) | Pattern 4 (historical chart) | ✗ (not importable in this research sandbox) | STACK.md pins 6.9.0 | Same as above — verify at execution time |

**Missing dependencies with no fallback:** None — this is a research-environment limitation
(the research sandbox doesn't have the project's venv active), not a missing-fallback
situation for the actual execution environment, which per STATE.md has completed Phases 1-3
of a working Reflex app (i.e., Reflex/Plotly are demonstrably installed and working in the
real dev environment; `app/app/app.py` already imports and uses `reflex` successfully).

**Missing dependencies with fallback:** None applicable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (per STACK.md, already a project dev dependency) |
| Config file | none found in repo scan — check for `pytest.ini`/`pyproject.toml [tool.pytest]` at execution time; if absent, Wave 0 must add minimal config |
| Quick run command | `pytest app/tests/test_state.py -x` (path assumed; confirm actual test dir at execution time — no `tests/` directory was found during this research pass) |
| Full suite command | `pytest app/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Add row persists to SQLite once date is valid | unit (State method, not full Reflex UI) | `pytest app/tests/test_state.py::test_add_row_deferred_persist -x` | ❌ Wave 0 |
| DATA-02 | Edit existing row inline updates SQLite | unit | `pytest app/tests/test_state.py::test_commit_edit_updates_db -x` | ❌ Wave 0 |
| DATA-03 | Delete with confirm step removes row | unit | `pytest app/tests/test_state.py::test_delete_confirm_flow -x` | ❌ Wave 0 |
| DATA-04 | Numeric validation rejects non-numeric/negative | unit | `pytest app/tests/test_validators.py::test_validate_numeric -x` | ❌ Wave 0 |
| DATA-05 | Writes survive reload (reload_rows reflects DB) | unit/integration | `pytest app/tests/test_state.py::test_load_rows_reflects_db -x` | ❌ Wave 0 |
| VIS-01 | Chart figure built for selected series from rows | unit | `pytest app/tests/test_state.py::test_historical_chart_figure -x` | ❌ Wave 0 |

**Testing approach note:** Reflex `State` event handler methods (`commit_edit`, `add_row`,
`request_delete`, `select_series`) are plain Python methods on a class and can be
instantiated/called directly in pytest without spinning up the full Reflex app/browser —
this is the pattern STACK.md already recommended ("keep forecasting/export as plain Python
functions callable from tests, not buried in `rx.State` methods... reflex apps are awkward to
unit-test directly"). For State methods specifically (which by nature live on `rx.State`),
tests should instantiate `DashboardState()` directly and call methods synchronously, using an
in-memory or temp-file SQLite DB fixture (override `rx.session()`'s DB URL for tests) rather
than attempting full end-to-end browser testing, which is out of scope for this phase's test
depth.

### Wave 0 Gaps
- [ ] `app/tests/` directory — does not exist yet in this repo; needs creation
- [ ] `app/tests/conftest.py` — shared fixture for a temp SQLite DB + seeded `PriceRow` rows,
      isolated from the real dev DB
- [ ] `app/tests/test_validators.py` — covers DATA-04 (D-01/D-02 validator functions)
- [ ] `app/tests/test_state.py` — covers DATA-01/02/03/05, VIS-01
- [ ] pytest config: confirm/add `pytest.ini` or `[tool.pytest.ini_options]` in
      `pyproject.toml` if not already present

## Security Domain

> This is a single-user, local, non-authenticated desktop-style tool per PROJECT.md scope
> (explicit Out of Scope: "Multi-user accounts / authentication"). ASVS categories below are
> scoped accordingly — most authentication/session-management categories do not apply.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Out of scope per PROJECT.md — single local user, no auth layer |
| V3 Session Management | no | Reflex's per-WebSocket session state is not a security boundary in this single-user local app |
| V4 Access Control | no | No multi-user access control surface exists |
| V5 Input Validation | yes | D-01/D-02 validators (numeric range + date parsing) — implemented via Python stdlib `float()`/`datetime.fromisoformat()` inside server-side event handlers, never trusting client-supplied values without server-side re-check |
| V6 Cryptography | no | No secrets, tokens, or encrypted data involved in this phase's scope |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via row edit values | Tampering | Not applicable in practice — all writes go through SQLModel/SQLAlchemy's ORM (`session.add`/`setattr` on typed model fields), which parameterizes queries automatically; never construct raw SQL strings from user input in this phase |
| Malformed/oversized input crashing the numeric parser | Denial of Service (minor, single-user) | `validate_numeric`/`validate_date` wrap `float()`/`date.fromisoformat()` in `try/except`, returning a validation error rather than propagating an unhandled exception that could crash the event handler / WebSocket connection |

## Sources

### Primary (HIGH confidence)
- https://reflex.dev/docs/library/forms/input/ — `on_blur`, `on_change`, `on_key_down`,
  `value`/`default_value` props for `rx.input` — fetched and cross-checked this session
- https://reflex.dev/docs/library/graphing/other-charts/plotly/ — `rx.plotly` + computed
  `@rx.var` figure pattern ("If the figure is set as a state var, it can be updated during
  run time") — fetched and cross-checked this session
- `app/app/models.py`, `app/app/state.py`, `app/app/app.py` (this repo) — existing schema,
  read path, and read-only table this phase extends — read directly this session

### Secondary (MEDIUM confidence)
- WebSearch results on `rx.cond` conditional rendering pattern for editable table cells —
  corroborated by the same conceptual pattern appearing across multiple Reflex
  docs/tutorial pages surfaced in search results

### Tertiary (LOW confidence)
- Exact `rx.select` value-binding signature for the specific pinned Reflex version
  (0.9.8.post1) — not independently verified against a live install in this research
  session (no Context7 MCP tool available; no importable `reflex` package in this sandbox);
  flagged in Open Questions and Assumptions Log for confirmation at execution time

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, both already pinned/verified in prior STACK.md research
- Architecture (state design patterns): MEDIUM-HIGH — core mechanics (rx.cond, rx.foreach,
  event handlers, rx.session write-through) are solidly documented; a few specific Var-syntax
  details (dict indexing, rx.select exact API) could not be verified against a live install
  in this session
- Pitfalls: HIGH — directly derived from this project's own established PITFALLS.md pattern
  plus standard Reflex `rx.foreach` closure gotchas

**Research date:** 2026-08-22
**Valid until:** 2026-09-21 (30 days — Reflex is an actively developed framework; re-verify
`rx.select`/`rx.input` prop signatures if this research is used after a Reflex version bump)
