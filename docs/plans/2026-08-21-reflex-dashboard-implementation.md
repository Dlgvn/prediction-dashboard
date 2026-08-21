# Reflex Forecasting Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single-process Reflex web app (`app/`) that stores commodity/FX price
history in SQLite, lets the user enter/edit rows manually and export to Excel, and
forecasts HDAN, PPAN, Diesel-MNT, and USD/MNT out to a user-chosen horizon (1-12 months,
or N weeks) with base/bull/bear scenario lines on a chart.

**Architecture:** Reflex app with `rx.Model` (SQLModel/SQLite) for persistence, a
framework-independent `forecasting/` Python package for model research + inference
(unit-testable without Reflex running), and Reflex pages/state for the data table,
horizon picker, chart, and export button. See
`docs/plans/2026-08-21-reflex-dashboard-design.md` for the design this implements.

**Tech Stack:** Python 3.12, Reflex, SQLModel/SQLite, statsmodels, pandas, openpyxl,
pytest.

---

## Sequencing note

Tasks 1-3 set up the app skeleton and data layer — do these first, in order. Task 4
(model research) can happen in parallel with Tasks 1-3 since it only needs the seed CSVs,
not the running app, but it's listed after them because Task 5 (forecasting module)
depends on its output. Tasks 5-9 depend on both the data layer and the research findings.

---

### Task 1: Project skeleton and dependencies

**Files:**
- Create: `app/requirements.txt`
- Create: `app/rxconfig.py`
- Create: `app/app/__init__.py`
- Create: `app/app/app.py`
- Create: `app/.gitignore`

**Step 1: Create the app directory and a virtualenv**

```bash
mkdir -p "/Users/dlgvnbyr/Desktop/Prediction Dashboard/app"
cd "/Users/dlgvnbyr/Desktop/Prediction Dashboard/app"
python3 -m venv .venv
source .venv/bin/activate
```

**Step 2: Write `requirements.txt`**

```
reflex>=0.6
pandas
statsmodels
openpyxl
scikit-learn
pytest
```

**Step 3: Install and verify**

Run: `pip install -r requirements.txt`
Expected: installs cleanly, no errors.

**Step 4: Scaffold the Reflex app**

Run: `reflex init --template blank`
Expected: creates `rxconfig.py`, `app/app.py`, `assets/`, etc. inside `app/`.

**Step 5: Verify it runs**

Run: `reflex run` (from `app/`), then check `http://localhost:3000` loads a blank page.
Expected: page loads without errors. Stop the server (Ctrl-C) once confirmed.

**Step 6: Add app-specific `.gitignore`**

```
.web/
*.db
__pycache__/
.venv/
```

**Step 7: Commit**

```bash
cd "/Users/dlgvnbyr/Desktop/Prediction Dashboard"
git add app/requirements.txt app/rxconfig.py app/app/__init__.py app/app/app.py app/.gitignore
git commit -m "chore: scaffold Reflex app skeleton"
```

---

### Task 2: Database model for price history

**Files:**
- Create: `app/app/models.py`
- Test: `app/tests/test_models.py`

**Step 1: Write the failing test**

```python
# app/tests/test_models.py
import reflex as rx
from app.models import PriceRow

def test_price_row_has_expected_fields():
    row = PriceRow(
        date="2026-07-01",
        hdan=459.24,
        ppan=463.56,
        baltic_an=392.50,
        ammonia=770.00,
        urea=362.00,
        natural_gas=3.24,
        brent=76.00,
        diesel_usd_ton=None,
        urals=None,
        fx_rate=None,
    )
    assert row.hdan == 459.24
    assert row.date == "2026-07-01"
```

**Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`

**Step 3: Write minimal implementation**

```python
# app/app/models.py
from typing import Optional
import reflex as rx

class PriceRow(rx.Model, table=True):
    date: str
    hdan: Optional[float] = None
    ppan: Optional[float] = None
    baltic_an: Optional[float] = None
    ammonia: Optional[float] = None
    urea: Optional[float] = None
    natural_gas: Optional[float] = None
    brent: Optional[float] = None
    diesel_usd_ton: Optional[float] = None
    urals: Optional[float] = None
    fx_rate: Optional[float] = None
    markup_pct: Optional[float] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/app/models.py app/tests/test_models.py
