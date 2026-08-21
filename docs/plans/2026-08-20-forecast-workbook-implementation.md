# Forecast Workbook Implementation Plan

**Goal:** Build `AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx` with live LINEST-based formulas for
HDAN/PPAN (VAR), Diesel-USD, FX rate, and derived Diesel-MNT, per
`docs/plans/2026-08-20-forecast-workbook-design.md`, plus a standalone `README.md`.

**Architecture:** A Python build script (`build_workbook.py`, using `openpyxl`) constructs the
workbook tab-by-tab: parses the two source CSVs into monthly rows, writes them to Input, writes
%-change formulas to PctChange, writes LINEST regression formulas to Regression, and writes
roll-forward forecast formulas to Forecast. The script is re-run (not hand-edited in Excel) any
time the design changes, keeping the build reproducible. LibreOffice headless (`soffice
--convert-to xlsx --calc`) is used after each build to force formula recalculation so we can
verify actual computed values, not just formula text.

**Tech Stack:** Python 3, `openpyxl`, `csv` (stdlib), LibreOffice headless for recalculation/verification.

---

### Task 1: Parse source CSVs into monthly rows

**Files:**
- Create: `scripts/build_workbook.py` (start with just the CSV-parsing section)
- Create: `scripts/verify_data.py` (throwaway check script)

**Step 1: Write `parse_an_data()` and `parse_diesel_data()` in `build_workbook.py`**

```python
import csv
from collections import defaultdict
from datetime import datetime

AN_COLS = ["PPAN", "HDAN", "Baltic_AN", "Ammonia", "Urea", "Natural_Gas", "Brent"]

def parse_an_data(path="AN Data.csv"):
    """AN Data.csv is weekly. Returns {(year, month): {col: avg_value}}."""
    monthly = defaultdict(lambda: defaultdict(list))
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Date"):
                continue
            year, month = int(row["Year"]), int(row[" Month "])
            monthly[(year, month)]["PPAN"].append(float(row[" PPAN "]))
            monthly[(year, month)]["HDAN"].append(float(row[" HDAN "]))
            monthly[(year, month)]["Baltic_AN"].append(float(row[" Baltic AN "]))
            monthly[(year, month)]["Ammonia"].append(float(row[" Ammonia "]))
            monthly[(year, month)]["Urea"].append(float(row[" Urea "]))
            monthly[(year, month)]["Natural_Gas"].append(float(row[" Natural_Gas "]))
            monthly[(year, month)]["Brent"].append(float(row["  Brent  "]))
    return {
        ym: {col: sum(vals) / len(vals) for col, vals in cols.items()}
        for ym, cols in monthly.items()
    }

def _num(s):
    """Diesel Data.csv values are comma-formatted strings like ' 1,760.33 '."""
    return float(s.replace(",", "").strip())

def parse_diesel_data(path="Diesel Data.csv"):
    """Diesel Data.csv is already monthly. Returns {(year, month): {col: value}}."""
    monthly = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Date"):
                continue
            year, month = map(int, row["Date"].split("-"))
            monthly[(year, month)] = {
                "Diesel_USD_ton": _num(row["Import_Volume_Price_per_ton_USD"]),
                "Urals": _num(row["URALS_Crude _Oil_(USD/BBL)"]),
                "FX_rate": _num(row["FX_rate"]),
            }
    return monthly

if __name__ == "__main__":
    an = parse_an_data()
    diesel = parse_diesel_data()
    print(f"AN months: {len(an)}, range {min(an)} to {max(an)}")
    print(f"Diesel months: {len(diesel)}, range {min(diesel)} to {max(diesel)}")
```

**Step 2: Run it and check the output makes sense**

Run: `cd "/Users/dlgvnbyr/Desktop/Prediction Dashboard" && python3 scripts/build_workbook.py`

Expected: something like `AN months: 48, range (2022, 8) to (2026, 7)` and
`Diesel months: 77, range (2020, 2) to (2026, 6)`. If a `KeyError` appears, the exact column
header (spacing) in the CSV doesn't match — re-check with `head -1 "AN Data.csv"` /
`head -1 "Diesel Data.csv"` and fix the dict keys (the CSVs have inconsistent leading/trailing
spaces in headers, confirmed during design research).

