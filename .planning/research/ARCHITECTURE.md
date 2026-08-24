# Architecture Research: v1.2 Data Entry Fix & Forecast Enrichment

**Domain:** Reflex (Python) single-state-class dashboard app — integrating new features into existing architecture
**Researched:** 2026-08-24
**Confidence:** HIGH (based on direct reading of `app/app/state.py`, `app/app/app.py`, `app/app/models.py`, `app/app/forecasting.py`)

## Existing Architecture Recap

`DashboardState(rx.State)` in `app/app/state.py` is the **sole DB-access boundary** — every `rx.session()` call lives there, per the file's own docstring ("Per ARCHITECTURE.md Pattern 2, DashboardState is the only place... that opens an rx.session()"). `app/app/app.py` holds pure render/component functions that read `DashboardState` vars via `rx.foreach`/`rx.cond` and never touch the DB. `app/app/models.py` has two flat `rx.Model` tables: `PriceRow` (17 columns: `date` + 16 `Optional[float]` series) and `AppSetting` (key/value, currently just `markup_pct`). `app/app/forecasting.py` exposes one dispatcher, `forecast_all(history, horizon, markup_pct) -> dict`, called from exactly one place: the `forecast_results` computed var in `state.py` (documented "Pitfall 2 guard" — never re-invoke `forecast_all` elsewhere).

Two established data-flow conventions matter for planning new features:
1. **Rendering-list vars are flat dicts / list-of-dicts, never nested dict Vars** — `freshness_chips`, `summary_cards`, `forecast_table_rows` are all `list[dict[str, str]]` built by plain Python inside a `@rx.var`, specifically to avoid unverified dict-Var-indexing syntax in `rx.foreach`. Any new list-rendering feature should follow this shape.
2. **`self.rows: list[PriceRow]`** is the in-memory, DB-mirrored source of every derived var (charts, cards, forecast). It's fully reloaded (`load_rows()`) after every write — never incrementally patched. At 167+ rows this reload is still cheap (SQLite, single table, small dataset by any standard), so the actual bottleneck for target feature 1 is **rendering** all rows into the table (`rx.foreach` over `DashboardState.rows` with no windowing), not the DB read.

## New Features vs Existing Architecture

### 1. Data Entry table pagination/windowing

**Root cause of the current problem:** `data_entry_section()` in `app.py` renders `data_table()` unconditionally over the full `DashboardState.rows` list via `rx.foreach`, and `rows` is loaded in full by `load_rows()` on every mount and after every mutation. There is no windowing anywhere in the stack — this is a pure **rendering-scale** problem, not a DB-query problem.

**Integration point:** `DashboardState.rows` must stay authoritative (charts, `forecast_results`, freshness chips, export all read all of `self.rows`) — do not filter `load_rows()`'s query itself, since a windowed `rows` would silently break `historical_chart_figure`, `forecast_chart_figure` (needs 12 trailing months), `freshness_chips`, and `_export_bytes` (needs full history), all of which currently read `self.rows` directly.

