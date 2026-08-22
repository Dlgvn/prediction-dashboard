"""Pure validation functions for price-table cell input.

Encodes two locked decisions from 04-CONTEXT.md:
  D-01: numeric validation is uniform across all 16 series columns — reject
        non-numeric input, reject negative values, allow blank/null. No
        series-specific business rules.
  D-02: date validation requires a valid calendar date that does not
        duplicate an existing row's calendar month (unless it is the row's
        own original date, i.e. editing in place).

No Reflex or app.models imports — kept dependency-free so it is importable
and unit-testable from both app/app/state.py and app/tests/.
"""

import math
from datetime import date

NUMERIC_ERROR = "Enter a positive number or leave blank."
DATE_INVALID_ERROR = "Enter a valid date."
DATE_DUPLICATE_ERROR = "This month already has a row — edit it instead."


def validate_numeric(raw: str) -> tuple[bool, float | None, str]:
    """D-01: reject non-numeric, reject negative, allow blank/null.

    One shared rule for all 16 series columns — no per-column branching.
    """
    stripped = raw.strip()
    if stripped == "":
        return True, None, ""

    try:
        value = float(stripped)
    except ValueError:
        return False, None, NUMERIC_ERROR

    if not math.isfinite(value) or value < 0:
        return False, None, NUMERIC_ERROR

    return True, value, ""


def validate_date(
    raw: str, existing_dates: list[str], own_original_date: str | None
) -> tuple[bool, str, str]:
    """D-02: must be a valid date and must not duplicate an existing month.

    `own_original_date` (if provided) is excluded from the duplicate check
    so a row being edited in place does not collide with itself.
    """
    stripped = raw.strip()
    try:
        parsed = date.fromisoformat(stripped)
    except ValueError:
        return False, "", DATE_INVALID_ERROR

    candidate_month = parsed.isoformat()[:7]
    occupied_months = {
        d[:7] for d in existing_dates if d != own_original_date
    }
    if candidate_month in occupied_months:
        return False, "", DATE_DUPLICATE_ERROR

    return True, parsed.isoformat(), ""
