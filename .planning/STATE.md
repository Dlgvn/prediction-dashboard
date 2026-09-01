---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: News/Sentiment Scenarios & Weekly Forecast Research
status: executing
stopped_at: Completed 16-01-PLAN.md
last_updated: "2026-09-01T00:00:00.000Z"
last_activity: 2026-09-01 -- Phase 16 Plan 01 (sentiment data loader) complete
progress:
  total_phases: 18
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-31)

**Core value:** The user can enter a month's actuals, pick a forecast horizon (1-12 months),
and see a chart with three price scenarios (bull/base/bear) for each of the four tracked
series — without opening Excel.

**Current focus:** v2.0 — research whether a news/sentiment-driven adjustment to the
bull/bear scenario bands is viable against the app's real HDAN/PPAN/Diesel-USD/FX series
(Phase 16), re-research whether weekly-cadence HDAN/PPAN forecasting can clear a new
backtest bar with genuinely new variables/model families (Phase 17, research-only — no
weekly UI ships this milestone regardless of outcome), and only if Phase 16 returns a go,
build an additive sentiment-adjusted band + provenance + toggle on the existing fan chart
(Phase 18).

## Current Position

Phase: 16 (Sentiment Data Sufficiency & Causality Research) — In progress
Plan: 16-02 (next)
Status: Plan 01 complete, Plan 02 (causality screen) ready to execute
Last activity: 2026-09-01 -- Phase 16 Plan 01 (sentiment data loader) complete

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 35min | 3 tasks | 9 files |
| Phase 01 P02 | 25min | 3 tasks | 2 files |
| Phase 02 P01 | 12min | 2 tasks | 4 files |
| Phase 02 P02 | 25min | 2 tasks | 3 files |
| Phase 02-model-research-backtesting P03 | 12min | 2 tasks | 3 files |
| Phase 02-model-research-backtesting P04 | 20min | 2 tasks | 4 files |
| Phase 02-model-research-backtesting P05 | 35min | 2 tasks | 2 files |
| Phase 02-model-research-backtesting P06 | 25min | 2 tasks | 2 files |
| Phase 02-model-research-backtesting P07 | 5min | 3 tasks | 4 files |
| Phase 03-forecasting-module-derived-series P01 | 25min | 2 tasks | 3 files |
| Phase 03 P02 | 20min | 2 tasks | 2 files |
| Phase 03 P03 | 15min | 2 tasks | 2 files |
| Phase 03 P04 | 40min | 3 tasks | 2 files |
| Phase 04 P01 | 10 | 2 tasks | 2 files |
| Phase 04 P02 | 15min | 3 tasks | 2 files |
| Phase 04 P03 | 15min | 2 tasks | 2 files |
| Phase 04 P04 | 55min | 3 tasks | 4 files |
| Phase 05 P01 | 35min | 3 tasks | 2 files |
| Phase 05 P02 | 25min | 3 tasks | 2 files |
| Phase 05 P03 | 20min | 3 tasks | 2 files |
| Phase 05 P04 | 10min | 3 tasks | 1 files |
| Phase 06-ux-ui-redesign P01 | 35 min | 3 tasks | 4 files |
| Phase 06-ux-ui-redesign P02 | 45 min | 3 tasks | 2 files |
| Phase 06-ux-ui-redesign P03 | 55min | 3 tasks | 7 files |
| Phase 07-table-pagination-windowing P01 | 15min | 3 tasks | 2 files |
| Phase 07-table-pagination-windowing P02 | 15min | 3 tasks | 2 files |
| Phase 08-forecast-context-enrichment P01 | 35min | 3 tasks | 2 files |
| Phase 08-forecast-context-enrichment P02 | 25min | 3 tasks | 2 files |
| Phase 09-excel-export-polish P01 | 25min | 2 tasks | 2 files |
| Phase 10-csv-bulk-import P01 | 20 min | 2 tasks | 2 files |
| Phase 10-csv-bulk-import P02 | 25 min | 2 tasks | 2 files |
| Phase 10-csv-bulk-import P03 | 45 min | 3 tasks | 2 files |
| Phase 11-background-fix-theme-toggle P01 | 25min | 2 tasks | 3 files |
| Phase 11-background-fix-theme-toggle P02 | 25min | 3 tasks | 3 files |
| Phase 11-background-fix-theme-toggle P03 | 35min | 3 tasks | 2 files |
| Phase 12-fan-chart-legend-axis-fix P01 | 55min | 3 tasks | 2 files |
| Phase 13 P01 | 20min | 2 tasks | 4 files |
| Phase 13 P02 | 15min | 2 tasks | 2 files |
| Phase 14-tab-nav-bar P01 | 15min | 2 tasks | 2 files |
| Phase 14-tab-nav-bar P02 | 25min | 2 tasks | 2 files |
| Phase 15 P01 | 15min | 1 tasks | 2 files |
| Phase 15 P02 | 25min | 2 tasks | 2 files |
| Phase 16-sentiment-data-sufficiency-causality-research P01 | 35min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Reflex + SQLite single-process monolith (not split FastAPI service, not Postgres)
- Init: Fresh model design/research rather than porting the Excel workbook's exact coefficients
- Init: v1 scenarios = base ± statistical spread; live news/sentiment integration deferred to v2
- Init: No file-upload UI in v1 — manual in-app entry + Excel export instead
- [Phase ?]: 01-01: markup_pct lives in AppSetting key/value table, never on PriceRow (D-04)
- [Phase ?]: 01-01: 16-series PriceRow schema per D-05b/D-05c supersession (natural_gas split into 4 named benchmarks, urea split into black_sea/china)
- [Phase ?]: 01-02: D-06b averaging (not .last()) applied uniformly to both AN Data.csv and AN price weekly.csv
- [Phase ?]: 01-02: AN price weekly.csv seeded as authoritative 10-column source per D-07b, both urea benchmarks kept separate per D-05c
- [Phase ?]: NULL-to-blank rendering uses rx.cond(value != None, value, '') per-cell — a Var-level conditional, since Reflex renders Vars client-side
- [Phase ?]: DB-access boundary held entirely within state.py — DashboardState is the app's sole rx.session() call site
- [Phase 02-01]: pandas 2.2.3/scikit-learn 1.7.2 installed, not STACK.md's 3.0.5/1.9.0 pins — research code written to pandas 2.x semantics
- [Phase 02-01]: walk_forward.py is the single shared rolling-origin harness (model-agnostic) reused by every Phase 2 model runner; LeakageError raised eagerly, not just commented
- [Phase ?]: 02-02: fx_rate re-tested (not assumed) against expanded predictor set — now shows real p<0.10/p<0.05 predictors, overturning prior no-predictor finding
- [Phase ?]: 02-02: no target-pair cointegration found at p<0.05 — VECM_CANDIDATES empty, plan 02-05 proceeds with plain VAR
- [Phase ?]: arch==8.0.0 approved at package-legitimacy checkpoint after manual PyPI/GitHub verification; SUS flag was a false positive
- [Phase ?]: GARCH(1,1) only per Assumption A4, no EGARCH/GJR sweep
- [Phase 02-04]: Baselines fitted on price levels not pct-change; ARIMA order fixed once by AIC and held fixed for the whole walk-forward run
- [Phase ?]: 02-05: VECM_CANDIDATES empty per 02-02 finding; wrote explicit non-applicability record instead of skipping the family
- [Phase ?]: 02-05: iterative VAR family shows explosive MAPE at long horizons for several series due to short-overlap predictor data; direct-OLS VAR variant stays bounded and is likely the safer family choice
- [Phase ?]: 02-06: ML baseline (RandomForest/GradientBoosting) does not clearly beat naive on diesel/fx and is flagged suspiciously_strong/small_sample on hdan/ppan; overfitting diagnostics attached as data per D-01
- [Phase 02-07]: Final winners accepted by human review: HDAN=SARIMAX(0,1,0)+exog (13.33% MAPE, GARCH vol), PPAN=Direct-OLS VAR-system [ppan,hdan,baltic_an,urals] (23.8% MAPE, ARIMA-SE vol), Diesel-USD=Naive (7.04% MAPE), FX=Naive (1.72% MAPE); MIN_ML_ORIGINS=5 thin-sample exclusion approved as an addition to the plan's literal overfit-flag rule
- [Phase 02-07]: Phase 2 complete — FCST-07 satisfied; Phase 3 must hard-code these winners from 02-MODEL-DECISIONS.md, no re-search at runtime
- [Phase ?]: 03-01: forecasting.py primitives complete; provenance comments intentionally kept despite literal-grep conflicts (see SUMMARY deviations)
- [Phase 03-02]: Ammonia lag-3 predictor uses last 3 observed actuals for future steps 1-3, only switching to forecast path at step 4+ (03-RESEARCH.md Pattern 1 was wrong to generalize the lag-1 case)
- [Phase ?]: PPAN uses Direct-OLS VAR-system (twelve per-horizon OLS regressions), not iterative statsmodels VAR() -- per 02-MODEL-DECISIONS.md binding spec and 03-03-PLAN.md planner_correction
- [Phase ?]: 03-04: forecast_ppan_var_system now selects the last row with all system-member features observed (dropna), not the literal last calendar row
- [Phase ?]: 04-02: SERIES_ATTRS tuple in state.py is single source of truth for 16 series columns, reused by draft-row promotion and future chart selector (04-04)
- [Phase ?]: 04-03: Combined Task1/Task2 edits in one app.py pass, committed separately to preserve plan task-level commit granularity
- [Phase 04-04]: SERIES_LABELS/LABEL_TO_ATTR promoted to state.py as single source of truth for series display labels; app.py rebuilds _COLUMNS from it instead of hardcoding
- [Phase 04-04]: Phase 4 complete — VIS-01 and DATA-05 satisfied; human checkpoint approved full add/edit/delete/persist/chart flow, including a to_string() quote-wrapping bug fixed during verification
- [Phase 05]: 05-01: forecast_results empty/error shape is {key: [] for key in FORECAST_SERIES_LABELS} — 05-02 indexes all 5 keys unconditionally
- [Phase 05]: 05-01: row.model_dump() misbehaves on PriceRow during export; _export_bytes builds records manually from date+SERIES_ATTRS instead
- [Phase ?]: 05-02: diesel_mnt historical values in forecast_chart_figure use the exact same diesel_usd*fx*(1+markup_pct/100) convention as forecasting.py's diesel_mnt_forecast
- [Phase ?]: 05-02: FORECAST_TABLE_COLUMNS derived programmatically from FORECAST_SERIES_LABELS x scenario names
- [Phase ?]: 05-03: Task 1+2 combined into one app.py commit per 04-03 precedent; test_index_on_mount_loads_markup_pct uses inspect.getsource since render() doesn't surface on_mount
- [Phase ?]: 05-04: Human-verified v1 acceptance gate approved in-browser; Phase 5 requirements ledger closed out, marking v1 scope fully complete
- [Phase ?]: Design tokens locked in app/theme.py; summary_cards derives from existing forecast_results with no new state var — Follows D-05..D-13 contract from 06-UI-SPEC.md/06-CONTEXT.md
- [Phase ?]: Arrow glyphs come from state data (Var-driven), not literal app.py strings; verified UP/DOWN hex cond wiring instead
- [Phase ?]: Hex-color regression test scoped to app.py source text, not rendered index() page, since Plotly figures embed their own default colorway hexes
- [Phase ?]: Darkened UP/ACCENT/BORDER tokens within their original hues to meet WCAG AA contrast; recorded ratios in UI-SPEC — 3 of 5 checked color pairings failed AA thresholds; no new accent color introduced per plan constraint
- [Phase ?]: Pinned Radix theme to appearance=light in rxconfig.py plugins — App silently inherited OS dark-mode preference, breaking text legibility while custom light backgrounds stayed hardcoded; found during Task 3 human verification
- [Phase 07-table-pagination-windowing]: 07-01: visible_rows/history_window_caption are separate small @rx.var properties, not embedded in an existing var, so Reflex only recomputes what changed — Follows PITFALLS.md Pitfall 8 guidance
- [Phase 07-table-pagination-windowing]: 07-02: data_table() render layer repointed to visible_rows; empty-state predicate deliberately kept on full rows/draft_rows counts so windowing never triggers a false empty state — Prevents windowing (a display concern) from leaking into the DB-emptiness check, per ARCHITECTURE.md integration note
- [Phase 08-forecast-context-enrichment]: 08-01: _actual_series_for(key) is now the sole diesel_mnt derivation site, replacing duplicated multiplier loops in _latest_actual_for and forecast_chart_figure; summary_cards high/low and YoY both reuse it, always reading self.rows (never visible_rows)
- [Phase 08-forecast-context-enrichment]: 08-01: YoY matches by calendar-month (YYYY-MM date prefix), not a 12-row offset, so history gaps and non-day-01 dates still compare the correct prior-year month; empty (not "N/A") when not computable per D-03
- [Phase 08-forecast-context-enrichment]: 08-02: YoY row is never wrapped in its own rx.cond — label always renders, only the value string is empty in the non-computable case, so card height never jumps; high/low value carries no directional color since it has no sign
- [Phase 09-excel-export-polish]: 09-01: _forecast_export_records reads forecast_table_rows (never forecast_all/forecast_results) so export/screen parity is structural, not coincidental; empty forecast yields a header-only Forecast sheet via explicit columns=
- [Phase 10-csv-bulk-import]: 10-01: parse_import_csv gates header/size/row-count before any row parsing (D-06); duplicate-date and invalid-value skips counted separately (D-04), both delegated entirely to validators.py
- [Phase 10-csv-bulk-import]: 10-02: confirm_import is structurally insert-only (no session.merge/setattr/select-then-update) so duplicates already excluded by the parser can never overwrite an existing row (IMPORT-02); import_added_count recomputed from len(self.rows) growth post-load_rows(), not the parse-time count
- [Phase 10-csv-bulk-import]: 10-03: Confirm import uses color_scheme="blue" not the red two-click delete-confirm pattern, since import only ever inserts and never overwrites; human verification directly queried SQLite (not just the UI) to prove IMPORT-02's non-overwrite guarantee
- [Phase 11-background-fix-theme-toggle]: 11-01: theme.LIGHT dict references existing flat constants (not re-typed literals) so there is exactly one source-of-truth value per light color; contrast-ratio helper lives in test_theme_tokens.py, not theme.py, to preserve theme.py's zero-import contract
- [Phase 11-background-fix-theme-toggle]: 11-02: default_color_mode="light" (top-level rx.Config kwarg) is the real OS-inheritance guard, replacing the rx.theme(appearance="light") pin that 11-RESEARCH.md proved is stripped at render by Theme._render()
- [Phase 11-background-fix-theme-toggle]: 11-02: DashboardState.theme_mode persists via its own "pd_theme_mode" localStorage key (not Reflex's built-in "theme" key); both Plotly figure builders now resolve every color through tokens(self.theme_mode)
- [Phase 11-background-fix-theme-toggle]: 11-03: rx.App(style={"html, body": {...}}) cannot carry a reactive backend Var — it compiles into a plain top-level JS module (utils/theme.js) with no React component context, so the state hook a Var needs is never injected; fixed by rendering an in-tree rx.el.style element as index()'s first child instead, verified against a passing `reflex export --frontend-only --no-zip` build
- [Phase 11-background-fix-theme-toggle]: 11-03: Assumption A2 (rx.icon_button firing a two-item on_click=[StateEvent, rx.toggle_color_mode] list in order) verified true in the compiled render tree — no single-handler fallback event needed
- [Phase 11-background-fix-theme-toggle]: Phase 11 complete — THEME-01 through THEME-04 all human-verified in a live browser (light-default under OS dark preference, no black margins at 1440px in either mode, single-click dual-mechanism toggle, dark legibility, persistence with both localStorage keys in sync)
- [Phase 12-fan-chart-legend-axis-fix]: 12-01: Plotly `legend.y` is a plot-domain fraction, not an absolute pixel offset — growing `margin.b` shrinks the plot's data area, so the same y-fraction yields less absolute pixel separation at narrower/shorter viewports; fixing cross-viewport legend/axis overlap required tuning `legend.y` itself (final value -0.55), not just margin
- [Phase 12-fan-chart-legend-axis-fix]: Phase 12 complete — VIS-04 satisfied; human-verified no legend/axis-title overlap at 1440px/768px/390px with a safe ~12px buffer at the narrowest width, no color regression from Phase 11
- [Phase 13-model-provenance-display]: 13-01: MODEL_INFO frozen constant in forecasting.py is single source of truth for model provenance; summary_cards model_text sourced exclusively from it, diesel_mnt carries None MAPE — VIS-05 — avoids PITFALLS.md Pitfall 4 (hand-typed duplicate model names/percentages drifting from backtest source)
- [Phase 13-model-provenance-display]: 13-02: Model line placed as the last line on each summary card, directly after YoY, per D-02 locked card line order; no arrow/color/font-weight (mirrors high/low line styling); aria_label extended as a single chained expression
- [Phase 13-model-provenance-display]: Phase 13 complete — VIS-05 satisfied; human-verified all 4 model lines character-for-character in a live browser in both light and dark mode, at 390px mobile width with no overflow
- [Phase 14-tab-nav-bar]: 14-01: active_section is a plain (non-persisted) base var per D-03 — always resets to "summary" on fresh load; set_active_section only assigns active_section and calls rx.call_script for scroll-to-top (rx.scroll_to needed a specific elem_id, unsuitable here), proven by source-inspection tests to never touch the edit/delete/draft-row/CSV-import state machine or re-trigger data loads
- [Phase 14-tab-nav-bar]: 14-02: index() panel switching uses rx.match(active_section, ...) rather than nesting rx.tabs.content inside nav_bar() — keeps every section factory called exactly once in one place; historical_section()+data_entry_section() grouped in a new _data_entry_tab() helper per D-01
- [Phase 14-tab-nav-bar]: Phase 14 complete — NAV-01 satisfied; human-verified live in browser that mid-edit cell state and mid-CSV-import-preview both survive a tab switch, on_mount fires exactly once, no full page reload, sticky bar, keyboard nav, both themes, D-01 grouping all confirmed
- [Phase 15-01]: start_edit guard only applies inside start_edit; Escape and window-toggle remain unconditional overrides
- [Phase 15-02]: rx.input(type="date") confirmed via installed reflex_components_radix TextFieldRoot source to pass `type` straight through and fire on_change with the native control's raw value string; _editable_cell branches a single shared input_kwargs dict on attr == "date" so every other column stays byte-identical
- [Phase 15-02]: Phase 15 complete — DATA-09 and DATA-10 both satisfied; human-verified live in browser: valid/duplicate date commit, error-survives-click-away (15-01 race fix), Escape recovery, in-place date edit, windowing-toggle-mid-error, and CSV-import-mid-draft-error, all passed with no corruption
- [v2.0 roadmap]: Sentiment (Phase 16) and weekly (Phase 17) research spikes are independent, sequenced as parallel-eligible phases; Phase 18 (sentiment UI) is strictly gated on Phase 16 returning a "go" and will be dropped from the milestone (not built degraded) if Phase 16 returns "no-go"
- [v2.0 roadmap]: No weekly UI phase exists in this milestone — WKLY-01/WKLY-02 close via Phase 17's research report alone; weekly UI is deferred to its own future milestone regardless of Phase 17's outcome, per REQUIREMENTS.md v2.1+ Deferred section
- [Phase 16-01]: weighted_compound/sent_ema3/sent_ema10/sent_momentum rebuilt from raw article timestamps corrected to Mongolia-local (UTC+8), never resampled from archive/news_sentiment_daily.csv (date-only, UTC-day-bucketed, cannot be corrected after the fact); vix_regime_code bucketed on ml_features.csv's own US-trading-day calendar with no MN_OFFSET shift
- [Phase 16-01]: merge_lagged() reindexes the gappy predictor onto the dense target index by calendar label before shifting, includes y_lag1 in its dropna so its row count equals causality_screen.granger_ftest()'s true effective n, and raises walk_forward.LeakageError (reused, not a parallel exception class) on lag<1 or non-monthly indexes

### Pending Todos

- [v1.2] Data Entry table renders all 167 rows × 17 columns (~2,950 editable cells) unpaginated —
  confirmed via browser DOM inspection during dogfooding (2026-08-23). Root cause of the "doesn't
  work" report: this scale of interactive DOM makes the table hang/unresponsive. Fix direction
  chosen by user: default to recent months + a "show all history" toggle. RESOLVED in v1.2 Phase 7.

- [v1.3] Data Entry silent-validation bug — RESOLVED in Phase 15 (2026-08-25): root cause was the
  `start_edit` click-away race (fixed in 15-01), and the entry UX itself was reworked in 15-02 to
  a native HTML5 date picker so no free-text ISO format is ever required. Human-verified both the
  race fix and the picker swap live in-browser, including windowing-toggle and CSV-import
  regression scenarios.

### Blockers/Concerns

- Weekly forecast mode is explicitly deferred to v2. Update 2026-08-21: the data-availability
  half of this blocker is resolved — `AN Data.csv` is native weekly for HDAN/PPAN, and
  `AN price weekly.csv` adds real weekly drivers (Middle East Ammonia, Black Sea/China Urea, gas
  benchmarks). But the backtest (backend_research/REPORT.md, "Weekly cadence" section) is a
  no-go: weekly-native VAR rolled 4 weeks forward underperforms the existing monthly VAR
  (10.35%/16.01% vs 9.49%/10.08% MAPE), so the deferral stands. No weekly Diesel/FX data exists
  at all, unchanged. Phase 17 (v2.0) re-researches this with genuinely new candidates before any
  future weekly-UI milestone can be considered.

- Model family selection (ARIMA/SARIMAX/VAR vs. ML baseline) is genuinely open — Phase 2 must
  produce real backtest results, not a formality, before Phase 3 forecasting logic is built.

- Confidence-band methodology (backtest MAPE vs. model-native forecast SE) needs a concrete
  design decision during Phase 3 planning.

- [v2.0] Sentiment relevance is genuinely unresolved going into Phase 16 — research (SUMMARY.md)
  found the `archive/` sentiment dataset is a generic US-equity-market (SPY/QQQ/DIA/VIX) news
  corpus with zero ammonium nitrate/diesel/Mongolia/tugrik content, and its dense daily coverage
  is only ~2 months wide (a NewsAPI free-tier artifact), not the 6-year span its date range
  implies. A "no-go" from Phase 16 is a likely, valid, and complete outcome — Phase 18 should not
  be started speculatively ahead of that result.

## Session Continuity

Last session: 2026-08-31T04:59:10.539Z
Stopped at: Phase 16 context gathered
Resume file: .planning/phases/16-sentiment-data-sufficiency-causality-research/16-CONTEXT.md
