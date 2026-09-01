"""Weekly-cadence SARIMAX / Exponential-Smoothing re-research (WKLY-01/WKLY-02).

Tests the prior weekly spike's two named follow-ups -- SARIMAX and Exponential
Smoothing at weekly cadence -- for HDAN and PPAN, using the exact same shared
`walk_forward_backtest` harness Phase 2's monthly research used (never a hand-rolled
loop). Extends one variant with the Baltic-AN-deduped driver (frozen by Plan 01 in
`results/baltic_an_dedup.json`) as a SARIMAX exogenous regressor. Every candidate is
compared against the prior spike's exact fixed monthly VAR benchmark (HDAN 9.49%,
PPAN 10.08%) -- this script never re-tests the prior plain weekly VAR(HDAN,PPAN) or
the prior OLS+Granger weekly-driver combination; those are the null result this spike
is following up on, not candidates being retested here.

Nothing here ships to `app/`; no weekly UI ships this milestone regardless of outcome;
zero new dependencies.
"""

from __future__ import annotations

import itertools
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# This file sits one directory below data_loader.py/walk_forward.py
# (backend_research/weekly/), mirroring sentiment/run_sentiment_causality_screen.py's
# and weekly/baltic_an_dedup.py's existing sys.path shim.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_loader import load_an_weekly, merged_weekly  # noqa: E402
from walk_forward import mape_by_horizon, walk_forward_backtest  # noqa: E402

warnings.filterwarnings("ignore")

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RESULTS_JSON = RESULTS_DIR / "weekly_sarimax_ets.json"
REPORT_PATH = Path(__file__).resolve().parent.parent / "REPORT-WEEKLY.md"
DEDUP_JSON = RESULTS_DIR / "baltic_an_dedup.json"

# ~2 years of weekly data -- leaves ~100 origins from the 206-row native weekly series
# (Pitfall 2 budget: enough origins for a meaningful walk-forward, not so many that the
# first training window is too short to fit SARIMAX/ETS stably).
MIN_TRAIN_WEEKLY = 104
# Covers a 5-week month; both h=4 (closest to a 30-day month) and h=5 (sensitivity) are
# extracted from the SAME backtest run (Pattern 2 -- horizon-matched rollup, never a
# separate re-run per horizon).
HORIZON_WEEKLY = 5

# Locked, exact figures (CONTEXT.md, ROADMAP.md Phase 17) -- the prior spike's monthly-
# native VAR(HDAN,PPAN) winner. Never re-derived here; this plan only compares against it.
BENCHMARK_MAPE = {"HDAN": 9.49, "PPAN": 10.08}

# Same p/d/q bounds as the monthly script (run_arima_sarimax_wf.py) -- the weekly-scale
# difference lives in MIN_TRAIN_WEEKLY/HORIZON_WEEKLY, not the order grid.
ARIMA_ORDER_GRID = list(itertools.product(range(3), range(2), range(3)))


def select_arima_order(train_y: pd.Series) -> tuple[tuple[int, int, int], float | None]:
    """Select (p,d,q) by AIC on a single training window. Returns (order, aic).

    Falls back to (1, 1, 0) if every candidate order fails to fit.
    """
    best_order = None
    best_aic = np.inf
    for order in ARIMA_ORDER_GRID:
        try:
            fitted = ARIMA(train_y.to_numpy(), order=order).fit()
            if fitted.aic < best_aic:
                best_aic = fitted.aic
                best_order = order
        except Exception:
            continue
    if best_order is None:
        return (1, 1, 0), None
    return best_order, best_aic


class _SARIMAXWrapper:
    """Weekly-cadence SARIMAX -- seasonal=None (no (P,D,Q,s) term): fewer than 4 clean
    annual cycles exist at weekly cadence over this ~206-row series (Pitfall 3)."""

    def __init__(self, train_y, train_x, order):
        self.fitted = sm.tsa.SARIMAX(
            train_y.to_numpy(),
            exog=train_x.to_numpy() if train_x is not None else None,
            order=order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)

    def forecast(self, steps, exog=None):
        if exog is not None:
            return self.fitted.forecast(steps=steps, exog=np.asarray(exog))
        return self.fitted.forecast(steps=steps)


class _HoltDampedWrapper:
    def __init__(self, train_y, train_x=None):
        self.fitted = ExponentialSmoothing(
            train_y.to_numpy(),
            trend="add",
            seasonal=None,
            damped_trend=True,
            initialization_method="estimated",
        ).fit()

    def forecast(self, steps, exog=None):
        return self.fitted.forecast(steps)