**Step 3: Checkpoint**

No git commit (not a git repo) — just keep this script; Task 2 builds on it directly.

---

### Task 2: Merge into one monthly row list and write the Input tab

**Files:**
- Modify: `scripts/build_workbook.py` (add merge + Input-tab writer)

**Step 1: Add a merge function and Input tab writer**

```python
import openpyxl
from openpyxl.utils import get_column_letter

INPUT_COLS = ["Date", "HDAN", "PPAN", "Baltic_AN", "Ammonia", "Urea", "Natural_Gas", "Brent",
              "Diesel_USD_ton", "Urals", "FX_rate"]

def merge_monthly(an, diesel):
    """Full outer join on (year, month), sorted ascending. Missing series -> None."""
    all_months = sorted(set(an) | set(diesel))
    rows = []
    for ym in all_months:
        a = an.get(ym, {})
        d = diesel.get(ym, {})
        rows.append({
            "Date": datetime(ym[0], ym[1], 1),
            "HDAN": a.get("HDAN"), "PPAN": a.get("PPAN"),
            "Baltic_AN": a.get("Baltic_AN"), "Ammonia": a.get("Ammonia"),
            "Urea": a.get("Urea"), "Natural_Gas": a.get("Natural_Gas"), "Brent": a.get("Brent"),
            "Diesel_USD_ton": d.get("Diesel_USD_ton"), "Urals": d.get("Urals"),
            "FX_rate": d.get("FX_rate"),
        })
    return rows

def write_input_tab(wb, rows):
    ws = wb.create_sheet("Input")
    for c, name in enumerate(INPUT_COLS, start=1):
        ws.cell(row=1, column=c, value=name)
    for r, row in enumerate(rows, start=2):
        for c, name in enumerate(INPUT_COLS, start=1):
            ws.cell(row=r, column=c, value=row[name])
    ws.cell(row=1, column=len(INPUT_COLS) + 2, value="Markup_%")
    ws.cell(row=2, column=len(INPUT_COLS) + 2, value=0.0282)
    return ws

if __name__ == "__main__":
    an = parse_an_data()
    diesel = parse_diesel_data()
    rows = merge_monthly(an, diesel)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    write_input_tab(wb, rows)
    wb.save("AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx")
    print(f"Wrote {len(rows)} rows to Input tab")
```

**Step 2: Run and verify**

Run: `python3 scripts/build_workbook.py`

Expected: `Wrote 77 rows to Input tab` (or similar). Then open with:

```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx')
ws = wb['Input']
print(ws['A1:L3'])
for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
    print(row)
"
```

Check: first data row (2020-02) has `HDAN`/`PPAN`/etc. as `None` (blank — AN data doesn't start
until 2022-08), and `Diesel_USD_ton`/`Urals`/`FX_rate` populated. A later row (2022-08 onward)
should have all columns populated. The `Markup_%` cell should read `0.0282`.

**Step 3: Checkpoint** — no commit; proceed to Task 3.

---

### Task 3: PctChange tab (month-over-month % change formulas)

**Files:**
- Modify: `scripts/build_workbook.py`

**Step 1: Add PctChange tab writer — Excel formulas, not Python-computed values**

For each numeric column in Input (HDAN, PPAN, Baltic_AN, Ammonia, Urea, Natural_Gas, Brent,
Diesel_USD_ton, Urals, FX_rate), write `=IFERROR((Input!X3-Input!X2)/Input!X2, "")` for each row
from the 2nd data row onward (first row has no prior month, so blank).

```python
PCTCHANGE_COLS = INPUT_COLS[1:]  # everything except Date

def write_pctchange_tab(wb, n_rows):
    ws = wb.create_sheet("PctChange")
    ws.cell(row=1, column=1, value="Date")
    for c, name in enumerate(PCTCHANGE_COLS, start=2):
        ws.cell(row=1, column=c, value=name)
    for r in range(2, n_rows + 2):
        ws.cell(row=r, column=1, value=f"=Input!A{r}")
        for c, name in enumerate(PCTCHANGE_COLS, start=2):
            col_letter = get_column_letter(c)
            if r == 2:
                continue  # no prior month for the first row
            ws.cell(row=r, column=c,
                     value=f'=IFERROR((Input!{col_letter}{r}-Input!{col_letter}{r-1})/Input!{col_letter}{r-1}, "")')
    return ws
```