**Recommended approach — add a display-only slice, don't touch `rows`:**
- New state field: `show_all_history: bool = False`.
- New computed var: `visible_rows: list[PriceRow]` (a `@rx.var`) — returns `self.rows` unmodified if `show_all_history` else the last N (e.g. 12 or 24) entries by date order, since `self.rows` is already date-ascending from `load_rows()`'s `order_by(PriceRow.date)`.
- `data_table()` in `app.py` switches its `rx.foreach(DashboardState.rows, ...)` to `rx.foreach(DashboardState.visible_rows, ...)`.
- `data_entry_section()`'s empty-state length check (`DashboardState.rows.length() + DashboardState.draft_rows.length()`) stays on `rows`/`draft_rows` (true DB emptiness), not `visible_rows`, so "no data yet" isn't shown when history exists but is just windowed out.
- Toggle control: a simple `rx.switch` or button pair bound to a new `toggle_history_view()` event handler that flips `show_all_history` — no DB call needed (it's a pure client-visible re-slice of already-loaded data).
- Edit/delete/add-row event handlers (`start_edit`, `commit_edit`, `request_delete`, `add_row`) are keyed by `row.date`, not list index, so windowing `visible_rows` requires **no changes** to any of those handlers — they already resolve rows by date against the DB or `draft_rows`, independent of what's currently rendered.

**Verdict:** This is additive and self-contained — one new bool field, one new computed var, one new event handler, one render-function line change. No DB schema change, no change to `forecast_results`/chart vars. Low risk, ships first.

### 2. Export/import UX improvements

**Export polish** (existing `_export_bytes`/`export_to_excel` in `state.py`): currently a single flat sheet of raw actuals with no formatting. Polish (column widths, header styling, maybe a second sheet with forecast output) is additive to `_export_bytes` — it's already a plain (non-event-handler) method per its own docstring specifically "so it's unit-testable," which is the right place to extend. No new state fields strictly required unless you add user-configurable export options (e.g. "include forecast sheet" checkbox → one new bool field + a branch in `_export_bytes`).

**CSV bulk import (new capability, not in current code at all):** PROJECT.md's "Out of Scope" section explicitly deferred file-upload UI to a future milestone — this milestone's target features description says "possible CSV bulk import," meaning it's scoping-only, not committed. If pursued in a later phase, integration points:
- `rx.upload` component (new) feeding a new `DashboardState` event handler, e.g. `handle_csv_upload(files)`.
- Must reuse `validate_date`/`validate_numeric` from `app/validators.py` (already used per-cell in `commit_edit`/`_commit_draft_cell`) — do not write a parallel validation path for bulk rows, or the two paths will drift.
- Must reuse the unique-date constraint logic already enforced in `validate_date` (rows keyed by unique `date`), and decide the upsert semantics (overwrite existing date rows vs reject duplicates) — this is a **product decision to research/scope in this milestone**, not to build.
- Should call `self.load_rows()` once at the end of a batch import, not per-row (avoid N reloads for N CSV rows) — this is a new pattern relative to the existing single-row-at-a-time handlers, worth flagging explicitly in the phase plan.
- SERIES_ATTRS (the 16-column tuple already defined once in `state.py`) is the correct single source of truth for expected CSV columns — reuse it rather than hardcoding a new column list.

**Verdict:** Export polish is small/independent, can ship anytime. CSV import (if built this milestone) is a materially bigger feature (new component, new validation-at-scale path, upsert-semantics decision) and should be scoped/researched as its own phase rather than bundled with pagination or export polish.

### 3. Richer forecast context (drivers, historical high/low, % change stats)

**Integration point:** These are pure derived stats over `self.rows` (historical high/low, % change) or over `forecast_results` (drivers — see caveat below), following the exact same pattern as `summary_cards`/`freshness_chips`: a new `@rx.var` returning `list[dict[str, str]]`, rendered by a new small component function in `app.py`, placed near `forecast_summary_cards()`.

- **Historical high/low, % change stats**: computable entirely from `self.rows` with plain Python (min/max/first/last over non-None values per series) — no new DB fields, no new call to `forecast_all()`. Follow `_latest_actual_for`'s existing pattern (loop `self.rows`, skip `None`) rather than introducing pandas aggregation inside a computed var (the codebase's existing computed vars are hand-rolled Python loops, not pandas, presumably to avoid pandas-Var interaction surprises — stay consistent).
- **"Drivers"**: ambiguous in the milestone brief — clarify during phase planning whether this means (a) the exogenous inputs already in `PriceRow` that feed each series' model (e.g. Brent → Diesel, Urals/Baltic AN → HDAN/PPAN per `forecasting.py`'s VAR/AR-lag structures), shown as a static "what feeds this forecast" caption, or (b) a magnitude-of-contribution breakdown requiring new computation inside `forecasting.py`. Reading `forecasting.py`'s dispatcher signatures (`forecast_hdan`, `forecast_ppan_var_system`, `forecast_diesel_usd`, `forecast_fx`) confirms the exogenous relationships already exist in code (e.g. `_build_future_exog`) — a **static, hardcoded "driven by: Brent, Urals" caption per series** is cheap and low-risk; an actual contribution-decomposition (e.g. Shapley-style attribution) would be a forecasting.py change, is far more research-heavy, and should not be assumed in scope without explicit confirmation.
- **Placement**: extend `forecast_summary_cards()`'s existing card dict shape (`card["label"]`, `card["base"]`, etc.) with additional optional keys, OR add a second row of "context" cards below the existing summary cards — the latter is safer since `summary_cards`' dict shape is already load-bearing for `_summary_card()`'s rendering and adding new keys risks distracting from D-01..D-13's existing locked UI-SPEC contract (see the many `D-xx` references throughout `state.py`/`app.py` — this app has a formal UI spec that later phases must not silently violate).

