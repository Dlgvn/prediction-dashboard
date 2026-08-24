# Stack Research

**Domain:** Reflex (Python) dashboard — v1.2 feature additions (table pagination, CSV import, forecast stats, performance)
**Researched:** 2026-08-24
**Confidence:** MEDIUM-HIGH

This is an incremental research pass on top of an already-validated stack (Reflex 0.9.8.post1, SQLite via `rx.Model`, statsmodels, pandas 3.0.5, openpyxl, `rx.plotly`). No replacement of validated pieces is recommended. All four new capabilities are achievable with libraries already in the stack plus Reflex's own built-in components — **no new third-party packages are required.**

## Recommended Stack

### Core Technologies (all already installed — no version changes)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Reflex `rx.upload` | bundled with reflex==0.9.8.post1 | CSV bulk-import UI (new capability #2) | Built-in component, no extra dependency. Confirmed current API (2026-08-24, reflex.dev/docs/library/forms/upload/): bind `rx.upload_files(upload_id=...)` to trigger, backend handler is `async def handle_upload(files: list[UploadFile])`, read bytes with `await file.read()`. Supports `max_files`, `max_size`, `min_size`, `multiple` props for basic validation before parsing. |
| Reflex `@rx.var(cache=True)` (computed vars) | bundled with reflex==0.9.8.post1 | Windowed/paginated table data, high/low/%-change stats (new capabilities #1, #3, #4) | This is the idiomatic Reflex mechanism for avoiding full-list re-renders: a cached computed var only recomputes when the specific state vars it reads (e.g. `page_offset`, `show_all`) change — not on every unrelated state update. Confirmed current in reflex.dev/docs/vars/computed-vars/ (cache=True is the default since it was introduced; explicit annotation still recommended for clarity). |
| pandas | 3.0.5 (already pinned) | Parsing uploaded CSV bytes (`pd.read_csv(io.BytesIO(contents))`), computing rolling/window stats (min/max/pct_change) for capability #3 | Already the project's data-wrangling library; `df["col"].pct_change()`, `.rolling(window).min()/.max()` cover the "historical high/low, % change" requirement with no new dependency. |
| Python stdlib `io` | 3.11/3.12 stdlib | Wrapping uploaded bytes as a file-like object for pandas | No install needed. |

### Supporting Libraries (no additions needed — confirms existing stack suffices)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| plotly (via `rx.plotly`) | 6.9.0 (already pinned) | Rendering high/low bands or annotations on the existing scenario chart for capability #3 | Plotly already supports `add_hline`/`add_annotation`/shaded `fill='tonexty'` bands natively — use these for "historical high/low" markers rather than adding a separate stats-charting library. |
| openpyxl | 3.1.5 (already pinned) | Improved Excel export UX (e.g. multi-sheet export, formatted headers, autosizing columns) for capability #2 | openpyxl's `Worksheet` API already supports column width, cell formatting, freeze panes, and multiple sheets — sufficient for "better Excel export UX" without adding `xlsxwriter` or similar. |

### Development Tools

No new dev tools needed. Continue using `reflex run`, `reflex db migrate`, `pytest`, `ruff` as already established.

## Implementation Notes by Capability

### 1. Table pagination/windowing in `rx.foreach`
- Do NOT try to slice a Python list inside the render function directly on a raw `list[dict]` state var per-render — that re-renders the full diff each time the underlying list state var changes.
- Pattern: keep the full dataset in one `rx.Model`-backed state var (or query directly per-page from SQLite), and expose a **cached computed var** (e.g. `visible_rows`) that returns only the current window (e.g. last 12 months by default) computed from `page_offset`/`show_all` and the underlying data. `rx.foreach` should iterate this computed var, never the raw full list, in the always-rendered case.
- For "show all history" toggle: keep it as a plain boolean state var; the computed var branches (`if self.show_all: return self.all_rows else: return self.all_rows[-N:]`) — with `cache=True` this only recomputes when `show_all` or the underlying rows change, not on unrelated UI state changes (e.g. sidebar toggles, chart hover state).
- If page-level DB queries are preferred over in-memory slicing (167 rows × 17 cols is small enough that in-memory slicing of a cached computed var is likely sufficient and simpler — no need for `query.offset()/.limit()` SQL pagination at this scale, but that pattern exists in Reflex's own docs if data grows into the thousands of rows).
- Source: reflex.dev/docs/vars/computed-vars/, reflex.dev/docs/library/dynamic-rendering/foreach/ (MEDIUM confidence — verified via official docs, general pattern not literally copy-pasted from a first-party pagination tutorial for this exact editable-table shape).

### 2. CSV upload/import
- Use `rx.upload(id="csv_upload", accept={"text/csv": [".csv"]}, max_files=1)` + a trigger button bound to `rx.upload_files(upload_id="csv_upload")`.
- Backend handler: `async def handle_csv_upload(self, files: list[UploadFile])`, read with `contents = await file.read()`, parse with `pd.read_csv(io.BytesIO(contents))`.
- Validate/preview before committing to SQLite — given "single user, occasional use," a simple preview-then-confirm step (show parsed rows in a table, user clicks "Import") is safer than silent auto-commit, and avoids needing a third-party CSV-mapping tool.
- Do not add CSVBox or similar hosted CSV-import SaaS (surfaced in search results) — it's a paid third-party service aimed at multi-tenant SaaS onboarding flows; unnecessary complexity/cost for a single local user when `rx.upload` + pandas already covers validation and parsing.
- Source: reflex.dev/docs/library/forms/upload/ (HIGH confidence, official docs, current as of 2026-08-24).

### 3. Historical high/low, % change, forecast context
- No new charting/stats library needed. Compute via pandas (`.min()`, `.max()`, `.pct_change()`, `.rolling()`) on the existing SQLite-backed price history, expose as cached computed vars, and either display as plain `rx.text`/`rx.stat`-style components or overlay on the existing `rx.plotly` chart using Plotly's native `add_hline`, `add_annotation`, or a shaded min/max band trace.
- If "drivers/context for the forecast" means showing which input series (e.g. Brent crude for Diesel) most influenced a forecast, that's a statsmodels-level question (e.g. VAR coefficient inspection or SARIMAX exog contribution) — flag this as needing phase-specific research when that feature is scoped in detail; it is a modeling question, not a new library dependency.

### 4. General Reflex performance for growing data
- Prefer cached computed vars (`@rx.var(cache=True)`, the default) over methods called directly in render, and over `@rx.var(cache=False)` for anything reading list/dict state.
- Keep `rx.foreach` bound to computed/derived vars (already-windowed), not raw full-history lists, everywhere a table or chart iterates state.
- At current and near-future scale (hundreds of rows), in-memory pandas/list operations inside cached computed vars are sufficient — do not prematurely introduce SQL-level pagination (`query.offset()/.limit()`), a caching layer (Redis), or a background task queue. Revisit only if row counts grow into the thousands or the app becomes multi-user.

## Installation

No new packages required.

```bash
# Nothing new to install — rx.upload, @rx.var(cache=True), and pandas stats
# functions are already available in the currently pinned reflex==0.9.8.post1
# and pandas==3.0.5.
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `rx.upload` + pandas `read_csv` for CSV import | CSVBox (hosted CSV-import widget) | Only if this ever becomes a multi-tenant/customer-facing product needing non-technical end-user column-mapping UX with support for malformed files at scale — not warranted for a single local user with a known, fixed CSV schema. |
| Cached computed var (`@rx.var(cache=True)`) windowing for table pagination | SQL-level `OFFSET`/`LIMIT` pagination against SQLite | Use if/when the price-entry table grows well beyond current scale (thousands of rows) such that loading the full table into a Python list per session becomes a real memory/latency concern — not the case at 167 rows × 17 cols. |
| Plotly native annotations/bands for high/low display | A dedicated stats/sparkline library (e.g. `plotly.express` subplots, or a JS sparkline component) | Only if the "richer forecast context" feature grows into a dedicated analytics sub-page with many small multiples — for a few summary stat lines on the existing dashboard, Plotly's existing primitives are sufficient. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| A separate pagination/data-grid library (e.g. `rx.data_table` from older Reflex versions, or a third-party AG-Grid wrapper) | Adds a new dependency and a different state-binding model than the rest of the app's `rx.foreach`-based editable table; current editable-cell UX already works, the problem is row count, not grid features. | Cached computed var windowing over the existing `rx.foreach` table, as above. |
| `xlsxwriter` for Excel export UX improvements | Would duplicate openpyxl, which is already pinned and already the pandas `.to_excel()` engine; the project's own STACK.md already flags this as a "what not to use." | openpyxl's existing formatting/multi-sheet/freeze-pane API. |
| Loading the entire uploaded CSV into a Reflex state var as a raw Python list before validation | Uploaded files can be arbitrary size/shape; dumping directly into reactive state risks the same "full re-render on large list" problem this milestone is fixing for the existing table. | Parse with pandas in the backend event handler first, validate/summarize, and only write to SQLite (and expose to state via the same windowed computed-var pattern) after user confirms. |
| Background task queue / Celery / Redis for CSV import processing | Massive overkill for single-user, occasional, small (hundreds-of-rows) CSV files — adds infra the single-process constraint explicitly rules out. | Reflex's built-in `async def` event handler is sufficient; use `@rx.event(background=True)` only if a specific import turns out to be slow enough to block the UI in testing, not preemptively. |

## Stack Patterns by Variant

**If the price-entry table grows past ~1,000-2,000 rows in a future milestone:**
- Move from in-memory computed-var slicing to actual SQL `OFFSET`/`LIMIT` queries per page via `rx.Model`/SQLAlchemy.
- Because in-memory Python list operations on every state read start becoming the bottleneck rather than the UI render itself.

**If CSV import needs to support multiple source schemas (not just one fixed layout):**
- Add a lightweight column-mapping step (dropdowns to map uploaded columns to `HDAN`/`PPAN`/`Diesel`/`FX` fields) before commit.
- Because the "Out of Scope" note in PROJECT.md that ruled out upload in v1 was about *not having* an upload UI at all, not about schema flexibility — keep the mapping step minimal rather than building a generic import-mapping engine.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| reflex==0.9.8.post1 | `rx.upload`, `@rx.var(cache=True)` | Both are stable, non-experimental APIs in this Reflex version as of 2026-08-24 — no upgrade needed to use either for this milestone. |
| pandas==3.0.5 | `io.BytesIO` + `pd.read_csv` | Standard combination; no compatibility concerns beyond what's already noted in the project's existing STACK.md re: pandas 3.x copy-on-write defaults. |

## Sources

- https://reflex.dev/docs/library/forms/upload/ — confirmed `rx.upload` API, event handler signature, chunked-upload option for large files — HIGH confidence, fetched 2026-08-24
- https://reflex.dev/docs/vars/computed-vars/ — confirmed cached computed var behavior and default `cache=True` — HIGH confidence, fetched 2026-08-24
- https://reflex.dev/docs/library/dynamic-rendering/foreach/ — confirmed `rx.foreach` usage pattern for state-driven lists — MEDIUM confidence (general docs, not a pagination-specific tutorial)
- WebSearch: "Reflex rx.upload component CSV file upload example" — surfaced CSVBox as a third-party alternative (rejected, see What NOT to Use) — LOW confidence source, not used for core recommendation
- WebSearch: "Reflex large table performance rx.foreach pagination best practices computed var cache" — surfaced GitHub discussion/issue threads confirming cached-var + pagination as the community-recommended pattern — MEDIUM confidence, cross-checked against official computed-vars docs
- Existing project file: `.planning/research/STACK.md` (v1 research, read via project context) — baseline stack this document extends, not re-researched

---
*Stack research for: Reflex dashboard v1.2 (pagination, CSV import, forecast stats, performance)*
*Researched: 2026-08-24*
