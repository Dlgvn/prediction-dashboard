"""Regression tests for `run_sentiment_causality_screen.py`.

These tests exist to prove the per-series go/no-go verdict is COMPUTED from
records, not hardwired to today's expected no-go outcome — so a future denser
sentiment archive automatically flips the answer without any code change.
House style follows `test_walk_forward.py`: a module docstring, plain
`assert` statements, and small local record-builder helpers rather than a
fixtures framework.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from causality_screen import MIN_GRANGER_N  # noqa: E402

from run_sentiment_causality_screen import (  # noqa: E402
    LAGS,
    SENTIMENT_JSON,
    series_verdict,
)


def _skip_record(target="hdan", predictor="weighted_compound", lag=1, n=14):
    return {
        "target": target,
        "predictor": predictor,
        "lag": lag,
        "F": None,
        "p": None,
        "n": n,
        "tier": "ns",
        "note": "insufficient overlap",
    }


def _real_record(target="hdan", predictor="weighted_compound", lag=1, p=0.5, n=30, tier="ns"):
    return {
        "target": target,
        "predictor": predictor,
        "lag": lag,
        "F": 1.0,
        "p": p,
        "n": n,
        "tier": tier,
    }


def test_series_verdict_no_go_when_all_insufficient_overlap():
    records = [_skip_record(lag=lag) for lag in LAGS]
    v = series_verdict(records, "hdan")
    assert v["verdict"] == "no-go"
    assert "sample size" in v["reason"]
    assert str(MIN_GRANGER_N) in v["reason"]


def test_series_verdict_go_on_synthetic_p05_record():
    # Proves the verdict is derived from records, not hardwired to the
    # real-world no-go: a synthetic p05 record must produce "go".
    records = [
        _real_record(predictor="weighted_compound", lag=1, p=0.02, n=30, tier="p05"),
        _real_record(predictor="sent_ema3", lag=1, p=0.5, n=30, tier="ns"),
    ]
    v = series_verdict(records, "hdan")
    assert v["verdict"] == "go"
    predictors = {r["predictor"] for r in v["qualifying"]}
    assert "weighted_compound" in predictors


def test_series_verdict_go_on_synthetic_p10_record():
    # D-01: both p05 and p10 tiers qualify.
    records = [
        _real_record(predictor="sent_momentum", lag=2, p=0.08, n=30, tier="p10"),
    ]
    v = series_verdict(records, "hdan")
    assert v["verdict"] == "go"
    predictors = {r["predictor"] for r in v["qualifying"]}
    assert "sent_momentum" in predictors


def test_series_verdict_best_lag_dedup():
    # D-02: a predictor appearing at lags 1, 2, 3 reduces to its single
    # lowest-p record; agreement across lags is never required.
    records = [
        _real_record(predictor="weighted_compound", lag=1, p=0.5, n=30, tier="ns"),
        _real_record(predictor="weighted_compound", lag=2, p=0.03, n=30, tier="p05"),
        _real_record(predictor="weighted_compound", lag=3, p=0.4, n=30, tier="ns"),
    ]
    v = series_verdict(records, "hdan")
    assert v["verdict"] == "go"
    assert len(v["qualifying"]) == 1
    assert v["qualifying"][0]["lag"] == 2
    assert v["qualifying"][0]["p"] == 0.03


def test_series_verdict_ignores_none_p_in_dedup():
    # A below-floor record (p is None) must never win the best-lag dedup.
    records = [
        _skip_record(predictor="weighted_compound", lag=1, n=10),
        _real_record(predictor="weighted_compound", lag=2, p=0.03, n=30, tier="p05"),
    ]
    v = series_verdict(records, "hdan")
    assert v["verdict"] == "go"
    assert len(v["qualifying"]) == 1
    assert v["qualifying"][0]["lag"] == 2


def test_series_verdict_max_effective_n():
    records = [
        _skip_record(predictor="weighted_compound", lag=1, n=10),
        _real_record(predictor="sent_ema3", lag=1, p=0.5, n=25, tier="ns"),
        _real_record(predictor="sent_ema10", lag=1, p=0.03, n=32, tier="p05"),
    ]
    v = series_verdict(records, "hdan")
    assert v["max_effective_n"] == 32


def test_series_verdict_no_go_when_records_present_but_none_qualify():
    records = [
        _real_record(predictor="weighted_compound", lag=1, p=0.5, n=30, tier="ns"),
        _real_record(predictor="sent_ema3", lag=1, p=0.9, n=30, tier="ns"),
    ]
    v = series_verdict(records, "hdan")
    assert v["verdict"] == "no-go"
    assert "reached" in v["reason"]


# The frozen JSON's structural properties must hold for ANY dataset, so these
# tests intentionally assert shape/invariants only — never today's real-world
# verdict strings or the specific N values (14/14/19/20) — pinning those would
# make the suite fail on a legitimate future archive refresh instead of
# reporting the new finding.
def test_frozen_json_has_60_records_covering_full_grid():
    with open(SENTIMENT_JSON) as f:
        records = json.load(f)

    assert len(records) == 60
    targets = {"hdan", "ppan", "diesel_usd_ton", "fx_rate"}
    predictors = {
        "weighted_compound",
        "sent_ema3",
        "sent_ema10",
        "sent_momentum",
        "vix_regime_code",
    }
    assert {r["target"] for r in records} == targets
    assert {r["predictor"] for r in records} == predictors
    assert {r["lag"] for r in records} == set(LAGS)

    required_keys = {"target", "predictor", "lag", "F", "p", "n", "tier"}
    for r in records:
        assert required_keys <= set(r)
        assert (r["F"] is None) == (r.get("note") == "insufficient overlap")
        assert (r["p"] is None) == (r.get("note") == "insufficient overlap")


def test_frozen_json_tiers_and_floor_consistency():
    with open(SENTIMENT_JSON) as f:
        records = json.load(f)

    for r in records:
        assert r["tier"] in ("p05", "p10", "ns")
        if r["n"] < MIN_GRANGER_N:
            assert r["tier"] == "ns"
