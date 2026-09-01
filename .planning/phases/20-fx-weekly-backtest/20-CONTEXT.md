# Phase 20: FX Weekly Backtest - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Source:** Direct context capture (roadmap/research already fully specify this backend-only
research phase; no UI/design gray areas requiring user interview — see rationale below)

<domain>
## Phase Boundary

Backend-only research/backtest phase, no UI, no app/ changes. Determines whether a
weekly-cadence FX forecasting model can beat the existing monthly FX benchmark, with a
documented, frozen go/no-go verdict. A "no-go" is a complete, valid outcome — if so, FX is
excluded from Phase 22's UI scope (HDAN/PPAN weekly forecasting still ships regardless of
this phase's outcome, since those are already validated by Phase 17).

**Why no interactive discussion:** No user-facing surface. This mirrors Phase 16/17's
precedent exactly (research-only, no UI, methodology and benchmark already locked by
ROADMAP.md/REQUIREMENTS.md). The only decisions left are technical/modeling, which are
Claude's job.

**Independent of Phase 19:** No shared state — Phase 19 seeds `WeeklyPriceRow` into SQLite,
this phase can read `FX Data.csv` directly for its own backtest purposes (backtest scripts
in this project's `backend_research/` convention read source CSVs directly, not the app's
seeded SQLite — see `backend_research/data_loader.py` precedent). Both phases can execute
in parallel.
</domain>

<decisions>
## Implementation Decisions

### Benchmark (locked, exact figure)
- The benchmark to beat is the existing **monthly FX model: 1.72% MAPE** (Naive/AR(1),
  per `app/app/forecasting.py`'s `MODEL_INFO["fx_rate"]` — re-confirm this exact figure by
  reading that constant directly at implementation time, per PITFALLS.md's flagged open
  question, rather than trusting the transcribed number blindly).
- This is a much tighter bar than Phase 17's weekly HDAN/PPAN benchmark (9.49%/10.08%) —
  FX's existing monthly model is already very accurate, so weekly FX may plausibly return
  a no-go even though HDAN/PPAN weekly returned go. Do not assume the outcome; compute it.

### Methodology (locked — mirrors Phase 17's precedent exactly, per PITFALLS.md Pitfall 1, 6)
- Reuse `backend_research/walk_forward.py`'s `walk_forward_backtest()` shared harness —
  the same harness Phase 2 (monthly) and Phase 17 (weekly HDAN/PPAN) both used. Do not
  hand-roll a new backtest loop (flagged in the harness's own docstring as the single most
  dangerous bug class in this codebase).
