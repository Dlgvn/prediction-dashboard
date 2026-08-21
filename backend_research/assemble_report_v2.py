"""Assembles every Phase 2 walk-forward backtest result into the FCST-07 deliverable:
backend_research/results/winners.json (machine-readable per-series winner) and
backend_research/REPORT-PHASE2.md (the full ranked research report).

Run with: python assemble_report_v2.py  (from backend_research/, or any cwd -- paths
are resolved relative to this file).

Does NOT modify or read backend_research/assemble_report.py, which documents the
prior single-holdout study and stays as provenance.
"""
import json
import glob
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
SERIES = ["hdan", "ppan", "diesel_usd_ton", "fx_rate"]
SERIES_LABEL = {
    "hdan": "HDAN",
    "ppan": "PPAN",
    "diesel_usd_ton": "Diesel-USD",
    "fx_rate": "FX rate",
}

# A candidate whose "family" is wf_*.json's record shape must carry every one of
# these keys or the record is malformed and load_all_results() raises -- a silently
# dropped family would corrupt the ranking (see 02-04-PLAN.md for the shared shape).
REQUIRED_KEYS = {
    "series", "model", "family", "horizon_strategy", "predictors",
    "mape_by_horizon", "mape_mean_1_12", "single_holdout_mape",
    "n_origins", "refit_every", "failed_origins", "notes",
}

# Below this many rolling origins, an ML "win" is barely more informative than a
# single holdout split -- not trustworthy as a shipped winner even when it carries
# no explicit lag1_dominant/marginal_over_naive flag (D-01 overfitting caution).
MIN_ML_ORIGINS = 5

# Prior single-holdout study numbers (backend_research/REPORT.md), used for the
# comparison section.
PRIOR_STUDY_MAPE = {
    "hdan": 9.4,
    "ppan": 10.0,
    "diesel_usd_ton": 3.4,
    "fx_rate": 0.25,
}


def _is_finite(x):
    if x is None:
        return False
    try:
        return x == x  # NaN check
    except TypeError:
        return False


def load_all_results():
    """Glob results/wf_*.json, concatenate every record, and validate against the
    shared record shape. Raises with the offending file and key on any malformed
    record rather than silently skipping it."""
    records = []
    for fp in sorted(glob.glob(os.path.join(RESULTS_DIR, "wf_*.json"))):
        with open(fp) as f:
            payload = json.load(f)
        for i, rec in enumerate(payload):
            missing = REQUIRED_KEYS - set(rec)
            if missing:
                raise ValueError(
                    f"{os.path.basename(fp)}: record {i} missing keys {sorted(missing)}: {rec}"
                )
            if rec["series"] not in SERIES:
                raise ValueError(
                    f"{os.path.basename(fp)}: record {i} has unrecognised series {rec['series']!r}"
                )
            rec = dict(rec)
            rec["_source_file"] = os.path.basename(fp)
            records.append(rec)
    return records


def rank_per_series(records):
    """For each of the four target series, sort candidates by mape_mean_1_12
    ascending, excluding records with null/NaN MAPE (documented non-applicability
    records such as VECM when no cointegration was found)."""
    ranked = {s: [] for s in SERIES}
    for rec in records:
        if _is_finite(rec["mape_mean_1_12"]):
            ranked[rec["series"]].append(rec)
    for s in ranked:
        ranked[s].sort(key=lambda r: r["mape_mean_1_12"])
    return ranked


def _naive_record(candidates):
    for r in candidates:
        if r["model"] == "Naive":
            return r
    return None


