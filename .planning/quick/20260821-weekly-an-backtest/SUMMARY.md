---
status: complete
---

# Weekly AN backtest — summary

Added `load_an_weekly()`, `load_weekly_drivers()`, `merged_weekly()` to
`backend_research/data_loader.py`, and `backend_research/run_weekly_candidates.py` backtesting
naive/VAR/OLS+Granger at native weekly cadence for HDAN/PPAN, plus a 4-week-ahead rollup for a
fair comparison against the existing monthly VAR winner.

**Result: no-go.** New weekly drivers give a small one-step MAPE improvement (3.15%/3.98% vs
naive's 3.44%/4.66%) but with very low R² (0.03-0.04) — mostly persistence, not signal. The
horizon-matched 4-week-ahead weekly VAR (10.35%/16.01%) underperforms the existing monthly-native
VAR (9.49%/10.08%), especially on PPAN. Weekly-mode deferral in `.planning/STATE.md` stands, but
its rationale is updated: the data-availability gap is resolved, the modeling gap is not.

Updated `backend_research/REPORT.md` (new "Weekly cadence" section) and `.planning/STATE.md`
(blocker note) accordingly. No changes to the Phase 1 app-skeleton work or the roadmap.