git commit -m "feat: add PriceRow database model"
```

---

### Task 3: One-time seed script from the three source CSVs

This loads `AN price weekly.csv`, `AN Data.csv`, and `Diesel Data.csv` into the
`PriceRow` table once, so both the model-research task and the running app start with
real history instead of an empty table.

**Files:**
- Create: `app/app/seed.py`
- Test: `app/tests/test_seed.py`

**Step 1: Write the failing test**

Use small inline fixture CSVs (not the real files) so the test is fast and doesn't
depend on file layout changing.

```python
# app/tests/test_seed.py
import pandas as pd
from app.seed import parse_an_data, parse_diesel_data

def test_parse_an_data_strips_whitespace_and_types_floats(tmp_path):
    csv = tmp_path / "an.csv"
    csv.write_text(
        "Date,Year, Month , PPAN , HDAN , Baltic AN , Ammonia , Urea , Natural_gas ,  Brent  ,\n"
        "7/10/2026,2026,7, 463.56 , 459.24 , 392.50 , 770.00 , 362.00 , 3.24 , 76.00 ,\n"
    )
    df = parse_an_data(csv)
    assert df.iloc[0]["hdan"] == 459.24
    assert df.iloc[0]["ppan"] == 463.56
    assert str(df.iloc[0]["date"]) == "2026-07-10"

def test_parse_diesel_data_strips_commas_and_quotes(tmp_path):
    csv = tmp_path / "diesel.csv"
    csv.write_text(
        "Date,FX_rate,Import_Volume_Price_per_ton_USD\n"
        '2020-02," 2,756.95 "," 638.50 "\n'
    )
    df = parse_diesel_data(csv)
    assert df.iloc[0]["fx_rate"] == 2756.95
    assert df.iloc[0]["diesel_usd_ton"] == 638.50
```

**Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_seed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.seed'`

**Step 3: Write minimal implementation**

```python
# app/app/seed.py
import pandas as pd
import reflex as rx
from app.models import PriceRow

def _clean_numeric(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"": None, "nan": None})
        .astype(float)
    )

def parse_an_data(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df["Date"]).dt.date.astype(str)
    out["hdan"] = _clean_numeric(df["HDAN"])
    out["ppan"] = _clean_numeric(df["PPAN"])
    out["baltic_an"] = _clean_numeric(df["Baltic AN"])
    out["ammonia"] = _clean_numeric(df["Ammonia"])
    out["urea"] = _clean_numeric(df["Urea"])
    out["natural_gas"] = _clean_numeric(df["Natural_gas"])
    out["brent"] = _clean_numeric(df["Brent"])
    return out

def parse_diesel_data(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = pd.DataFrame()
    out["date"] = df["Date"].astype(str)
    out["fx_rate"] = _clean_numeric(df["FX_rate"])
    out["diesel_usd_ton"] = _clean_numeric(df["Import_Volume_Price_per_ton_USD"])
    if "URALS_Crude _Oil_(USD/BBL)" in df.columns:
        out["urals"] = _clean_numeric(df["URALS_Crude _Oil_(USD/BBL)"])
    return out

def seed_database(an_data_path, diesel_data_path):
    """Merge AN + Diesel data by month (date rounded to month start) and upsert into PriceRow."""
    an_df = parse_an_data(an_data_path)
    diesel_df = parse_diesel_data(diesel_data_path)
    an_df["month"] = pd.to_datetime(an_df["date"]).dt.to_period("M")
    diesel_df["month"] = pd.to_datetime(diesel_df["date"]).dt.to_period("M")
    an_monthly = an_df.groupby("month").last().reset_index()
    diesel_monthly = diesel_df.groupby("month").last().reset_index()
    merged = pd.merge(an_monthly, diesel_monthly, on="month", how="outer")
    merged["date"] = merged["month"].dt.start_time.dt.date.astype(str)

    with rx.session() as session:
        for _, row in merged.iterrows():
            session.add(PriceRow(
                date=row["date"],
                hdan=row.get("hdan"),
                ppan=row.get("ppan"),
                baltic_an=row.get("baltic_an"),
                ammonia=row.get("ammonia"),
                urea=row.get("urea"),
                natural_gas=row.get("natural_gas"),
                brent=row.get("brent"),
                diesel_usd_ton=row.get("diesel_usd_ton"),
                urals=row.get("urals"),
                fx_rate=row.get("fx_rate"),
            ))
        session.commit()

if __name__ == "__main__":
    import sys
    seed_database(sys.argv[1], sys.argv[2])
```

