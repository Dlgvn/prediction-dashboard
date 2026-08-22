# Phase 5: Forecast UI, Scenario Chart & Excel Export - Research

**Researched:** 2026-08-22
**Domain:** Reflex UI components (slider, plotly fan chart, select, download) + pandas/openpyxl export, wired to an existing framework-independent forecasting module
**Confidence:** HIGH (mechanics of Reflex components, verified against official docs) / MEDIUM (exact on_change slider value shape, background-task necessity — not verified against the pinned 0.9.8 source, see Open Questions)

## Summary

Phase 5 is pure UI-and-wiring: `forecasting.py`'s `forecast_all(history, horizon, markup_pct)` already returns exactly the shape the UI needs (`dict[str, list[{"month","base","bull","bear"}]]` for 5 keys), and Phase 4 already established every pattern this phase reuses — the `selected_series` + `rx.select` + `@rx.var` figure-builder pattern for the chart selector, the `rx.session()`-only-in-state.py boundary, and the `SERIES_LABELS`/`SERIES_ATTRS` single-source-of-truth convention. Nothing new needs to be installed; `pandas`, `openpyxl`, and `plotly` are already pinned in `app/requirements.txt`. The three genuinely new mechanics this phase introduces are: (1) `rx.slider`, new to the app, whose Radix-derived `value` prop is a *list* not a scalar even for a single thumb, requiring a small unwrap in the change handler; (2) a 3-trace Plotly fan chart (two boundary traces + `fill='tonexty'` + a solid line on top) built the same way Phase 4 built its single-line figure, as another `@rx.var`; (3) `rx.download` fed `bytes` produced by writing a `pandas.DataFrame` to an in-memory `io.BytesIO()` buffer via `openpyxl` — never an on-disk path.

**Primary recommendation:** Extend `DashboardState` with `horizon_months: int = 3`, a `forecast_series: str` selector (mirroring `selected_series`), and two new `@rx.var`s (`forecast_chart_figure`, `forecast_table_rows`) that call `forecast_all(self._history_df(), self.horizon_months, self._markup_pct())` fresh on every access — matching Phase 3's D-06 "no caching" contract and Phase 4's existing pattern of computing chart figures as `@rx.var`s from in-memory state rather than re-hitting the DB. Wrap the `forecast_all` call in a `try/except InsufficientHistoryError` to drive the UI-SPEC's defensive empty-state copy. Build the Excel export as a plain `def export_to_excel(self)` event handler (no `@rx.background` needed at this data scale — see Pitfall 3) that writes `self.rows` to a `BytesIO` via `pandas.DataFrame(...).to_excel(buffer, engine="openpyxl")` and returns `rx.download(data=buffer.getvalue(), filename=...)`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** A slider (not dropdown, not stepper) selects the horizon, range 1-12 months.
- **D-02:** The forecast recomputes live on every slider change (no explicit "Forecast"
  button) — justified by Phase 3's D-06, which established models refit in milliseconds
  at this data scale, so live recompute has no perceptible lag.
- **D-03 (resolves a real VIS-03 wording tension, not just a UI preference):** The
  forecast chart uses ONE chart with a series selector/toggle, matching Phase 4's
  historical-chart pattern — only one series' scenario band is visible on the chart at a
  time. This appears to conflict with VIS-03's literal wording ("all four tracked series
  visible together... not requiring the user to switch"), but is resolved by FCST-06's
  forecast table: the table lists ALL FOUR series' base/bull/bear numbers together,
  simultaneously, satisfying VIS-03's spirit (all four "visible together") through the
  table rather than the chart. This was an explicit, discussed trade-off — not an
  oversight. Downstream planner should treat VIS-03 as satisfied by the combination of
  (selector-chart + all-series table), not by the chart alone.
- **D-04:** Bull/bear renders as a filled/shaded area (two boundary traces with
  `fill='tonexty'`-style fill between them), with a solid base-forecast line drawn on top
  — the standard fan-chart pattern. Not 3 separate crisp lines (which VIS-02 explicitly
  rejects), and not a fill-only band without a visible base line.
- **D-05:** The forecast chart includes 12 months of recent historical actuals leading
  into the forecast band, not a forecast-only view. Separate from Phase 4's historical
  chart (full history, all 16 series); this one is scoped to the 4 forecast series with a
  12-month trailing window plus the horizon.
- **D-06:** Phase 5's new UI sections append below Phase 4's existing content, in build
  order: data table → historical chart (Phase 4) → horizon slider → forecast chart →
  forecast table → export button (Phase 5). No tabs, no reorganization of Phase 4's
  layout.
