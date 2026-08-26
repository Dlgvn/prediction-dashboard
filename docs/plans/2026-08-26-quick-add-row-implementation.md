# Quick Add-Row Form Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the click-to-edit draft-row flow for adding a new month's actuals with a single quick-add form (17 fields, Date required) above the Data Entry table, plus sticky header/Date column and restyled CSV import states.

**Architecture:** New `quick_add_values`/`quick_add_error` state on `DashboardState`, validated with the existing `validate_date`/`validate_numeric` functions and inserted in one shot on submit — replacing `draft_rows` and its per-cell commit machinery entirely. Editing of already-saved rows (click-to-edit cells) is untouched.

**Tech Stack:** Reflex (Python), SQLModel/`rx.Model`, pytest. No new dependencies.

**Design doc:** `docs/plans/2026-08-26-quick-add-row-design.md`

---

## Task 1: Add `quick_add_values` / `quick_add_error` state and `update_quick_add_field`

**Files:**
- Modify: `app/app/state.py`
- Test: `app/tests/test_state.py`

**Step 1: Write the failing tests**

Add near the existing draft-row tests (around line 355 in `app/tests/test_state.py`):

```python
def test_update_quick_add_field_sets_one_key(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    state.update_quick_add_field("hdan", "7")

    assert state.quick_add_values["hdan"] == "7"
    assert state.quick_add_values.get("date", "") == ""


def test_update_quick_add_field_does_not_touch_other_keys(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()

    state.update_quick_add_field("hdan", "7")
    state.update_quick_add_field("ppan", "3")

    assert state.quick_add_values["hdan"] == "7"
    assert state.quick_add_values["ppan"] == "3"
```

**Step 2: Run tests to verify they fail**

Run: `cd app && .venv/bin/python -m pytest tests/test_state.py -k quick_add_field -v`
Expected: FAIL with `AttributeError: 'DashboardState' object has no attribute 'update_quick_add_field'`

**Step 3: Write minimal implementation**

In `app/app/state.py`, find the state field block that currently declares `draft_rows` (around line 140) and the `pending_delete` field just below it (around line 155). Leave `draft_rows` in place for now (Task 3 removes it) and add the new fields right after `pending_delete: str = ""`:

```python
    quick_add_values: dict[str, str] = {}
    quick_add_error: str = ""
```

Then add the handler near `update_draft` (around line 983):

```python
    def update_quick_add_field(self, attr: str, value: str) -> None:
        # Whole-dict reassignment, not in-place mutation, so Reflex reliably
        # detects the change (same pattern as draft_rows elsewhere in this
        # file).
        self.quick_add_values = {**self.quick_add_values, attr: value}
```

**Step 4: Run tests to verify they pass**

Run: `cd app && .venv/bin/python -m pytest tests/test_state.py -k quick_add_field -v`
Expected: PASS (2 passed)

**Step 5: Commit**

```bash
git add app/app/state.py app/tests/test_state.py
git commit -m "feat(data-entry): add quick_add_values state and field updater"
```

---

## Task 2: Add `submit_quick_add` handler

**Files:**
- Modify: `app/app/state.py`
- Test: `app/tests/test_state.py`

**Step 1: Write the failing tests**

Add after the tests from Task 1:

```python
def test_submit_quick_add_inserts_row_with_all_fields(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    state.update_quick_add_field("date", "2026-06-01")
    state.update_quick_add_field("hdan", "7")
    state.update_quick_add_field("ppan", "3.5")

    state.submit_quick_add()

    db_row = _get_db_row(session, "2026-06-01")
    assert db_row is not None
    assert db_row.hdan == 7.0
    assert db_row.ppan == 3.5
    assert db_row.brent is None
    assert any(r.date == "2026-06-01" for r in state.rows)


def test_submit_quick_add_clears_form_and_error_on_success(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    state.update_quick_add_field("date", "2026-06-01")
    state.update_quick_add_field("hdan", "7")

    state.submit_quick_add()

    assert state.quick_add_values == {}
    assert state.quick_add_error == ""


def test_submit_quick_add_missing_date_rejected(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.update_quick_add_field("hdan", "7")

    state.submit_quick_add()

    assert _db_row_count(session) == before
    assert state.quick_add_error != ""
    # Nothing the user typed is lost on failure.
    assert state.quick_add_values["hdan"] == "7"


def test_submit_quick_add_invalid_date_rejected(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.update_quick_add_field("date", "nope")

    state.submit_quick_add()

    assert _db_row_count(session) == before
    assert state.quick_add_error == validators.DATE_INVALID_ERROR


def test_submit_quick_add_duplicate_month_rejected(session, monkeypatch):
    session.add(PriceRow(date="2026-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.update_quick_add_field("date", "2026-01-20")

    state.submit_quick_add()

    assert _db_row_count(session) == before
    assert state.quick_add_error == validators.DATE_DUPLICATE_ERROR


def test_submit_quick_add_invalid_numeric_field_rejected_and_names_field(
    session, monkeypatch
):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    before = _db_row_count(session)
    state.update_quick_add_field("date", "2026-06-01")
    state.update_quick_add_field("ammonia", "not-a-number")

    state.submit_quick_add()

    assert _db_row_count(session) == before
    assert "Ammonia" in state.quick_add_error
    # Values persist so the user doesn't have to retype everything.
    assert state.quick_add_values["date"] == "2026-06-01"
    assert state.quick_add_values["ammonia"] == "not-a-number"


def test_submit_quick_add_blank_series_fields_stay_null(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.load_rows()
    state.update_quick_add_field("date", "2026-06-01")

    state.submit_quick_add()

    db_row = _get_db_row(session, "2026-06-01")
    assert db_row is not None
    for attr in SERIES_ATTRS:
        assert getattr(db_row, attr) is None
```

**Step 2: Run tests to verify they fail**

Run: `cd app && .venv/bin/python -m pytest tests/test_state.py -k submit_quick_add -v`
Expected: FAIL with `AttributeError: 'DashboardState' object has no attribute 'submit_quick_add'`

**Step 3: Write minimal implementation**

Add to `app/app/state.py`, right after `update_quick_add_field`:

```python
    def submit_quick_add(self) -> None:
        raw_date = self.quick_add_values.get("date", "")
        ok, iso_date, error = validate_date(
            raw_date, [r.date for r in self.rows], own_original_date=None
        )
        if not ok:
            self.quick_add_error = error
            return

        parsed_values: dict[str, float | None] = {}
        for attr in SERIES_ATTRS:
            raw = self.quick_add_values.get(attr, "")
            ok, value, error = validate_numeric(raw)
            if not ok:
                self.quick_add_error = f"{SERIES_LABELS[attr]}: {error}"
                return
            parsed_values[attr] = value

        with rx.session() as session:
            session.add(PriceRow(date=iso_date, **parsed_values))
            session.commit()

        self.quick_add_values = {}
        self.quick_add_error = ""
        self.load_rows()
```

Note: `validate_date` is only called once and is not per-field, so the
"which field failed" naming in the error only applies to numeric fields —
matches the design's requirement to name the first offending field.

**Step 4: Run tests to verify they pass**

Run: `cd app && .venv/bin/python -m pytest tests/test_state.py -k submit_quick_add -v`
Expected: PASS (7 passed)

**Step 5: Run the full test suite to check nothing else broke**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: all existing tests still pass (this task is additive so far — nothing removed yet)

**Step 6: Commit**

```bash
git add app/app/state.py app/tests/test_state.py
git commit -m "feat(data-entry): add submit_quick_add handler with validation"
```

---

## Task 3: Remove `draft_rows` and old draft-cell machinery

**Files:**
- Modify: `app/app/state.py`
- Modify: `app/tests/test_state.py`

**Step 1: Update/replace the old draft-row tests**

The quick-add tests in Task 2 already cover the same scenarios the old draft tests covered. Delete these now-obsolete tests from `app/tests/test_state.py`:

- `test_add_row_creates_unsaved_draft` (~line 355)
- `test_add_row_disabled_while_draft_pending` (~line 368)
- `test_draft_numeric_edit_does_not_touch_db` (~line 380)
- `test_add_row_deferred_persist` (~line 395)
- `test_draft_invalid_date_stays_draft` (~line 417)
- `test_draft_duplicate_month_rejected` (~line 433, and any of its continuation lines using `add_row`/draft cells — check the lines immediately following 433 for the rest of that test body before deleting)

Update `test_toggle_show_all_history_cancels_edit_and_pending_delete` (~line 1552): remove the `state.draft_rows = [PriceRow(date="")]` setup line and the `assert len(state.draft_rows) == 1` assertion, replacing the latter with an assertion that the quick-add form survives the toggle untouched (same rationale as the old comment — an in-progress unsaved entry must survive a window-size change):

