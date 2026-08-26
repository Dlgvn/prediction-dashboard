# Precision Instrument Visual Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the dashboard's current generic-SaaS color/type tokens with the "precision instrument" system (teal-cyan accent, IBM Plex Mono/Sans typography, sharper radius, gauge-bezel summary cards) without changing any IA, behavior, or token variable names.

**Architecture:** Change only the *values* inside `app/app/theme.py`'s existing `LIGHT`/`DARK` dicts and top-level constants (never renaming keys, so every existing `theme.X`/`DashboardState.x_color` reference app-wide keeps working unmodified). Add font loading at the `rx.App()` level. Apply the new typography and gauge-bezel treatment only to the specific components the design doc calls out.

**Tech Stack:** Reflex (Python), Radix Themes (via `rx.theme`), Google Fonts (IBM Plex Mono, IBM Plex Sans), pytest.

**Design doc:** `docs/plans/2026-08-26-precision-instrument-redesign-design.md`

---

## Task 1: Update light-mode color tokens in `theme.py`

**Files:**
- Modify: `app/app/theme.py`
- Modify: `app/tests/test_theme.py`

**Step 1: Update the failing tests first**

In `app/tests/test_theme.py`, update the two tests that assert on old hex
literals:

```python
def test_accent_is_locked_hex():
    # 2026-08-26 precision-instrument redesign: teal-cyan INDICATOR accent
    # (#0E7C86) replaces the prior generic blue (#2563EB). 4.95:1 against
    # SURFACE white, meets WCAG AA 4.5:1 normal-text threshold.
    assert theme.ACCENT == "#0E7C86"


def test_all_locked_color_hex_values_present():
    # 2026-08-26 precision-instrument redesign: PAGE_BG, BORDER, ACCENT,
    # and MUTED_TEXT were retuned to the new palette; SURFACE, DESTRUCTIVE,
    # and UP are unchanged (already correct/contrast-verified).
    for hex_value in (
        "#EEF1F3",
        "#FFFFFF",
        "#7B838B",
        "#0E7C86",
        "#DC2626",
        "#15803D",
    ):
        assert hex_value in (
            theme.PAGE_BG,
            theme.SURFACE,
            theme.BORDER,
            theme.ACCENT,
            theme.DESTRUCTIVE,
            theme.UP,
            theme.DOWN,
        )
```

**Step 2: Run tests to verify they fail**

Run: `cd app && .venv/bin/python -m pytest tests/test_theme.py -v`
Expected: `test_accent_is_locked_hex` and `test_all_locked_color_hex_values_present` FAIL (old hex values still in `theme.py`).

**Step 3: Update `theme.py`'s light-mode constants**

In `app/app/theme.py`, replace lines 25-44 (the light-mode literal block)
with:

```python
PAGE_BG = "#EEF1F3"
SURFACE = "#FFFFFF"
# 2026-08-26 precision-instrument redesign: darkened from #8E9096 to
# #7B838B (a cooler blue-gray) to clear WCAG 3:1 non-text-boundary
# contrast against the new PAGE_BG (#EEF1F3, 3.39:1) as well as SURFACE
# (3.85:1) — the redesign's lighter/cooler PAGE_BG made the prior value
# fail against PAGE_BG specifically (2.81:1 measured).
BORDER = "#7B838B"
# 2026-08-26 precision-instrument redesign: teal-cyan accent (was generic
# blue #2563EB) — 4.95:1 against SURFACE white (WCAG AA 4.5:1 threshold).
ACCENT = "#0E7C86"
ACCENT_FILL = "rgba(14,124,134,0.15)"
DESTRUCTIVE = "#DC2626"
NEUTRAL_LINE = "#697177"
UP = "#15803D"
DOWN = "#DC2626"
# 2026-08-26 precision-instrument redesign: darkened from #71717A to
# #5B6167 within the same neutral hue — 6.27:1 against SURFACE (was
# already passing; kept comfortably above threshold after the palette's
# other tones shifted cooler, for visual consistency of the neutral family).
MUTED_TEXT = "#5B6167"
```

Do not change the `LIGHT: dict[str, str] = {...}` block below it — it
already references these constants by name, so it picks up the new
values automatically.

**Step 4: Update `CARD_RADIUS`**

In the same file, find `CARD_RADIUS = "8px"` (near the bottom, in the
"Shared surface chrome" section) and change it to:

```python
CARD_RADIUS = "4px"
```

**Step 5: Run tests to verify they pass**

Run: `cd app && .venv/bin/python -m pytest tests/test_theme.py -v`
Expected: PASS (all tests in this file)

