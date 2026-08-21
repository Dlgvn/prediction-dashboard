import csv
from collections import defaultdict
from datetime import datetime

AN_COLS = ["PPAN", "HDAN", "Baltic_AN", "Ammonia", "Urea", "Natural_Gas", "Brent"]

def _num(s):
    """Both CSVs have comma-formatted numeric strings like ' 1,760.33 '.
    Some cells are blank -> return None."""
    s = s.replace(",", "").strip()
    return float(s) if s else None

def parse_an_data(path="AN Data.csv"):
    """AN Data.csv is weekly. Returns {(year, month): {col: avg_value}}."""
    monthly = defaultdict(lambda: defaultdict(list))
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Date"):
                continue
            year, month = int(row["Year"]), int(row[" Month "])
            monthly[(year, month)]["PPAN"].append(_num(row[" PPAN "]))
            monthly[(year, month)]["HDAN"].append(_num(row[" HDAN "]))
            monthly[(year, month)]["Baltic_AN"].append(_num(row[" Baltic AN "]))
            monthly[(year, month)]["Ammonia"].append(_num(row[" Ammonia "]))
            monthly[(year, month)]["Urea"].append(_num(row[" Urea "]))
            monthly[(year, month)]["Natural_Gas"].append(_num(row[" Natural_gas "]))
            monthly[(year, month)]["Brent"].append(_num(row["  Brent  "]))
    return {
        ym: {col: sum(vals) / len(vals) for col, vals in cols.items()}
        for ym, cols in monthly.items()
    }

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

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.formula import ArrayFormula

INPUT_COLS = ["Date", "HDAN", "PPAN", "Baltic_AN", "Ammonia", "Urea", "Natural_Gas", "Brent",
              "Diesel_USD_ton", "Urals", "FX_rate"]

PCTCHANGE_COLS = INPUT_COLS[1:]  # everything except Date

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

def write_pctchange_tab(wb, n_rows):
    """For each numeric Input column, write live month-over-month % change formulas.
    Row 2 (first data row) has no prior month, so it's left blank in the numeric columns."""
    ws = wb.create_sheet("PctChange")
    ws.cell(row=1, column=1, value="Date")
    for c, name in enumerate(PCTCHANGE_COLS, start=2):
        ws.cell(row=1, column=c, value=name)
    for r in range(2, n_rows + 2):
        ws.cell(row=r, column=1, value=f"=Input!A{r}")
        for c, name in enumerate(PCTCHANGE_COLS, start=2):
            col_letter = get_column_letter(c)
            if r == 2:
                continue  # no prior month for the first data row
            ws.cell(row=r, column=c,
                     value=f'=IFERROR((Input!{col_letter}{r}-Input!{col_letter}{r-1})/Input!{col_letter}{r-1}, "")')
    return ws