```python
def test_toggle_show_all_history_cancels_edit_and_pending_delete(session, monkeypatch):
    monkeypatch.setattr("reflex.session", lambda: session)
    state = DashboardState()
    state.rows = _rows_ascending(20)
    state.editing_key = "2024-01-01:hdan"
    state.draft_value = "9"
    state.edit_error = "x"
    state.pending_delete = "2024-01-01"
    state.update_quick_add_field("hdan", "9")

    state.toggle_show_all_history(True)

    assert state.editing_key == ""
    assert state.draft_value == ""
    assert state.edit_error == ""
    assert state.pending_delete == ""
    assert state.quick_add_values["hdan"] == "9"
```

Update `test_handle_csv_upload_does_not_touch_edit_error_or_editing_key` (~line 1996) to use the quick-add flow instead of `add_row`/draft cells to produce a pending duplicate-date error, and to assert the quick-add state is untouched by CSV upload too:

```python
def test_handle_csv_upload_does_not_touch_edit_error_or_editing_key(session, monkeypatch):
    """D-03 audit proof: CSV import must not interact with the edit machine
    or the quick-add form, even while a genuine validation error is pending.
    """
    session.add(PriceRow(date="2025-01-01", hdan=1.0))
    session.commit()
    monkeypatch.setattr("reflex.session", lambda: session)

    state = DashboardState()
    state.load_rows()
    state.update_quick_add_field("date", "2025-01-20")
    state.submit_quick_add()

    assert state.quick_add_error == validators.DATE_DUPLICATE_ERROR
    editing_key_before = state.editing_key
    draft_value_before = state.draft_value
    quick_add_values_before = dict(state.quick_add_values)
    quick_add_error_before = state.quick_add_error

    csv_bytes = _import_csv([_full_import_row("2026-01-01")])
    asyncio.run(state.handle_csv_upload([_FakeUpload(csv_bytes)]))

    assert state.editing_key == editing_key_before
    assert state.draft_value == draft_value_before
    assert state.quick_add_values == quick_add_values_before
    assert state.quick_add_error == quick_add_error_before
```

**Step 2: Run the edited tests to verify they still make sense as failing (pre-implementation) or passing**

Run: `cd app && .venv/bin/python -m pytest tests/test_state.py -k "toggle_show_all_history_cancels or handle_csv_upload_does_not_touch" -v`
Expected: these should already PASS at this point since `quick_add_values`/`update_quick_add_field`/`submit_quick_add` exist from Tasks 1-2, and `draft_rows` still exists too (not yet removed) — this step is a sanity check before deleting code.

**Step 3: Remove the old draft-row state and methods from `app/app/state.py`**

Remove:
- The `draft_rows: list[PriceRow] = []` field declaration (~line 140).
- The `can_add_row` computed var (~line 314) — no longer needed; the quick-add form has no "one draft at a time" constraint. Check the file for `can_add_row` usages first (`grep -n can_add_row app/app/state.py app/app/app.py`) and confirm it is only used by the soon-to-be-removed `add_row_button()` in `app.py` (removed in Task 5) before deleting.
- The `_commit_draft_cell` method (~lines 1051-1094).
- The `if row_date == "": self._commit_draft_cell(column); return` branch inside `commit_edit` (~lines 1016-1018) — `commit_edit` now always operates on an existing saved row, since there is no more draft-cell editing key format (`":attr"`).
- The `add_row` method (~lines 1102-1107).

Update the state-transition table comment above `start_edit` (~lines 935-965) to drop the `draft_rows` column and the two draft-row-specific table rows ("Draft-row date entry" and "Draft-row non-date entry"), since those triggers no longer exist. Leave the rest of the table (normal cell edit, Escape, blur success/failure, window toggle, delete-arm) as-is — those all still apply to editing already-saved rows.

**Step 4: Run the full test suite**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: all pass. If anything still references `draft_rows`/`add_row`/`can_add_row`/`_commit_draft_cell` in a test not yet updated, it will fail here with a clear `AttributeError` — fix any stragglers found by `grep -rn "draft_rows\|can_add_row\|_commit_draft_cell" app/tests/` before moving on (Task 4 handles the two known ones in `test_app_components.py`).

