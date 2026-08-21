"""GARCH(1,1) conditional volatility research script (D-01, plan 02-03).

Fits a GARCH(1,1) model on percent returns for each of db_loader.TARGETS and
records a per-horizon (1-12) conditional volatility forecast, or an honest
non-viability finding with a named fallback, to
`backend_research/results/garch_volatility.json`.

Per Assumption A4: GARCH(1,1) only — no EGARCH/GJR sweep, the sample is too
small to support them.

This feeds Phase 3's horizon-widening bull/bear spread (per PITFALLS.md
Pitfall 3: spreads must widen with horizon). Where GARCH is not viable for a
series, the documented fallback is ARIMA/SARIMAX forecast standard errors
(plan 02-04), which already grow with horizon natively.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np

from arch import arch_model

from db_loader import TARGETS, load_price_history

RESULTS_PATH = Path(__file__).resolve().parent / "results" / "garch_volatility.json"

HORIZON = 12
ORIGIN_OFFSETS = [0, 12, 24]  # last observation, minus 12 months, minus 24 months
STABILITY_RELATIVE_THRESHOLD = 0.5  # 50% relative to median


def fit_garch(returns):
    """Fit a GARCH(1,1) model on a percent-returns series.

    Returns the fitted arch result object.
    """
    model = arch_model(returns, vol="Garch", p=1, q=1, mean="Constant", dist="normal")
    return model.fit(disp="off")


def garch_horizon_sigma(res, horizon: int = HORIZON) -> list[float]:
    """Return per-horizon conditional sigma (percent) as a list of `horizon` floats."""
    forecast = res.forecast(horizon=horizon, reindex=False)
    variance = forecast.variance.values[-1]
    sigma = np.sqrt(variance)
    return [float(v) for v in sigma]


def _is_non_decreasing(values: list[float], tol: float = 1e-8) -> bool:
    return all(b >= a - tol for a, b in zip(values, values[1:]))


def _fit_at_origin(pct_returns, offset: int):
    """Fit GARCH(1,1) on returns truncated to drop the last `offset` observations.

    Returns horizon-1 sigma, or None if the truncated series is too short or
    the fit fails/does not converge.
    """
    if offset > 0:
        series = pct_returns.iloc[:-offset]
    else:
        series = pct_returns

    if len(series) < 20:
        return None

    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            res = fit_garch(series)
        sigma_h1 = garch_horizon_sigma(res, horizon=1)[0]
        return sigma_h1
    except Exception:
        return None


def _check_origin_stability(pct_returns) -> bool | None:
    """Refit at three origins and check whether horizon-1 sigma is stable.

    Returns True/False, or None if fewer than 2 origins produced a usable fit
    (stability cannot be assessed).
    """
    sigmas = []
    for offset in ORIGIN_OFFSETS:
        sigma_h1 = _fit_at_origin(pct_returns, offset)
        if sigma_h1 is not None:
            sigmas.append(sigma_h1)

    if len(sigmas) < 2:
        return None

    median = float(np.median(sigmas))
    if median == 0:
        return None

    max_rel_diff = max(abs(s - median) / median for s in sigmas)
    return max_rel_diff <= STABILITY_RELATIVE_THRESHOLD


def _fit_series(name: str, series) -> dict:
    pct_returns = series.dropna().pct_change().dropna() * 100
    n_returns = len(pct_returns)

    record: dict = {"n_returns": int(n_returns)}

    if n_returns < 20:
        record.update(
            {
                "viable": False,
                "converged": False,
                "fallback": "arima_forecast_se",
                "note": f"Only {n_returns} return observations — too few to fit GARCH(1,1) reliably.",
            }
        )
        return record

    caught_warnings: list[str] = []
    try:
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            res = fit_garch(pct_returns)
            caught_warnings = [str(w.message) for w in wlist]
    except Exception as exc:
        record.update(
            {
                "viable": False,
                "converged": False,
                "convergence_flag": None,
                "warnings": caught_warnings,
                "fallback": "arima_forecast_se",
                "note": f"GARCH fit raised: {exc}",
            }
        )
        return record

    convergence_flag = getattr(res, "convergence_flag", None)
    converged = convergence_flag == 0

    record["convergence_flag"] = convergence_flag
    record["warnings"] = caught_warnings
    record["converged"] = bool(converged)

    if not converged:
        record.update(
            {
                "viable": False,
                "fallback": "arima_forecast_se",
                "note": "GARCH optimizer did not report successful convergence.",
            }
        )
        return record

    sigma_by_horizon = garch_horizon_sigma(res, horizon=HORIZON)
    widening = _is_non_decreasing(sigma_by_horizon)

    stable = _check_origin_stability(pct_returns)

    record.update(
        {
            "viable": True,
            "sigma_by_horizon": sigma_by_horizon,
        }
    )

    if not widening:
        record["widening"] = False
        record["note"] = (
            "Horizon-1 sigma does not monotonically widen through horizon-12 "
            "within floating tolerance — reported as-is per PITFALLS.md Pitfall 3, "
            "not smoothed over."
        )

    if stable is None:
        record["stable_across_origins"] = None
    else:
        record["stable_across_origins"] = bool(stable)
        if not stable:
            record.setdefault(
                "note",
                "Horizon-1 sigma is not stable across refit origins (>50% relative "
                "spread) — treat this series' GARCH volatility with caution.",
            )

    return record


def main():
    df = load_price_history()

    results: dict = {}
    for target in TARGETS:
        series = df[target]
        record = _fit_series(target, series)
        results[target] = record

        sigma = record.get("sigma_by_horizon")
        s1 = f"{sigma[0]:.3f}" if sigma else "n/a"
        s6 = f"{sigma[5]:.3f}" if sigma else "n/a"
        s12 = f"{sigma[11]:.3f}" if sigma else "n/a"
        print(
            f"{target}: n_returns={record['n_returns']} converged={record.get('converged')} "
            f"sigma(h1/h6/h12)={s1}/{s6}/{s12} viable={record.get('viable')}"
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