def write_regression_tab(wb, rows):
    """Single-predictor LINEST models for FX (AR1) and Diesel-USD (Brent lag2).

    Row bounds are derived empirically from `rows` (the merged monthly data) rather than
    assumed, because PctChange row availability differs per column:
      - FX_rate and Diesel_USD_ton are both populated Input!row 2..(n+1) except the very last
        row (2026-07), which is blank for both (AN/Brent data extends one month further than
        the FX/Diesel source). So the last usable PctChange row for both is n (not n+1).
      - Brent (AN data) doesn't start until partway through the series (2022-08), so
        PctChange!Brent is only non-blank from row 33 onward (first row with both current and
        prior-month Brent present).
    """
    ws = wb.create_sheet("Regression")
    pc = "PctChange"
    n_rows = len(rows)
    last_row = n_rows + 1  # PctChange data rows are 2..last_row

    fx_col = get_column_letter(2 + PCTCHANGE_COLS.index("FX_rate"))
    diesel_col = get_column_letter(2 + PCTCHANGE_COLS.index("Diesel_USD_ton"))
    brent_col = get_column_letter(2 + PCTCHANGE_COLS.index("Brent"))

    # FX_rate and Diesel_USD_ton are blank on the last Input row (2026-07 has no FX/Diesel
    # source data yet, only AN data extends that far) -> last usable row is last_row - 1.
    fx_last_valid = last_row - 1 if rows[-1]["FX_rate"] is None else last_row
    diesel_last_valid = last_row - 1 if rows[-1]["Diesel_USD_ton"] is None else last_row

    # First PctChange row where Brent is non-blank (needs current AND prior month non-blank).
    brent_first_valid = None
    for r in range(2, last_row + 1):
        cur = rows[r - 2]["Brent"]
        prev = rows[r - 3]["Brent"] if r - 3 >= 0 else None
        if cur is not None and prev is not None:
            brent_first_valid = r
            break

    ws["A1"] = "Model"
    ws["B1"] = "coef1 (slope)"
    ws["C1"] = "coef2 (intercept)"

    # --- Model 1: FX (AR1) -- y = FX_t, x = FX_{t-1} ---
    ws["A2"] = "FX (AR1)"
    fx_y_first, fx_y_last = 4, fx_last_valid
    fx_x_first, fx_x_last = fx_y_first - 1, fx_y_last - 1
    fx_formula = (f"=LINEST({pc}!{fx_col}{fx_y_first}:{fx_col}{fx_y_last},"
                  f"{pc}!{fx_col}{fx_x_first}:{fx_col}{fx_x_last})")
    ws["D2"] = ArrayFormula("D2:E2", fx_formula)

    # --- Model 2: Diesel-USD (Brent lag2) -- y = Diesel_t, x = Brent_{t-2} ---
    # y and x ranges must both be non-blank over the same window: x (Brent) is only valid
    # from brent_first_valid onward, so y must start 2 rows later (brent_first_valid + 2);
    # y and x both end at diesel_last_valid / diesel_last_valid - 2.
    ws["A3"] = "Diesel-USD (Brent lag2)"
    diesel_y_first = brent_first_valid + 2
    diesel_y_last = diesel_last_valid
    diesel_x_first = diesel_y_first - 2
    diesel_x_last = diesel_y_last - 2
    diesel_formula = (f"=LINEST({pc}!{diesel_col}{diesel_y_first}:{diesel_col}{diesel_y_last},"
                      f"{pc}!{brent_col}{diesel_x_first}:{brent_col}{diesel_x_last})")
    ws["D3"] = ArrayFormula("D3:E3", diesel_formula)

    # --- Model 3 & 4: VAR(1) for HDAN and PPAN ---
    # ΔHDAN_t = c1 + a11*ΔHDAN_{t-1} + a12*ΔPPAN_{t-1}
    # ΔPPAN_t = c2 + a21*ΔHDAN_{t-1} + a22*ΔPPAN_{t-1}
    # LINEST with 2 predictors needs a contiguous 2-column x-range, so we build helper columns
    # J (ΔHDAN_{t-1}) and K (ΔPPAN_{t-1}) on the Regression sheet itself, placed well clear of
    # the D:F LINEST spill targets used above/below, starting at row 10 to leave room.
    hdan_col = get_column_letter(2 + PCTCHANGE_COLS.index("HDAN"))
    ppan_col = get_column_letter(2 + PCTCHANGE_COLS.index("PPAN"))

    # First index in `rows` where HDAN (equivalently PPAN, same AN-sourced availability) is
    # non-blank -- computed empirically from the data, not assumed to match Brent's row 33.
    hdan_first_idx = next(i for i, r in enumerate(rows) if r["HDAN"] is not None)
    # PctChange sheet row numbering: rows[] index i -> PctChange row i+2.
    hdan_first_pct_row = hdan_first_idx + 2  # first row where PctChange!HDAN (& PPAN) itself is populated

    # A VAR predictor needs ΔHDAN_{t-1} and ΔPPAN_{t-1} both non-blank, i.e. the *prior* row's
    # % change must already exist. PctChange row 2 is always blank (Task 3), and the first row
    # with a real % change is hdan_first_pct_row + 1 (needs current AND prior month HDAN/PPAN
    # non-blank). So the earliest usable predictor row is (hdan_first_pct_row + 1) + 1, and
    # y_start (the dependent-variable row) must be one row after that.
    first_pctchange_with_value = hdan_first_pct_row + 1
    var_y_start = first_pctchange_with_value + 1
    # y and x both end at the last row where HDAN/PPAN data exists in PctChange, i.e. the last
    # merged row (HDAN/PPAN run through the end of `rows`, confirmed empirically below).
    hdan_last_idx = max(i for i, r in enumerate(rows) if r["HDAN"] is not None)
    var_y_end = hdan_last_idx + 2  # PctChange row for the last non-blank HDAN/PPAN month

    helper_start_row = 10
    n_var_rows = var_y_end - var_y_start + 1
    for i in range(n_var_rows):
        y_row = var_y_start + i
        x_row = y_row - 1
        ws.cell(row=helper_start_row + i, column=10, value=f"={pc}!{hdan_col}{x_row}")  # J
        ws.cell(row=helper_start_row + i, column=11, value=f"={pc}!{ppan_col}{x_row}")  # K
    helper_last_row = helper_start_row + n_var_rows - 1

    ws["A5"] = "VAR: HDAN eq (a11, a12, c1)"
    hdan_var_formula = (f"=LINEST({pc}!{hdan_col}{var_y_start}:{hdan_col}{var_y_end},"
                        f"J{helper_start_row}:K{helper_last_row})")
    ws["D5"] = ArrayFormula("D5:F5", hdan_var_formula)

    ws["A6"] = "VAR: PPAN eq (a21, a22, c2)"
    ppan_var_formula = (f"=LINEST({pc}!{ppan_col}{var_y_start}:{ppan_col}{var_y_end},"
                        f"J{helper_start_row}:K{helper_last_row})")
    ws["D6"] = ArrayFormula("D6:F6", ppan_var_formula)

    return ws


