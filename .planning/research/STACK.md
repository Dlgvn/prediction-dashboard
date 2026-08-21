# Stack Research

**Domain:** Python-only web dashboard (Reflex) — SQLite CRUD + statsmodels forecasting + interactive charts + Excel export
**Researched:** 2026-08-21
**Confidence:** HIGH (core stack verified via PyPI live version lookups + Reflex/statsmodels official docs); MEDIUM on ML-baseline library choice (design doc leaves model selection open)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 or 3.12 | Runtime | Reflex 0.9.x and statsmodels 0.14.x both fully support 3.11/3.12; avoid 3.13 until you confirm all pinned deps (esp. numpy/scipy wheels) publish 3.13 wheels — as of this research 3.11/3.12 is the safest target for a dependency set this heavy on compiled scientific packages. |
| Reflex | 0.9.8 (post1) | Full-stack Python web framework — UI + backend + state in one process | Matches PROJECT.md's explicit constraint ("Reflex (Python-only web framework)"). Confirmed current stable on PyPI as of 2026-08-21. Ships built-in SQLAlchemy/SQLModel integration (`rx.Model`) so persistence and the app process are genuinely one deployable unit — correct fit for the single-user, single-process architecture called out in the design doc (§2). |
| SQLite (via `rx.Model` / SQLModel / SQLAlchemy) | stdlib `sqlite3` (bundled with Python); SQLModel 0.0.39 | Persistent storage for the price-entry table | Reflex's model layer wraps SQLAlchemy via SQLModel; SQLite needs no separate server process, matching "single user, occasional (roughly monthly) use" from PROJECT.md. No reason to introduce Postgres at this scale — confirmed by Reflex's own docs describing SQLite as a first-class, zero-config backend for `rx.Model`. |
| statsmodels | 0.14.6 (installed from PyPI; do not use the `0.15.0.dev` docs branch — that's the *unreleased* dev docs version, not installable) | ARIMA / SARIMAX / VAR forecasting | This is the explicit constraint in PROJECT.md ("statsmodels for forecasting") and the direct continuation of the `backend_research/` prototyping already done for the Excel workbook. 0.14.6 is the current stable PyPI release; note that statsmodels' own hosted docs default to showing "0.15.0 (devel)" which is pre-release documentation, not the shipped API — pin to 0.14.6 in requirements and cross-check any 0.15-only API syntax found in docs before using it. |
| pandas | 3.0.5 | Data wrangling — CSV seed import, wide/long transforms, feeding statsmodels/Excel | pandas 3.x is current stable; note pandas 3.0 changed some defaults (e.g. copy-on-write is now permanent/default behavior, `Index` dtype inference tweaks) versus the pandas 1.x/2.x era much tutorial content assumes — worth a quick changelog skim before writing the seed-import script so date parsing/dtype behavior isn't silently different from what older statsmodels examples expect. |
| openpyxl | 3.1.5 | Reading source `.xlsx`-adjacent exports and writing the Excel export feature | Standard, actively maintained pure-Python engine for `.xlsx` read/write; pandas uses it automatically as the `.to_excel()` engine for `.xlsx`. No native dependencies, which matters for a single-user desktop-style deploy. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLModel | 0.0.39 | ORM layer Reflex's `rx.Model` is built on | Automatically pulled in by Reflex; you'll subclass `rx.Model` (which itself subclasses `SQLModel`) for the price-entry table rather than importing SQLModel directly in most cases. |
| plotly | 6.9.0 | Interactive charting (bull/base/bear scenario lines) inside Reflex via `rx.plotly` | Recommended over `rx.recharts` for this specific use case: multi-series time-series line charts with hover tooltips, zoom, and export-to-PNG are Plotly's strength, and `rx.plotly` renders full Plotly/Plotly Express figures natively in Reflex. Recharts (`rx.recharts`) is the lighter-weight, more "dashboard-native-feeling" alternative — see Alternatives below. |
| scikit-learn | 1.9.0 | ML baseline forecaster (gradient boosting / random forest regression on lagged features), per PROJECT.md's "research-first" requirement to test at least one ML baseline against statsmodels candidates | Only needed during the model-research phase (§4 of the design doc), not for the shipped app if a statsmodels model wins the backtest. Keep as a research-phase dependency; don't hard-wire it into the production forecast module unless it wins. |
| pytest | latest 8.x | Unit-testing the forecasting module, which the design doc explicitly calls out as needing to be "independent of the UI... so it can be unit-tested" (§2) | Test the forecasting module and Excel export logic in isolation from Reflex state/UI — Reflex apps are awkward to unit-test directly, so keeping forecasting/export as plain Python functions callable from tests (not buried in `rx.State` methods) is the pattern to follow. |
| ruff | latest | Linting/formatting | Standard modern choice for a Python project this size; fast, single tool replaces flake8+black+isort. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `reflex run` | Local dev server with hot reload | Reflex's built-in dev workflow; no separate frontend dev server needed since Reflex compiles to a React frontend + FastAPI backend under the hood but you never touch either directly. |
| `reflex db init` / `reflex db migrate` | Schema management for `rx.Model` tables | Wraps Alembic under the hood. Use this rather than hand-editing the SQLite file or writing raw `CREATE TABLE` — keeps schema changes (e.g. adding a column for weekly mode later) reproducible. |
| uv or pip-tools | Dependency pinning | Given the heavy, version-sensitive scientific stack (numpy/scipy/pandas/statsmodels), pin exact versions in a lockfile rather than loose ranges — these packages have historically had real breaking changes between minor versions (e.g. pandas 2→3 copy-on-write, statsmodels API churn between 0.13→0.14). |

## Installation

```bash
# Core
pip install reflex==0.9.8.post1 statsmodels==0.14.6 pandas==3.0.5 openpyxl==3.1.5

# Charting
pip install plotly==6.9.0

# Model research phase only (not necessarily shipped)
pip install scikit-learn==1.9.0

# Dev dependencies
pip install pytest ruff
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `rx.plotly` (Plotly) for scenario charts | `rx.recharts` (Recharts) | If you want charts that visually match Reflex's default dashboard-template aesthetic out of the box and don't need Plotly-specific features (range sliders, native PNG export, log-scale toggles) — Recharts is lighter and more "React-native-feeling" inside Reflex, but has less built-in interactivity for multi-scenario line comparison. |
| SQLite via `rx.Model` | Postgres | Only if this ever becomes multi-user, cloud-hosted, or needs concurrent writers — explicitly out of scope per PROJECT.md ("single local user"). Don't pre-adopt Postgres; it adds an external service dependency for zero benefit at this scale. |
| Single Reflex process (UI + backend + DB) | Split FastAPI backend + separate frontend | Only if the project later needs a mobile client, a public API, or multi-tenant auth — none of which are in scope. The design doc (§2) already made this call; this research confirms it's still the right default for Reflex's intended use case at this scale. |
| statsmodels ARIMA/SARIMAX/VAR | `pmdarima` (auto_arima) for automated order selection | Useful as a *research-phase convenience* to auto-search (p,d,q) orders faster than manual grid search in `backend_research/`-style backtesting, but not a production dependency — once winning orders are found via backtest, hard-code them in the statsmodels call rather than keeping auto_arima as a runtime dependency (it re-searches on every fit, which is unnecessary cost for a single-user monthly-cadence app). Confirmed current PyPI version: 2.1.1, compatible with statsmodels 0.14.x. |
| scikit-learn gradient boosting as ML baseline | `xgboost` (3.4.1, confirmed current) | If the research phase shows scikit-learn's `GradientBoostingRegressor`/`HistGradientBoostingRegressor` underperforms on these particular series (small, few-hundred-row datasets), xgboost is a reasonable next thing to try, but for datasets this small (monthly data since 2020, weekly since 2022 — low hundreds of rows) scikit-learn's built-in boosting is very likely sufficient and keeps one fewer heavy native dependency in the stack. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| Flask/Django + a separate JS frontend framework | PROJECT.md explicitly constrains this project to Reflex, Python-only, single-process — this rules out any split frontend/backend approach and any JS build tooling. | Reflex, as already decided. |
| Postgres, MySQL, or any hosted DB service | Massive overkill for single-user, monthly-cadence data entry; adds an external service, connection-string secrets, and ops burden with zero benefit at this scale. | SQLite via `rx.Model`, as already decided in PROJECT.md constraints. |
| `pmdarima`'s `auto_arima` as a runtime/production dependency | It's meant for exploratory order search, not repeated production inference; re-running a search on every forecast call is wasted compute and non-deterministic across statsmodels/numpy versions in subtle ways. | Use it only during the research/backtest phase; hard-code the winning (p,d,q)/(P,D,Q,s) orders in the shipped forecasting module. |
| Hand-rolled `sqlite3` + raw SQL for the price table | Reflex's `rx.Model`/SQLModel layer already gives you schema definition, migrations (`reflex db migrate`), and typed query building for free — bypassing it means losing Reflex's reactive state binding between the DB and the UI table component, which is the main reason to use Reflex at all. | `rx.Model` subclasses + `reflex db init`/`migrate`. |
| pandas `.to_excel()` with the `xlsxwriter` engine | xlsxwriter is write-only (can't help with any future read-back need) and is a second dependency doing largely the same job openpyxl already does (which Reflex/pandas will pull in anyway for reading `.xlsx` seed-adjacent files). Keep one Excel library, not two. | openpyxl for both read and write paths. |
| statsmodels' hosted "devel"/0.15.0 docs as an API reference without checking | The default statsmodels.org docs frequently show the *unreleased* dev branch (0.15.0 at time of this research) rather than the installed 0.14.6 API — following dev-branch examples verbatim can reference methods/params not yet in the pinned release. | Cross-check any statsmodels example against the 0.14.x-tagged docs or the installed package's own docstrings (`help(SARIMAX)`) before relying on a signature. |

## Stack Patterns by Variant

**If weekly-mode forecasting ships (per design doc §6):**
- Keep the same statsmodels/pandas stack — no new tech needed, just additional model variants (e.g. proxy regression Baltic AN → HDAN/PPAN) fit on a different resampling of the same tables.
- Because the data-cadence gap is a modeling/data problem, not a stack problem — resolving it doesn't require different libraries, just different backtest configurations.

**If v2 news/sentiment scenario adjustment ships (per design doc §5):**
- This will need an HTTP client (`httpx`) and likely an LLM API SDK — deliberately not researched here since PROJECT.md marks this "explicitly deferred to v2" and provider selection as "an open research question, not decided yet." Re-research at that milestone rather than pre-selecting now.
- Because locking in a news/LLM provider now would be premature — the design doc is explicit that this needs its own research pass later.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| reflex==0.9.8.post1 | sqlmodel==0.0.39 (auto-pulled) | Installed automatically as a Reflex dependency; don't pin a different SQLModel version manually unless you've verified compatibility with your Reflex version. |
| pandas==3.0.5 | statsmodels==0.14.6 | Confirmed working combination as of 2026-08-21 (both current stable on PyPI simultaneously); if either is upgraded independently later, re-verify — statsmodels has historically lagged pandas major-version support by a few months. |
| pandas==3.0.5 | openpyxl==3.1.5 | pandas auto-selects openpyxl as the `.xlsx` engine when installed; no explicit `engine=` argument needed for `.to_excel()`/`.read_excel()` in most cases, but pass `engine="openpyxl"` explicitly for clarity/future-proofing. |
| statsmodels==0.14.6 | numpy/scipy (whatever pip resolves) | Let pip resolve numpy/scipy versions from statsmodels' own constraints rather than pinning them yourself — these are the packages most likely to have platform-specific wheel gaps on newer Python versions. |

## Sources

- PyPI JSON API (`pypi.org/pypi/<package>/json`) — live version lookups for reflex, statsmodels, pandas, openpyxl, sqlmodel, plotly, pmdarima, scikit-learn, xgboost — HIGH confidence (authoritative, current as of 2026-08-21)
- https://reflex.dev/docs/database/overview/ — confirmed `rx.Model`/SQLAlchemy/SQLModel architecture — HIGH confidence
- https://reflex.dev/docs/library/graphing/other-charts/plotly/ and https://reflex.dev/docs/library/graphing/charts/linechart/ — confirmed `rx.plotly` and `rx.recharts` both current, actively supported charting paths — HIGH confidence
- https://www.statsmodels.org (devel docs) — flagged as showing pre-release "0.15.0" docs, cross-checked against installed 0.14.6 via PyPI — MEDIUM confidence on exact API surface, HIGH confidence that 0.14.6 is the correct pin
- Project files: `.planning/PROJECT.md`, `docs/plans/2026-08-21-reflex-dashboard-design.md` — source of hard constraints (Reflex, SQLite, statsmodels, single-process) that this research confirms and versions rather than second-guesses

---
*Stack research for: Reflex forecasting dashboard (Prediction Dashboard project)*
*Researched: 2026-08-21*