- At minimum, test **SARIMAX and Exponential Smoothing** at weekly cadence for FX — the
  same two model families Phase 17 validated for HDAN/PPAN (`backend_research/weekly/
  run_weekly_sarimax_ets.py` is the direct structural precedent to mirror for wrapper
  classes/fit_fn shape, per STACK.md's confirmation that the pattern transfers directly).
- Write a **dedicated FX backtest script**, NOT a clone of
  `backend_research/weekly/run_weekly_sarimax_ets.py` with FX bolted on. FX has a very
  different row count (865 vs. HDAN/PPAN's ~206) and needs its own examined
  `MIN_TRAIN_WEEKLY` constant — reusing HDAN/PPAN's `MIN_TRAIN_WEEKLY=104` unexamined is
  explicitly flagged as a pitfall (PITFALLS.md Pitfall 6: "unexamined constant reuse").
  Determine a sensible train window for FX's much longer history from first principles
  (e.g. considering how many origins a given `min_train`/`horizon` combination yields
  against 865 rows), not by copying HDAN/PPAN's value.
- "Horizon-matched" here should follow the same pattern Phase 17 established: report
  results at the horizon that corresponds to roughly 1 month (4-5 weekly steps), so the
  comparison against the monthly 1.72% benchmark is apples-to-apples (never compare a raw
  weekly one-step MAPE directly against a monthly-horizon MAPE, per Phase 17's own
  documented methodology in `backend_research/REPORT-WEEKLY.md`).

### Data source (locked — matches Phase 19's ingestion decisions)
- Source: `FX Data.csv`'s **Weekly** column (865 rows, 2010-01-04 to 2026-07-27, perfect
  7-day cadence). Same parsing hazards apply as documented for Phase 19 (three-cadence
  single-file layout, positional slicing required, thousands-separator cleanup) — this
  phase should parse independently (backtest scripts read CSVs directly per project
  convention) rather than depending on Phase 19's SQLite seeding completing first.

### Output artifacts (locked — mirrors Phase 16/17's precedent)
- Frozen results JSON (e.g. `backend_research/results/weekly_fx.json`) recording each
  candidate's backtested MAPE, mirroring `causality_screen.json`/`sentiment_causality_
  screen.json`/`weekly_sarimax_ets.json`'s existing field-shape conventions in this repo.
- A documented go/no-go verdict, computed (not hardwired) — proven non-hardwired by a test
  that flips a synthetic below/above-benchmark record to the opposite verdict, mirroring
  Phase 16/17's "provably computed, not asserted" test discipline.
- No wall-clock timestamps in generated report content (byte-identical across reruns), if
  a Markdown report is produced — same discipline as `REPORT-SENTIMENT.md`/
  `REPORT-WEEKLY.md`.

### Non-goals
- No forecasting-module wiring (`app/app/forecasting.py` changes) — that's Phase 21, and
  only if this phase returns "go".
- No UI changes — that's Phase 22.
- No changes to `backend_research/weekly/run_weekly_sarimax_ets.py` or its frozen HDAN/PPAN
  results — this phase is additive, testing FX independently.
- Do not re-test or re-derive HDAN/PPAN weekly results here — those are Phase 17's closed,
  frozen output; this phase is FX-only.

### Claude's Discretion
- Exact `MIN_TRAIN_WEEKLY` value for FX (must be justified against FX's 865-row history,
  not copied from HDAN/PPAN's 104).
- Exact SARIMAX/ETS order-search strategy (grid bounds, seasonal period choice) — follow
  the same judgment Phase 17 already exercised for weekly HDAN/PPAN, adapted for FX's much
  longer and denser history.
- Whether to also test a plain univariate AR/Naive weekly baseline as a sanity check
  alongside SARIMAX/ETS (not required by the roadmap's success criteria, which only
  mandates SARIMAX + ETS, but may be useful context for the report).
- Report structure/format — mirror `REPORT-WEEKLY.md`'s existing style for consistency.

## Deferred Ideas

None raised — this is a tightly-scoped, pre-specified research phase with no scope-creep
surface.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` (Phase 20 section) — goal, success criteria, exact requirement
- `.planning/REQUIREMENTS.md` (WKUI-02) — requirement text
- `.planning/research/PITFALLS.md` — Pitfalls 1 (frozen-result discipline), 2/3 (CSV
  parsing), 6 (unexamined constant reuse), all specific to this phase
- `.planning/research/SUMMARY.md` — Phase B (FX Weekly Backtest) synthesis, including the
  flagged gap that FX's model choice is genuinely open (unlike HDAN/PPAN)
- `backend_research/walk_forward.py` — the shared walk-forward harness to reuse
- `backend_research/weekly/run_weekly_sarimax_ets.py` — Phase 17's structural precedent
  for weekly SARIMAX/ETS wrapper classes and fit_fn shape (mirror the pattern, write a
  separate script, do not modify this file)
- `backend_research/REPORT-WEEKLY.md` — Phase 17's methodology for horizon-matching a
  weekly backtest against a monthly benchmark, and report structure precedent
- `app/app/forecasting.py` — source of the exact `MODEL_INFO["fx_rate"]` benchmark figure
  to re-confirm at implementation time
- `FX Data.csv` (repo root) — the data source, verified structure documented in Phase 19's
  CONTEXT.md (same file, same parsing hazards)
</canonical_refs>