**Step 6: Run the full test suite**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: some failures are possible in `test_theme_tokens.py` (dark-mode
tests, untouched so far — that's Task 2) and possibly in
`test_app_components.py` if anything asserts on the old `8px` radius or
old hex literals directly. Note any such failures; Task 2 and Task 3
address the dark-mode ones. If `test_app_components.py` has a stray
assertion on `"8px"` or the old ACCENT hex, fix it now as part of this
task (search with `grep -rn "8px\|2563EB\|8E9096\|FAFAFA" app/tests/test_app_components.py`) — these would be incidental hardcoded expectations elsewhere, not part of the design system itself.

**Step 7: Commit**

```bash
git add app/app/theme.py app/tests/test_theme.py
git commit -m "feat(theme): retune light-mode color tokens for precision-instrument redesign"
```

---

## Task 2: Update dark-mode color tokens in `theme.py`

**Files:**
- Modify: `app/app/theme.py`
- Modify: `app/tests/test_theme_tokens.py`

**Step 1: Update the failing test first**

In `app/tests/test_theme_tokens.py`, replace the `CONTRAST_TABLE` list
(around line 68) with the newly-computed ratios (all measured against
the new `DARK["SURFACE"]` value from Step 3 below):

```python
CONTRAST_TABLE = [
    ("BORDER", 4.70, 3.0),
    ("ACCENT", 7.68, 4.5),
    ("DESTRUCTIVE", 5.89, 4.5),
    ("UP", 9.34, 4.5),
    ("DOWN", 5.89, 4.5),
    ("MUTED_TEXT", 6.24, 4.5),
]
```

Leave `test_rejected_border_candidate_stays_below_threshold` as-is (it
tests a specific rejected hex value from the *original* Phase 11 design
history, unrelated to this redesign — still a valid regression guard).

**Step 2: Run to verify it fails**

Run: `cd app && .venv/bin/python -m pytest tests/test_theme_tokens.py -v`
Expected: the parametrized `test_dark_token_meets_contrast_threshold_and_matches_spec` cases FAIL (old `DARK` values don't match the new expected ratios yet).

**Step 3: Update `theme.py`'s `DARK` dict**

Replace the `DARK: dict[str, str] = {...}` block (lines 68-98) with:

```python
DARK: dict[str, str] = {
    # 2026-08-26 precision-instrument redesign: darkened from #18181B to
    # #101416 (cooler near-black) to match the light mode's cooler
    # PAGE_BG shift. No contrast pairing (background reference only).
    "PAGE_BG": "#101416",
    # 2026-08-26 precision-instrument redesign: #1B2124 (was #27272A) —
    # cooler card layer matching the new PAGE_BG hue family. No contrast
    # pairing (background reference only).
    "SURFACE": "#1B2124",
    # 2026-08-26 precision-instrument redesign: #828B92 (was #71717A) —
    # 4.70:1 against the new SURFACE dark (threshold 3:1 non-text).
    "BORDER": "#828B92",
    # 2026-08-26 precision-instrument redesign: brightened teal-cyan (was
    # #60A5FA blue) — 7.68:1 against SURFACE dark (threshold 4.5:1).
    "ACCENT": "#3FC3CE",
    "ACCENT_FILL": "rgba(63,195,206,0.15)",
    # Unchanged hex from before the redesign, but ratio vs the new
    # SURFACE dark recalculated: 5.89:1 (was 5.39:1 vs the old SURFACE).
    "DESTRUCTIVE": "#F87171",
    "NEUTRAL_LINE": "#A1A1AA",
    # Unchanged hex; ratio vs new SURFACE dark recalculated: 9.34:1.
    "UP": "#4ADE80",
    # Same value as DESTRUCTIVE dark, reused — mirrors light mode's
    # DOWN == DESTRUCTIVE reuse. Ratio vs new SURFACE dark: 5.89:1.
    "DOWN": "#F87171",
    # 2026-08-26 precision-instrument redesign: #9BA1A6 (was #A1A1AA) —
    # 6.24:1 against SURFACE dark (threshold 4.5:1).
    "MUTED_TEXT": "#9BA1A6",
}
```

**Step 4: Run tests to verify they pass**

Run: `cd app && .venv/bin/python -m pytest tests/test_theme_tokens.py -v`
Expected: PASS (all tests in this file)

**Step 5: Run the full test suite**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: PASS (all tests — this closes out every token-value test affected by the redesign)

**Step 6: Commit**

```bash
git add app/app/theme.py app/tests/test_theme_tokens.py
git commit -m "feat(theme): retune dark-mode color tokens for precision-instrument redesign"
```

---

## Task 3: Update Radix theme accent color and radius in `rxconfig.py`

**Files:**
- Modify: `app/rxconfig.py`

**Step 1: Make the change**

In `app/rxconfig.py`, change:

```python
            theme=rx.theme(accent_color="blue")
```

to:

```python
            theme=rx.theme(accent_color="cyan", radius="small")
```

This is the closest built-in Radix palette name to the new `ACCENT` hex
(`#0E7C86`), and switches Radix-native chrome (buttons, switches, focus
rings, tabs) to match the hand-tuned hex tokens instead of the old
generic blue. `radius="small"` sharpens Radix-native component corners
(buttons, inputs, etc.) to match the redesign's `CARD_RADIUS = "4px"`
from Task 1 — Radix's own `"small"` radius token renders visually close
to 4px at its default scale, keeping hand-drawn cards and Radix-native
controls consistent.

**Step 2: Verify the app compiles**

Reflex config changes require a fresh compile since `rxconfig.py` isn't
hot-reloaded the same way component code is. Run:
`cd app && .venv/bin/reflex run --frontend-port 3010 --backend-port 8010`
Expected: `App Running` with no compile errors. Stop the server after
confirming (Ctrl-C, or `lsof -ti:3010,8010 | xargs kill` if backgrounded).

**Step 3: Commit**

```bash
git add app/rxconfig.py
git commit -m "feat(theme): switch Radix accent to cyan, radius to small"
```

---

## Task 4: Load IBM Plex fonts and set them as the app-wide defaults

**Files:**
- Modify: `app/app/app.py`

**Step 1: Add the Google Fonts stylesheet and global font-family style**

Reflex's `rx.App()` accepts a `stylesheets` list (external `<link>` URLs)
and a `style` dict (global CSS applied to every component unless
overridden locally). In `app/app/app.py`, find the line near the bottom:

```python
app = rx.App()
```

Replace it with:

```python
app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap",
    ],
    style={
        "font_family": "'IBM Plex Sans', sans-serif",
    },
)
```

This sets IBM Plex Sans as the default for all text (headings, labels,
body, buttons) app-wide. Numeric components get IBM Plex Mono explicitly
in Task 5 (Radix/Reflex's per-component `font_family` prop overrides this
global default where set).

**Step 2: Verify the app compiles and the font loads**

Run: `cd app && .venv/bin/reflex run --frontend-port 3010 --backend-port 8010`
Expected: `App Running`, no compile errors. Open `http://localhost:3010`
in a browser and confirm body text visually changed from the default
Radix font (Inter-like) to IBM Plex Sans (check via browser devtools:
inspect any `<p>` or heading element, confirm computed `font-family`
includes "IBM Plex Sans"). Stop the server after confirming.

**Step 3: Commit**

```bash
git add app/app/app.py
git commit -m "feat(theme): load and apply IBM Plex Sans as the app-wide font"
```

---

## Task 5: Apply IBM Plex Mono to numeric data

**Files:**
- Modify: `app/app/app.py`

**Step 1: Add Plex Mono to the Data Entry table's numeric cells**

In `_editable_cell` (around line 36), both the `display` (`rx.text`) and
the `editor`'s `rx.input` render numeric values. Find the `display =
rx.text(...)` block (around line 57) and add `font_family`:

```python
    display = rx.text(
        shown_text,
        on_click=DashboardState.start_edit(key, edit_value),
        cursor="pointer",
        size="2",
        font_family="'IBM Plex Mono', monospace",
    )
```

**Step 2: Add Plex Mono to the Forecast table's cells**

In `forecast_table()` (around line 365), the `rx.table.cell(row["month"])`
and `rx.table.cell(row[key])` cells render numbers. Update:

```python
    table = rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Month"),
                *[
                    rx.table.column_header_cell(label)
                    for _, label in FORECAST_TABLE_COLUMNS
                ],
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.forecast_table_rows,
                lambda row: rx.table.row(
                    rx.table.cell(row["month"], font_family="'IBM Plex Mono', monospace"),
                    *[
                        rx.table.cell(row[key], font_family="'IBM Plex Mono', monospace")
                        for key, _ in FORECAST_TABLE_COLUMNS
                    ],
                ),
            )
        ),
    )