Note: `AN price weekly.csv` doesn't map cleanly onto the monthly `PriceRow` schema (see
design doc §6) — it's used directly by the model-research task (Task 4) rather than
merged into this monthly seed table. Don't try to force it into `parse_an_data`.

**Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_seed.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/app/seed.py app/tests/test_seed.py
git commit -m "feat: add seed script to import AN/Diesel CSVs into PriceRow"
```

**Step 6: Run the real seed against production CSVs (manual, one-time)**

```bash
cd "/Users/dlgvnbyr/Desktop/Prediction Dashboard/app"
python -m app.seed "../AN Data.csv" "../Diesel Data.csv"
```

Expected: no errors; inspect `reflex.db` with `sqlite3` to confirm rows were inserted.
Do not commit the resulting `.db` file (already gitignored).

---

### Task 4: Model research — pick per-product forecasting models

This repeats the `backend_research/` pattern: try candidate models per product, backtest
on holdout months, record results. This is exploratory and doesn't follow strict TDD —
write scripts, run them, record findings in a report, same shape as the existing
`backend_research/` scripts.

**Files:**
- Create: `app/research/` (new directory, separate from the shipped `app/app/` package)
- Create: `app/research/candidates.py` — fits ARIMA, SARIMAX, VAR (statsmodels) and a
  gradient-boosting baseline (scikit-learn) per product
- Create: `app/research/backtest.py` — holdout backtest harness (reuse the approach in
  `backend_research/model_harness.py` as a reference, don't copy blindly since data
  shape differs)
- Create: `app/research/weekly_gap_analysis.py` — tests whether Baltic AN is a usable
  proxy for HDAN/PPAN at weekly resolution (design doc §6); if no defensible relationship
  is found, weekly mode ships monthly-only for HDAN/PPAN/Diesel/FX in Task 5
- Create: `app/research/REPORT.md` — findings: winning model per product, MAPE per
  candidate, weekly-mode decision

**Step 1: Run candidate models per product against seeded data, record MAPE**

No fixed code here — this is genuinely exploratory. Use `backend_research/` scripts as a
starting reference for structure (data loading, train/holdout split, MAPE calc) but expect
to write new fitting code since the data now lives in SQLite, not the two raw CSVs.

**Step 2: Resolve the weekly-mode question**

Test correlation/Granger-causality between weekly Baltic AN and monthly HDAN/PPAN
(aggregated or interpolated). Write the decision and reasoning into `REPORT.md` — this
is a real finding, not a formality; if the proxy doesn't hold up, say so and scope weekly
mode down (per design doc §6 option (b)).

**Step 3: Write `REPORT.md` summarizing winners**

Format: one section per product (HDAN, PPAN, Diesel-USD, FX), each with the models
tried, holdout MAPE for each, and which one wins. Include the weekly-mode decision as its
own section.

**Step 4: Commit**

```bash
git add app/research/
git commit -m "research: backtest forecasting model candidates per product"
```

---

### Task 5: Forecasting module (uses Task 4's winning models)

**Files:**
- Create: `app/app/forecasting.py`
- Test: `app/tests/test_forecasting.py`

**Step 1: Write the failing test**

Use a small synthetic series so the test doesn't depend on the research winners' exact
coefficients (those come from real data and will drift as more months are added).

```python
# app/tests/test_forecasting.py
from app.forecasting import forecast_series

def test_forecast_series_returns_base_bull_bear_for_each_horizon_step():
    history = [100.0, 102.0, 101.0, 105.0, 107.0, 106.0, 110.0, 112.0]
    result = forecast_series(history, horizon=3)
    assert len(result) == 3
    for point in result:
        assert set(point.keys()) == {"period", "base", "bull", "bear"}
        assert point["bear"] <= point["base"] <= point["bull"]
