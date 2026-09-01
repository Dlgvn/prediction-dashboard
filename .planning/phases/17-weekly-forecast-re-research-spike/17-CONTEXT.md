# Phase 17: Weekly Forecast Re-Research Spike - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Source:** Direct context capture (roadmap/requirements already fully specify this research-only phase; no UI/design gray areas requiring user interview — see rationale below)

<domain>
## Phase Boundary

Research-only spike, no `app/` changes, no weekly UI ships this milestone regardless of
outcome (ROADMAP.md is explicit on this point twice). The phase produces a documented
go/no-go on whether weekly-cadence HDAN/PPAN forecasting can beat the existing monthly-native
VAR benchmark, using genuinely new candidates — not a rerun of the prior no-go.

**Why no interactive discussion:** This phase has no user-facing surface (no UI, no visual
presentation, no interaction design) and the roadmap/requirements already lock the
methodology, the candidates to test, and the exact benchmark to beat. The only decisions
a user could weigh in on are technical/modeling choices, which are Claude's job per
`domain-probes.md`'s own philosophy ("Claude handles: technical implementation details,
architecture patterns — don't ask").
</domain>

<decisions>
## Implementation Decisions

### Prior spike (must not repeat)
- `.planning/quick/20260821-weekly-an-backtest/` ran weekly VAR(HDAN,PPAN) + OLS+Granger
  against `AN Data.csv`'s native weekly rows and `AN price weekly.csv`'s driver set. Result:
  **no-go**. One-step MAPE looked good (3.15%/3.98%) but R² was only 0.03-0.04 (persistence,
  not signal); the horizon-matched 4-week-ahead VAR rollup (10.35%/16.01%) underperformed the
  monthly-native VAR benchmark (**9.49%/10.08%**), especially on PPAN.
- That prior spike's own report (`backend_research/REPORT.md`, "Weekly cadence" section) named
  two specific follow-ups before revisiting — this phase does exactly those two, not a vague
  "try more models":
  1. Test **SARIMAX and Exponential Smoothing at weekly cadence** — the monthly SARIMAX
     exploration (`run_arima_sarimax_wf.py`) and ETS baseline (`run_baseline_ets.py`) were
     never repeated at weekly cadence; only VAR/OLS were tried weekly.
  2. **Resolve the Baltic-AN dedup question** — `AN Data.csv` has its own `Baltic AN` column
     and `AN price weekly.csv` has a separate `BalticAN_wk` column; sanity-check whether
     these are duplicate/overlapping sources (in which case only one should feed any model)
     or genuinely independent signal.
- Do NOT re-test plain weekly VAR(HDAN,PPAN) on the identical monthly-mirrored predictor set,
  and do NOT re-test the same OLS+Granger weekly-driver combination already tried — that is
  the "not a rerun" constraint from ROADMAP.md/WKLY-01 verbatim.