**Verdict:** Historical high/low and % change stats are low-risk, additive computed vars — no forecasting.py change needed. "Drivers" needs scope clarification before estimation; the static-caption version is trivial, the attribution version is a forecasting research topic that would need its own backtest-style validation per PROJECT.md's "Model provenance" constraint ("no un-backtested model ships to the dashboard" — this constraint arguably extends to any new *derived* forecast-adjacent number, not just top-line forecasts).

### 4. Performance patterns for growing data scale

At current scale (167 rows since 2013, 16 columns) SQLite + full in-memory `self.rows` is not itself a bottleneck — the pagination fix (feature 1) addresses the actual observed symptom (hanging table), which is a **rendering** cost (`rx.foreach` generating hundreds of editable-cell components client-side), not a DB or state-size cost. Confirm this diagnosis before over-building:
- `load_rows()`'s single `SELECT ... ORDER BY date` on a table this size is sub-millisecond; no query optimization needed yet.
- If data scale grows by 10-100x (e.g. weekly cadence backfill, per PROJECT.md's deferred weekly-mode work), reassess: `historical_chart_figure` and `forecast_chart_figure` already loop `self.rows` in Python per render — at very large row counts this loop cost (not just table rendering) would start to matter, and pushing the trailing-N-months slice (already done for `hist_dates`/`hist_values` via `[-12:]`) further upstream (e.g. querying only the needed window from SQLite rather than loading all rows into `self.rows` first) would be the next optimization tier. Not needed for this milestone's scale.
- The one true "growing data" risk in the current code is `data_table()`'s **full-row rendering with per-cell editable components** (`_editable_cell` creates an `rx.cond`-wrapped input+text pair per cell per row) — that's O(rows × 17 columns) DOM nodes. Feature 1's windowing directly caps this. No other perf work is justified by current evidence.

**Verdict:** Feature 1 (pagination/windowing) *is* the performance fix for this milestone. Don't scope additional performance work (query batching, caching layers, pagination at the SQL level) without a demonstrated bottleneck beyond the already-diagnosed rendering issue.

## Build Order

1. **Data Entry pagination/windowing (Feature 1)** — ship first, independently. Small, self-contained (`show_all_history` bool + `visible_rows` computed var + one render-function change), fixes the actual reported usability bug, and has zero dependency on the other three features. This is also effectively "Feature 4" (performance) — building it satisfies both target features in one phase.
2. **Historical high/low & % change stats (part of Feature 3)** — independent of Feature 1, can be built in parallel or immediately after; low risk, same computed-var pattern as existing `freshness_chips`/`summary_cards`, no forecasting.py changes.
3. **Export polish (part of Feature 2)** — independent of 1 and 2; touches only `_export_bytes`/`export_to_excel`, low risk, can slot in anywhere.
4. **"Drivers" context (part of Feature 3, static-caption version)** — do after 2, since it likely reuses the same new "forecast context" component/section; needs an explicit scope decision (static caption vs. real attribution) before estimation. If real attribution is wanted, this becomes its own research-then-build phase, not a quick add.
5. **CSV bulk import (part of Feature 2, if pursued this milestone)** — build last, as its own phase. It's the only feature here requiring a genuinely new component type (`rx.upload`), a new validation-at-scale path, and a product decision (upsert semantics) that doesn't yet exist in the codebase. Should not be bundled into the same phase as pagination or export polish — different risk profile and it's explicitly still just "possible" per the milestone framing, not committed scope.

**Dependency notes:**
- Feature 1 has no dependency on 2, 3, or 4 and should not be blocked by them.
- Feature 3's "drivers" sub-feature depends on a scope decision, not on any other feature's code.
- Feature 2's CSV import depends on `app/validators.py`'s existing `validate_date`/`validate_numeric` (already available, no blocker) but is the highest-complexity, most research-worthy item — sequence it last so scope/risk is better understood by the time it's tackled.
- None of features 2-4 require schema changes to `PriceRow`/`AppSetting` as currently read — flag this if a "drivers" attribution approach or CSV import's upsert semantics end up requiring new columns (e.g. an `imported_at` audit column), which would need a `reflex db migrate` step per the project's established migration pattern.

## Sources

- Direct reading of `app/app/state.py`, `app/app/app.py`, `app/app/models.py`, `app/app/forecasting.py` (function signatures only) — HIGH confidence, these are the actual files this milestone builds on.
- `.planning/PROJECT.md` — HIGH confidence, authoritative scope/constraints document, explicitly confirms CSV import was previously out-of-scope and is now only tentatively re-opened ("possible").