def beats_benchmark(mape_h4, series_name: str) -> bool:
    """Live comparison against BENCHMARK_MAPE -- factored out as a standalone function
    (not inlined) so tests can exercise it directly on synthetic values in both
    directions. A missing horizon-4 MAPE never silently counts as a win."""
    return mape_h4 is not None and mape_h4 < BENCHMARK_MAPE[series_name]


def load_dedup_choice() -> dict:
    """Reads Plan 01's frozen Baltic-AN dedup verdict. This is a hard dependency, not an
    optional fallback -- if Plan 01's script has not been run yet, fail loudly."""
    if not DEDUP_JSON.exists():
        raise FileNotFoundError(
            f"{DEDUP_JSON} not found -- run backend_research/weekly/baltic_an_dedup.py "
            "(Plan 01) first to produce the frozen dedup verdict this plan consumes."
        )
    with open(DEDUP_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_univariate_records(series_name: str, y: pd.Series) -> list[dict]:
    """Weekly SARIMAX and ETS-HoltDamped, univariate, run through the shared
    walk_forward_backtest harness."""
    y = y.dropna()
    order, aic = select_arima_order(y.iloc[:MIN_TRAIN_WEEKLY])

    specs = [
        (
            f"SARIMAX{order}",
            "sarimax",
            lambda train_y, train_x: _SARIMAXWrapper(train_y, train_x, order),
            f"order selected by AIC={aic} on first {MIN_TRAIN_WEEKLY}-obs window, seasonal=None",
        ),
        (
            "ETS-HoltDamped",
            "ets",
            lambda train_y, train_x: _HoltDampedWrapper(train_y),
            "trend=add, seasonal=None, damped_trend=True",
        ),
    ]

    records = []
    for model_name, family, fit_fn, notes in specs:
        wf = walk_forward_backtest(
            y, None, fit_fn, min_train=MIN_TRAIN_WEEKLY, horizon=HORIZON_WEEKLY, step=1, refit_every=1
        )
        mbh = mape_by_horizon(wf)
        mape_h4 = float(mbh.get(4)) if 4 in mbh.index else None
        mape_h5 = float(mbh.get(5)) if 5 in mbh.index else None
        records.append(
            {
                "series": series_name,
                "model": model_name,
                "family": family,
                "driver_variant": "univariate",
                "mape_h4": mape_h4,
                "mape_h5": mape_h5,
                "benchmark_mape": BENCHMARK_MAPE[series_name],
                "beats_benchmark_h4": beats_benchmark(mape_h4, series_name),
                "n_origins": int(wf["origin_date"].nunique()) if len(wf) else 0,
                "failed_origins": len(wf.attrs.get("failed_origins", [])),
                "min_train": MIN_TRAIN_WEEKLY,
                "horizon": HORIZON_WEEKLY,
                "notes": notes,
            }
        )
    return records


def build_exog_sarimax_record(series_name: str, mg: pd.DataFrame, order, dedup_choice: dict) -> dict:
    """The Baltic-AN-deduped driver-set variant: a SARIMAX+exog regression, not a new
    model family. The exog column set is chosen from Plan 01's frozen verdict."""
    verdict = dedup_choice["verdict"]
    if verdict == "duplicate":
        exog_cols = ["Baltic AN"]
    else:
        exog_cols = ["Baltic AN", "BalticAN_wk"]

    frame = pd.concat([mg[series_name].rename("y"), mg[exog_cols]], axis=1).dropna()
    y = frame["y"]
    exog = frame[exog_cols]

    fit_fn = lambda train_y, train_x: _SARIMAXWrapper(train_y, train_x, order)
    wf = walk_forward_backtest(
        y, exog, fit_fn, min_train=MIN_TRAIN_WEEKLY, horizon=HORIZON_WEEKLY, step=1, refit_every=1
    )
    mbh = mape_by_horizon(wf)
    mape_h4 = float(mbh.get(4)) if 4 in mbh.index else None
    mape_h5 = float(mbh.get(5)) if 5 in mbh.index else None

    return {
        "series": series_name,
        "model": f"SARIMAX{order}+BalticAN(exog, {verdict})",
        "family": "sarimax",
        "driver_variant": f"baltic_an_exog_{verdict}",
        "mape_h4": mape_h4,
        "mape_h5": mape_h5,
        "benchmark_mape": BENCHMARK_MAPE[series_name],
        "beats_benchmark_h4": beats_benchmark(mape_h4, series_name),
        "n_origins": int(wf["origin_date"].nunique()) if len(wf) else 0,
        "failed_origins": len(wf.attrs.get("failed_origins", [])),
        "min_train": MIN_TRAIN_WEEKLY,
        "horizon": HORIZON_WEEKLY,
        "notes": (
            f"exog columns={exog_cols} chosen from Plan 01's baltic_an_dedup.json "
            f"verdict={verdict} (corr={dedup_choice.get('corr')}, "
            f"mean_abs_pct_diff={dedup_choice.get('mean_abs_pct_diff')}); n={len(frame)} after dropna"
        ),
    }


def run_all() -> list[dict]:
    an = load_an_weekly()
    mg = merged_weekly()
    dedup_choice = load_dedup_choice()

    records: list[dict] = []
    for series_name in ("HDAN", "PPAN"):
        y = an[series_name].dropna()
        order, _ = select_arima_order(y.iloc[:MIN_TRAIN_WEEKLY])
        records.extend(build_univariate_records(series_name, y))
        records.append(build_exog_sarimax_record(series_name, mg, order, dedup_choice))

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    return records


def write_report(records: list[dict]) -> str:
    """Builds REPORT-WEEKLY.md's full Markdown text from `records` (the same list
    run_all() just froze to RESULTS_JSON -- backtests are never re-run for the report)
    and writes it to REPORT_PATH.

    DETERMINISM RULE: no wall-clock timestamp, no "generated on {date}" line, no
    run-duration figure anywhere in this text -- re-running the script must produce a
    byte-identical file (mirrors REPORT-SENTIMENT.md's determinism discipline).
    """
    dedup = load_dedup_choice()

    def fmt(v):
        return f"{v:.2f}%" if v is not None else "NA"

    def fmt_bool(v):
        return "yes" if v else "no"

    series_list = ["HDAN", "PPAN"]

    # Computed overall verdict: "go" only if EACH series has at least one record with
    # beats_benchmark_h4 == True. Computed here from records, never hand-typed.
    per_series_go = {}
    for s in series_list:
        s_records = [r for r in records if r["series"] == s]
        per_series_go[s] = any(r["beats_benchmark_h4"] for r in s_records)
    overall_verdict = "go" if all(per_series_go.values()) else "no-go"

    lines = []
    lines.append("# Phase 17: Weekly Forecast Re-Research Spike -- Research Report")
    lines.append("")
    lines.append(
        "Generated deterministically by `backend_research/weekly/run_weekly_sarimax_ets.py` "
        "from `backend_research/results/weekly_sarimax_ets.json`. This is WKLY-01/WKLY-02's "
        "deliverable. A \"no-go\" is a complete and valid outcome, not a failure to fix. No "
        "`app/` code changed this phase, and no weekly UI ships this milestone regardless of "
        "outcome."
    )
    lines.append("")
    lines.append("## Prior spike recap")
    lines.append("")
    lines.append(
        "The prior weekly-cadence spike (`.planning/quick/20260821-weekly-an-backtest/`) "
        "ended in a no-go: its horizon-matched 4-week rollup of a plain weekly "
        "VAR(HDAN,PPAN) scored 10.35% (HDAN) and 16.01% (PPAN), both worse than the existing "
        "monthly-native VAR benchmark. That spike named two follow-ups this report closes: "
        "(a) test SARIMAX/exponential-smoothing at weekly cadence, since only VAR/OLS were "
        "tried before, and (b) resolve whether AN Data.csv's Baltic AN column and AN price "
        "weekly.csv's BalticAN_wk column are duplicate or independent signal. The prior plain "
        "weekly VAR(HDAN,PPAN) and OLS+Granger weekly-driver combination are not retested here."
    )
    lines.append("")
    lines.append("## Go/No-Go at a glance")
    lines.append("")
    lines.append(
        "| Series | Model | Driver variant | MAPE (h=4, ~1mo) | MAPE (h=5, sensitivity) "
        "| Benchmark MAPE | Beats benchmark (h=4)? |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for r in records:
        lines.append(
            f"| {r['series']} | {r['model']} | {r['driver_variant']} | {fmt(r['mape_h4'])} "
            f"| {fmt(r['mape_h5'])} | {r['benchmark_mape']}% | {fmt_bool(r['beats_benchmark_h4'])} |"
        )
    lines.append("")
    lines.append(
        f"**Overall verdict: {overall_verdict}.** Computed rule: \"go\" only if at least one "
        "record for EACH of HDAN and PPAN has beats_benchmark_h4 == True; otherwise \"no-go\". "
        f"HDAN clears the benchmark: {fmt_bool(per_series_go['HDAN'])}. "
        f"PPAN clears the benchmark: {fmt_bool(per_series_go['PPAN'])}."
    )
    lines.append("")
    lines.append("## Horizon-matched methodology")
    lines.append("")
    lines.append(
        f"`MIN_TRAIN_WEEKLY={MIN_TRAIN_WEEKLY}` (~2 years of weekly history before the first "
        f"backtest origin) and `HORIZON_WEEKLY={HORIZON_WEEKLY}` (covers a 5-week month). Both "
        "h=4 (primary, closest to an actual 30-day month) and h=5 (secondary sensitivity) are "
        "extracted from the same walk_forward_backtest run via mape_by_horizon, per CONTEXT.md's "
        "instruction to match actual weeks-per-month rather than hardcode 4. The benchmark being "
        "compared against is the fixed monthly-native VAR(HDAN,PPAN) figures -- 9.49% (HDAN) / "
        "10.08% (PPAN) -- from Phase 2, never re-derived in this report."
    )
    lines.append("")
    lines.append("## Baltic-AN dedup resolution")
    lines.append("")
    lines.append(
        f"Plan 01's measured comparison (`results/baltic_an_dedup.json`) found "
        f"verdict=**{dedup['verdict']}** (n={dedup['n']}, corr={dedup['corr']}, "
        f"mean_abs_pct_diff={dedup['mean_abs_pct_diff']}%). Preferred column: "
        f"{dedup['preferred_column']}. This drove the SARIMAX+exog record's driver-set choice "
        f"below (`baltic_an_exog_{dedup['verdict']}`)."
    )
    lines.append("")
    lines.append("## Per-series detail")
    lines.append("")
    for s in series_list:
        lines.append(f"### {s} -- Go/No-Go: {'go' if per_series_go[s] else 'no-go'}")
        lines.append("")
        lines.append(
            "| Model | Driver variant | n_origins | failed_origins | MAPE (h=4) | MAPE (h=5) "
            "| Benchmark MAPE | Beats benchmark (h=4)? |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in [rec for rec in records if rec["series"] == s]:
            lines.append(
                f"| {r['model']} | {r['driver_variant']} | {r['n_origins']} | {r['failed_origins']} "
                f"| {fmt(r['mape_h4'])} | {fmt(r['mape_h5'])} | {r['benchmark_mape']}% "
                f"| {fmt_bool(r['beats_benchmark_h4'])} |"
            )
        lines.append("")
    lines.append("## Closing WKLY-01 / WKLY-02")
    lines.append("")
    closing = (
        f"This report closes both WKLY-01 and WKLY-02 regardless of the computed verdict "
        f"(**{overall_verdict}**). SARIMAX and Exponential Smoothing were backtested at weekly "
        "cadence for HDAN and PPAN via the shared walk_forward_backtest harness, extended with "
        "a Baltic-AN-deduped SARIMAX+exog driver-set variant, and compared against the fixed "
        "monthly VAR benchmark -- satisfying WKLY-01's requirement for genuinely new candidates "
        "tested with horizon-matched methodology, and WKLY-02's requirement for a documented "
        "go/no-go against the fixed benchmark."
    )
    if overall_verdict == "no-go":
        closing += (
            " As a consequence of this no-go, no weekly-cadence UI is planned; the dashboard "
            "continues on its monthly-native forecasting path."
        )
    lines.append(closing)
    lines.append("")

    text = "\n".join(lines)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    return text


if __name__ == "__main__":
    records = run_all()
    print("series | model | driver_variant | mape_h4 | mape_h5 | benchmark | beats_benchmark_h4")
    for r in records:
        h4 = f"{r['mape_h4']:.2f}" if r["mape_h4"] is not None else "NA"
        h5 = f"{r['mape_h5']:.2f}" if r["mape_h5"] is not None else "NA"
        print(
            f"{r['series']:6s} {r['model']:28s} {r['driver_variant']:26s} "
            f"{h4:>8s} {h5:>8s} {r['benchmark_mape']:>8}  {r['beats_benchmark_h4']}"
        )
    write_report(records)
    print(f"\nWrote {len(records)} records to {RESULTS_JSON}")
    print(f"Wrote report to {REPORT_PATH}")
