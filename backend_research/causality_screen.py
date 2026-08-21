"""Full-predictor-set Granger causality + Engle-Granger cointegration screen (D-04/D-05).

D-04 forbids intuition-based pre-filtering of predictors: every one of the 12 candidate
predictors in `db_loader.PREDICTORS`, PLUS the other three targets as cross-predictors
(for the VAR/VECM candidate), is tested against all four targets at lags 1-3. This module
is the principled reconciliation of that requirement against RESEARCH.md Pitfall 2 (full
predictor x walk-forward grid is computationally explosive): screen cheaply once here, then
downstream walk-forward runners (plans 02-04/02-05/02-06) only backtest predictors that
passed this screen via `shortlist_for(target)`.

Two distinct statistical framings are used, deliberately:
- `run_granger_sweep()` operates on PERCENT-CHANGE data (stationary) — Granger causality
  requires (approximately) stationary series.
- `run_cointegration_sweep()` operates on LEVELS (raw, non-stationary) — Engle-Granger
  cointegration tests for a long-run equilibrium relationship, the opposite framing.

The `shortlist_for()` cap of 6 predictors per target is a deliberate COMPUTE BOUND (Pitfall
2 cost control for the downstream walk-forward grid), not a modelling opinion about how many
predictors "should" matter.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import statsmodels.api as sm
from scipy.stats import f as fdist
from statsmodels.tsa.stattools import coint, grangercausalitytests

from db_loader import PREDICTORS, TARGETS, load_price_history, pct_change_frame

RESULTS_DIR = Path(__file__).resolve().parent / "results"
CAUSALITY_JSON = RESULTS_DIR / "causality_screen.json"
COINTEGRATION_JSON = RESULTS_DIR / "cointegration.json"

MIN_GRANGER_N = 24
MIN_COINT_N = 30

# Cross-check pair for the manual F-test against the statsmodels library implementation.
CROSSCHECK_PAIR = ("hdan", "baltic_an")


def granger_ftest(y: pd.Series, predictor: pd.Series, lag: int) -> tuple[float, float, int]:
    """Incremental F-test Granger causality (ported verbatim from causality_matrix.py).

    y, predictor: pandas Series sharing an index (percent-change / stationary data).
    Returns (F, p, n).
    """
    d = pd.DataFrame({"y": y, "y_lag1": y.shift(1), "x_lag": predictor.shift(lag)}).dropna()
    Xb = sm.add_constant(d[["y_lag1"]])
    Xf = sm.add_constant(d[["y_lag1", "x_lag"]])
    mb, mf = sm.OLS(d["y"], Xb).fit(), sm.OLS(d["y"], Xf).fit()
    n, k = len(d), Xf.shape[1]
    F = ((mb.ssr - mf.ssr) / 1) / (mf.ssr / (n - k))
    p = 1 - fdist.cdf(F, 1, n - k)
    return float(F), float(p), int(n)


def _tier(p: float, n: int) -> str:
    if n < MIN_GRANGER_N:
        return "ns"
    if p < 0.05:
        return "p05"
    if p < 0.10:
        return "p10"
    return "ns"


def _all_pairs() -> list[tuple[str, str]]:
    """Every target x (12 predictors + other 3 targets) pair, skipping self-pairs."""
    pairs: list[tuple[str, str]] = []
    for target in TARGETS:
        candidates = PREDICTORS + [t for t in TARGETS if t != target]
        for predictor in candidates:
            if predictor == target:
                continue
            pairs.append((target, predictor))
    return pairs


def run_granger_sweep() -> list[dict]:
    """Granger F-test across every target x predictor x lag(1-3) combo. No pre-filtering."""
    pct = pct_change_frame(load_price_history())
    results: list[dict] = []

    for target, predictor in _all_pairs():
        y = pct[target]
        x = pct[predictor]
        for lag in (1, 2, 3):
            d = pd.DataFrame({"y": y, "x": x.shift(lag)}).dropna()
            n_overlap = len(d)
            if n_overlap < MIN_GRANGER_N:
                record = {
                    "target": target,
                    "predictor": predictor,
                    "lag": lag,
                    "F": None,
                    "p": None,
                    "n": n_overlap,
                    "tier": "ns",
                    "note": "insufficient overlap",
                }
                results.append(record)
                continue

            F, p, n = granger_ftest(y, x, lag)
            record = {
                "target": target,
                "predictor": predictor,
                "lag": lag,
                "F": round(F, 4),
                "p": round(p, 4),
                "n": n,
                "tier": _tier(p, n),
            }

            if (target, predictor) == CROSSCHECK_PAIR and lag == 1:
                # Cross-check only at lag=1: statsmodels' grangercausalitytests reports a
                # JOINT F-test over all lags 1..maxlag at each key, which only coincides
                # with our single-lag incremental F-test when maxlag == lag == 1. At
                # higher lags the two tests answer different questions (joint vs.
                # single-lag-added), so they are not expected to agree numerically.
                pair_df = pd.DataFrame({target: y, predictor: x}).dropna()
                gc = grangercausalitytests(
                    pair_df[[target, predictor]], maxlag=3, verbose=False
                )
                p_sm = gc[1][0]["ssr_ftest"][1]
                record["p_statsmodels_crosscheck"] = round(float(p_sm), 4)

            results.append(record)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(CAUSALITY_JSON, "w") as f:
        json.dump(results, f, indent=2)

    _print_granger_summary(results)
    return results


def _print_granger_summary(results: list[dict]) -> None:
    print("=== Granger causality sweep summary (significant predictors per target) ===")
    for target in TARGETS:
        sig = [
            r
            for r in results
            if r["target"] == target and r["tier"] in ("p05", "p10")
        ]
        sig.sort(key=lambda r: r["p"])
        if not sig:
            print(f"  {target}: (none significant at p<0.10)")
            continue
        print(f"  {target}:")
        for r in sig:
            print(f"    {r['predictor']} (lag={r['lag']}): p={r['p']} tier={r['tier']}")


def shortlist_for(target: str, tier: str = "p10") -> dict[str, int]:
    """Data-derived predictor shortlist for `target`, capped at 6 (Pitfall 2 compute bound).

    Reads causality_screen.json, keeps predictors whose BEST (lowest-p) lag reached the
    requested tier or better (p05 always qualifies for tier="p10"), dedupes to one best-p
    lag per predictor, sorts ascending by p, caps at 6 entries.

    Returns {predictor_name: best_lag}.
    """
    tier_rank = {"p05": 0, "p10": 1, "ns": 2}
    accept_rank = tier_rank[tier]

    with open(CAUSALITY_JSON) as f:
        records = json.load(f)

    by_predictor: dict[str, dict] = {}
    for r in records:
        if r["target"] != target:
            continue
        if r["p"] is None:
            continue
        if tier_rank[r["tier"]] > accept_rank:
            continue
        current = by_predictor.get(r["predictor"])
        if current is None or r["p"] < current["p"]:
            by_predictor[r["predictor"]] = r

    ordered = sorted(by_predictor.values(), key=lambda r: r["p"])[:6]
    return {r["predictor"]: r["lag"] for r in ordered}


def run_cointegration_sweep() -> list[dict]:
    """Engle-Granger cointegration on LEVELS (not pct-change) for every target/predictor pair.

    Tests for a long-run equilibrium between non-stationary series — the opposite framing
    from run_granger_sweep()'s stationary percent-change data.
    """
    levels = load_price_history()
    results: list[dict] = []

    for target, predictor in _all_pairs():
        d = pd.DataFrame({"y": levels[target], "x": levels[predictor]}).dropna()
        n_overlap = len(d)
        if n_overlap < MIN_COINT_N:
            results.append(
                {
                    "target": target,
                    "predictor": predictor,
                    "skipped": "insufficient overlap",
                    "n": n_overlap,
                }
            )
            continue

        t_stat, p, _crit = coint(d["y"], d["x"])
        results.append(
            {
                "target": target,
                "predictor": predictor,
                "t_stat": round(float(t_stat), 4),
                "p": round(float(p), 4),
                "n": n_overlap,
                "cointegrated": bool(p < 0.05),
            }
        )

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(COINTEGRATION_JSON, "w") as f:
        json.dump(results, f, indent=2)

    return results


def _compute_vecm_candidates(cointegration_results: list[dict]) -> list[dict]:
    """Target-pair (not target x predictor-only) cointegrated relationships, either direction.

    Only pairs where BOTH sides are members of TARGETS qualify — this is specifically the
    VAR-vs-VECM decision input for plan 02-05, not a general cointegration finding.
    """
    seen: set[frozenset] = set()
    candidates: list[dict] = []
    for r in cointegration_results:
        if r.get("skipped"):
            continue
        if not r.get("cointegrated"):
            continue
        a, b = r["target"], r["predictor"]
        if a not in TARGETS or b not in TARGETS:
            continue
        key = frozenset({a, b})
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"pair": sorted([a, b]), "p": r["p"], "t_stat": r["t_stat"]})
    return candidates


def _compute_vecm_candidates_lazy() -> list[dict]:
    """Load cointegration.json from disk and derive VECM_CANDIDATES (used at import time)."""
    if not COINTEGRATION_JSON.exists():
        return []
    with open(COINTEGRATION_JSON) as f:
        records = json.load(f)
    return _compute_vecm_candidates(records)


# Module-level derivation so plan 02-05 can `from causality_screen import VECM_CANDIDATES`.
# Populated from disk if cointegration.json already exists; otherwise empty until
# run_cointegration_sweep() is called (which does not refresh this constant automatically —
# callers running fresh should re-import after the sweep, or call _compute_vecm_candidates()
# directly on the sweep's return value).
VECM_CANDIDATES = _compute_vecm_candidates_lazy()


def _print_vecm_summary(vecm_candidates: list[dict]) -> None:
    if not vecm_candidates:
        print("No cointegrated target pairs found")
        return
    for c in vecm_candidates:
        a, b = c["pair"]
        print(f"VECM candidate: {a} ~ {b} (p={c['p']})")


if __name__ == "__main__":
    run_granger_sweep()
    coint_results = run_cointegration_sweep()
    vecm_candidates = _compute_vecm_candidates(coint_results)
    _print_vecm_summary(vecm_candidates)