```

**Step 3: Add Plex Mono to the summary card's big figure and freshness chip dates**

In `_summary_card` (around line 443), the big number:

```python
                    rx.text(
                        card["base"],
                        font_size=FONT_SIZE_DISPLAY,
                        font_weight=FONT_WEIGHT_SEMIBOLD,
                        line_height="1.2",
                        font_family="'IBM Plex Mono', monospace",
                    ),
```

In `_freshness_chip` (around line 263), the date text:

```python
            rx.cond(
                chip["has_data"] == "yes",
                rx.text(
                    chip["date"],
                    size=RADIX_SIZE_BODY,
                    font_weight=FONT_WEIGHT_SEMIBOLD,
                    font_family="'IBM Plex Mono', monospace",
                ),
                rx.text("no data yet", size=RADIX_SIZE_BODY, color=DashboardState.muted_text),
            ),
```

**Step 4: Add Plex Mono to the quick-add form's numeric inputs**

In `_quick_add_field` (added by the prior quick-add-row feature, around
line 710), add `font_family` to the `rx.input`:

```python
        rx.input(
            value=DashboardState.quick_add_values[attr].to(str),
            on_change=lambda value: DashboardState.update_quick_add_field(attr, value),
            type="date" if attr == "date" else "text",
            size="2",
            font_family="'IBM Plex Mono', monospace",
        ),