```

**Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_forecasting.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.forecasting'`

**Step 3: Write minimal implementation**

Implement `forecast_series` using whichever model Task 4's `REPORT.md` names as the
per-series winner (fill in the exact model call once Task 4 is done — e.g. statsmodels
`SARIMAX` or `VAR`, fit on the passed-in history), with bull/bear = base ± the winning
model's backtest MAPE (design doc §5, v1 statistical band). Keep this function
model-family-agnostic in its signature (`history: list[float], horizon: int -> list[dict]`)
so swapping the underlying model later doesn't touch callers.

```python
# app/app/forecasting.py
from typing import TypedDict
import numpy as np

class ForecastPoint(TypedDict):
    period: int
    base: float
    bull: float
    bear: float

def forecast_series(history: list[float], horizon: int, mape: float = 0.05) -> list[ForecastPoint]:
    # Placeholder momentum model until Task 4's winner is filled in here.
    pct_changes = np.diff(history) / np.array(history[:-1])
    drift = float(np.mean(pct_changes))
    points = []
    last = history[-1]
    for i in range(1, horizon + 1):
        last = last * (1 + drift)
        points.append({
            "period": i,
            "base": round(last, 2),
            "bull": round(last * (1 + mape), 2),
            "bear": round(last * (1 - mape), 2),
        })
    return points
```

**Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_forecasting.py -v`
Expected: PASS

**Step 5: Replace the placeholder with Task 4's actual winning model(s) per product**

Once `app/research/REPORT.md` names winners, update `forecast_series` (or split into
per-product functions if different products need different model classes) and re-run the
test plus a manual sanity check against real seeded data.

**Step 6: Commit**

```bash
git add app/app/forecasting.py app/tests/test_forecasting.py
git commit -m "feat: add forecasting module with base/bull/bear scenario output"
```

---

### Task 6: Diesel-MNT derived forecast

**Files:**
- Modify: `app/app/forecasting.py`
- Test: `app/tests/test_forecasting.py`

**Step 1: Write the failing test**

```python
def test_diesel_mnt_is_diesel_usd_times_fx_times_markup():
    from app.forecasting import diesel_mnt_forecast
    diesel_usd = {"period": 1, "base": 650.0, "bull": 680.0, "bear": 620.0}
    fx = {"period": 1, "base": 2800.0, "bull": 2850.0, "bear": 2750.0}
    result = diesel_mnt_forecast(diesel_usd, fx, markup_pct=0.0282)
    expected_base = 650.0 * 2800.0 * 1.0282
    assert abs(result["base"] - expected_base) < 0.01
```

**Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_forecasting.py -v`
Expected: FAIL with `ImportError: cannot import name 'diesel_mnt_forecast'`

**Step 3: Write minimal implementation**

```python
# app/app/forecasting.py (append)
def diesel_mnt_forecast(diesel_usd: ForecastPoint, fx: ForecastPoint, markup_pct: float) -> ForecastPoint:
    return {
        "period": diesel_usd["period"],
        "base": diesel_usd["base"] * fx["base"] * (1 + markup_pct),
        "bull": diesel_usd["bull"] * fx["bull"] * (1 + markup_pct),
        "bear": diesel_usd["bear"] * fx["bear"] * (1 + markup_pct),
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_forecasting.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/app/forecasting.py app/tests/test_forecasting.py
git commit -m "feat: derive Diesel-MNT forecast from Diesel-USD, FX, and markup"
```

---

### Task 7: Reflex state — data table (view, add, edit rows)

**Files:**
- Create: `app/app/state.py`
- Test: `app/tests/test_state.py`

**Step 1: Write the failing test**

```python
# app/tests/test_state.py
import reflex as rx
from app.state import DashboardState
from app.models import PriceRow

def test_add_row_persists_to_database():
    state = DashboardState()
    state.new_row_date = "2026-08-01"
    state.new_row_hdan = "450.0"
    state.add_row()
    with rx.session() as session:
        row = session.exec(
            PriceRow.select().where(PriceRow.date == "2026-08-01")
        ).first()
        assert row is not None
        assert row.hdan == 450.0
```

**Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.state'`

**Step 3: Write minimal implementation**