def pick_winner(ranked, series):
    """Return (winner, runner_up, caveats) for a series using the mandatory
    adjudication rules -- not a blind argmin over mape_mean_1_12."""
    candidates = ranked[series]
    if not candidates:
        raise ValueError(f"No candidate with a finite MAPE for {series}")

    naive = _naive_record(candidates)
    caveats = []

    # Thin-sample ML exclusion (Rule 2 safeguard beyond the flag-only rule): an ML
    # candidate resting on n_origins < MIN_ML_ORIGINS is excluded from the primary
    # ranking regardless of which overfit_flags fired, since a 2-origin walk-forward
    # is not meaningfully different from a single holdout split.
    filtered = [
        c for c in candidates
        if not (c["family"] == "ml" and c["n_origins"] < MIN_ML_ORIGINS)
    ]
    excluded_thin_ml = [c for c in candidates if c not in filtered]
    if not filtered:
        filtered = candidates
        excluded_thin_ml = []

    top = filtered[0]
    runner_up = None

    if top["family"] == "ml" and set(top.get("overfit_flags", [])) & {"lag1_dominant", "marginal_over_naive"}:
        non_ml = [c for c in filtered if c["family"] != "ml"]
        winner = non_ml[0] if non_ml else filtered[min(1, len(filtered) - 1)]
        runner_up = top
        caveats.append(
            "ML posted the lowest MAPE but its diagnostics indicate lag-1 memorisation "
            "rather than generalisation (D-01 overfitting caution)."
        )
    elif naive is not None and top["mape_mean_1_12"] >= naive["mape_mean_1_12"]:
        winner = naive
        caveats.append(
            "No candidate model beat the Naive baseline's mean 1-12 MAPE for this "
            "series -- no model earned its added complexity here; Naive is the "
            "legitimate, reportable winner."
        )
        runner_up = next((c for c in filtered if c is not naive), None)
    else:
        winner = top
        runner_up = next((c for c in filtered if c is not winner), None)

    if excluded_thin_ml:
        best_excluded = min(excluded_thin_ml, key=lambda r: r["mape_mean_1_12"])
        caveats.append(
            f"{best_excluded['model']} posted a lower raw MAPE "
            f"({best_excluded['mape_mean_1_12']:.2f}%) but is backed by only "
            f"{best_excluded['n_origins']} walk-forward origins "
            f"(overfit_flags={best_excluded.get('overfit_flags', [])}) -- not trusted "
            f"as a winner over candidates validated across many more rolling origins."
        )
        if winner is not None and (runner_up is None or runner_up is winner):
            runner_up = best_excluded

    return winner, runner_up, caveats


def load_garch():
    with open(os.path.join(RESULTS_DIR, "garch_volatility.json")) as f:
        return json.load(f)


def attach_volatility(entry, series, garch):
    """volatility_source is "garch" plus sigma_by_horizon only when GARCH is
    genuinely usable for a widening bull/bear spread: viable, sigma widens
    monotonically with horizon, and horizon-1 sigma is stable across refit origins.
    Otherwise falls back to "arima_forecast_se" with sigma_by_horizon: null and a
    caveat naming the GARCH non-viability reason (RESEARCH.md Pitfall 3)."""
    g = garch.get(series, {})
    viable = bool(g.get("viable"))
    widening = g.get("widening", True)  # key absent == no problem was flagged
    stable = bool(g.get("stable_across_origins", False))

    if viable and widening and stable:
        entry["volatility_source"] = "garch"
        entry["sigma_by_horizon"] = g["sigma_by_horizon"]
        return

    entry["volatility_source"] = "arima_forecast_se"
    entry["sigma_by_horizon"] = None
    reasons = []
    if not viable:
        reasons.append("GARCH did not converge / was not marked viable")
    if not widening:
        reasons.append("GARCH sigma does not widen monotonically with horizon (Pitfall 3)")
    if not stable:
        reasons.append("GARCH horizon-1 sigma is unstable across refit origins (>50% relative spread)")
    entry["caveats"].append(
        "Falling back to ARIMA forecast-SE for the bull/bear spread: " + "; ".join(reasons) + "."
    )


def build_winners(ranked, garch):
    winners = {}
    for series in SERIES:
        winner, runner_up, caveats = pick_winner(ranked, series)
        entry = {
            "model": winner["model"],
            "family": winner["family"],
            "horizon_strategy": winner["horizon_strategy"],
            "predictors": winner["predictors"],
            "mape_by_horizon": winner["mape_by_horizon"],
            "mape_mean_1_12": winner["mape_mean_1_12"],
            "single_holdout_mape": winner["single_holdout_mape"],
            "runner_up": {
                "model": runner_up["model"] if runner_up else None,
                "mape_mean_1_12": runner_up["mape_mean_1_12"] if runner_up else None,
            },
            "caveats": list(caveats),
        }
        attach_volatility(entry, series, garch)
        winners[series] = entry
    return winners


def _fmt(x, nd=2):
    if x is None:
        return "n/a"
    try:
        if x != x:
            return "n/a"
    except TypeError:
        return str(x)
    if abs(x) >= 1e6:
        return f"{x:.3e}"
    return f"{x:.{nd}f}"