- **D-07:** DATA-06's "as of" freshness date appears as a small label above the forecast
  section, one per series (e.g. "HDAN as of 2026-07-01").
- **D-08:** Export produces an `.xlsx` file of the currently stored actuals table (the
  same data Phase 4's editable table shows) — not a forecast export.

### Claude's Discretion
None flagged this round — all four presented gray areas were explicitly decided, with
follow-up rounds on VIS-03's wording tension and the historical-context window size.

### Deferred Ideas (OUT OF SCOPE)
None raised outside phase scope — discussion stayed within Phase 5's boundary (horizon
selector, forecast layout, band rendering, page layout, freshness indicator).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-06 | Each series (HDAN, PPAN, Diesel-USD, FX) shows an "as of" / last-updated date | See "Freshness chip computation (D-07)" code example and `freshness_dates` @rx.var pattern; Don't Hand-Roll table entry on freshness computation |
| FCST-01 | User can select a forecast horizon from 1 to 12 months | See Pattern 1 (slider bound to live-recomputing state) and Pitfall 1 (list-typed slider value) |
| FCST-06 | Forecast values shown in a table (exact numbers per month/series/scenario), not chart-only | See Pattern 3 (series selector) and forecast_table_rows @rx.var recommendation in Primary Recommendation; Validation Architecture test map row FCST-06 |
| VIS-02 | Forecast chart shows base/bull/bear as a shaded confidence band, not three crisp lines | See Pattern 2 (fan chart — two boundary traces + fill='tonexty' + solid top line), full go.Figure code example |
| VIS-03 | All four tracked series visible together on a single dashboard page | Resolved per D-03 (locked decision above) via selector-chart + all-series table combination; see Architectural Responsibility Map and Pattern 3 |
| EXPORT-01 | User can export the current stored price table to an .xlsx file | See "Export event handler (EXPORT-01/D-08)" code example, Pitfall 4 (engine="openpyxl" for BytesIO), Alternatives Considered (rx.download data= vs path) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Horizon selection (slider) | Frontend Server (SSR) — Reflex State | Browser (renders the Radix slider primitive) | `horizon_months` is a Reflex `rx.State` var; the browser only renders/drags the Radix thumb and emits `on_change` events back to the Python process. Reflex's compiled architecture means there is no separate "API" tier here — State methods run in the same backend process. |
| Forecast computation (`forecast_all`) | API / Backend (Reflex event handler calling a framework-independent module) | — | `forecasting.py` is explicitly zero-Reflex (D-08 from Phase 3) — it is a pure backend/business-logic module. `DashboardState` is the sole caller, matching the existing "DB/model access boundary held entirely within state.py" pattern (STATE.md). |
| Fan chart rendering | Frontend Server (SSR) — Reflex `@rx.var` builds the `go.Figure`, `rx.plotly` ships it to browser | Browser (Plotly.js renders/hover) | Same split as Phase 4's `historical_chart_figure`: the Python process constructs the full Plotly figure object server-side; the browser only renders it and handles hover/zoom interactivity client-side via Plotly.js. |
| Forecast table | Frontend Server (SSR) — `@rx.var` + `rx.foreach` | Browser (renders rows) | Read-only, same mechanism as the existing editable table's row rendering minus the edit machinery. |
| Excel export | API / Backend (event handler: pandas + openpyxl, in-memory) | Browser (receives blob download) | File generation must happen server-side (openpyxl is a backend-only library); `rx.download` is Reflex's mechanism for pushing generated bytes to the browser without a persisted file on disk. |
| Freshness ("as of") dates | Frontend Server (SSR) — `@rx.var` computed from `self.rows` | — | Pure derived data from already-loaded `self.rows`, no new DB access needed (D-07's dates are `max(date)` per series over in-memory rows). |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| reflex | ~=0.9.8 (already pinned, confirmed in `app/requirements.txt`) | `rx.slider`, `rx.select`, `rx.plotly`, `rx.download`, `rx.table` | Already the project's framework; no new package. |
| pandas | ~=3.0 (already pinned) | `pd.DataFrame(rows_as_dicts).to_excel(buffer, engine="openpyxl")` for EXPORT-01 | Already the project's data-wrangling library; `forecasting.py` already consumes a `pd.DataFrame` as `history`, so the state layer already builds one from `self.rows` (or must for the forecast call) and can reuse it for export. |
| openpyxl | ~=3.1 (already pinned) | `.xlsx` write engine for `to_excel()` | Already pinned; project's STACK.md explicitly rejects `xlsxwriter` to avoid a second Excel dependency. |
| plotly (`plotly.graph_objects`) | ~=6.9 (already pinned, already imported in `state.py` as `go`) | 3-trace fan chart figure construction | Already used for the historical chart; `go.Scatter` with `fill='tonexty'` is the standard Plotly technique for a shaded band. |

**No new packages required for this phase.** Package Legitimacy Audit is therefore not applicable — see that section below for the explicit statement.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `io.BytesIO` (stdlib) | n/a | In-memory buffer target for `to_excel()` so no file persists on disk | Always for this export — writing to a real path and reading it back is unnecessary I/O and would leave a stale file artifact on the server. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `go.Scatter` fill='tonexty' band | `plotly.express` with a pre-melted long dataframe | px is faster to write for simple line charts (as Phase 4 used it), but px does not have first-class support for asymmetric fill-between-two-traces bands — go.Figure with manually added traces is the standard/only clean way to build a fan chart in Plotly. Stick with `go.Figure`, matching this phase's own D-04 spec language ("two boundary traces with fill='tonexty'"). |
| `rx.download(data=bytes)` | Write to a temp file path + `rx.download(url=...)` | Writing to disk requires a static-file serving route and manual cleanup (stale temp files); `data=` bytes is the documented, simpler path for dynamically generated content and avoids ever touching the filesystem for output that's inherently transient per D-08's "not an on-disk path that persists" requirement. |

## Package Legitimacy Audit

Not applicable — this phase installs zero new external packages. All libraries used (`reflex`, `pandas`, `openpyxl`, `plotly`) are already pinned in `app/requirements.txt` and were audited in prior phases' research. No `slopcheck`/registry verification needed.

## Architecture Patterns

### System Architecture Diagram

```
Browser (Radix slider drag / select change / export click)
        |
        v  Reflex WS event
DashboardState (Reflex backend process, app/app/state.py)
        |
        |-- horizon_months, forecast_series: plain rx.State vars, updated by on_change handlers
        |
        v
@rx.var forecast_chart_figure / forecast_table_rows
        |
        |-- builds pd.DataFrame from self.rows (in-memory, already loaded by load_rows())
        |-- reads markup_pct from AppSetting (loaded once via a new load_markup_pct-style
        |   read, OR cached on state at on_mount alongside load_rows — see Open Questions)
        v
forecasting.forecast_all(history_df, horizon_months, markup_pct)   <-- zero-Reflex, pure function
        |
        |-- forecast_hdan / forecast_ppan_var_system / forecast_diesel_usd / forecast_fx
        |-- diesel_mnt_forecast (derived, no independent fit)
        v
dict[str, list[{"month","base","bull","bear"}]]  (5 keys, P-02 shape)
        |
        |---------------------------------------------------------------+
        v                                                               v
forecast_chart_figure (@rx.var, go.Figure: 3 traces         forecast_table_rows (@rx.var,
for forecast_series only)                                    list of row-dicts across all 5 keys,
        |                                                     transposed month-major for rx.foreach)
        v                                                               v
rx.plotly(data=...)  ------------------------------->  rx.table + rx.foreach  ------> Browser render

separately:
export_to_excel event handler
        |
        |-- pd.DataFrame([row.dict() for row in self.rows]) or column-list construction
        |-- df.to_excel(io.BytesIO(), engine="openpyxl")
        v
rx.download(data=buffer.getvalue(), filename="prices.xlsx")  --> Browser triggers file save
```

### Recommended Project Structure
No new files — this phase extends the existing two files:
```
app/app/
├── state.py   # add horizon_months, forecast_series, forecast_* @rx.var, export_to_excel event handler
└── app.py     # add horizon_slider(), freshness_chips(), forecast_chart(), forecast_table(), export_button() components, appended to index()
```

### Pattern 1: Slider bound to live-recomputing state (D-01/D-02)
**What:** `rx.slider` with `value=[DashboardState.horizon_months]` (list-wrapped — see Pitfall 1), `min=1, max=12, step=1`, `on_change` firing on every drag tick.
**When to use:** D-02 explicitly forbids a separate "Forecast" button — `on_change` (not `on_value_commit`) is required so recompute happens live during drag, not only on release.
**Example:**
```python
# Source: https://reflex.dev/docs/library/forms/slider/ (verified pattern, adapted to list-value contract)
def set_horizon(self, value: list[int]) -> None:
    """on_change fires on every drag tick per D-02; value arrives as a
    single-element list because rx.slider wraps the Radix Slider primitive,
    which always uses an array value even for one thumb."""
    self.horizon_months = value[0]

# component:
rx.hstack(
    rx.text("Forecast horizon", weight="bold", size="2"),
    rx.slider(
        value=[DashboardState.horizon_months],
        min=1,
        max=12,
        step=1,
        on_change=DashboardState.set_horizon,
        size="2",
        width="240px",
    ),
    rx.text(
        DashboardState.horizon_months.to_string() + " month"
        + rx.cond(DashboardState.horizon_months != 1, "s", ""),
        size="2",
    ),
    spacing="2",
    align="center",
)
```

### Pattern 2: Fan chart — two boundary traces + fill='tonexty' + solid top line (D-04/D-05)
**What:** A `go.Figure` with, in this exact trace order: (1) historical gray line (12 trailing months), (2) bear boundary trace with no fill, (3) bull boundary trace with `fill='tonexty'` (fills to the *previous* trace, i.e. the bear trace added just before it — this is why bear must be added before bull, not the reverse), (4) solid accent base line drawn last so it renders on top.
**When to use:** This is the only Plotly technique that produces a shaded band between two arbitrary (non-monotonic-vs-axis) lines; `fill='tozeroy'` or `fill='toself'` are not appropriate here since the band shouldn't touch the x-axis.
**Example:**
```python
# Source: standard Plotly go.Scatter fill='tonexty' pattern (Plotly official docs
# "Filled Area Plots" — https://plotly.com/python/filled-area-plots/), adapted to
# this phase's D-04/D-05 spec (historical + bear + bull + base trace order)
import plotly.graph_objects as go

def _build_fan_chart(hist_dates, hist_values, fc_months, fc_base, fc_bull, fc_bear, label):
    figure = go.Figure()

    # 1. Trailing historical actuals — neutral gray, matches Phase 4's line color
    figure.add_trace(go.Scatter(
        x=hist_dates, y=hist_values, mode="lines",
        line=dict(color="#697177"), name="Historical",
    ))

    # 2. Bear boundary — drawn first, no fill of its own
    figure.add_trace(go.Scatter(
        x=fc_months, y=fc_bear, mode="lines",
        line=dict(width=0), showlegend=False, name="Bear",
    ))

    # 3. Bull boundary — fill='tonexty' fills the gap back to the PREVIOUS
    #    trace (the bear trace above), which is what produces the shaded
    #    band between bull and bear, not a fill down to the x-axis.
    figure.add_trace(go.Scatter(
        x=fc_months, y=fc_bull, mode="lines",
        line=dict(width=0),
        fill="tonexty", fillcolor="rgba(59,130,246,0.15)",  # blue.9 @ ~15%
        name="Forecast band",
    ))

    # 4. Solid base line — added LAST so it draws on top of the band fill
    figure.add_trace(go.Scatter(
        x=fc_months, y=fc_base, mode="lines",
        line=dict(color="#3B82F6", width=2), name="Base forecast",
    ))

    figure.update_layout(
        xaxis_title="Month", yaxis_title=label,
        margin=dict(l=40, r=16, t=16, b=40),
        legend=dict(orientation="h"),
    )
    return figure
```
**X-axis continuity note (D-05):** historical and forecast x-values must be on the same continuous axis (e.g. actual dates for history, and either continued dates or month-index labels appended immediately after the last historical date) so the two segments visually connect rather than appearing as two disjoint charts. Simplest correct approach: convert the forecast rows' `month` (1..horizon) into calendar dates by adding `month` months to the last historical date, so the whole x-axis is one continuous date series — do NOT mix a date-typed historical x-axis with an integer 1..12 forecast x-axis on the same figure, as Plotly will not align them.

### Pattern 3: Series selector reusing Phase 4's exact mechanism (D-03)
**What:** Second `selected_series`-style var + `@rx.var` figure, scoped to the 5 `forecast_all()` keys instead of the 16 `SERIES_ATTRS`.
**Confirmed structure to replicate from `state.py`:** `series_label`/`select_series`/`historical_chart_figure` triad. For the forecast chart, define an analogous `FORECAST_SERIES_LABELS: dict[str, str]` (5 entries: hdan, ppan, diesel_usd_ton, diesel_mnt, fx_rate — note the UI-SPEC's interaction contract item 3 lists exactly these 5, matching `forecast_all()`'s 5 output keys) and a parallel `forecast_series`/`forecast_series_label`/`select_forecast_series` triad — do not conflate this with `selected_series` (Phase 4's historical-chart selector), since they are independent controls per D-06's "two separate chart sections."

### Anti-Patterns to Avoid
- **Calling `forecast_all()` inside the component-building function (`app.py`) instead of a state `@rx.var`:** breaks Reflex's reactivity model — `@rx.var` is the mechanism that re-triggers on `horizon_months`/`forecast_series`/`rows` changes; a plain Python function call in `app.py` would only run once at compile time.
- **Re-deriving `diesel_usd_ton`/`fx_rate` forecasts separately for the chart vs. the table:** call `forecast_all()` once per `@rx.var` evaluation and have both the chart var and the table var read from a single cached intermediate — see Pitfall 2 (double-refit cost) below.
- **Writing the exported `.xlsx` to a real path under the Reflex app directory:** D-08 requires it not persist; always use `io.BytesIO()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Shaded confidence band | Manual SVG/CSS overlay or a second `rx.plotly` layered via CSS | `go.Scatter(fill='tonexty')` two-trace pattern | Plotly's built-in fill mechanism handles hover, zoom, and responsive resize for free; CSS overlay would desync from the chart's zoom/pan state. |
| In-browser file download of generated bytes | A custom `/download/<file>` FastAPI route added manually alongside Reflex's router | `rx.download(data=bytes, filename=...)` | Reflex ships this exact mechanism (Special Events docs) specifically so apps don't need to hand-write a static file server for dynamically generated content. |
| Freshness "as of" date computation | A new DB query or stored "last updated" column | `max(row.date for row in self.rows if getattr(row, attr) is not None)` computed in a `@rx.var` from already-loaded `self.rows` | `self.rows` is already the full, current table (loaded by `load_rows()`); a new column or query would be redundant state to keep in sync. |

**Key insight:** Every mechanism this phase needs (fan chart fill, selector pattern, download trigger, freshness computation) already has a first-class Reflex or Plotly primitive — this phase is assembly, not invention.

## Common Pitfalls

### Pitfall 1: `rx.slider` value is list-typed, not scalar
**What goes wrong:** Binding `value=DashboardState.horizon_months` directly (a plain `int`) to `rx.slider`'s `value` prop, or writing an `on_change` handler that expects a scalar argument.
**Why it happens:** `rx.slider` wraps Radix UI's `Slider` primitive, which always represents its value as an array (to support range/multi-thumb sliders) even when there is exactly one thumb.
**How to avoid:** Bind `value=[DashboardState.horizon_months]` and write the handler as `def set_horizon(self, value: list[int]): self.horizon_months = value[0]`.
**Warning signs:** A TypeError/validation error at compile time about list vs int, or a slider that renders but whose thumb position doesn't match state on load.
**Confidence:** MEDIUM — confirmed via community/docs search describing "a list of two values creates a range slider" (implying single-thumb is also list-shaped), but not directly confirmed against the installed 0.9.8 source in this session. Flagged in Assumptions Log — verify with a quick manual render before committing to this exact shape in the plan's task breakdown.

### Pitfall 2: Double-refitting statsmodels models if chart and table each call `forecast_all()` independently
**What goes wrong:** If `forecast_chart_figure` and `forecast_table_rows` are both separate `@rx.var`s that each independently call `forecast_all(...)`, every render/access refits all 4 statsmodels models (HDAN SARIMAX+exog, PPAN's 12 direct-OLS regressions, 2x auxiliary ARIMA SE fits) twice — doubling CPU cost per interaction, on top of D-06's already-accepted "refit every request" cost.
**Why it happens:** `@rx.var`s are independently memoized by Reflex per access, so two separate vars each calling the same expensive function look correct but silently duplicate work.
**How to avoid:** Define a single `@rx.var forecast_results(self) -> dict` that calls `forecast_all()` once, and have `forecast_chart_figure` and `forecast_table_rows` read from `self.forecast_results` (Reflex will still recompute `forecast_results` once per relevant state change and reuse the cached value within that render cycle — confirm Reflex's `@rx.var` caching semantics recompute once per access cycle, not per every downstream var, per official docs on computed vars).
**Warning signs:** Perceptibly slower UI response than Phase 3's "milliseconds" backtested refit time would suggest; CPU usage doubling when both the chart and table are visible simultaneously.

### Pitfall 3: Assuming `forecast_all()` needs `@rx.background`/async handling
**What goes wrong:** Over-engineering the horizon-slider handler as an `@rx.event(background=True)` task out of caution about blocking the event loop, when D-02's own justification (from Phase 3's backtest) is that refits are millisecond-scale at this data size.
**Why it happens:** Statsmodels fits are CPU-bound and *could* block Reflex's single-threaded event loop for slow models on large datasets, which is a real general concern.
**How to avoid:** Given Phase 3's explicit, backtested D-06 finding ("models refit in milliseconds at this data scale" — a few hundred rows, single-user), a plain synchronous state method is correct and matches every other DB-touching handler already in `state.py` (none use `@rx.background`). Do NOT introduce `@rx.background` speculatively — it adds real complexity (the `async with self` locking pattern) for a cost this project's own research already ruled out. If a future dataset grows enough to make this matter, that's a new research question, not a default to build against now.
**Warning signs:** None expected at current data scale; only revisit if `.fit()` calls are measured to exceed ~200-300ms in practice (Reflex's soft threshold for a UI feeling "live").
**Confidence:** MEDIUM — inference from Phase 3's own backtest finding (HIGH confidence, cited in CONTEXT.md D-02) plus general Reflex background-task guidance (HIGH confidence, official docs); the specific "no background task needed" conclusion for *this* phase is a reasoned extrapolation, not independently re-benchmarked in this research session.

### Pitfall 4: `to_excel()` needs an explicit `engine="openpyxl"` when writing to a `BytesIO` buffer
**What goes wrong:** `df.to_excel(buffer)` without `engine=` can raise or silently pick a different installed engine if more than one Excel-writer package is present, or raise `ImportError` if openpyxl isn't picked up automatically for a buffer target (auto-engine-detection is more reliable for path targets with a `.xlsx` extension than for in-memory buffers with no filename to inspect).
**Why it happens:** pandas infers the engine from the file extension when given a path string; a `BytesIO` object has no extension to infer from.
**How to avoid:** Always pass `engine="openpyxl"` explicitly when the target is a `BytesIO` buffer (STACK.md already recommends this "for clarity/future-proofing" even for path targets — it's load-bearing, not just style, for buffer targets).
**Warning signs:** `ValueError: No engine for filetype: ''` or similar at export time.

### Pitfall 5: `markup_pct` must come from `AppSetting`, not be hardcoded or omitted
**What goes wrong:** Forgetting `forecast_all()`'s third required argument, or hardcoding a placeholder markup value instead of reading the live `AppSetting(key="markup_pct")` row — silently producing wrong Diesel-MNT numbers that don't reflect what the user configured.
**Why it happens:** Phase 4's `DashboardState` never needed to read `AppSetting` (it only touches `PriceRow`), so there's no existing precedent in `state.py` for reading this table — this phase must add the first `AppSetting` read.
**How to avoid:** Add a small helper (e.g. load once in `load_rows()` or a new `load_markup_pct()` called from the same `on_mount`) that does `session.exec(AppSetting.select().where(AppSetting.key == "markup_pct")).first()` and stores `self.markup_pct: float` on state, defaulting sensibly (e.g. `0.0`) if the row doesn't exist yet (no evidence in the codebase that a markup_pct row is seeded — check whether Phase 1/3 already inserts a default row; if not, this phase's plan should handle the missing-row case explicitly).
**Warning signs:** Diesel-MNT forecast values silently off by a fixed percentage; no error, just wrong numbers.

## Code Examples

### Freshness chip computation (D-07)
```python
# Source: derived from existing self.rows pattern in app/app/state.py; no
# external doc citation needed, this is pure Python over already-loaded data.
FRESHNESS_SERIES = ["hdan", "ppan", "diesel_usd_ton", "fx_rate"]  # not diesel_mnt (derived, no own date)

@rx.var
def freshness_dates(self) -> dict[str, str]:
    """Per-series 'as of' date (D-07); '' means no data yet for that series."""
    result: dict[str, str] = {}
    for attr in FRESHNESS_SERIES:
        dated = [row.date for row in self.rows if getattr(row, attr) is not None]
        result[attr] = max(dated) if dated else ""
    return result
```

### Export event handler (EXPORT-01/D-08)
```python
# Source: pandas.DataFrame.to_excel official docs (engine="openpyxl") +
# Reflex Special Events docs (rx.download data= param) — pattern composition,
# not a copy-pasted single source.
import io
import pandas as pd

def export_to_excel(self):
    try:
        records = [row.dict() for row in self.rows]  # confirm rx.Model exposes .dict(); else build manually from SERIES_ATTRS + date
        df = pd.DataFrame(records)
        buffer = io.BytesIO()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        return rx.download(data=buffer.getvalue(), filename="prediction_dashboard_prices.xlsx")
    except Exception:
        # Surface the Copywriting Contract's export-error copy via a transient state var
        self.export_error = "Export failed. Check that the app has write access and try again."
```
**Note on `row.dict()`:** `rx.Model` subclasses SQLModel, which in turn is a Pydantic model — `.dict()`/`.model_dump()` should work, but confirm the exact method name against the installed SQLModel 0.0.39 (Pydantic v1 vs v2 style) before relying on it in the plan; falling back to manually building a dict from `SERIES_ATTRS + ["date"]` (already a proven pattern in `state.py`'s `_commit_draft_cell`) is a safe, zero-risk alternative if `.dict()`/`.model_dump()` behaves unexpectedly.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A | N/A | — | This phase uses stable, long-standing Reflex/Plotly/pandas APIs (`rx.slider`, `go.Scatter(fill=)`, `to_excel`) — no recent breaking changes identified for the pinned versions (reflex 0.9.8, plotly 6.9, pandas 3.0.5). |

**Deprecated/outdated:** None identified specific to this phase's APIs.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rx.slider`'s `value`/`on_change` use a list (`list[int]`) even for a single thumb | Pitfall 1, Pattern 1 | Slider binding code as written would fail to compile/render; low-cost fix (drop the list wrap) but worth a 2-minute manual check before the plan locks this exact signature. |
| A2 | No `@rx.background` needed for the `forecast_all()`-calling handler at this data scale | Pitfall 3 | If wrong, a live-recomputing slider drag could visibly stall the UI during rapid drags; would require retrofitting the async/background pattern — moderate rework, not a redesign. |
| A3 | `row.dict()` (or `.model_dump()`) is the right way to serialize a `PriceRow` for the export DataFrame | Code Examples (Export) | If the method name/behavior differs from assumed, export silently fails or produces malformed columns; safe fallback (manual dict-building from `SERIES_ATTRS`) already exists as a proven pattern in this codebase. |
| A4 | A default `AppSetting(key="markup_pct")` row may or may not already exist from an earlier phase | Pitfall 5 | If no default row exists and the plan doesn't handle it, `forecast_all()` could be called with a wrong/zero markup, producing incorrect Diesel-MNT numbers with no visible error. |

## Open Questions

1. **Does an `AppSetting(key="markup_pct")` row already exist in the DB from an earlier phase (seeded during Phase 1's CSV import) or does Phase 5 need to handle the missing-row / first-run case?**
   - What we know: `models.py` defines the `AppSetting` table; STATE.md confirms "markup_pct lives in AppSetting key/value table" as a Phase 1 decision, but no phase's SUMMARY explicitly confirms a default row was inserted.
   - What's unclear: whether the row is guaranteed present by the time Phase 5 runs.
   - Recommendation: the planner should add an explicit task step to check for and, if absent, seed a sensible default `markup_pct` (e.g. 0 or a value from the design doc) — do not assume the row exists.

2. **Exact `@rx.var` computed-value caching semantics in Reflex 0.9.8 — does calling `self.forecast_results` from two sibling `@rx.var`s within the same render cycle actually dedupe to one `forecast_all()` call, or does each access re-run it?**
   - What we know: Reflex documents computed vars (`@rx.var`) as cached and invalidated on dependency change, matching how Phase 4's single `historical_chart_figure` var already works.
   - What's unclear: whether cross-var reuse within one render (var A reading var B) triggers exactly one recomputation of B, or whether Reflex's dependency graph recomputes B once per distinct *consumer* var per state-change cycle (functionally fine either way for this phase's traffic, but relevant to Pitfall 2's severity).
   - Recommendation: treat as MEDIUM risk, not blocking — even in the worst case (double compute per slider change) this remains "milliseconds x2" per Phase 3's backtest, well within an acceptable live-recompute budget; no need to resolve before planning, just don't over-optimize prematurely.

## Environment Availability

Skipped — this phase has no external service/tool dependencies beyond already-installed Python packages (reflex, pandas, openpyxl, plotly), all confirmed present in `app/requirements.txt` and already exercised by Phases 1-4.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ~=8.0 (pinned in `app/requirements.txt`) |
| Config file | none found — no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section located in `app/` |
| Quick run command | `pytest app/tests/ -x -q` (directory name assumed by convention; confirm actual test location during planning — none was found under `app/` in files read this session) |
| Full suite command | `pytest app/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-06 | Freshness date computed correctly per series from `self.rows` | unit | `pytest app/tests/test_state.py::test_freshness_dates -x` | ❌ Wave 0 |
| FCST-01 | Horizon slider bounds enforced 1-12, forecast recomputes on change | unit/manual | `pytest app/tests/test_state.py::test_set_horizon -x` (bounds); slider drag itself is manual/UI, not automatable without a browser test harness (none present in this project) | ❌ Wave 0 |
| FCST-06 | Forecast table rows contain all 5 series x horizon months x 3 scenario values | unit | `pytest app/tests/test_state.py::test_forecast_table_rows_shape -x` | ❌ Wave 0 |
| VIS-02 | Fan chart figure has exactly 4 traces in the documented order (historical, bear, bull-with-fill, base) | unit | `pytest app/tests/test_state.py::test_forecast_chart_figure_traces -x` | ❌ Wave 0 |
| VIS-03 | Forecast table includes all 4 headline series (hdan, ppan, diesel_mnt, fx_rate) simultaneously | unit | `pytest app/tests/test_state.py::test_forecast_table_includes_all_series -x` | ❌ Wave 0 |
| EXPORT-01 | `export_to_excel` produces a readable `.xlsx` (round-trip via `pd.read_excel` on the returned bytes) with correct row count/columns | unit | `pytest app/tests/test_state.py::test_export_to_excel_roundtrip -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest app/tests/test_state.py -x -q` (scoped to whatever new tests the task adds)
- **Per wave merge:** `pytest app/ -q` (full suite, matching prior phases' pattern implied by `app/requirements.txt`'s pytest pin)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_state.py` (or the project's actual existing test file, if one exists under a different path not surfaced in files read this session — confirm during planning) — needs new test functions for all 6 rows in the table above
- [ ] Framework install: none — pytest already pinned; only test file(s) are missing
- [ ] No `conftest.py` fixtures for building a synthetic `PriceRow` history usable by `forecast_all()`-dependent tests were located — planner should confirm whether Phase 3's own test suite (if any exists under `backend_research/` or elsewhere) already has a reusable synthetic-history fixture worth importing, rather than duplicating one

**Confidence on this section:** LOW — no existing test directory for `app/` was located in the files read during this research session; the planner/executor should do a quick `find app -name "test_*"` at plan time to confirm actual test infra before trusting the paths guessed above.

## Security Domain

Not applicable at meaningful depth — this is a single-user, local, non-authenticated app (explicitly out of scope per REQUIREMENTS.md "Multi-user accounts / authentication"). The one relevant control:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes (already covered by Phase 4's `validate_numeric`/`validate_date`) | `horizon_months` should be clamped/validated to 1-12 server-side in `set_horizon`, not trusted purely from the client-controlled slider event payload — Reflex sliders enforce min/max client-side, but defense-in-depth (a one-line `max(1, min(12, value[0]))` clamp) costs nothing and matches the existing project convention of never trusting raw client input without a state-side check. |

No other ASVS categories are meaningfully applicable (no auth, no session, no crypto, no injection surface — `forecast_all()` and `to_excel()` operate on already-validated internal data).

## Sources

### Primary (HIGH confidence)
- https://reflex.dev/docs/library/forms/slider/ — `rx.slider` props (`value`, `min`, `max`, `step`, `on_change`, `on_value_commit`) and state-binding example, fetched directly
- https://reflex.dev/docs/api-reference/special-events/ — `rx.download` signature (`url`/`data`/`filename`, mutual exclusivity, bytes example), fetched directly
- `app/app/state.py`, `app/app/app.py`, `app/app/forecasting.py`, `app/app/models.py` — read directly, ground truth for existing patterns and the exact contract this phase must call into
- `app/requirements.txt` — confirmed all needed packages already pinned (reflex 0.9.8, pandas 3.0, openpyxl 3.1, plotly 6.9)

### Secondary (MEDIUM confidence)
- WebSearch on `rx.slider` list-value behavior (Radix Slider primitive array-value convention) — consistent with Radix UI's own documented behavior for its underlying Slider primitive, but not independently re-verified against the installed reflex 0.9.8 Python source in this session (see Assumption A1)
- WebSearch on Reflex background tasks / `@rx.event(background=True)` semantics — official docs describe the mechanism correctly; the specific "not needed here" conclusion is this research's own extrapolation from Phase 3's backtest data (see Assumption A2)
- Plotly `fill='tonexty'` fan-chart pattern — standard, widely-documented Plotly technique (plotly.com "Filled Area Plots"), applied here by composition rather than fetched verbatim this session

### Tertiary (LOW confidence)
- None — the Validation Architecture section's test-infra claims were verified via a direct `find app -iname "test_*"` during this session (see Wave 0 Gaps).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages, all already pinned and in active use in the codebase
- Architecture: HIGH — directly extends verified, already-shipped Phase 4 patterns (`@rx.var` figure builder, `selected_series` selector triad, state-as-sole-DB-boundary)
- Pitfalls: MEDIUM — slider value-shape and background-task-necessity claims are reasoned/searched but not independently re-verified against the exact installed 0.9.8 source; flagged in Assumptions Log for a quick manual check during planning/execution
- Validation architecture: HIGH — `app/tests/` (conftest.py, test_state.py, test_forecasting.py, etc.) confirmed present via direct filesystem check

**Research date:** 2026-08-22
**Valid until:** 2026-09-21 (30 days — stable, pinned-version stack; re-check if `reflex` is upgraded past 0.9.8 before this phase executes)
</content>
