---
phase: 16-sentiment-data-sufficiency-causality-research
plan: 02
subsystem: backend_research/sentiment
tags: [sentiment, granger-causality, data-sufficiency, research, close-out]
requires: [load_sentiment_monthly, merge_lagged, SENTIMENT_PREDICTORS]
provides:
  - run_sentiment_causality_screen
  - series_verdict
  - write_report
  - SENTIMENT_JSON
  - REPORT_PATH
  - LAGS
affects: []
tech-stack:
  added: []
  patterns:
    - "Reuse causality_screen.granger_ftest/_tier/MIN_GRANGER_N by import, never redefine (D-01/D-05 structural guarantee)"
    - "Project a gappy predictor onto the target's dense index once, then reuse that same series for both merge_lagged and granger_ftest so a positional .shift(lag) is a true calendar lag"
    - "Deterministic report generation: no wall-clock content, plain f-string Markdown assembly, written with explicit encoding='utf-8'"
key-files:
  created:
    - backend_research/sentiment/run_sentiment_causality_screen.py
    - backend_research/sentiment/test_sentiment_causality_screen.py
    - backend_research/results/sentiment_causality_screen.json
    - backend_research/REPORT-SENTIMENT.md
  modified: []
decisions:
  - "app/reflex.db (gitignored, not present in this checkout) was rebuilt from the checked-in AN Data.csv/AN price weekly.csv/Diesel Data.csv sources using a one-off scratchpad script mirroring app/app/seed.py's parse/collapse/merge logic exactly (without importing reflex/sqlmodel, which are not installed in the research Python) — this was a blocking-issue auto-fix (Rule 3), not a plan deliverable; no file under app/ or backend_research/ was created or modified by it, and it is not tracked in the repo."
  - "write_report() and json.dump both write with explicit encoding='utf-8' (Rule 1 bug fix) — Python's default open() encoding on this Windows environment is the system codepage, not UTF-8, which corrupted the report's em-dash characters on first generation."
metrics:
  duration: "~50 min"
  completed: "2026-09-01"
---

# Phase 16 Plan 02: Sentiment Causality Screen & SENT-01/SENT-02 Close-out Summary

Ran the real Granger causality screen (60 target x predictor x lag combinations) against
the app's live HDAN/PPAN/Diesel-USD/FX price history and Plan 01's monthly sentiment
predictors, computed a per-series go/no-go verdict, and froze the result — all four
series come back "no-go" because every combination's effective monthly overlap (14-19)
sits below `MIN_GRANGER_N=24`, exactly as RESEARCH.md's measurement predicted, but the
verdict is a genuinely computed branch, proven non-hardwired by tests that make a
synthetic p05/p10 record flip to "go".

## What Was Built

- `backend_research/sentiment/run_sentiment_causality_screen.py`:
  - `run_sentiment_causality_screen()` — nested loop over `TARGETS` (4) x
    `SENTIMENT_PREDICTORS` (5) x `LAGS` (1-3) = 60 combinations. Targets enter as
    percent-changed `db_loader` series; sentiment predictors enter as LEVELS (never
    pct-changed — `weighted_compound` is bounded [-1, 1] and crosses zero). For each
    combination, the sentiment predictor is reindexed onto the target's dense monthly
    index once, then that same series is passed to both `merge_lagged` (effective-N
    measurement) and `granger_ftest` (the F-test), so `granger_ftest`'s positional
    `.shift(lag)` is provably a calendar-month lag. `MIN_GRANGER_N`, `_tier`, and
    `granger_ftest` are imported unchanged from `causality_screen.py` — never
    redefined — so the sentiment bar is identical to every other predictor's bar
    (D-01/D-05). A `ValueError` guards that `merge_lagged`'s measured `n_overlap`
    always equals `granger_ftest`'s own regression `n`. Writes 60 records to
    `results/sentiment_causality_screen.json`.
  - `series_verdict(records, target)` — per-target (D-04) reduction mirroring
    `shortlist_for()`'s dedup: best (lowest-p) record per predictor (D-02, no
    cross-lag agreement required; `p is None` records never win), `qualifying` =
    those at tier `p05`/`p10` (D-03, no sign/direction filter), `verdict` =
    `"go"` if any qualify else `"no-go"`, `max_effective_n` reported, and a
    `reason` string distinguishing "insufficient sample size" (every record
    below-floor) from "no predictor reached p<0.10" (records present but none
    qualify) from naming the qualifying predictors.
  - `write_report(records, sentiment)` — assembles and writes
    `REPORT-SENTIMENT.md` deterministically (no wall-clock content anywhere in
    the body): title, provenance paragraph, glance table, effective-N table
    with coverage-context caveat, methodology bullets, one per-series detail
    subsection (`### {label} — Go/No-Go: {verdict}`) with all 15 of that
    target's records, and a closing "what would change this result" paragraph.
  - `__main__` block runs the sweep, prints the summary, and writes the report.

- `backend_research/sentiment/test_sentiment_causality_screen.py` — 9 tests:
  6 `series_verdict` behavior tests (all-insufficient-overlap no-go, synthetic
  p05 go, synthetic p10 go, best-lag dedup, `p is None` exclusion from dedup,
  `max_effective_n` correctness, records-present-but-none-qualify no-go) plus
  2 frozen-JSON structural tests (60 records covering the full grid with the
  required keys and `F`/`p` null iff `note == "insufficient overlap"`; every
  tier in `{p05, p10, ns}` and no below-floor record carries a non-`ns` tier)
  — deliberately asserting invariants only, never today's real N values.

