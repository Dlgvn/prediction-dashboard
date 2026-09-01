"""Dedicated FX weekly-cadence backtest (WKUI-02) -- NOT a clone of
`run_weekly_sarimax_ets.py` with FX bolted on.

Tests SARIMAX and Exponential Smoothing weekly-cadence candidates for the FX
rate against `FX Data.csv`'s native Weekly column, using the exact same
shared `walk_forward_backtest` harness Phase 2 (monthly) and Phase 17
(weekly HDAN/PPAN) both used -- never a hand-rolled loop. FX's own weekly
loader lives in this file (parsed independently, per 20-CONTEXT.md), and
`MIN_TRAIN_WEEKLY` is examined here specifically for FX's much longer
865-row history rather than copied unexamined from HDAN/PPAN's 104-row
derivation.

Every candidate is compared against the confirmed 1.72% MAPE monthly-native
FX benchmark (`app/app/forecasting.py`'s `MODEL_INFO["fx_rate"] ==
("Naive", 1.72)`, re-confirmed live at implementation time).

`run_weekly_sarimax_ets.py`, its frozen HDAN/PPAN results
(`results/weekly_sarimax_ets.json`), and everything under `app/` are
untouched by this plan. This phase is research-only: nothing in `app/`
changes regardless of the computed go/no-go verdict.
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

# This file sits one directory below walk_forward.py (backend_research/weekly/),
# mirroring the existing weekly-script sys.path shim used across this repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from walk_forward import mape_by_horizon, walk_forward_backtest  # noqa: E402

warnings.filterwarnings("ignore")

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # backend_research/weekly/ -> repo root
FX_CSV = str(_REPO_ROOT / "FX Data.csv")

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RESULTS_JSON = RESULTS_DIR / "weekly_fx.json"
REPORT_PATH = Path(__file__).resolve().parent.parent / "REPORT-WEEKLY-FX.md"

# MIN_TRAIN_WEEKLY -- examined specifically for FX, not copied unexamined from
# HDAN/PPAN's derivation (even though the resulting number matches):
#
# walk_forward_backtest uses an EXPANDING window (train_y = series.iloc[:origin]),
# so min_train only controls how early the first backtest origin starts -- it does
# NOT scale proportionally with total series length, and does not cap any
# individual origin's training-window size. The real question to answer is "how
# many weekly observations does SARIMAX/ETS need to converge stably", not "what
# fraction of FX's 865-row history should be burn-in."
#
# Phase 17 answered that stability question as 104 weeks (~2 years) for the same
# model families (SARIMAX, ETS-HoltDamped) at the same weekly cadence. FX's
# data-generating process is a currency rate -- generally smoother / lower
# variance-per-step than an ammonium-nitrate spot price -- so nothing about FX
# suggests it needs MORE burn-in than HDAN/PPAN did; 104 remains a reasonable,
# examined starting point rather than an arbitrary reuse.
#
# Applying MIN_TRAIN_WEEKLY=104 to FX's 865 rows yields
# n_origins ~= 865 - 104 - 5 + 1 = 757 (~7.4x Phase 17's ~102-origin backtest),
# spanning FX's full 2011-2026 history rather than a short recent slice.
MIN_TRAIN_WEEKLY = 104

# Covers a 5-week month; both h=4 (closest to a 30-day month) and h=5
# (sensitivity) are extracted from the SAME backtest run via mape_by_horizon,
# never a separate re-run per horizon.
HORIZON_WEEKLY = 5

# Fresh local dict (NOT imported from run_weekly_sarimax_ets.py's
# {"HDAN": ..., "PPAN": ...} dict). Source of truth re-confirmed live this
# research pass against app/app/forecasting.py's MODEL_INFO constant:
#   MODEL_INFO["fx_rate"] == ("Naive", 1.72)   (app/app/forecasting.py line 104)
# BENCHMARK_MAPE is a frozen local constant, never imported/read live from
# forecasting.py at script runtime, so a later edit to forecasting.py cannot
# silently change this phase's frozen comparison.
BENCHMARK_MAPE = {"FX": 1.72}

# Same p/d/q bounds as every other ARIMA-order-search script in this repo.
ARIMA_ORDER_GRID = list(itertools.product(range(3), range(2), range(3)))


def load_fx_weekly() -> pd.Series:
    """Returns FX rate as a weekly pd.Series indexed by week-ending Date
    (Mondays), 865 rows, 2010-01-04..2026-07-27.

    Positional slicing (columns 3-4: 'Date.1', 'Weekly') -- NEVER name-based
    selection, since FX Data.csv's duplicate 'Date'/blank spacer columns and
    the three cadences (Daily/Weekly/Monthly) are NOT row-aligned.
    """
    df = pd.read_csv(FX_CSV)
    weekly = df.iloc[:, 3:5].copy()
    weekly.columns = ["Date", "Weekly"]
    weekly = weekly.dropna()
    weekly["Date"] = pd.to_datetime(weekly["Date"])
    weekly["Weekly"] = weekly["Weekly"].astype(str).str.replace(",", "").astype(float)
    weekly = weekly.sort_values("Date").set_index("Date")
    return weekly["Weekly"]


def select_arima_order(train_y: pd.Series) -> tuple[tuple[int, int, int], float | None]:
    """Select (p,d,q) by AIC on a single training window. Returns (order, aic).

    Falls back to (1, 1, 0) if every candidate order fails to fit. Run ONCE
    on the first MIN_TRAIN_WEEKLY-row window, not per-origin.
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
    """Weekly-cadence SARIMAX, univariate only -- no exog variant, no FX
    equivalent of the Baltic-AN driver exists in scope this phase."""

    def __init__(self, train_y, train_x, order):
        self.fitted = sm.tsa.SARIMAX(
            train_y.to_numpy(),
            order=order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)

    def forecast(self, steps, exog=None):
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