```

**Step 5: Run the full test suite**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: PASS. If any `test_app_components.py` test does exact source-string matching on one of these blocks (e.g. asserting the full `rx.text(...)` call signature), it will fail on the added `font_family` kwarg — search first with `grep -rn "card\[.base.\]\|_editable_cell\|forecast_table_rows" app/tests/test_app_components.py` and update any such test to account for the new kwarg rather than removing it.

**Step 6: Commit**

```bash
git add app/app/app.py app/tests/test_app_components.py
git commit -m "style(theme): apply IBM Plex Mono to numeric data throughout the app"
```

---

## Task 6: Gauge-bezel treatment for summary cards and freshness chips

**Files:**
- Modify: `app/app/app.py`

**Step 1: Add the gauge-bezel border treatment to `_summary_card`**

Per the design doc, the signature element is a thin top rule with small
corner ticks. Reflex/CSS can approximate "corner ticks" with a
`border-image` or, more simply and robustly across browsers, two small
absolutely-positioned pseudo-elements — but Reflex's component API
doesn't expose `::before`/`::after` directly. The pragmatic equivalent
that stays within plain component props: a distinctly thicker/colored
top border plus the existing full border, which reads as a "panel top
rule" without needing custom CSS pseudo-elements. Update `_summary_card`'s
outer `rx.box` (around line 514) call's border props:

```python
        background=DashboardState.surface,
        border=DashboardState.card_border,
        border_top=f"2px solid {DashboardState.accent_color}",
        border_radius=CARD_RADIUS,
        padding=CARD_PADDING,
```

**Step 2: Apply the same top-rule treatment to `_freshness_chip`**

In `_freshness_chip` (around line 265), the outer `rx.box`:

```python
    return rx.box(
        rx.vstack(
            ...unchanged...
        ),
        border=DashboardState.card_border,
        border_top=f"2px solid {DashboardState.accent_color}",
        border_style=rx.cond(chip["has_data"] == "yes", "solid", "dashed"),
        border_radius=CARD_RADIUS,
        padding="8px 12px",
    )
```

Note: `border_style="dashed"` on the "no data yet" chip will also dash
the top rule via the shorthand `border` prop's style — that's fine and
consistent (an empty gauge reads as "dashed/incomplete," which fits the
existing `has_data` semantics).

**Step 3: Run the full test suite**

Run: `cd app && .venv/bin/python -m pytest tests/ -q`
Expected: PASS. If a test asserts on the exact border props of these two functions, update it to account for the new `border_top` kwarg.

**Step 4: Manual visual check**

Start the dev server (`cd app && .venv/bin/reflex run --frontend-port 3010 --backend-port 8010`), open the Summary tab, and confirm: each summary card and freshness chip shows a colored top rule in the new teal-cyan `ACCENT`, the big numbers render in IBM Plex Mono, and body text/labels render in IBM Plex Sans. Check both light and dark mode via the theme toggle. Stop the server after confirming.

**Step 5: Commit**

```bash
git add app/app/app.py
git commit -m "feat(theme): add gauge-bezel top rule to summary cards and freshness chips"
```

---

## Task 7: Full-app manual verification

**Files:** none (verification only)

**Step 1: Start the dev server**

Run: `cd app && .venv/bin/reflex run --frontend-port 3005 --backend-port 8005`

**Step 2: Check each tab in both light and dark mode**

1. **Summary tab**: four summary cards show the teal-cyan top rule, Plex Mono figures, Plex Sans labels; freshness chips match.
2. **Forecast tab**: chart renders (chart line colors come from `NEUTRAL_LINE`/`UP`/`DOWN`, unchanged by this redesign — confirm they still look reasonable against the new card backgrounds), forecast table numbers render in Plex Mono, horizon slider and series selector use the new cyan accent.
3. **Data Entry tab**: table numbers render in Plex Mono, sticky header/Date column still work, quick-add form inputs use Plex Mono, "Save row" button uses the new cyan accent, CSV import states unaffected in behavior.
4. Toggle dark mode (the sun/moon icon in the header) and repeat the same checks — confirm text stays legible against the new darker `PAGE_BG`/`SURFACE` values.

**Step 3: Report findings**

If anything looks wrong (illegible text, a component still showing the old blue, a layout break from the radius change), note exactly what and where before considering this plan complete.

---