**Step 5: Commit**

```bash
git add app/app/state.py app/tests/test_state.py
git commit -m "refactor(data-entry): remove draft_rows in favor of quick-add form"
```

---

## Task 4: Update `test_app_components.py` for the removed `add_row_button`/`draft_rows` UI

**Files:**
- Modify: `app/tests/test_app_components.py`

**Step 1: Update the two tests that reference removed symbols**

`test_draft_rows_foreach_unchanged` (~line 355) — delete this test; `data_table()` will no longer have a `draft_rows` foreach (removed in Task 5). Replace it with:

```python
def test_data_table_has_no_draft_rows_foreach():
    source = inspect.getsource(app_module.data_table)
    assert "draft_rows" not in source
```

`test_data_entry_section_places_import_control_after_add_row` (~line 529) — rename and update to reference the new `quick_add_form()` instead of `add_row_button()`:

```python
def test_data_entry_section_places_import_control_after_quick_add_form():
    source = inspect.getsource(app_module.data_entry_section)
    assert source.index("quick_add_form()") < source.index("csv_import_control()")
```

**Step 2: Run to verify these fail (since `quick_add_form`/the updated `data_table` don't exist yet)**

Run: `cd app && .venv/bin/python -m pytest tests/test_app_components.py -k "draft_rows_foreach or places_import_control" -v`
Expected: FAIL (`quick_add_form()` not found in source / `draft_rows` still present in `data_table` source) — confirms these are real, currently-failing specs for Task 5.

**Step 3: Commit the test changes**

```bash
git add app/tests/test_app_components.py
git commit -m "test(data-entry): update component tests for quick-add form"
```

(This intentionally leaves the suite red until Task 5 lands the UI — the next task's Step 4 will turn it green.)

---

## Task 5: Build `quick_add_form()` and wire it into `data_entry_section()`

**Files:**
- Modify: `app/app/app.py`

**Step 1: Remove the draft-row foreach from `data_table()`**

In `app/app/app.py`, `data_table()` (~lines 121-145) currently has two `rx.foreach` calls in its `rx.table.body(...)` — one over `DashboardState.visible_rows` and one over `DashboardState.draft_rows`. Delete the second one entirely:

```python
def data_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                *[rx.table.column_header_cell(label) for label, _ in _COLUMNS],
                rx.table.column_header_cell(""),
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.visible_rows,
                lambda row: rx.table.row(
                    *[_editable_cell(row, attr) for _, attr in _COLUMNS],
                    _delete_cell(row),
                ),
            ),
        ),
    )
```

**Step 2: Add sticky header and sticky Date column**

Still in `data_table()`, add sticky positioning. The header row's cells need `position="sticky"` + `top="0"`; the Date column (first column in each body row) needs `position="sticky"` + `left="0"` plus a background so scrolled-under content doesn't show through. Reflex's `rx.table.column_header_cell`/`rx.table.cell` accept style props directly:

```python
def data_table() -> rx.Component:
    header_cell_style = {
        "position": "sticky",
        "top": "0",
        "background": DashboardState.surface,
        "z_index": "1",
    }
    date_cell_style = {
        "position": "sticky",
        "left": "0",
        "background": DashboardState.surface,
        "z_index": "1",
    }
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                *[
                    rx.table.column_header_cell(label, **header_cell_style)
                    for label, _ in _COLUMNS
                ],
                rx.table.column_header_cell("", **header_cell_style),
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.visible_rows,
                lambda row: rx.table.row(
                    _editable_cell(row, "date", cell_style=date_cell_style),
                    *[_editable_cell(row, attr) for _, attr in _COLUMNS[1:]],
                    _delete_cell(row),
                ),
            ),
        ),
    )
```

This requires `_editable_cell` to accept an optional `cell_style` kwarg. Update its signature and its final `return rx.table.cell(...)` (~lines 35-94):

```python
def _editable_cell(row: PriceRow, attr: str, cell_style: dict | None = None) -> rx.Component:
    ...  # body unchanged down to the final return
    return rx.table.cell(
        rx.cond(DashboardState.editing_key == key, editor, display),
        **(cell_style or {}),
    )
```

**Step 3: Write `quick_add_form()`**

Add this new function in `app/app/app.py`, placed just above `data_entry_section()`:

```python
def _quick_add_field(attr: str, label: str, required: bool = False) -> rx.Component:
    return rx.vstack(
        rx.text(
            label + (" *" if required else ""),
            size=RADIX_SIZE_LABEL,
            font_weight=FONT_WEIGHT_SEMIBOLD if required else FONT_WEIGHT_REGULAR,
            color_scheme="gray",
        ),
        rx.input(
            value=DashboardState.quick_add_values[attr].to(str),
            on_change=lambda value: DashboardState.update_quick_add_field(attr, value),
            type="date" if attr == "date" else "text",
            size="2",
        ),
        spacing="1",
        align="start",
    )


def quick_add_form() -> rx.Component:
    """Compact form for entering one full month's actuals at once (replaces
    the old add-row-then-click-each-cell draft flow).
    """
    return rx.box(
        rx.cond(
            DashboardState.quick_add_error != "",
            rx.hstack(
                rx.icon("circle-alert", size=16, color=DashboardState.destructive_color),
                rx.text(
                    DashboardState.quick_add_error,
                    size=RADIX_SIZE_BODY,
                    color=DashboardState.destructive_color,
                ),
                spacing="2",
                align="center",
                margin_bottom=SPACE_SM,
            ),
            rx.fragment(),
        ),
        rx.flex(
            _quick_add_field("date", "Date", required=True),
            *[
                _quick_add_field(attr, SERIES_LABELS[attr])
                for attr in SERIES_ATTRS
            ],
            wrap="wrap",
            spacing="3",
            align="end",
        ),
        rx.button(
            "Save row",
            on_click=DashboardState.submit_quick_add,
            size="2",
            color_scheme="blue",
            margin_top=SPACE_SM,
        ),
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
        width="100%",
        aria_label="Add a month's actuals",
    )
```

Add `SPACE_SM` and `FONT_WEIGHT_REGULAR` to the existing `from app.theme import (...)` block at the top of `app.py` if not already present (check first — `FONT_WEIGHT_REGULAR` is already imported per the current import list; only `SPACE_SM` needs adding).

**Step 4: Replace `add_row_button()` with `quick_add_form()` in `data_entry_section()`**

`data_entry_section()` (~lines 712-748) currently renders `history_toggle()`, the table, then an `rx.hstack(add_row_button(), rx.text("Import CSV", ...))`. Replace that hstack's `add_row_button()` call with the form, placed as its own row above the "Import CSV" label line — matching the design's "always visible above the table" placement, and keeping `quick_add_form()` before `csv_import_control()` in source order (required by the updated test from Task 4):

```python
def data_entry_section() -> rx.Component:
    """Data-entry table under its own heading, at the bottom of the page (D-02/D-03)."""
    return rx.vstack(
        rx.heading("Data Entry", size=RADIX_SIZE_HEADING, as_="h2"),
        rx.text("Click any cell to edit a month's actuals.", size=RADIX_SIZE_BODY),
        history_toggle(),
        rx.cond(
            DashboardState.rows.length() > 0,
            rx.box(
                data_table(),
                background=DashboardState.surface,
                border=DashboardState.card_border,
                border_radius=CARD_RADIUS,
                padding=CARD_PADDING,
                overflow_x="auto",
                overflow_y="auto",
                max_height="80vh",
                width="100%",
                min_width="0",
            ),
            empty_state(),
        ),
        quick_add_form(),
        rx.text(
            "Import CSV",
            size=RADIX_SIZE_BODY,
            font_weight=FONT_WEIGHT_SEMIBOLD,
        ),
        csv_import_control(),
        spacing="3",
        aria_label="Data entry",
        role="region",
    )
```

Note the `rx.cond` guard changed from `(DashboardState.rows.length() + DashboardState.draft_rows.length()) > 0` to `DashboardState.rows.length() > 0` — there is no more `draft_rows` to add to the count, and the existing `test_data_entry_section_empty_state_uses_full_rows` test (~line 360 in `test_app_components.py`) already asserts `"visible_rows" not in source`, which this satisfies; it does not check for `draft_rows`, so no test change needed there, but double check by running it in Step 5.

Now delete the old `add_row_button()` function entirely (it's fully superseded).

**Step 5: Run the full test suite**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: all pass, including the two tests updated in Task 4 (`test_data_table_has_no_draft_rows_foreach`, `test_data_entry_section_places_import_control_after_quick_add_form`).

If `rx.input`'s `value=` binding to a dict-keyed Var (`DashboardState.quick_add_values[attr]`) causes a Reflex compile-time type error (dict indexing with a Python string key that isn't a literal known at compile time can be finicky in some Reflex versions), fall back to a `rx.foreach` over a list of `{"attr": ..., "label": ..., "value": ...}` dicts built as a computed var on `DashboardState`, mirroring the pattern already used for `freshness_chips`/`_freshness_chip` (~line 263 in `app.py`). Only take this fallback if the straightforward version fails to compile — verify with `cd app && .venv/bin/reflex run --frontend-port 3006 --backend-port 8006` and watch for compile errors before assuming it's needed.

**Step 6: Commit**

```bash
git add app/app/app.py
git commit -m "feat(data-entry): add quick_add_form, sticky header/date column"
```

---

## Task 6: Restyle CSV import states

**Files:**
- Modify: `app/app/app.py`

**Step 1: Update `csv_import_control()`'s visual treatment**

In `app/app/app.py`, `csv_import_control()` (~lines 584-709) already has four branches (`error_state`, `preview_state`, `done_state`, `idle_state`). Apply the mockup's visual polish without changing any behavior, event handlers, or the `import_stage` branching logic:

- `idle_state`: already uses `rx.icon("upload", ...)` and dashed border — leave as-is (already matches).
- `error_state`: wrap in a bordered/tinted box for visual weight, matching the mockup's red-bordered card, instead of a bare `rx.hstack`:

```python
    error_state = rx.hstack(
        rx.icon("circle-alert", size=16, color=DashboardState.destructive_color),
        rx.text(
            DashboardState.import_error,
            size=RADIX_SIZE_BODY,
            color=DashboardState.destructive_color,
        ),
        rx.button(
            "Try again",
            variant="ghost",
            color_scheme="blue",
            on_click=DashboardState.cancel_import,
        ),
        spacing="2",
        align="center",
        padding=SPACE_MD,
        border=f"1px solid {DashboardState.destructive_color}",
        border_radius=CARD_RADIUS,
    )
```

(Only the trailing `padding`/`border`/`border_radius` kwargs are new — everything else in this block is unchanged from the current source.)

- `preview_state`/`done_state`: already boxed with `background`/`border`/`border_radius`/`padding` — no change needed, they already match the mockup's card treatment.

**Step 2: Run the CSV-specific tests**

Run: `cd app && .venv/bin/python -m pytest tests/test_app_components.py -k csv_import_control -v`
Expected: PASS — in particular `test_csv_import_control_introduces_no_new_hex_or_px_literals` must still pass, so double-check the added `border=f"1px solid {DashboardState.destructive_color}"` line does not introduce a literal hex code or `"Npx"` string (it doesn't — `DashboardState.destructive_color` is a computed var reference, and `"1px solid ..."` contains `1px` not `\d+px` matching the full pattern... actually re-read the test regex: `r'"\d+px"'` matches a standalone quoted px value like `"12px"`, not `1px` embedded inside a longer string like `"1px solid ..."` since the regex requires the digits+px to be the entire quoted string content — run the test to confirm rather than assuming).

**Step 3: Run the full test suite**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: all pass.

**Step 4: Commit**

```bash
git add app/app/app.py
git commit -m "style(data-entry): restyle CSV import error state"
```

---

## Task 7: Manual verification in the running app

**Files:** none (verification only)

**Step 1: Start the dev server**

Run: `cd app && .venv/bin/reflex run --frontend-port 3005 --backend-port 8005`

**Step 2: Verify in browser**

Open `http://localhost:3005`, go to the Data Entry tab, and check:
1. The quick-add form appears above the table with 17 labeled fields, Date marked required.
2. Entering a date + a couple of series values and clicking "Save row" adds a new row to the table, clears the form, and the form stays open (ready for the next month).
3. Submitting with no date shows an error and does not add a row.
4. Submitting a non-numeric value in a series field shows an error naming that field.
5. Scrolling the table vertically keeps the header pinned; scrolling horizontally keeps the Date column pinned.
6. The CSV import section still transitions correctly through idle → preview → done, and shows the restyled error card when an invalid file is dropped.

**Step 3: Report findings**

If anything in Step 2 doesn't match, note exactly what's wrong (screenshot if possible) before considering this plan complete — do not mark done on unverified UI.

---