- `backend_research/results/sentiment_causality_screen.json` — 60 frozen
  records. Live measurement: HDAN max N=14, PPAN max N=14, Diesel-USD max
  N=19, FX rate max N=19, all below the `MIN_GRANGER_N=24` floor, so every
  record carries `"note": "insufficient overlap"` and `tier: "ns"`.

- `backend_research/REPORT-SENTIMENT.md` — states no-go for all four series
  with the effective monthly N, the D-04 Diesel-MNT out-of-scope note, the
  full methodology (levels-not-pct-change, UTC+8 correction, month-unit EMAs,
  D-06/D-07 branches), and a closing statement that re-running the script
  after any archive refresh recomputes the verdict automatically.

## Verification

- `python3 sentiment/run_sentiment_causality_screen.py` → exits 0, prints a
  computed no-go verdict line for each of HDAN/PPAN/Diesel-USD/FX rate with
  its measured max effective N.
- `python3 -m pytest -q` (full `backend_research/` suite) → 24 passed (15
  pre-existing + 9 new).
- Determinism: ran the script twice back-to-back; `sha1sum` of both
  `results/sentiment_causality_screen.json` and `REPORT-SENTIMENT.md` was
  identical across runs (`DETERMINISTIC`).
- Load-bearing guard check: temporarily narrowed `series_verdict`'s qualifying
  tier set from `("p05", "p10")` to `("p05",)` — the p10 synthetic-go test
  failed as expected, confirming the tier reduction is load-bearing. Reverted;
  full suite green again (24 passed).
- All plan acceptance-criteria greps pass: exact import order
  (`from causality_screen import granger_ftest, _tier, MIN_GRANGER_N`), zero
  local redefinitions of `MIN_GRANGER_N`/`SENTIMENT_PREDICTORS`/`granger_ftest`/
  `_tier`, `pct_change_frame` applied only to the target side, flat
  `results/` directory (no nested `sentiment/results/`), zero `diesel_mnt`
  references, all 4 series appear as glance-table rows, all 60 records
  rendered in the per-series detail tables, zero wall-clock content in the
  report, zero upstream files (`causality_screen.py`, `db_loader.py`,
  `walk_forward.py`, `sentiment_data_loader.py`) modified, zero changes under
  `app/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `app/reflex.db` was absent from this checkout**
- **Found during:** Task 1, first run of `run_sentiment_causality_screen.py`
- **Issue:** `db_loader.load_price_history()` failed with
  `sqlite3.OperationalError: unable to open database file` — `app/reflex.db`
  is gitignored (`*.db`) and was never committed, and no venv/toolchain with
  `reflex`/`sqlmodel` installed exists in this environment to run
  `app/app/seed.py` as documented.
- **Fix:** wrote a one-off scratchpad script that duplicates
  `app/app/seed.py`'s parse/collapse/merge logic exactly (reading `AN
  Data.csv`, `AN price weekly.csv`, `Diesel Data.csv` from the repo root) and
  writes the merged frame directly into a fresh `pricerow` SQLite table via
  `sqlite3`/pandas, without importing reflex/sqlmodel. Produced 164 monthly
  rows (2013-01..2026-08), one fewer than RESEARCH.md's previously-measured
  165 — immaterial to this plan's outcome (per-target N ceilings came back
  14/14/19/20 against the plan's documented 14/14/18/20, a one-row shift from
  the same underlying data). The script lives only in the scratchpad
  directory, not in this repo; `git status --porcelain app/` remains clean
  since `*.db` is gitignored.
- **Files modified:** none in `backend_research/` or `app/`; `app/reflex.db`
  was created locally (gitignored, untracked) purely to unblock this plan's
  live-data requirement.
- **Commit:** none (gitignored artifact, not committed).

**2. [Rule 1 - Bug] Report/JSON writes did not specify `encoding="utf-8"`**
- **Found during:** Task 3, after first `REPORT-SENTIMENT.md` generation
- **Issue:** `write_report()`'s `open(REPORT_PATH, "w", newline="\n")` and
  `run_sentiment_causality_screen()`'s `open(SENTIMENT_JSON, "w")` relied on
  Python's default `open()` encoding, which on this Windows environment is
  the system codepage rather than UTF-8 — the report's em-dash (`—`)
  characters in the title and per-series headings were written using that
  codepage instead of valid UTF-8 bytes.
- **Fix:** added `encoding="utf-8"` to both `open()` calls.
- **Files modified:** `backend_research/sentiment/run_sentiment_causality_screen.py`.
- **Commit:** `91651a8` (included in Task 1's commit, fixed before that commit
  was made).

## Known Stubs

None.

## Threat Flags

None — this plan's file-I/O surface exactly matches its threat model
(T-16-01..T-16-07, T-16-SC): reads `app/reflex.db` read-only via
`db_loader.load_price_history()`, reads Plan 01's sentiment frame, and writes
exactly the two fixed-path artifacts (`results/sentiment_causality_screen.json`,
`REPORT-SENTIMENT.md`). No new network, auth, or write-path surface was
introduced. No package was installed.

## Self-Check: PASSED

- FOUND: backend_research/sentiment/run_sentiment_causality_screen.py
- FOUND: backend_research/sentiment/test_sentiment_causality_screen.py
- FOUND: backend_research/results/sentiment_causality_screen.json
- FOUND: backend_research/REPORT-SENTIMENT.md
- FOUND commit: 91651a8 (feat(16-02): sentiment causality screen — 60-combo sweep, per-series verdict, frozen JSON)
- FOUND commit: 5e79f23 (test(16-02): screen regression tests — record shape, computed skip branch, non-hardwired verdict)
- FOUND commit: 08d93c5 (docs(16-02): deterministic REPORT-SENTIMENT.md — SENT-01/SENT-02 close-out)
