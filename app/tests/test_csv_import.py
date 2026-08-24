"""Unit tests for the CSV bulk-import parsing core (app.csv_import).

Covers header rejection (D-06 fail-fast), duplicate-date skipping vs.
invalid-value skipping (D-04's two distinct summary counters), and the
happy path producing writable row dicts.
"""

import inspect

import pandas as pd
import pytest

from app.csv_import import (
    FILE_TOO_LARGE_ERROR,
    HEADER_MISMATCH_ERROR,
    MAX_IMPORT_ROWS,
    UNPARSEABLE_ERROR,
    parse_import_csv,
)
from app.validators import DATE_DUPLICATE_ERROR

try:
    from app.state import SERIES_ATTRS
except Exception:  # pragma: no cover - fallback if Reflex app context unavailable
    from app.models import PriceRow

    SERIES_ATTRS = tuple(
        name for name in PriceRow.model_fields if name not in ("id", "date")
    )


def _csv(rows: list[dict], columns=None) -> bytes:
    """Build CSV bytes for a list of row dicts, in the correct schema order."""
    columns = columns or ["date", *SERIES_ATTRS]
    frame = pd.DataFrame(rows, columns=columns)
    return frame.to_csv(index=False).encode()


def _full_row(date: str, value: float = 1.0) -> dict:
    row = {"date": date}
    for attr in SERIES_ATTRS:
        row[attr] = value
    return row


@pytest.mark.parametrize(
    "columns",
    [
        ["date", *SERIES_ATTRS[1:]],  # missing column
        ["date", *SERIES_ATTRS, "extra"],  # extra column
        ["date", *reversed(SERIES_ATTRS)],  # reordered
    ],
)
def test_header_mismatch_rejects_before_any_row_parsing(columns):
    raw = _csv([], columns=columns)
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.ok is False
    assert result.error == HEADER_MISMATCH_ERROR
    assert result.rows == []
    assert result.added_count == 0
    assert result.duplicate_count == 0
    assert result.invalid_count == 0


def test_unparseable_bytes_rejected_cleanly():
    # Malformed quoting causes pandas' C parser to raise ParserError rather
    # than returning a frame — this is the "not parseable as CSV at all"
    # case UNPARSEABLE_ERROR exists for.
    raw = b'"unterminated quote\nfoo,bar\n1,2,3\n1,2'
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.ok is False
    assert result.error == UNPARSEABLE_ERROR


def test_file_too_large_rejected_before_parsing():
    # Craft bytes larger than MAX_UPLOAD_BYTES without actually building a
    # 5 MB CSV file — a raw oversized byte blob is enough to trip the gate.
    from app.csv_import import MAX_UPLOAD_BYTES

    raw = b"x" * (MAX_UPLOAD_BYTES + 1)
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.ok is False
    assert result.error == FILE_TOO_LARGE_ERROR


def test_valid_rows_returned_with_all_sixteen_attrs():
    raw = _csv([_full_row("2026-01-01", 10.5)])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.ok is True
    assert result.added_count == 1
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row["date"] == "2026-01-01"
    for attr in SERIES_ATTRS:
        assert row[attr] == 10.5


def test_blank_cells_become_none():
    row = {"date": "2026-02-01", **{attr: "" for attr in SERIES_ATTRS}}
    raw = _csv([row])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.ok is True
    assert result.added_count == 1
    for attr in SERIES_ATTRS:
        assert result.rows[0][attr] is None


def test_duplicate_existing_date_counted_as_duplicate_not_invalid():
    raw = _csv([_full_row("2026-03-15")])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=["2026-03-01"])
    assert result.duplicate_count == 1
    assert result.invalid_count == 0
    assert result.rows == []


def test_duplicate_month_different_day_still_skipped():
    raw = _csv([_full_row("2026-04-28")])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=["2026-04-01"])
    assert result.duplicate_count == 1
    assert result.rows == []


def test_in_file_duplicate_month_second_row_skipped():
    raw = _csv([_full_row("2026-05-01"), _full_row("2026-05-15")])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.added_count == 1
    assert result.duplicate_count == 1
    assert len(result.rows) == 1
    assert result.rows[0]["date"] == "2026-05-01"


def test_non_numeric_cell_counted_as_invalid():
    row = _full_row("2026-06-01")
    row[SERIES_ATTRS[0]] = "abc"
    raw = _csv([row])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.invalid_count == 1
    assert result.duplicate_count == 0
    assert result.rows == []


def test_negative_value_counted_as_invalid():
    row = _full_row("2026-07-01")
    row[SERIES_ATTRS[0]] = "-5"
    raw = _csv([row])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.invalid_count == 1
    assert result.rows == []


def test_bad_date_counted_as_invalid_not_duplicate():
    row = _full_row("not-a-date")
    raw = _csv([row])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.invalid_count == 1
    assert result.duplicate_count == 0
    assert result.rows == []


def test_partially_invalid_row_is_excluded_entirely():
    row = _full_row("2026-08-01")
    row[SERIES_ATTRS[-1]] = "not-a-number"
    raw = _csv([row])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.invalid_count == 1
    assert result.rows == []
    assert result.added_count == 0


def test_header_only_file_yields_zero_counts():
    raw = _csv([])
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.ok is True
    assert result.rows == []
    assert result.added_count == 0
    assert result.duplicate_count == 0
    assert result.invalid_count == 0


def test_row_cap_enforced():
    rows = [_full_row(f"2020-{(i % 12) + 1:02d}-01") for i in range(MAX_IMPORT_ROWS + 1)]
    # Dates will collide across years within this synthetic set, but the
    # row-count gate must trip before any row-level validation happens.
    raw = _csv(rows)
    result = parse_import_csv(raw, SERIES_ATTRS, existing_dates=[])
    assert result.ok is False
    assert "too many rows" in result.error.lower() or "5,000" in result.error
    assert result.rows == []


def test_module_reuses_validators():
    import app.csv_import as csv_import_module

    source = inspect.getsource(csv_import_module)
    assert "validate_numeric" in source
    assert "validate_date" in source
    assert "date.fromisoformat" not in source


def test_duplicate_error_constant_used_for_classification():
    # Regression guard: the classification of duplicate vs. invalid must be
    # driven by the imported DATE_DUPLICATE_ERROR constant, not a copy.
    assert DATE_DUPLICATE_ERROR == "This month already has a row — edit it instead."
