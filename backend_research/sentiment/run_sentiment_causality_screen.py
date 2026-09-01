"""Phase 16 sentiment causality screen (SENT-01 / SENT-02).

Wires Plan 01's monthly sentiment predictors into the *unmodified*
`causality_screen.granger_ftest` / `_tier` / `MIN_GRANGER_N` pipeline so the
sentiment bar is provably identical to every other predictor's bar (D-01,
D-05) — no local reimplementation of the F-test, the tier thresholds, or the
sample-size floor. Runs the screen against the app's real HDAN/PPAN/
Diesel-USD/FX rate series (via `db_loader`), never against equities.

D-07's insufficient-overlap branch below is a COMPUTED condition on the
measured effective monthly N for each target x predictor x lag combination
(via `sentiment_data_loader.merge_lagged`) — it is never a hardcoded outcome.
RESEARCH.md's live measurement puts the per-target N ceiling well below
`MIN_GRANGER_N`, so a "no-go" verdict is the expected result today, but a
denser future sentiment archive would automatically flip individual
combinations into real F/p values and a real tier without any code change
here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Pitfall 4: flat imports (`from causality_screen import ...`, `from db_loader
# import ...`) only resolve once `backend_research/` is on sys.path; this
# script lives one directory deeper (backend_research/sentiment/), so both the
# parent directory (for backend_research/ flat modules) and this file's own
# directory (for the sibling sentiment_data_loader, so this module also
# imports cleanly under e.g. `python3 -c "import run_sentiment_causality_screen"`
# invocations and any future runner, not only direct script execution) are
# inserted onto sys.path before any of these imports run.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Imported, never redefined: granger_ftest, _tier and MIN_GRANGER_N are the
# structural guarantee (D-01/D-05) that the sentiment screen's statistical bar
# is identical to causality_screen.py's bar for every other predictor.
# SENTIMENT_PREDICTORS is likewise imported (D-08) rather than re-listed here.
from causality_screen import granger_ftest, _tier, MIN_GRANGER_N  # noqa: E402
from db_loader import TARGETS, load_price_history, pct_change_frame  # noqa: E402
from sentiment_data_loader import (  # noqa: E402
    SENTIMENT_PREDICTORS,
    load_sentiment_monthly,
    merge_lagged,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
SENTIMENT_JSON = RESULTS_DIR / "sentiment_causality_screen.json"
REPORT_PATH = Path(__file__).resolve().parent.parent / "REPORT-SENTIMENT.md"

LAGS = (1, 2, 3)

SERIES_LABELS = {
    "hdan": "HDAN",
    "ppan": "PPAN",
    "diesel_usd_ton": "Diesel-USD",
    "fx_rate": "FX rate",
}


def run_sentiment_causality_screen() -> list[dict]:
    """Granger F-test across every target x sentiment-predictor x lag(1-3) combo.

    Targets are the app's real percent-changed price series (stationary, via
    `db_loader.pct_change_frame`); sentiment predictors enter as monthly LEVELS
    and are deliberately NEVER percent-changed here — `weighted_compound` is
    bounded in [-1, 1] and crosses zero, so a pct-change on it produces sign
    flips and `inf` values (Pattern 2 / Pitfall 2).
    """
    pct = pct_change_frame(load_price_history())
    sentiment = load_sentiment_monthly()

    results: list[dict] = []

    for target in TARGETS:
        y = pct[target]
        for predictor in SENTIMENT_PREDICTORS:
            # Project the (gappy, 20-month) sentiment predictor onto the
            # target's dense monthly index ONCE, then pass that same series to
            # both merge_lagged and granger_ftest. granger_ftest shifts
            # POSITIONALLY, so only a series already reindexed onto the
            # target's dense index makes that positional .shift(lag) a true
            # calendar-month lag.
            x_on_y = sentiment[predictor].reindex(y.index)

            for lag in LAGS:
                # merge_lagged is Plan 01's leakage-guarded measurement of the
                # effective monthly sample size; it includes the y_lag1
                # column, so len(frame) equals the exact n granger_ftest's own
                # regression will use.
                frame = merge_lagged(y, x_on_y, lag)
                n_overlap = len(frame)

                if n_overlap < MIN_GRANGER_N:
                    # D-07: computed branch on the MEASURED n_overlap — no
                    # target or predictor name is special-cased, and no
                    # target's loop is short-circuited.
                    results.append(
                        {
                            "target": target,
                            "predictor": predictor,
                            "lag": lag,
                            "F": None,
                            "p": None,
                            "n": n_overlap,
                            "tier": "ns",
                            "note": "insufficient overlap",
                        }
                    )
                    continue

                F, p, n = granger_ftest(y, x_on_y, lag)
                if n != n_overlap:
                    raise ValueError(
                        f"run_sentiment_causality_screen: n mismatch for "
                        f"target={target!r} predictor={predictor!r} lag={lag}: "
                        f"merge_lagged measured n_overlap={n_overlap} but "
                        f"granger_ftest's regression used n={n}. These must agree, "
                        "or the reported effective N is not the regression's N."
                    )

                results.append(
                    {
                        "target": target,
                        "predictor": predictor,
                        "lag": lag,
                        "F": round(F, 4),
                        "p": round(p, 4),
                        "n": n,
                        "tier": _tier(p, n),
                    }
                )

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(SENTIMENT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


def series_verdict(records: list[dict], target: str) -> dict:
    """Per-series (D-04) go/no-go reduction, mirroring `shortlist_for()`'s dedup.

    D-02: a predictor qualifies at its single best (lowest-p) lag; agreement
    across lags is never required. D-03: no sign or direction filter is
    applied — tier alone decides.
    """
    target_records = [r for r in records if r["target"] == target]

    by_predictor: dict[str, dict] = {}
    for r in target_records:
        if r["p"] is None:
            continue
        current = by_predictor.get(r["predictor"])
        if current is None or r["p"] < current["p"]:
            by_predictor[r["predictor"]] = r

    qualifying = sorted(
        (r for r in by_predictor.values() if r["tier"] in ("p05", "p10")),
        key=lambda r: r["p"],
    )

    verdict = "go" if qualifying else "no-go"
    max_effective_n = max((r["n"] for r in target_records), default=0)

    if target_records and all(
        r.get("note") == "insufficient overlap" for r in target_records
    ):
        reason = (
            f"insufficient sample size (max effective monthly N = {max_effective_n}, "
            f"floor MIN_GRANGER_N = {MIN_GRANGER_N})"
        )
    elif not qualifying:
        reason = "no sentiment predictor reached p < 0.10 at any lag"
    else:
        parts = [
            f"{r['predictor']} (lag={r['lag']}, p={r['p']})" for r in qualifying
        ]
        reason = "qualifying predictors: " + ", ".join(parts)

    return {
        "target": target,
        "label": SERIES_LABELS[target],
        "verdict": verdict,
        "max_effective_n": max_effective_n,
        "reason": reason,
        "qualifying": qualifying,
    }


def _print_sentiment_summary(records: list[dict]) -> None:
    print("=== Sentiment causality screen summary (per-series go/no-go) ===")
    for target in TARGETS:
        v = series_verdict(records, target)
        print(
            f"  {v['label']}: {v['verdict']} "
            f"(max effective monthly N = {v['max_effective_n']}, floor = {MIN_GRANGER_N})"
        )
        if v["qualifying"]:
            for r in v["qualifying"]:
                print(f"    {r['predictor']} (lag={r['lag']}): p={r['p']} tier={r['tier']}")
        else:
            print(f"    reason: {v['reason']}")


def write_report(records: list[dict], sentiment) -> str:
    """Generate REPORT-SENTIMENT.md deterministically from `records`/`sentiment`.

    NO wall-clock timestamp, "generated on {date}" line, or run-duration
    figure appears anywhere in the generated body, so re-running this script
    produces a byte-identical file — provenance lives in git history instead.
    """
    lines: list[str] = []

    lines.append("# Phase 16: Sentiment Data Sufficiency & Causality Screen — Research Report")
    lines.append("")
    lines.append(
        "Generated deterministically by `backend_research/sentiment/"
        "run_sentiment_causality_screen.py` from `backend_research/results/"
        "sentiment_causality_screen.json`. This is SENT-01/SENT-02's deliverable: "
        "a per-series go/no-go verdict for whether monthly news sentiment "
        "Granger-causes each tracked price series, with the effective monthly "
        "sample size stated explicitly. A \"no-go\" verdict is a complete and "
        "valid outcome of this screen, not a failure to fix."
    )
    lines.append("")

    lines.append("## Go/No-Go at a glance")
    lines.append("")
    lines.append(
        "| Series | Verdict | Max effective monthly N | Floor (MIN_GRANGER_N) | Qualifying predictors |"
    )
    lines.append("|---|---|---|---|---|")
    verdicts = {target: series_verdict(records, target) for target in TARGETS}
    for target in TARGETS:
        v = verdicts[target]
        if v["qualifying"]:
            qual = ", ".join(
                f"{r['predictor']} (lag={r['lag']}, p={r['p']})" for r in v["qualifying"]
            )
        else:
            qual = "—"
        lines.append(
            f"| {v['label']} | {v['verdict']} | {v['max_effective_n']} | "
            f"{MIN_GRANGER_N} | {qual} |"
        )
    lines.append("")
    lines.append(
        "Diesel-MNT has no row above because it is a derived series "
        "(Diesel-USD x FX rate x markup) whose sentiment status follows from "
        "the Diesel-USD and FX rate rows, per D-04 — it is never screened as "
        "its own go/no-go target."
    )
    lines.append("")

    lines.append("## Effective monthly sample size")
    lines.append("")
    lines.append("| Series | Effective monthly N | Floor | Clears floor? |")
    lines.append("|---|---|---|---|")
    for target in TARGETS:
        v = verdicts[target]
        clears = "yes" if v["max_effective_n"] >= MIN_GRANGER_N else "no"
        lines.append(f"| {v['label']} | {v['max_effective_n']} | {MIN_GRANGER_N} | {clears} |")
    lines.append("")
    total_articles = int(sentiment["article_count"].sum())
    distinct_months = int(sentiment.shape[0])
    lines.append(
        f"Coverage context (NOT sample size): the underlying sentiment archive "
        f"covers {distinct_months} distinct months with {total_articles} total "
        f"articles. This raw article/month count is context only and must not "
        f"be read as the effective monthly sample size — the number that "
        f"actually matters for a monthly Granger test is the overlap between "
        f"sentiment coverage and each target's price history after the lag "
        f"shift, reported in the table above."
    )
    lines.append("")

    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- **Targets (D-04)**: the four live `PriceRow` series — HDAN, PPAN, "
        "Diesel-USD, FX rate — loaded via `db_loader.load_price_history()` and "
        "percent-changed via `db_loader.pct_change_frame()` for stationarity. "
        "Never equities."
    )
    lines.append(
        "- **Sentiment predictors as levels**: the five sentiment predictors "
        "enter as monthly LEVELS and are deliberately NOT percent-changed — "
        "`weighted_compound` is bounded in [-1, 1] and crosses zero, so a "
        "percent-change transform on it produces sign flips and `inf` values."
    )
    lines.append(
        "- **UTC+8 correction**: the monthly `weighted_compound` series is "
        "rebuilt from `archive/news_sentiment_raw.csv`'s raw `published_at` "
        "article timestamps, corrected to Mongolia local time (UTC+8), because "
        "`archive/news_sentiment_daily.csv`'s date-only column has already been "
        "bucketed to a UTC calendar day and cannot be timezone-corrected after "
        "the fact."
    )
    lines.append(
        "- **Month-unit EMAs**: `sent_ema3`, `sent_ema10` and `sent_momentum` "
        "are EMAs computed on the monthly `weighted_compound` series itself "
        "(month-unit spans) and therefore intentionally do NOT match a naive "
        "resample of the archive's day-unit EMA columns."
    )
    lines.append(
        "- **vix_regime_code**: the numeric `vix_regime_code` column is used, "
        "never the string `vix_regime` column, and is bucketed on its own US "
        "trading-day calendar with no UTC+8 shift applied (it is not "
        "article-publication-timestamped data)."
    )
    lines.append(
        "- **Zero-article months (D-06)**: months with zero articles are "
        "dropped from the sentiment frame, never forward-filled or "
        "interpolated."
    )
    lines.append(
        "- **Monthly aggregation**: the monthly `weighted_compound` value is a "
        "source-credibility-weighted mean per the archive's documented "
        "formula."
    )
    lines.append(
        f"- **Statistical bar (D-01, D-05)**: the p<0.05 / p<0.10 tiers and the "
        f"`MIN_GRANGER_N = {MIN_GRANGER_N}` floor are imported unchanged from "
        f"`causality_screen.py` — never redefined here — so the sentiment "
        f"screen's bar is identical to every other predictor's bar."
    )
    lines.append(
        "- **Best-lag qualification (D-02, D-03)**: a predictor qualifies at "
        "its single best (lowest-p) lag among 1-3, with no directional or "
        "sign filter applied — tier alone decides."
    )
    lines.append(
        "- **Insufficient overlap (D-07)**: below-`MIN_GRANGER_N` combinations "
        "are recorded with `note: \"insufficient overlap\"` and the F-test is "
        "not run, as a branch computed on the measured effective monthly N."
    )
    lines.append("")

    lines.append("## Per-series detail")
    lines.append("")
    for target in TARGETS:
        v = verdicts[target]
        lines.append(f"### {v['label']} — Go/No-Go: {v['verdict']}")
        lines.append("")
        lines.append(f"{v['reason']}.")
        lines.append("")
        lines.append("| Predictor | Lag | N | p-value | Tier | Note |")
        lines.append("|---|---|---|---|---|---|")
        target_records = sorted(
            (r for r in records if r["target"] == target),
            key=lambda r: (r["predictor"], r["lag"]),
        )
        for r in target_records:
            p_display = r["p"] if r["p"] is not None else "—"
            note_display = r.get("note", "—")
            lines.append(
                f"| {r['predictor']} | {r['lag']} | {r['n']} | {p_display} | "
                f"{r['tier']} | {note_display} |"
            )
        lines.append("")

    lines.append("## What would change this result")
    lines.append("")
    lines.append(
        "Reaching a real (non-`ns`) tier for any target would require "
        f"continuous, commodity/FX-relevant sentiment coverage spanning at "
        f"least {MIN_GRANGER_N} overlapping months with each target's price "
        "history — substantially denser and longer than the current archive. "
        "Building that additional data collection pipeline is out of scope for "
        "v2.0. Re-running `run_sentiment_causality_screen.py` after any future "
        "archive refresh recomputes every verdict above automatically, so a "
        "denser archive would surface a real finding without any code change."
    )
    lines.append("")

    text = "\n".join(lines)
    with open(REPORT_PATH, "w", newline="\n", encoding="utf-8") as f:
        f.write(text)
    return text


if __name__ == "__main__":
    results = run_sentiment_causality_screen()
    _print_sentiment_summary(results)
    write_report(results, load_sentiment_monthly())