def write_forecast_tab(wb, rows):
    """Next-month roll-forward forecast for HDAN, PPAN, Diesel_USD_ton, FX_rate, and the
    derived Diesel_MNT purchasing price.

    Row/lag arithmetic:
      - n_rows = len(rows); Input/PctChange data rows are 2..(n_rows+1).
      - HDAN/PPAN (AN-sourced) are valid through the last row (n_rows+1 = 79), so the last
        actual is Input!B79/C79 and the lag-1 VAR predictor uses PctChange row 79 (the most
        recent HDAN/PPAN % change) to forecast the row *after* it.
      - Diesel_USD_ton and FX_rate (Diesel-CSV-sourced) are blank on the last Input row
        (2026-07 has no Diesel/FX source data yet), so their last valid row is n_rows
        (=78), not n_rows+1.
      - FX AR1 predictor: forecast uses the last valid PctChange!FX_rate row (78) as x,
        since the model is y_t = c + phi*y_{t-1} and we want y at row 79 (one past the
        last valid actual).
      - Diesel Brent-lag2 predictor: the fitted model regressed y=PctChange!Diesel over
        x=PctChange!Brent, with x lagged 2 rows behind y (x_row = y_row - 2), fitted over
        y in [diesel_first_valid_y .. diesel_last_valid] i.e. y_last=78, so x_last=76.
        To forecast Diesel for the row after diesel_last_valid (row 79), the required x
        row is 79-2=77, i.e. diesel_last_valid - 1 (78-1=77) -- one row past the x_last
        used in fitting (76), exactly the next available Brent-lag2 observation.
    """
    ws = wb.create_sheet("Forecast")
    n_rows = len(rows)
    last_row = n_rows + 1  # last Input/PctChange row overall (AN-sourced series valid here)

    fx_last_valid = last_row - 1 if rows[-1]["FX_rate"] is None else last_row
    diesel_last_valid = last_row - 1 if rows[-1]["Diesel_USD_ton"] is None else last_row

    hdan_input_col = get_column_letter(1 + INPUT_COLS.index("HDAN"))
    ppan_input_col = get_column_letter(1 + INPUT_COLS.index("PPAN"))
    diesel_input_col = get_column_letter(1 + INPUT_COLS.index("Diesel_USD_ton"))
    fx_input_col = get_column_letter(1 + INPUT_COLS.index("FX_rate"))
    markup_col = get_column_letter(len(INPUT_COLS) + 2)  # M (matches write_input_tab)

    hdan_pct_col = get_column_letter(2 + PCTCHANGE_COLS.index("HDAN"))
    ppan_pct_col = get_column_letter(2 + PCTCHANGE_COLS.index("PPAN"))
    brent_pct_col = get_column_letter(2 + PCTCHANGE_COLS.index("Brent"))
    fx_pct_col = get_column_letter(2 + PCTCHANGE_COLS.index("FX_rate"))

    var_lag_row = last_row  # PctChange row 79: most recent HDAN/PPAN % change (lag-1 predictor)
    fx_lag_row = fx_last_valid  # PctChange row 78: most recent FX % change
    diesel_lag_row = diesel_last_valid - 1  # PctChange row 77: Brent % change lagged 2 from target

    ws["A1"] = "Series"; ws["B1"] = "Last Actual"; ws["C1"] = "Predicted % Change"; ws["D1"] = "Forecast"

    ws["A2"] = "HDAN"
    ws["B2"] = f"=Input!{hdan_input_col}{last_row}"
    ws["C2"] = (f"=Regression!D5*PctChange!{hdan_pct_col}{var_lag_row}"
                f"+Regression!E5*PctChange!{ppan_pct_col}{var_lag_row}+Regression!F5")
    ws["D2"] = "=B2*(1+C2)"

    ws["A3"] = "PPAN"
    ws["B3"] = f"=Input!{ppan_input_col}{last_row}"
    ws["C3"] = (f"=Regression!D6*PctChange!{hdan_pct_col}{var_lag_row}"
                f"+Regression!E6*PctChange!{ppan_pct_col}{var_lag_row}+Regression!F6")
    ws["D3"] = "=B3*(1+C3)"

    ws["A4"] = "Diesel_USD_ton"
    ws["B4"] = f"=Input!{diesel_input_col}{diesel_last_valid}"
    ws["C4"] = f"=Regression!D3*PctChange!{brent_pct_col}{diesel_lag_row}+Regression!E3"
    ws["D4"] = "=B4*(1+C4)"

    ws["A5"] = "FX_rate"
    ws["B5"] = f"=Input!{fx_input_col}{fx_last_valid}"
    ws["C5"] = f"=Regression!D2*PctChange!{fx_pct_col}{fx_lag_row}+Regression!E2"
    ws["D5"] = "=B5*(1+C5)"

    ws["A6"] = "Diesel_MNT (purchasing price)"
    ws["B6"] = "—"
    ws["C6"] = "—"
    ws["D6"] = f"=D4*D5*(1+Input!{markup_col}2)"

    return ws


