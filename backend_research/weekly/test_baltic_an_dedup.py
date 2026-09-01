"""Tests proving baltic_an_dedup.py's verdict is computed, not hardwired.

verdict_from_stats() is exercised directly on synthetic near-duplicate and
synthetic independent inputs (both branches), plus a boundary case. Then
compare_baltic_an() is run against the real repo-root CSVs to confirm it
produces a sane, real-data-derived verdict, and the frozen JSON output is
checked for the same contract.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baltic_an_dedup import (  # noqa: E402
    DEDUP_JSON,
    DUPLICATE_CORR_THRESHOLD,
    DUPLICATE_MAPE_THRESHOLD,
    compare_baltic_an,
    main,
    verdict_from_stats,
)


def test_verdict_synthetic_duplicate():
    # Near-identical pair: high correlation, tiny percentage difference.
    assert verdict_from_stats(corr=0.995, mape_between=1.5) == "duplicate"


def test_verdict_synthetic_independent():
    # Uncorrelated pair: low correlation, large percentage difference.
    assert verdict_from_stats(corr=0.05, mape_between=45.0) == "independent"


def test_verdict_boundary_not_duplicate():
    # Exactly at the thresholds does not spuriously pass as "duplicate" --
    # the comparison is strict (>) so equality falls on the "independent" side.
    assert verdict_from_stats(
        corr=DUPLICATE_CORR_THRESHOLD, mape_between=DUPLICATE_MAPE_THRESHOLD
    ) == "independent"


def test_verdict_high_corr_but_high_mape_is_independent():
    # High correlation alone is not sufficient -- large magnitude difference
    # (e.g. two series that move together but on very different scales)
    # must still be "independent".
    assert verdict_from_stats(corr=0.99, mape_between=50.0) == "independent"


def test_compare_baltic_an_real_data():
    result = compare_baltic_an()
    assert result["n"] == 206, result["n"]
    assert result["verdict"] in ("duplicate", "independent")
    assert -1.0 <= result["corr"] <= 1.0


def test_frozen_json_contract():
    computed = main()
    assert DEDUP_JSON.exists()
    with open(DEDUP_JSON) as f:
        frozen = json.load(f)
    assert frozen["verdict"] == computed["verdict"]
    assert frozen["corr"] == computed["corr"]
    assert frozen["n"] == computed["n"]