def beats_benchmark(mape_h4, series_name: str = "FX") -> bool:
    """Live comparison against BENCHMARK_MAPE -- factored out as a standalone
    function (not inlined) so tests can exercise it directly on synthetic
    values in both directions. A missing horizon-4 MAPE never silently
    counts as a win."""
    return mape_h4 is not None and mape_h4 < BENCHMARK_MAPE[series_name]


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
            f"order selected by AIC={aic} on first {MIN_TRAIN_WEEKLY}-obs window, "
            "seasonal=None; MIN_TRAIN_WEEKLY=104 examined for FX's 865-row history "
            "(expanding-window burn-in, not a length-proportional fraction -- see "
            "module-level comment).",
        ),
        (
            "ETS-HoltDamped",
            "ets",
            lambda train_y, train_x: _HoltDampedWrapper(train_y),
            "trend=add, seasonal=None, damped_trend=True; MIN_TRAIN_WEEKLY=104 "
            "examined for FX's 865-row history (see module-level comment).",
        ),
    ]

    sarimax_name, sarimax_family, sarimax_fit_fn, sarimax_notes = specs[0]
    ets_name, ets_family, ets_fit_fn, ets_notes = specs[1]

    # Two explicit walk_forward_backtest calls (one per model family) rather than a
    # single hidden call inside a generic loop -- keeps each model's backtest
    # invocation visible and auditable, matching Phase 17's per-family call shape.
    sarimax_wf = walk_forward_backtest(
        y, None, sarimax_fit_fn, min_train=MIN_TRAIN_WEEKLY, horizon=HORIZON_WEEKLY,
        step=1, refit_every=1,
    )
    ets_wf = walk_forward_backtest(
        y, None, ets_fit_fn, min_train=MIN_TRAIN_WEEKLY, horizon=HORIZON_WEEKLY,
        step=1, refit_every=1,
    )

    records = []
    for model_name, family, notes, wf in (
        (sarimax_name, sarimax_family, sarimax_notes, sarimax_wf),
        (ets_name, ets_family, ets_notes, ets_wf),
    ):
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


def run_all() -> list[dict]:
    y = load_fx_weekly()
    records = build_univariate_records("FX", y)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    return records


