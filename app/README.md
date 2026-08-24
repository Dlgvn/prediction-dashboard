# Prediction Dashboard (Reflex app)

A single-user Reflex web dashboard that forecasts ammonium nitrate (HDAN, PPAN),
imported diesel purchasing price (MNT), and the USD/MNT exchange rate. It's a
companion to (not a replacement for) the Excel workbook one level up
(`../AN_HDAN_PPAN_Diesel_FX_Forecast_Model.xlsx`) — this app adds an adjustable
forecast horizon, bull/base/bear scenario charting, in-app data entry, and Excel
export, all in one Python process (UI + backend + SQLite).

See `../PROJECT_VISION.md` and `../.planning/PROJECT.md` for the full product
context; this file covers running and working on the app itself.

## Quick start

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate   # if .venv doesn't already exist
pip install -r requirements.txt
reflex run
```

Opens the dashboard at `http://localhost:3000` (frontend) with the backend on
`http://localhost:8000`. First run compiles the frontend, which takes a minute.

## What's in this folder

| Path | What it is |
|---|---|
| `app/app.py` | Page composition — all `rx.Component` render functions (`forecast_summary_cards`, `forecast_chart`, `data_table`, etc.) and the `index()` page, wired into `app = rx.App()` |
| `app/state.py` | `DashboardState` — all reactive state: row CRUD, horizon slider, forecast computed vars, chart figure builders |
| `app/forecasting.py` | `forecast_all()` — the validated (Phase 2/3 backtested) base/bull/bear forecasting dispatcher; the only place models are called |
| `app/models.py` | `PriceRow` / `AppSetting` — the `rx.Model` (SQLModel) SQLite schema |
| `app/validators.py` | Input validation for manual data entry (numeric, unique-month date) |
| `app/theme.py` | The locked design-token module (color/spacing/typography) — the single source of truth for the UI's visual design; see `.planning/phases/06-ux-ui-redesign/06-UI-SPEC.md` |
| `app/seed.py` | One-time seed script loading historical rows from the root-level CSVs into SQLite |
| `rxconfig.py` | Reflex app config — plugins, including the pinned light Radix theme |
| `tests/` | Pytest suite — state, forecasting, models, seed, validators, theme, and component compile-smoke tests. Run with `pytest tests/ -q` |
| `alembic/` | Schema migrations (wraps Reflex's `reflex db migrate`) |
| `reflex.db` | The SQLite database file (gitignored in spirit, but currently tracked — don't hand-edit; use the app or `reflex db migrate`) |

## Running tests

```bash
cd app
pytest tests/ -q
```

Tests instantiate `DashboardState` directly and don't require a running Reflex
server or browser.

## Architecture notes

- **Single process, single user.** No auth, no split frontend/backend service —
  matches the "one person, roughly monthly use" usage pattern (see
  `.planning/research/STACK.md` for why this stack was chosen over
  Postgres/split-service alternatives).
- **Forecasting is a hard boundary.** `state.py` calls `forecast_all()` exactly
  once per computed var (`forecast_results`) — every other forecast-derived value
  (summary cards, chart, table) reads that memoized result rather than re-fitting
  models on every horizon-slider drag. Don't add a second call site.
- **Design tokens are centralized.** `app/theme.py` is the single source for every
  color/spacing/typography value used in `app.py` and the Plotly figure builders in
  `state.py` — don't hardcode a hex or px value elsewhere.
- **No file upload.** Historical data entry is manual, in-app, via the editable
  table at the bottom of the page — this is a deliberate v1 scope decision (see
  `.planning/PROJECT.md`), not a missing feature.

## Where to look next

- `.planning/ROADMAP.md` — phase-by-phase build history and what's currently in
  progress
- `.planning/phases/06-ux-ui-redesign/06-UI-SPEC.md` — the as-built UI design
  contract (layout order, color/spacing/typography rules, copy)
- `../backend_research/REPORT.md` — the model backtests this app's forecasts are
  built on
