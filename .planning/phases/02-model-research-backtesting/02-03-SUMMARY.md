---
phase: 02-model-research-backtesting
plan: 03
subsystem: model-research
tags: [garch, arch, volatility, statsmodels, pandas]

# Dependency graph
requires:
  - phase: 02-model-research-backtesting
    provides: "db_loader.py's SQLite-backed load_price_history() and TARGETS list (02-01)"
provides:
  - "GARCH(1,1) conditional volatility forecasts per target series (hdan, ppan, diesel_usd_ton, fx_rate) across horizons 1-12"
  - "Per-series convergence, widening, and origin-stability diagnostics for Phase 3's bull/bear spread selection"
  - "research-only requirements-research.txt separating arch/scikit-learn from the shipped app's requirements"
affects: [03-phase3-forecasting-charting, 02-07-assemble-report]

# Tech tracking
tech-stack:
  added: [arch==8.0.0]
  patterns: ["Research-only pins live in backend_research/requirements-research.txt, never in app/requirements.txt", "GARCH fit on pct_change() * 100 returns, not price levels"]

key-files:
  created: [backend_research/run_garch.py, backend_research/results/garch_volatility.json, backend_research/requirements-research.txt]
  modified: []

key-decisions:
  - "arch==8.0.0 approved at the [SUS] package-legitimacy checkpoint after manual PyPI/GitHub verification (bashtage/arch, ~10yr history)"
  - "GARCH(1,1) only, no EGARCH/GJR sweep, per Assumption A4 — sample too small to support richer variants"
  - "Non-widening or origin-unstable GARCH results are reported as explicit flags rather than smoothed over, per PITFALLS.md Pitfall 3"

patterns-established:
  - "Convergence, widening, and origin-stability are all explicit reportable fields, not silently assumed"

requirements-completed: [FCST-07]

# Metrics
duration: 12min
completed: 2026-08-21
---

# Phase 2 Plan 03: GARCH Volatility Research Summary

**GARCH(1,1) conditional volatility fitted per series via the human-verified `arch` package, with per-horizon sigma, convergence, and origin-stability diagnostics written to garch_volatility.json for Phase 3's bull/bear spread.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-21T05:50:00Z (approx, prior session context)
- **Completed:** 2026-08-21T06:02:44Z
- **Tasks:** 2 (checkpoint + auto)
- **Files modified:** 3 created

## Accomplishments
- Human verified `arch==8.0.0` legitimacy at the blocking checkpoint (PyPI project page, bashtage/arch GitHub repo, maintainer match) — [SUS] flag resolved as false positive
- Installed `arch` behind a research-only `requirements-research.txt`, kept separate from `app/requirements.txt`
- Fit GARCH(1,1) on percent returns for all four target series; all four converged and are viable
- Recorded per-horizon sigma (1-12), non-decreasing/widening check, and a three-origin (0/12/24-month) stability check per series

## Task Commits

Each task was committed atomically:

1. **Task 1: Package legitimacy gate** - approved by human (no code change; verification recorded here)
2. **Task 2: Install arch and fit GARCH(1,1) per series** - `8c6aeb8` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `backend_research/requirements-research.txt` - Research-only pins (arch==8.0.0, scikit-learn==1.7.2) with explicit "not a runtime dependency" header
- `backend_research/run_garch.py` - `fit_garch`, `garch_horizon_sigma`, `main`; per-series GARCH(1,1) fit, convergence/widening/stability diagnostics
- `backend_research/results/garch_volatility.json` - Per-series results: n_returns, converged, convergence_flag, warnings, viable, sigma_by_horizon, widening (if false), stable_across_origins, note

## Decisions Made
- Task 1 checkpoint: **approved**. Human confirmed via PyPI (https://pypi.org/project/arch/) that the project description, multi-year release history (since well before this project), and Homepage/Source link to `bashtage/arch` on GitHub all check out; maintainer `bashtage` (Kevin Sheppard) also owns `linearmodels`, consistent with a legitimate long-standing econometrics maintainer. The `[SUS]` name-similarity flag (arch vs torch) was confirmed a false positive.
- Kept GARCH strictly to (1,1) per Assumption A4 — no order search, matching the small-sample constraint already used elsewhere in Phase 2 research.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**GARCH results are not uniformly clean, and that is by design, not a bug:**
- `ppan`: sigma at h=1 (12.496) is slightly *higher* than at h=12 (11.756) — recorded with `"widening": false` and an explanatory note per the plan's PITFALLS.md Pitfall 3 requirement. This is a legitimate GARCH(1,1) mean-reversion-in-variance outcome on a 47-observation series, not smoothed over.
- `diesel_usd_ton` and `fx_rate`: horizon-1 sigma is not stable across the three refit origins (>50% relative spread), flagged `"stable_across_origins": false`. Both series still converged and produced widening sigma sequences at the current origin, so they remain `"viable": true`, but Phase 3 should treat their GARCH bands with caution given this instability, or prefer the ARIMA-forecast-SE fallback for those two series specifically if a more robust band is needed.
- `hdan` and `ppan` (both 47 return observations, the shorter AN-family history) converged cleanly and passed the stability check for `hdan`; `ppan` converged but showed non-widening sigma. No series required the `arima_forecast_se` fallback outright — all four are technically viable, but two carry caution flags for Phase 3 to weigh.

These are exactly the kind of "documented convergence/behavior findings, not silently accepted" outcomes the plan's must_haves called for.

## Next Phase Readiness

- Phase 3's horizon-widening bull/bear spread has a per-series, per-horizon volatility source in `backend_research/results/garch_volatility.json`, with explicit caution flags (`widening`, `stable_across_origins`) that Phase 3 planning should read before choosing GARCH vs. the ARIMA-forecast-SE fallback per series.
- No blockers. `arch` is installed and pinned only in the research-only requirements file; the shipped app's `requirements.txt` was not touched.

---
*Phase: 02-model-research-backtesting*
*Completed: 2026-08-21*

## Self-Check: PASSED