def write_report(records: list[dict]) -> str:
    """Builds REPORT-WEEKLY-FX.md's full Markdown text from `records` (the
    same list run_all() just froze to RESULTS_JSON -- the backtest is never
    re-run for the report) and writes it to REPORT_PATH.

    DETERMINISM RULE: no wall-clock timestamp, no "generated on {date}"
    line, no run-duration figure anywhere in this text -- re-running the
    script must produce a byte-identical file (mirrors REPORT-WEEKLY.md's
    determinism discipline).
    """

    def fmt(v):
        return f"{v:.2f}%" if v is not None else "NA"

    def fmt_bool(v):
        return "yes" if v else "no"

    # Computed overall verdict: "go" if ANY record has beats_benchmark_h4 ==
    # True, otherwise "no-go". Computed here from records, never hand-typed.
    overall_verdict = "go" if any(r["beats_benchmark_h4"] for r in records) else "no-go"

    lines = []
    lines.append("# Phase 20: FX Weekly Backtest -- Research Report")
    lines.append("")
    lines.append(
        "Generated deterministically by `backend_research/weekly/run_fx_weekly_backtest.py` "
        "from `backend_research/results/weekly_fx.json`. This is WKUI-02's deliverable. A "
        "\"no-go\" is a complete and valid outcome, not a failure to fix. No `app/` code "
        "changed this phase, and `run_weekly_sarimax_ets.py`'s frozen HDAN/PPAN results are "
        "untouched."
    )
    lines.append("")
    lines.append("## Go/No-Go at a glance")
    lines.append("")
    lines.append(
        "| Model | MAPE (h=4, ~1mo) | MAPE (h=5, sensitivity) | Benchmark MAPE "
        "| Beats benchmark (h=4)? |"
    )
    lines.append("|---|---|---|---|---|")
    for r in records:
        lines.append(
            f"| {r['model']} | {fmt(r['mape_h4'])} | {fmt(r['mape_h5'])} "
            f"| {r['benchmark_mape']}% | {fmt_bool(r['beats_benchmark_h4'])} |"
        )
    lines.append("")
    lines.append(
        f"**Overall verdict: {overall_verdict}.** Computed rule: \"go\" if ANY record has "
        "beats_benchmark_h4 == True, otherwise \"no-go\" -- computed here from `records` in "
        "Python, never hand-typed."
    )
    lines.append("")
    lines.append("## Horizon-matched methodology")
    lines.append("")
    lines.append(
        f"`MIN_TRAIN_WEEKLY={MIN_TRAIN_WEEKLY}` -- examined specifically for FX's 865-row "
        "history: walk_forward_backtest uses an expanding window, so min_train only controls "
        "how early the first backtest origin starts, not a length-proportional fraction of "
        "burn-in. Phase 17 established 104 weeks (~2 years) as sufficient for SARIMAX/ETS to "
        "converge stably at weekly cadence for HDAN/PPAN; FX's data-generating process (a "
        "currency rate) is generally smoother / lower-variance-per-step than an "
        "ammonium-nitrate spot price, so nothing suggests FX needs MORE burn-in. Applied to "
        "FX's 865 rows this yields ~757 backtest origins, spanning FX's full 2011-2026 "
        "history. `HORIZON_WEEKLY=5` (covers a 5-week month); both h=4 (primary, closest to "
        "an actual 30-day month) and h=5 (secondary sensitivity) are extracted from the same "
        "walk_forward_backtest run via mape_by_horizon. The benchmark being compared against "
        "is the fixed monthly-native Naive/AR(1) figure -- 1.72% -- from "
        "`app/app/forecasting.py`'s `MODEL_INFO[\"fx_rate\"]`, never re-derived here."
    )
    lines.append("")
    lines.append("## Model detail")
    lines.append("")
    lines.append(
        "| Model | n_origins | failed_origins | MAPE (h=4) | MAPE (h=5) | Benchmark MAPE "
        "| Beats benchmark (h=4)? |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for r in records:
        lines.append(
            f"| {r['model']} | {r['n_origins']} | {r['failed_origins']} | {fmt(r['mape_h4'])} "
            f"| {fmt(r['mape_h5'])} | {r['benchmark_mape']}% | {fmt_bool(r['beats_benchmark_h4'])} |"
        )
    lines.append("")
    lines.append("## Closing WKUI-02")
    lines.append("")
    closing = (
        f"This report closes WKUI-02 regardless of the computed verdict (**{overall_verdict}**). "
        "SARIMAX and Exponential Smoothing were backtested at weekly cadence for FX via the "
        "shared walk_forward_backtest harness, with an independently-examined MIN_TRAIN_WEEKLY "
        "for FX's 865-row history, and compared against the fixed monthly-native FX benchmark "
        "(1.72%) -- satisfying WKUI-02's requirement for a documented go/no-go against the "
        "existing monthly benchmark."
    )
    if overall_verdict == "no-go":
        closing += (
            " As a consequence of this no-go, FX weekly forecasting is excluded from Phase "
            "21/22's scope; the dashboard's FX path stays monthly-only, consistent with the "
            "project's \"no un-backtested model ships\" discipline."
        )
    lines.append(closing)
    lines.append("")

    text = "\n".join(lines)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    return text


if __name__ == "__main__":
    records = run_all()
    print("series | model | mape_h4 | mape_h5 | benchmark | beats_benchmark_h4")
    for r in records:
        h4 = f"{r['mape_h4']:.2f}" if r["mape_h4"] is not None else "NA"
        h5 = f"{r['mape_h5']:.2f}" if r["mape_h5"] is not None else "NA"
        print(
            f"{r['series']:6s} {r['model']:28s} {h4:>8s} {h5:>8s} "
            f"{r['benchmark_mape']:>8}  {r['beats_benchmark_h4']}"
        )
    write_report(records)
    print(f"\nWrote {len(records)} records to {RESULTS_JSON}")
    print(f"Wrote report to {REPORT_PATH}")