def write_dashboard_tab(wb, rows):
    """KPI-card dashboard summarizing current values, next-month forecasts, and static
    backtest-MAPE-based approximate ranges for each forecasted series.

    Reuses the exact same "last valid row" logic as write_forecast_tab (HDAN/PPAN valid
    through last_row = n_rows+1; Diesel_USD_ton/FX_rate valid only through last_row-1 since
    the 2026-07 Input row has no Diesel/FX source data yet) rather than recomputing it.
    """
    ws = wb.create_sheet("Dashboard")
    n_rows = len(rows)
    last_row = n_rows + 1

    fx_last_valid = last_row - 1 if rows[-1]["FX_rate"] is None else last_row
    diesel_last_valid = last_row - 1 if rows[-1]["Diesel_USD_ton"] is None else last_row

    hdan_input_col = get_column_letter(1 + INPUT_COLS.index("HDAN"))
    ppan_input_col = get_column_letter(1 + INPUT_COLS.index("PPAN"))
    diesel_input_col = get_column_letter(1 + INPUT_COLS.index("Diesel_USD_ton"))
    fx_input_col = get_column_letter(1 + INPUT_COLS.index("FX_rate"))
    markup_col = get_column_letter(len(INPUT_COLS) + 2)  # M (matches write_input_tab)

    ws["A1"] = "Product"
    ws["B1"] = "Current Value"
    ws["C1"] = "Next-Month Forecast"
    ws["D1"] = "95% Range (approx, ±MAPE)"
    ws["E1"] = "Backtest MAPE (static, from backend_research/REPORT.md)"
    ws["F1"] = "MAPE (decimal, static)"

    # Row 2: HDAN
    ws["A2"] = "HDAN"
    ws["B2"] = f"=Input!{hdan_input_col}{last_row}"
    ws["C2"] = "=Forecast!D2"
    ws["F2"] = 0.094
    ws["D2"] = '=TEXT(C2*(1-$F2),"#,##0.0")&" - "&TEXT(C2*(1+$F2),"#,##0.0")'
    ws["E2"] = "=F2"
    ws["E2"].number_format = "0.0%"

    # Row 3: PPAN
    ws["A3"] = "PPAN"
    ws["B3"] = f"=Input!{ppan_input_col}{last_row}"
    ws["C3"] = "=Forecast!D3"
    ws["F3"] = 0.100
    ws["D3"] = '=TEXT(C3*(1-$F3),"#,##0.0")&" - "&TEXT(C3*(1+$F3),"#,##0.0")'
    ws["E3"] = "=F3"
    ws["E3"].number_format = "0.0%"

    # Row 4: Diesel-USD
    ws["A4"] = "Diesel-USD"
    ws["B4"] = f"=Input!{diesel_input_col}{diesel_last_valid}"
    ws["C4"] = "=Forecast!D4"
    ws["F4"] = 0.034
    ws["D4"] = '=TEXT(C4*(1-$F4),"#,##0.0")&" - "&TEXT(C4*(1+$F4),"#,##0.0")'
    ws["E4"] = "=F4"
    ws["E4"].number_format = "0.0%"

    # Row 5: FX rate
    ws["A5"] = "FX rate"
    ws["B5"] = f"=Input!{fx_input_col}{fx_last_valid}"
    ws["C5"] = "=Forecast!D5"
    ws["F5"] = 0.0025
    ws["D5"] = '=TEXT(C5*(1-$F5),"#,##0.0")&" - "&TEXT(C5*(1+$F5),"#,##0.0")'
    ws["E5"] = "=F5"
    ws["E5"].number_format = "0.0%"

    # Row 6: Diesel-MNT (derived purchasing price) -- current value uses today's spot
    # Diesel-USD and FX actuals with the markup, NOT Forecast!D6 (that's next month, in C6).
    ws["A6"] = "Diesel-MNT (purchasing price)"
    ws["B6"] = (f"=Input!{diesel_input_col}{diesel_last_valid}*Input!{fx_input_col}{fx_last_valid}"
                f"*(1+Input!{markup_col}2)")
    ws["C6"] = "=Forecast!D6"
    ws["F6"] = 0.0925
    ws["D6"] = '=TEXT(C6*(1-$F6),"#,##0.0")&" - "&TEXT(C6*(1+$F6),"#,##0.0")'
    ws["E6"] = "=F6"
    ws["E6"].number_format = "0.0%"

    ws["A8"] = ("MAPE values are static, from the 12-month holdout backtest in "
                "backend_research/REPORT.md — they do not recalculate as Input grows. "
                "The range is an approximate ±MAPE band, not a calibrated statistical "
                "interval; see backend_research/REPORT.md's interval-calibration section "
                "for why even a proper analytic interval under-covers its stated 95% "
                "target on this data.")
    ws.merge_cells("A8:E8")
    ws["A8"].alignment = openpyxl.styles.Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[8].height = 60

    for col, width in zip("ABCDEF", [30, 16, 20, 26, 30, 18]):
        ws.column_dimensions[col].width = width

    return ws


if __name__ == "__main__":
    an = parse_an_data()
    diesel = parse_diesel_data()
    print(f"AN months: {len(an)}, range {min(an)} to {max(an)}")
    print(f"Diesel months: {len(diesel)}, range {min(diesel)} to {max(diesel)}")

    rows = merge_monthly(an, diesel)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    write_input_tab(wb, rows)
    write_pctchange_tab(wb, len(rows))
    write_regression_tab(wb, rows)
    write_forecast_tab(wb, rows)
    write_dashboard_tab(wb, rows)
    wb.save("AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx")
    print(f"Wrote {len(rows)} rows to Input tab")
