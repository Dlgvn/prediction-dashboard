"""Baltic-AN dedup comparison: is AN Data.csv's 'Baltic AN' column duplicate or
independent signal versus AN price weekly.csv's 'BalticAN_wk' column?

This resolves the prior spike's second named follow-up (see RESEARCH.md) via a
direct, measured comparison -- correlation and mean-absolute-percentage-difference
between the two columns over their overlapping weekly window -- rather than an
assumed answer. The frozen verdict this script writes to
`backend_research/results/baltic_an_dedup.json` feeds Plan 02's SARIMAX+exog
driver-set variant: if the columns are a duplicate, only one should be used as an
exogenous predictor; if independent, both may be considered separately.
"""

import json
import sys
from pathlib import Path

import pandas as pd

# This file sits one directory below data_loader.py (backend_research/weekly/),
# mirroring sentiment/sentiment_data_loader.py's existing sys.path shim.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data_loader import load_an_weekly, load_weekly_drivers  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
DEDUP_JSON = RESULTS_DIR / "baltic_an_dedup.json"

# Thresholds for calling the two columns a "duplicate" signal. Both must hold:
# a strong positive correlation AND a small mean-absolute-percentage-difference
# between the raw values. Anything short of both is treated as "independent".
DUPLICATE_CORR_THRESHOLD = 0.9
DUPLICATE_MAPE_THRESHOLD = 10.0


def verdict_from_stats(corr: float, mape_between: float) -> str:
    """Pure decision function, unit-tested directly on synthetic inputs.

    Returns "duplicate" if corr is strictly above DUPLICATE_CORR_THRESHOLD and
    mape_between is strictly below DUPLICATE_MAPE_THRESHOLD; otherwise
    "independent". Values exactly at either threshold are NOT duplicate (the
    boundary belongs to "independent").
    """
    if corr > DUPLICATE_CORR_THRESHOLD and mape_between < DUPLICATE_MAPE_THRESHOLD:
        return "duplicate"
    return "independent"


def compare_baltic_an() -> dict:
    """Merge AN Data.csv's Baltic AN column with AN price weekly.csv's
    BalticAN_wk column on their nearest weekly dates (+/- 3 days) and compute
    a real correlation and mean-absolute-percentage-difference between them.
    """
    an = load_an_weekly()[["Baltic AN"]].rename(columns={"Baltic AN": "baltic_an_data_csv"})
    drv = load_weekly_drivers()[["BalticAN_wk"]]

    cmp = pd.merge_asof(
        an.sort_index(), drv.sort_index(), left_index=True, right_index=True,
        direction="nearest", tolerance=pd.Timedelta(days=3),
    ).dropna()

    corr = float(cmp["baltic_an_data_csv"].corr(cmp["BalticAN_wk"]))
    mape_between = float(
        ((cmp["baltic_an_data_csv"] - cmp["BalticAN_wk"]).abs() / cmp["baltic_an_data_csv"].abs() * 100).mean()
    )
    verdict = verdict_from_stats(corr, mape_between)
    preferred_column = (
        "AN Data.csv (Baltic AN)" if verdict == "duplicate"
        else "both (independent signal — consider as separate exogenous predictors)"
    )

    return {
        "n": int(len(cmp)),
        "corr": round(corr, 4),
        "mean_abs_pct_diff": round(mape_between, 4),
        "verdict": verdict,
        "preferred_column": preferred_column,
        "duplicate_corr_threshold": DUPLICATE_CORR_THRESHOLD,
        "duplicate_mape_threshold": DUPLICATE_MAPE_THRESHOLD,
    }


def main() -> dict:
    result = compare_baltic_an()
    print(result)
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(DEDUP_JSON, "w") as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    main()