### Methodology (locked, reuse existing harness)
- Reuse `backend_research/walk_forward.py`'s `walk_forward_backtest()` rolling-origin harness
  — the same shared harness Phase 2's monthly research used — rather than hand-rolling a new
  backtest loop. The prior weekly spike's 4-week rollup used an ad-hoc loop with only 9
  rolling-origin windows (explicitly flagged in its own report as "thin... indicative, not
  conclusive"); this phase should get a properly-sized walk-forward window count by using the
  shared harness, matching Phase 2's rigor bar.
- "Horizon-matched" means: forecast weekly-cadence models out to whatever horizon corresponds
  to ~1 calendar month (4-5 weekly steps, matching actual weeks-per-month rather than a fixed
  4), then compare that rolled-forward error against the monthly-native VAR's 1-month-ahead
  MAPE — never compare a raw weekly one-step MAPE directly against the monthly figures (the
  prior report explicitly flags this as an invalid comparison).
- The benchmark to beat is exact and fixed: **HDAN 9.49%, PPAN 10.08%** (monthly-native
  VAR(HDAN,PPAN), Phase 2's winner). The go/no-go report must state a side-by-side comparison
  against these exact figures for each series.
- Candidate model families for this phase: SARIMAX (weekly cadence) and Exponential Smoothing
  (weekly cadence), at minimum. The Baltic-AN dedup resolution is a data-hygiene fix that
  should be tried as a variant driver set on top of whichever model(s) it's relevant to
  (e.g. VAR or a regression variant), not a new model family — it is not one of the two named
  model-family candidates.
- Reuse `backend_research/data_loader.py`'s existing `load_an_weekly()`, `load_weekly_drivers()`,
  `merged_weekly()` — these already exist from the prior spike and need no changes for the
  new model families. Any dedup fix (candidate 2) should be additive (e.g. a documented choice
  of which Baltic AN column to prefer, or an explicit comparison of both) rather than a rewrite
  of these loaders.

### Scope / non-goals
- No `app/` code changes. No weekly-cadence UI ships this milestone even if this spike returns
  a "go" (ROADMAP.md is explicit: "research-only" and "no weekly UI ships this milestone
  regardless of the outcome").
- A "no-go" is a complete, valid, non-blocking outcome for closing WKLY-01/WKLY-02 — same
  discipline as Phase 16's no-go closeout.
- This phase is independent of Phase 16 (already closed, no-go) — no shared code or blocking
  dependency between them.

### Claude's Discretion
- Exact SARIMAX/ETS order search strategy (grid search bounds, seasonal period choice — note
  AN data is native weekly, not necessarily seasonal-daily/weekly in a textbook sense; use
  judgment matching how `run_arima_sarimax_wf.py`/`run_baseline_ets.py` did it at monthly
  cadence, adapted for weekly frequency).
- Whether to test the new model families against `merged_weekly()`'s full driver set as
  exogenous regressors or univariate-only first, then add drivers — pick whichever ordering
  most directly produces a clean go/no-go signal without redundant runs.
- Report structure/format — mirror `backend_research/REPORT.md`'s existing "Weekly cadence"
  section and `backend_research/REPORT-SENTIMENT.md`'s per-series go/no-go table style
  (Phase 16 precedent) for consistency, but the plan can adapt as needed.
- Python environment: system `python3` (verified: pandas 2.2.3, statsmodels 0.14.6, scipy,
  pytest, scikit-learn 1.7.2, arch 8.0.0 all installed and working on this machine as of
  2026-09-01) — same research environment Phase 16 used. Do not use `app/.venv` (pandas 3.0.5,
  wrong environment for `backend_research/` scripts per `ENV.md`).

## Deferred Ideas

None raised — this is a tightly-scoped, pre-specified research phase with no scope-creep
surface (no UI, no new capabilities suggested).
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` (Phase 17 section, lines ~364-375) — goal, success criteria, exact
  benchmark figures
- `.planning/REQUIREMENTS.md` (WKLY-01, WKLY-02) — requirement text
- `.planning/quick/20260821-weekly-an-backtest/SUMMARY.md` and `PLAN.md` — the prior spike
  being extended, not repeated
- `backend_research/REPORT.md` ("Weekly cadence" section, ~line 791) — prior spike's full
  results, the two named follow-ups, and the exact benchmark numbers
- `backend_research/walk_forward.py` — the shared walk-forward harness to reuse
- `backend_research/data_loader.py` (`load_an_weekly`, `load_weekly_drivers`, `merged_weekly`)
  — existing weekly data loaders, reusable as-is
- `backend_research/run_arima_sarimax_wf.py`, `backend_research/run_baseline_ets.py` — the
  monthly-cadence SARIMAX/ETS scripts whose approach adapts to weekly cadence here
- `backend_research/run_var_candidates.py` — source of the 9.49%/10.08% monthly VAR benchmark
  being compared against
- Phase 16 precedent (`.planning/phases/16-sentiment-data-sufficiency-causality-research/`,
  especially `16-02-PLAN.md` and `REPORT-SENTIMENT.md`) — house style for a computed,
  non-hardwired go/no-go verdict with a frozen JSON + deterministic Markdown report
</canonical_refs>