Call `write_pctchange_tab(wb, len(rows))` in `__main__` after `write_input_tab`.

**Step 2: Run, recalculate with LibreOffice, and verify actual values**

```bash
python3 scripts/build_workbook.py
soffice --headless --convert-to xlsx --outdir /tmp/recalc AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('/tmp/recalc/AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx', data_only=True)
ws = wb['PctChange']
for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
    print(row)
"
```

Expected: row 2 (first data row) is blank in the numeric columns; row 3 onward shows small
decimal % changes (e.g. `0.02`, `-0.04`), not errors or `None` where Input had two consecutive
non-blank values. Where Input has a `None` (blank month), PctChange for that cell and the
following cell should be blank too (division against/of a blank) — spot-check this doesn't throw
a `#VALUE!` visible in the recalculated file.

**Step 3: Checkpoint** — no commit; proceed to Task 4.

---

### Task 4: Regression tab — LINEST for FX and Diesel-USD (single-predictor models first)

**Files:**
- Modify: `scripts/build_workbook.py`

**Step 1: Add Regression tab, starting with the two simpler models**

FX: `ΔFX_t = c + φ·ΔFX_{t-1}` — regress PctChange FX_rate column against itself shifted by one row.
Diesel: `ΔDiesel_t = c + b·ΔBrent_{t-2}` — regress PctChange Diesel_USD_ton against Brent shifted
by two rows.

`LINEST` in Excel returns coefficients highest-order-predictor-first, constant last (when
`const=TRUE`). For a single predictor: `LINEST(known_y, known_x, TRUE, FALSE)` returns a 1x2
array `{slope, intercept}`.

```python
def write_regression_tab(wb, n_rows):
    ws = wb.create_sheet("Regression")
    pc = "PctChange"
    # FX rate column letter and Diesel/Brent column letters depend on PCTCHANGE_COLS order —
    # confirm via PCTCHANGE_COLS.index(...) rather than hardcoding, e.g.:
    fx_col = get_column_letter(2 + PCTCHANGE_COLS.index("FX_rate"))
    diesel_col = get_column_letter(2 + PCTCHANGE_COLS.index("Diesel_USD_ton"))
    brent_col = get_column_letter(2 + PCTCHANGE_COLS.index("Brent"))

    last_row = n_rows + 1  # PctChange row range: 2..n_rows+1

    ws["A1"] = "Model"
    ws["A2"] = "FX (AR1)"
    ws["B2"] = "slope"
    ws["C2"] = "intercept"
    # y = FX_t (rows 4..last_row), x = FX_{t-1} (rows 3..last_row-1)
    ws["D2"] = (f"=LINEST({pc}!{fx_col}4:{fx_col}{last_row},"
                f"{pc}!{fx_col}3:{fx_col}{last_row-1})")  # array formula, spills slope|intercept

    ws["A3"] = "Diesel-USD (Brent lag2)"
    # y = Diesel_t (rows 5..last_row), x = Brent_{t-2} (rows 3..last_row-2)
    ws["D3"] = (f"=LINEST({pc}!{diesel_col}5:{diesel_col}{last_row},"
                f"{pc}!{brent_col}3:{brent_col}{last_row-2})")
    return ws
```