```python
# app/app/state.py
import reflex as rx
from app.models import PriceRow

class DashboardState(rx.State):
    rows: list[PriceRow] = []
    new_row_date: str = ""
    new_row_hdan: str = ""
    new_row_ppan: str = ""
    new_row_fx_rate: str = ""
    new_row_diesel_usd_ton: str = ""

    def load_rows(self):
        with rx.session() as session:
            self.rows = session.exec(PriceRow.select().order_by(PriceRow.date)).all()

    def add_row(self):
        with rx.session() as session:
            session.add(PriceRow(
                date=self.new_row_date,
                hdan=float(self.new_row_hdan) if self.new_row_hdan else None,
                ppan=float(self.new_row_ppan) if self.new_row_ppan else None,
                fx_rate=float(self.new_row_fx_rate) if self.new_row_fx_rate else None,
                diesel_usd_ton=float(self.new_row_diesel_usd_ton) if self.new_row_diesel_usd_ton else None,
            ))
            session.commit()
        self.new_row_date = ""
        self.new_row_hdan = ""
        self.new_row_ppan = ""
        self.new_row_fx_rate = ""
        self.new_row_diesel_usd_ton = ""
        self.load_rows()
```

**Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_state.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/app/state.py app/tests/test_state.py
git commit -m "feat: add DashboardState with row load/add"
```

---

### Task 8: Reflex state — forecast + export

**Files:**
- Modify: `app/app/state.py`
- Test: `app/tests/test_state.py`

**Step 1: Write the failing test**

```python
def test_run_forecast_populates_forecast_results():
    state = DashboardState()
    state.horizon_months = 3
    state.rows = [
        PriceRow(date=f"2026-0{i}-01", hdan=450 + i, ppan=460 + i, fx_rate=2800 + i, diesel_usd_ton=650 + i)
        for i in range(1, 6)
    ]
    state.run_forecast()
    assert len(state.forecast_results["hdan"]) == 3
    assert "base" in state.forecast_results["hdan"][0]

def test_export_to_excel_writes_file(tmp_path):
    state = DashboardState()
    state.rows = [PriceRow(date="2026-08-01", hdan=450.0)]
    path = tmp_path / "export.xlsx"
    state.export_to_excel(str(path))
    assert path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest app/tests/test_state.py -v`
Expected: FAIL — `run_forecast`/`export_to_excel`/`forecast_results`/`horizon_months`
don't exist yet.

**Step 3: Write minimal implementation**

```python
# app/app/state.py (append to DashboardState)
import pandas as pd
from app.forecasting import forecast_series, diesel_mnt_forecast

class DashboardState(rx.State):
    # ...(existing fields)...
    horizon_months: int = 1
    forecast_results: dict = {}

    def run_forecast(self):
        hdan_hist = [r.hdan for r in self.rows if r.hdan is not None]
        ppan_hist = [r.ppan for r in self.rows if r.ppan is not None]
        fx_hist = [r.fx_rate for r in self.rows if r.fx_rate is not None]
        diesel_hist = [r.diesel_usd_ton for r in self.rows if r.diesel_usd_ton is not None]

        hdan_fc = forecast_series(hdan_hist, self.horizon_months)
        ppan_fc = forecast_series(ppan_hist, self.horizon_months)
        fx_fc = forecast_series(fx_hist, self.horizon_months)
        diesel_fc = forecast_series(diesel_hist, self.horizon_months)
        markup = next((r.markup_pct for r in reversed(self.rows) if r.markup_pct), 0.0282)
        diesel_mnt_fc = [
            diesel_mnt_forecast(d, f, markup) for d, f in zip(diesel_fc, fx_fc)
        ]

        self.forecast_results = {
            "hdan": hdan_fc,
            "ppan": ppan_fc,
            "fx_rate": fx_fc,
            "diesel_usd": diesel_fc,
            "diesel_mnt": diesel_mnt_fc,
        }

    def export_to_excel(self, path: str = "export.xlsx"):
        df = pd.DataFrame([r.dict() for r in self.rows])
        df.to_excel(path, index=False)
