# Prediction Dashboard

A single-user Reflex web dashboard that forecasts ammonium nitrate (HDAN, PPAN),
imported diesel purchasing price (MNT), and the USD/MNT exchange rate. Adjustable
forecast horizon, bull/base/bear scenario charting, in-app data entry with CSV
bulk import, Excel export, and light/dark theming — all in one Python process
(UI + backend + SQLite).

## Quick start

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate   # if .venv doesn't already exist
pip install -r requirements.txt
.venv/bin/reflex run --frontend-port 3005 --backend-port 8005
```

Wait for the terminal to print `App Running`, then open **http://localhost:3005**
in your browser (backend runs on `http://localhost:8005`). First run compiles the
frontend, which takes a minute.

Ports 3005/8005 are this project's pinned dev ports (see `.claude/launch.json`) —
use them consistently rather than plain `reflex run`'s default 3000/8000, so you
don't end up with two different servers running side by side and end up looking
at a stale one. If `3005`/`8005` are already in use, either a server is already
running (just open the URL — nothing to start) or a previous run didn't shut
down cleanly:

```bash
lsof -ti:3005,8005 | xargs kill -9   # frees the ports if something stale is stuck
```

## What's in this folder

| Path | What it is |
|---|---|
| `app/app.py` | Page composition — all `rx.Component` render functions (`forecast_summary_cards`, `forecast_chart`, `data_table`, `csv_import_control`, etc.) and the `index()` page, wired into `app = rx.App()` |
| `app/state.py` | `DashboardState` — all reactive state: row CRUD, horizon slider, forecast computed vars, chart figure builders, theme mode, CSV import handlers |
| `app/forecasting.py` | `forecast_all()` — the validated (research-backtested) base/bull/bear forecasting dispatcher; the only place models are called |
| `app/csv_import.py` | Pure, Reflex-free CSV parsing and validation for bulk data import — reuses the same validators as manual entry, never opens a DB session |
| `app/models.py` | `PriceRow` / `AppSetting` — the `rx.Model` (SQLModel) SQLite schema |
| `app/validators.py` | Input validation for manual data entry (numeric, unique-month date) |
| `app/theme.py` | The design-token module (color/spacing/typography) — light and dark palettes, single source of truth for the UI's visual design |
| `app/seed.py` | One-time seed script loading historical rows from CSV into SQLite |
| `rxconfig.py` | Reflex app config — plugins, theme, default color mode |
| `tests/` | Pytest suite — state, forecasting, models, seed, validators, theme, CSV import, and component tests. Run with `pytest tests/ -q` |
| `alembic/` | Schema migrations (wraps Reflex's `reflex db migrate`) |
| `reflex.db` | The SQLite database file — don't hand-edit; use the app or `reflex db migrate` |

## Running tests

```bash
cd app
pytest tests/ -q
```

Tests instantiate `DashboardState` directly and don't require a running Reflex
server or browser.

## Features

- **Forecast summary cards** — base forecast, expected range, direction vs. latest
  actual, all-time high/low, and year-over-year change for each tracked series.
- **Scenario chart** — a fan chart showing historical actuals and a base/bull/bear
  forecast band across an adjustable 1-12 month horizon.
- **Data entry** — an editable table for monthly actuals, with validation, a
  windowed view (recent months by default, full history on toggle), and CSV bulk
  import with a preview-and-confirm step that never overwrites existing rows.
- **Excel export** — download the stored price table and current forecast to
  `.xlsx`.
- **Light/dark theming** — a toggle in the header, persisted across visits.

## Architecture notes

- **Single process, single user.** No auth, no split frontend/backend service —
  matches an occasional, low-volume usage pattern.
- **Forecasting is a hard boundary.** `state.py` calls `forecast_all()` exactly
  once per computed var (`forecast_results`) — every other forecast-derived value
  (summary cards, chart, table) reads that memoized result rather than re-fitting
  models on every horizon-slider drag. Don't add a second call site.
- **Design tokens are centralized.** `app/theme.py` is the single source for every
  color/spacing/typography value used in `app.py` and the Plotly figure builders in
  `state.py` — don't hardcode a hex or px value elsewhere. Colors are mode-aware
  (light/dark) and resolved through `DashboardState`'s computed vars.
- **CSV import reuses existing validation.** `csv_import.py` calls the same
  `validate_numeric`/`validate_date` functions the manual-entry table uses — no
  parallel validation logic.

## Where to look next

- `.planning/ROADMAP.md` — phase-by-phase build history and what's currently in
  progress