*(Note for whoever implements this: openpyxl writes the formula text; Excel/LibreOffice handles
the dynamic-array spill on open. Read back with `data_only=True` after LibreOffice recalculation
to get the actual spilled slope/intercept values — the top-left cell alone won't show both.)*

**Step 2: Run and verify against the report's known-good numbers**

```bash
python3 scripts/build_workbook.py
soffice --headless --convert-to xlsx --outdir /tmp/recalc AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('/tmp/recalc/AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx', data_only=True)
ws = wb['Regression']
for row in ws.iter_rows(min_row=1, max_row=3, values_only=True):
    print(row)
"
```

Expected: real numeric slope/intercept values (not formula text, not `#NAME?`/`#REF!`). There's
no exact target to match (the report's coefficients weren't published, only MAPEs), so the check
here is "produces a plausible small slope (roughly -1 to 1) and doesn't error" — sanity, not
exact reproduction.

**Step 3: Checkpoint** — no commit; proceed to Task 5.

---

### Task 5: Regression tab — VAR(HDAN, PPAN) two-predictor LINEST

**Files:**
- Modify: `scripts/build_workbook.py`

**Step 1: Add the two VAR equations**

`ΔHDAN_t = c₁ + a₁₁·ΔHDAN_{t-1} + a₁₂·ΔPPAN_{t-1}` and the PPAN mirror. Two predictors means
`LINEST` needs a 2-column x-range; the easiest way in a single-sheet formula is to reference a
contiguous 2-column block, so add two helper columns to the Regression tab that pull HDAN_{t-1}
and PPAN_{t-1} side by side, then LINEST over that block.

```python
    hdan_col = get_column_letter(2 + PCTCHANGE_COLS.index("HDAN"))
    ppan_col = get_column_letter(2 + PCTCHANGE_COLS.index("PPAN"))
    # AN data starts partway through Input; find first row where both HDAN and PPAN are non-blank
    # in PctChange (row index within PctChange, 1-based sheet row).
    an_first_pct_row = None  # computed in Python from `rows`, passed into this function
    ...
    # Helper columns F (HDAN_t-1) and G (PPAN_t-1), rows aligned to y-range start
    y_start = an_first_pct_row + 1  # first row with a valid prior-month predictor too
    for i, r in enumerate(range(y_start, last_row + 1)):
        ws.cell(row=10 + i, column=6, value=f"={pc}!{hdan_col}{r-1}")
        ws.cell(row=10 + i, column=7, value=f"={pc}!{ppan_col}{r-1}")
    n_var_rows = last_row - y_start + 1
    ws["A5"] = "VAR: HDAN eq (a11, a12, c1)"
    ws["D5"] = f"=LINEST({pc}!{hdan_col}{y_start}:{hdan_col}{last_row}, F10:G{9+n_var_rows})"
    ws["A6"] = "VAR: PPAN eq (a21, a22, c2)"
    ws["D6"] = f"=LINEST({pc}!{ppan_col}{y_start}:{ppan_col}{last_row}, F10:G{9+n_var_rows})"
```

*(This is sketched, not copy-paste-exact — the implementer needs to compute `an_first_pct_row`
in Python from the actual `rows` list built in Task 2, since it depends on where AN data starts
being non-blank. Compute it as: index of first row in `rows` where `row["HDAN"] is not None`,
+2 for the header/1-based offset, matching the same row numbering PctChange uses.)*

**Step 2: Run and verify**

Same LibreOffice-recalc-then-read pattern as Task 4. Expected: `D5` and `D6` spill 3 values each
(`a11, a12, c1` and `a21, a22, c2`), all real numbers, no errors.

**Step 3: Checkpoint** — no commit; proceed to Task 6.

---

### Task 6: Forecast tab — roll-forward formulas for all four series

**Files:**
- Modify: `scripts/build_workbook.py`

**Step 1: Write the Forecast tab**

One row: next month's forecast for each series, referencing the last actual value in Input and
the fitted coefficients in Regression.

```python
def write_forecast_tab(wb, n_rows):
    ws = wb.create_sheet("Forecast")
    last_input_row = n_rows + 1
    last_pct_row = n_rows + 1

    ws["A1"] = "Series"; ws["B1"] = "Last Actual"; ws["C1"] = "Predicted % Change"; ws["D1"] = "Forecast"

    ws["A2"] = "HDAN"
    ws["B2"] = f"=Input!B{last_input_row}"
    ws["C2"] = f"=Regression!D5 + Regression!E5*PctChange!<HDAN_col>{last_pct_row} + Regression!F5*PctChange!<PPAN_col>{last_pct_row}"
    ws["D2"] = "=B2*(1+C2)"

    ws["A3"] = "PPAN"
    ws["B3"] = f"=Input!C{last_input_row}"
    ws["C3"] = f"=Regression!D6 + Regression!E6*PctChange!<HDAN_col>{last_pct_row} + Regression!F6*PctChange!<PPAN_col>{last_pct_row}"
    ws["D3"] = "=B3*(1+C3)"

    ws["A4"] = "Diesel_USD_ton"
    ws["B4"] = f"=Input!I{last_input_row}"
    ws["C4"] = f"=Regression!D3 + Regression!E3*PctChange!<Brent_col>{last_pct_row-1}"  # lag2 from forecast point
    ws["D4"] = "=B4*(1+C4)"

    ws["A5"] = "FX_rate"
    ws["B5"] = f"=Input!K{last_input_row}"
    ws["C5"] = f"=Regression!D2 + Regression!E2*PctChange!<FX_col>{last_pct_row}"
    ws["D5"] = "=B5*(1+C5)"

    ws["A6"] = "Diesel_MNT (purchasing price)"
    ws["B6"] = ""
    ws["C6"] = ""
    ws["D6"] = "=D4*D5*(1+Input!N2)"  # N2 = Markup_% cell from Task 2
    return ws
```

*(`<HDAN_col>` etc. placeholders — implementer substitutes the actual column letters from
`PCTCHANGE_COLS.index(...)`, same pattern as Tasks 4-5. The LINEST spill layout from Task 5
needs confirming in the recalculated file before wiring `E5`/`F5`/`E6`/`F6` — LINEST with 2
predictors + const spills as `{a1, a2, c}` left-to-right, so column D=a1 (HDAN_{t-1} coefficient
if that's the first x-column), E=a2 (PPAN_{t-1}), F=c. Verify this against Task 5's output before
finalizing these references.)*

**Step 2: Run, recalculate, and verify**

```bash
python3 scripts/build_workbook.py
soffice --headless --convert-to xlsx --outdir /tmp/recalc AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('/tmp/recalc/AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx', data_only=True)
ws = wb['Forecast']
for row in ws.iter_rows(min_row=1, max_row=6, values_only=True):
    print(row)
"
```

Expected: all five forecast values (`D2:D6`) are real numbers in a plausible range (within, say,
20-30% of the last actual — a sanity bound, not an exact target), no `#REF!`/`#VALUE!`/`#NAME?`.
Cross-check `D2` (HDAN forecast) manually: `B2 * (1 + C2)` should equal `D2` to rounding.

**Step 3: Checkpoint** — no commit; proceed to Task 7.

---

### Task 7: Write standalone README.md

**Files:**
- Create: `README_forecast_model.md` (or update the existing `README.md` — confirm with user
  which, since a `README.md` already exists describing the *planned* workbook; this task should
  reconcile that file to describe the *actual* built workbook, not create a second one)

**Step 1: Rewrite the existing `README.md`'s methodology section to match what was actually
built** — reuse the equation/provenance content already validated in
`docs/plans/2026-08-20-forecast-workbook-design.md` §6, adjusted to reference actual cell
locations in the finished workbook (e.g. "Regression!D5" for the HDAN VAR coefficients) so a
reader can find and verify every number.

**Step 2: Read it back and sanity-check** it renders correctly and every cell reference it
claims actually exists in the built file (spot-check 2-3 references against the workbook opened
in Task 6's verification step).

**Step 3: Checkpoint** — no commit (no git repo); this is the final task.

---

## Notes for the implementer

- **No git repository exists** in this project directory — skip all `git add`/`git commit`
  steps from the generic plan template; checkpoint by re-running `build_workbook.py` and the
  LibreOffice-recalc-and-inspect pattern shown in each task instead.
- **Close the workbook in Excel before running the build script** if it's ever been opened
  there — README.md already documents this hazard (an open Excel session can silently overwrite
  script changes on save).
- Tasks 4-6 involve LINEST array-formula spill behavior that is easiest to get wrong sight
  unseen — after writing each, always recalculate with LibreOffice and read back `data_only=True`
  rather than trusting the formula text alone.