```

**Step 4: Run test to verify it passes**

Run: `pytest app/tests/test_state.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/app/state.py app/tests/test_state.py
git commit -m "feat: add forecast run and Excel export to DashboardState"
```

---

### Task 9: Dashboard UI — table, horizon picker, chart, export button

**Files:**
- Modify: `app/app/app.py`

**Step 1: Build the page**

```python
# app/app/app.py
import reflex as rx
from app.state import DashboardState

def data_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Date"),
                rx.table.column_header_cell("HDAN"),
                rx.table.column_header_cell("PPAN"),
                rx.table.column_header_cell("FX Rate"),
                rx.table.column_header_cell("Diesel USD/ton"),
            )
        ),
        rx.table.body(
            rx.foreach(
                DashboardState.rows,
                lambda row: rx.table.row(
                    rx.table.cell(row.date),
                    rx.table.cell(row.hdan),
                    rx.table.cell(row.ppan),
                    rx.table.cell(row.fx_rate),
                    rx.table.cell(row.diesel_usd_ton),
                ),
            )
        ),
    )

def add_row_form() -> rx.Component:
    return rx.hstack(
        rx.input(placeholder="YYYY-MM-DD", value=DashboardState.new_row_date, on_change=DashboardState.set_new_row_date),
        rx.input(placeholder="HDAN", value=DashboardState.new_row_hdan, on_change=DashboardState.set_new_row_hdan),
        rx.input(placeholder="PPAN", value=DashboardState.new_row_ppan, on_change=DashboardState.set_new_row_ppan),
        rx.input(placeholder="FX rate", value=DashboardState.new_row_fx_rate, on_change=DashboardState.set_new_row_fx_rate),
        rx.input(placeholder="Diesel USD/ton", value=DashboardState.new_row_diesel_usd_ton, on_change=DashboardState.set_new_row_diesel_usd_ton),
        rx.button("Add row", on_click=DashboardState.add_row),
    )

def forecast_chart() -> rx.Component:
    return rx.recharts.line_chart(
        rx.recharts.line(data_key="base", stroke="#333"),
        rx.recharts.line(data_key="bull", stroke="green"),
        rx.recharts.line(data_key="bear", stroke="red"),
        rx.recharts.x_axis(data_key="period"),
        rx.recharts.y_axis(),
        data=DashboardState.forecast_results["hdan"],
        width=600,
        height=300,
    )

def index() -> rx.Component:
    return rx.vstack(
        rx.heading("Price Forecasting Dashboard"),
        add_row_form(),
        data_table(),
        rx.hstack(
            rx.input(
                type="number", min=1, max=12,
                value=DashboardState.horizon_months,
                on_change=DashboardState.set_horizon_months,
            ),
            rx.button("Forecast", on_click=DashboardState.run_forecast),
            rx.button("Export to Excel", on_click=DashboardState.export_to_excel),
        ),
        forecast_chart(),
        on_mount=DashboardState.load_rows,
    )

app = rx.App()
app.add_page(index)
```

**Step 2: Run the app and manually verify**

Run: `reflex run` (from `app/`)
Expected: page loads at `localhost:3000`; adding a row via the form appears in the table
after refresh; clicking "Forecast" populates the chart; clicking "Export to Excel"
produces a file.

**Step 3: Commit**

```bash
git add app/app/app.py
git commit -m "feat: build dashboard UI with table, horizon picker, chart, export"
```

---

### Task 10: End-to-end manual verification

**Step 1:** Start the app (`reflex run` from `app/`), open it in the browser tool.

**Step 2:** Add 6+ rows of realistic data (or confirm the seeded rows from Task 3 show up).

**Step 3:** Set horizon to 3, click Forecast, confirm the chart shows three lines
(base/bull/bear) and bear ≤ base ≤ bull at each point.

**Step 4:** Click Export to Excel, confirm the file opens and matches the table.

**Step 5:** Note in a follow-up commit message or `README.md` update any manual-testing
findings (e.g. UI rough edges) as known issues — don't silently fix scope creep here.

---

## Deferred (not in this plan — v2/future, per design doc §5 and §7)

- File-upload UI for bulk CSV import
- Weekly-mode UI (blocked on Task 4's weekly-gap research decision; if the proxy holds,
  add a follow-up task then)
- Live news/sentiment-driven scenario adjustment
- Any API auto-fetch of source data