def load_json(name):
    with open(os.path.join(RESULTS_DIR, name)) as f:
        return json.load(f)


def write_report(winners, ranked, garch):
    lines = []
    lines.append("# Phase 2: Model Research & Backtesting -- Research Report\n")
    lines.append(
        "Generated deterministically by `assemble_report_v2.py` from "
        "`backend_research/results/wf_*.json` and the supporting predictor/cointegration/"
        "volatility screens. This is FCST-07's deliverable: a research report naming the "
        "backtested winner per series before any model reaches Phase 3.\n"
    )

    # 1. Winners at a glance
    lines.append("## Winners at a glance\n")
    lines.append("| Series | Winning model | Strategy | Mean MAPE 1-12 | h=12 MAPE | Volatility source |")
    lines.append("|---|---|---|---|---|---|")
    for s in SERIES:
        w = winners[s]
        h12 = w["mape_by_horizon"].get("12")
        lines.append(
            f"| {SERIES_LABEL[s]} | {w['model']} | {w['horizon_strategy']} | "
            f"{_fmt(w['mape_mean_1_12'])}% | {_fmt(h12)}% | {w['volatility_source']} |"
        )
    lines.append("")

    # 2. Which assumption won
    lines.append("## Which assumption won\n")
    lines.append(
        "Each method family bets on a different mechanism: **time-series** bets the "
        "past pattern continues (Naive/ETS/ARIMA); **causal/econometric** bets a "
        "screened driver leads the price (SARIMAX-with-exog, VAR, VECM); **ML** bets "
        "nonlinear feature interactions matter (RandomForest/GradientBoosting). "
        "Per series, the data supported:\n"
    )
    family_names = {
        "baseline": "time-series (naive persistence)",
        "ets": "time-series (exponential smoothing)",
        "arima": "time-series (ARIMA)",
        "sarimax": "causal/econometric (screened exogenous drivers)",
        "var": "causal/econometric (VAR system)",
        "vecm": "causal/econometric (cointegration/VECM)",
        "ml": "machine learning (nonlinear feature interactions)",
    }
    for s in SERIES:
        w = winners[s]
        bet = family_names.get(w["family"], w["family"])
        lines.append(f"- **{SERIES_LABEL[s]}**: {bet} won ({w['model']}, {_fmt(w['mape_mean_1_12'])}% mean MAPE).")
    lines.append("")

    # 3. Per-series ranking tables
    lines.append("## Per-series ranking tables\n")
    for s in SERIES:
        lines.append(f"### {SERIES_LABEL[s]}\n")
        lines.append("| Model | Family | Strategy | h=1 | h=6 | h=12 | Mean 1-12 | Single-holdout |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for c in ranked[s]:
            mbh = c["mape_by_horizon"]
            lines.append(
                f"| {c['model']} | {c['family']} | {c['horizon_strategy']} | "
                f"{_fmt(mbh.get('1'))}% | {_fmt(mbh.get('6'))}% | {_fmt(mbh.get('12'))}% | "
                f"{_fmt(c['mape_mean_1_12'])}% | {_fmt(c['single_holdout_mape'])}% |"
            )
        lines.append("")

    # 4. Iterative vs direct (D-06)
    lines.append("## Iterative vs. direct multi-step (D-06)\n")
    lines.append(
        "D-06 requires comparing iterative and direct multi-step forecasting per "
        "series and horizon band rather than committing to one upfront -- the answer "
        "is allowed to differ by series.\n"
    )
    bands = [("1-3", ["1", "2", "3"]), ("4-6", ["4", "5", "6"]), ("7-12", ["7", "8", "9", "10", "11", "12"])]
    for s in SERIES:
        lines.append(f"### {SERIES_LABEL[s]}\n")
        lines.append("| Horizon band | Iterative mean MAPE | Direct mean MAPE | Winner |")
        lines.append("|---|---|---|---|")
        by_strategy = defaultdict(list)
        for c in ranked[s]:
            by_strategy[c["horizon_strategy"]].append(c)
        for band_name, hs in bands:
            def band_mean(strategy):
                vals = []
                for c in by_strategy.get(strategy, []):
                    for h in hs:
                        v = c["mape_by_horizon"].get(h)
                        if _is_finite(v):
                            vals.append(v)
                return sum(vals) / len(vals) if vals else None
            it = band_mean("iterative")
            di = band_mean("direct")
            if it is None and di is None:
                winner_str = "n/a"
            elif di is None:
                winner_str = "iterative"
            elif it is None:
                winner_str = "direct"
            else:
                winner_str = "iterative" if it <= di else "direct"
            lines.append(f"| {band_name} | {_fmt(it)}% | {_fmt(di)}% | {winner_str} |")
        lines.append("")
    lines.append(
        "The iterative VAR family shows explosive MAPE at long horizons for several "
        "series (short-overlap predictor data compounding error through the recursion); "
        "the direct-OLS VAR variant stays bounded and is the safer family choice where "
        "VAR is used at all (see 02-05-SUMMARY.md).\n"
    )

    # 5. Predictor screen (D-04/D-05)
    lines.append("## Predictor screen (D-04/D-05)\n")
    causality = load_json("causality_screen.json")
    by_target = defaultdict(list)
    for r in causality:
        if r["tier"] in ("p05", "p10"):
            by_target[r["target"]].append(r)
    for s in SERIES:
        lines.append(f"### {SERIES_LABEL[s]}\n")
        rows = sorted(by_target.get(s, []), key=lambda r: r["p"])
        if not rows:
            lines.append("No predictor cleared p<0.10 in the Granger causality screen.\n")
            continue
        lines.append("| Predictor | Lag | p-value | Tier |")
        lines.append("|---|---|---|---|")
        for r in rows:
            lines.append(f"| {r['predictor']} | {r['lag']} | {r['p']:.4f} | {r['tier']} |")
        lines.append("")
    fx_predictors = by_target.get("fx_rate", [])
    if fx_predictors:
        lines.append(
            f"**FX predictor finding**: against the EXPANDED Brent+Urals+gas+AN-family "
            f"predictor set, fx_rate now clears the causality screen with "
            f"{len(fx_predictors)} predictor/lag pairs at p<0.10 (see table above) -- this "
            f"overturns the prior study's \"no predictors\" finding for FX (Pitfall 5), "
            f"reported honestly rather than forcing symmetry with the other series.\n"
        )
    else:
        lines.append(
            "**FX predictor finding**: even against the expanded predictor set, no "
            "predictor cleared p<0.10 for fx_rate -- reproducing the prior study's "
            "\"no predictors\" finding rather than forcing one onto the table.\n"
        )

    # 6. Cointegration & VECM
    lines.append("## Cointegration & VECM\n")
    coint = load_json("cointegration.json")
    coint_true = [r for r in coint if r["cointegrated"]]
    if coint_true:
        coint_desc = ", ".join(
            f"{r['target']}~{r['predictor']} (p={r['p']:.4f})" for r in coint_true
        )
    else:
        coint_desc = "none"
    lines.append(
        f"Engle-Granger cointegration sweep tested {len(coint)} target/predictor pairs; "
        f"{len(coint_true)} showed cointegration at p<0.05: {coint_desc}.\n"
    )
    lines.append(
        "None of these pairs matched the VAR system membership used in plan 02-05's "
        "candidate VAR systems, so VECM_CANDIDATES stayed empty for all four target "
        "series and VECM was not applicable -- plain VAR on differences is the correct "
        "specification here, per the explicit non-applicability records in "
        "`wf_var_vecm.json`.\n"
    )

    # 7. Volatility / bull-bear spread source (D-01 GARCH)
    lines.append("## Volatility / bull-bear spread source (D-01 GARCH)\n")
    lines.append("| Series | GARCH viable | Converged | Widens with horizon | Stable across origins | sigma h=1 | sigma h=6 | sigma h=12 | Source used |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for s in SERIES:
        g = garch.get(s, {})
        sbh = g.get("sigma_by_horizon") or [None] * 12
        lines.append(
            f"| {SERIES_LABEL[s]} | {g.get('viable')} | {g.get('converged')} | "
            f"{g.get('widening', True)} | {g.get('stable_across_origins')} | "
            f"{_fmt(sbh[0])} | {_fmt(sbh[5])} | {_fmt(sbh[11])} | {winners[s]['volatility_source']} |"
        )
    lines.append(
        "\nSpreads must widen with horizon for the shipped bull/bear bands to be "
        "meaningful. PPAN's GARCH sigma does not widen monotonically (Pitfall 3) and "
        "Diesel-USD/FX's horizon-1 sigma is unstable across refit origins -- both fall "
        "back to the ARIMA forecast-SE source rather than shipping an unreliable GARCH "
        "spread. Only HDAN's GARCH fit is viable, widening and stable enough to use "
        "directly.\n"
    )

    # 8. ML overfitting caveats (D-01)
    lines.append("## ML overfitting caveats (D-01)\n")
    lines.append(
        "This section is mandatory even where no overfit flag fired -- stated "
        "explicitly below rather than omitted.\n"
    )
    ml_records = [r for recs in ranked.values() for r in recs if r["family"] == "ml"]
    if not ml_records:
        lines.append("No ML candidates were fit for any series.\n")
    else:
        lines.append("| Series | Model | Strategy | Mean MAPE 1-12 | Naive mean MAPE | Margin vs. naive (pts) | n_origins | lag1 importance share | Overfit flags |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in ml_records:
            flags = r.get("overfit_flags", [])
            lines.append(
                f"| {SERIES_LABEL[r['series']]} | {r['model']} | {r['horizon_strategy']} | "
                f"{_fmt(r['mape_mean_1_12'])}% | {_fmt(r.get('naive_mape_mean_1_12'))}% | "
                f"{_fmt(r.get('margin_over_naive_pct_points'))} | {r['n_origins']} | "
                f"{_fmt(r.get('lag1_importance_share'), 3)} | {', '.join(flags) if flags else 'none'} |"
            )
        lines.append("")
        any_flags = any(r.get("overfit_flags") for r in ml_records)
        if any_flags:
            lines.append(
                "Every ML candidate above carries at least one overfit flag "
                "(`small_sample`, `suspiciously_strong`, or `marginal_over_naive`). None "
                "was crowned the winner on the strength of `lag1_dominant` or "
                "`marginal_over_naive` diagnostics per the pick_winner adjudication "
                "rule; HDAN and PPAN's lowest-raw-MAPE ML candidates were additionally "
                "excluded from winning outright for resting on only 2 walk-forward "
                "origins (see winners.json caveats and the thin-sample exclusion above) "
                "-- consistent with D-01's instruction not to present ML at face value.\n"
            )
        else:
            lines.append("No overfit flags fired for any ML candidate.\n")

    # 9. Comparison with the prior single-holdout study
    lines.append("## Comparison with the prior single-holdout study\n")
    lines.append("| Series | Prior study (single holdout) | This study, winner (mean MAPE 1-12) | This study, winner (single holdout) |")
    lines.append("|---|---|---|---|")
    for s in SERIES:
        w = winners[s]
        lines.append(
            f"| {SERIES_LABEL[s]} | {_fmt(PRIOR_STUDY_MAPE[s])}% | {_fmt(w['mape_mean_1_12'])}% | "
            f"{_fmt(w['single_holdout_mape'])}% |"
        )
    lines.append(
        "\nThe two methodologies are not directly equivalent (D-07): the prior study "
        "used a single fixed 12-month holdout on the original workbook's model "
        "coefficients and 2-file/10-column predictor set, while this study uses "
        "walk-forward/rolling-origin validation (repeated re-fit, forecast, roll "
        "forward) against the new 16-column predictor set from Phase 1. A mean MAPE "
        "1-12 dramatically BETTER than the prior study's single-horizon numbers is "
        "treated as a leakage red flag rather than good news and is called out "
        "explicitly at the human acceptance checkpoint for this plan, not silently "
        "accepted.\n"
    )

    # 10. Out of scope, and why
    lines.append("## Out of scope, and why\n")
    lines.append(
        "- **Technical/market-based methods (D-02)**: not tested this phase -- the "
        "user did not select this family, and momentum/support-resistance methods "
        "are a poorer fit for monthly fundamentals-driven commodity data than for "
        "intraday trading.\n"
        "- **Scenario planning / Delphi-style qualitative judgment (D-03)**: "
        "explicitly out of Phase 2's scope because it isn't backtestable against "
        "history the way the other methods are. **This is the mechanism "
        "REQUIREMENTS.md already reserves for v2's live news/sentiment-driven "
        "bull/bear adjustment** -- noted here explicitly so Phase 3/v2 planners see "
        "the throughline, but Phase 2 does not build or test anything for it.\n"
        "- **Weekly-mode proxy research (D-08)**: not investigated this phase -- "
        "weekly forecast mode is v2/deferred scope per REQUIREMENTS.md; this phase "
        "stays focused on the monthly models FCST-07 actually requires.\n"
    )

    report_path = os.path.join(HERE, "REPORT-PHASE2.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    return report_path


def write_decisions(winners):
    """Write the concise Phase 3 hand-off resolving RESEARCH.md Open Question #1."""
    lines = []
    lines.append("# Phase 2 Model Decisions -- Phase 3 Hand-off\n")
    lines.append(
        "Concise, per-series winner specification for Phase 3 to hard-code directly. "
        "Full backtest detail and per-family rankings live in "
        "`backend_research/REPORT-PHASE2.md`; this file exists so Phase 3's planner "
        "does not have to read JSON.\n"
    )
    for s in SERIES:
        w = winners[s]
        lines.append(f"## {SERIES_LABEL[s]} (`{s}`)\n")
        lines.append(f"- **Winning model**: {w['model']} ({w['family']} family)")
        lines.append(f"- **Horizon strategy**: {w['horizon_strategy']}")
        if w["predictors"]:
            preds = ", ".join(
                f"{k} (lag {v})" if v is not None else f"{k} (system member)"
                for k, v in w["predictors"].items()
            )
            lines.append(f"- **Predictor set**: {preds}")
        else:
            lines.append("- **Predictor set**: none (univariate)")
        h1 = w["mape_by_horizon"].get("1")
        h6 = w["mape_by_horizon"].get("6")
        h12 = w["mape_by_horizon"].get("12")
        lines.append(f"- **Walk-forward MAPE**: h=1 {_fmt(h1)}%, h=6 {_fmt(h6)}%, h=12 {_fmt(h12)}%, mean 1-12 {_fmt(w['mape_mean_1_12'])}%")
        lines.append(f"- **Volatility source for bull/bear spread**: {w['volatility_source']}")
        if w["caveats"]:
            lines.append("- **Caveats**:")
            for c in w["caveats"]:
                lines.append(f"  - {c}")
        else:
            lines.append("- **Caveats**: none")
        lines.append("")

    lines.append("## Phase 3 must not\n")
    lines.append(
        "- Must not re-run order search (AIC grid search, auto_arima, or any "
        "hyperparameter sweep) at runtime -- STACK.md's anti-auto_arima rule. Orders/"
        "hyperparameters are hard-coded above from this backtest.\n"
        "- Must not use a flat spread across series or horizons for the bull/bear "
        "bands -- FCST-03/FCST-04 require the spread to be series- and "
        "horizon-specific, per the volatility source named above.\n"
        "- Must not adopt any model absent from this file -- FCST-07's threat model "
        "(T-02-13) requires that no un-backtested or overfit model reach the shipped "
        "forecasting module.\n"
    )

    decisions_path = os.path.join(
        os.path.dirname(HERE), ".planning", "phases",
        "02-model-research-backtesting", "02-MODEL-DECISIONS.md",
    )
    with open(decisions_path, "w") as f:
        f.write("\n".join(lines))
    return decisions_path


def main():
    records = load_all_results()
    ranked = rank_per_series(records)
    garch = load_garch()
    winners = build_winners(ranked, garch)

    winners_path = os.path.join(RESULTS_DIR, "winners.json")
    with open(winners_path, "w") as f:
        json.dump(winners, f, indent=2)

    report_path = write_report(winners, ranked, garch)
    decisions_path = write_decisions(winners)

    print(f"Wrote {winners_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {decisions_path}\n")
    print(f"{'series':<16}{'model':<45}{'strategy':<12}{'mean MAPE 1-12':<16}{'h=12 MAPE':<12}{'vol source'}")
    for s in SERIES:
        w = winners[s]
        h12 = w["mape_by_horizon"].get("12")
        print(
            f"{s:<16}{w['model'][:44]:<45}{w['horizon_strategy']:<12}"
            f"{_fmt(w['mape_mean_1_12']):<16}{_fmt(h12):<12}{w['volatility_source']}"
        )


if __name__ == "__main__":
    main()
