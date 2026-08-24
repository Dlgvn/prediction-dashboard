"""Pure CSV parsing and per-row validation core for bulk import.

Deliberately Reflex-free and ORM-free (importable from tests without a Reflex
runtime), mirroring `validators.py`'s dependency discipline. This module never
opens a database session — all persistence stays behind `DashboardState` per
the app's sole-DB-boundary rule.

Encodes locked decisions from 10-CONTEXT.md:
  D-02/D-03: per-row validation reuses `validate_numeric`/`validate_date`
             from validators.py verbatim — never reimplemented here.
  D-04:      the parse result carries added / duplicate-skipped /
             invalid-skipped counts as a summary.
  D-06:      header/schema mismatch is a fail-fast gate — no row is ever
             parsed from a file whose header doesn't exactly match.
"""

import dataclasses
import io

import pandas as pd

from app.validators import DATE_DUPLICATE_ERROR, validate_date, validate_numeric

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # Claude's Discretion cap per 10-CONTEXT.md
MAX_IMPORT_ROWS = 5000

HEADER_MISMATCH_ERROR = (
    "This file doesn't match the expected format. Expected columns: date, "
    "HDAN, PPAN, … (16 series columns), in that order — export a "
    "template from 'Export to Excel' if unsure."
)
UNPARSEABLE_ERROR = "This file couldn't be read as a CSV. Save it as .csv and try again."
FILE_TOO_LARGE_ERROR = "This file is too large to import (limit 5 MB)."
TOO_MANY_ROWS_ERROR = "This file has too many rows to import (limit 5,000)."


@dataclasses.dataclass(frozen=True)
class ImportParseResult:
    """Summary of a CSV parse/validate pass, ready for a batch DB write."""

    ok: bool
    error: str
    rows: list[dict]
    added_count: int
    duplicate_count: int
    invalid_count: int

    @property
    def total_skipped(self) -> int:
        return self.duplicate_count + self.invalid_count


def _failure(error: str) -> ImportParseResult:
    return ImportParseResult(
        ok=False,
        error=error,
        rows=[],
        added_count=0,
        duplicate_count=0,
        invalid_count=0,
    )


def parse_import_csv(
    raw: bytes, series_attrs: tuple[str, ...], existing_dates: list[str]
) -> ImportParseResult:
    """Parse and validate an uploaded CSV against the wide-table schema.

    Order of operations is strict and fail-fast (D-06): size gate, then
    parse, then header gate (before any row-level work), then row-count
    gate, then the per-row validation loop.
    """
    # 1. Size gate.
    if len(raw) > MAX_UPLOAD_BYTES:
        return _failure(FILE_TOO_LARGE_ERROR)

    # 2. Parse. dtype=str + keep_default_na=False so every cell reaches
    #    validate_numeric as the raw string the manual-edit path would have
    #    received, and blanks arrive as "" rather than float NaN.
    try:
        frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except Exception:
        return _failure(UNPARSEABLE_ERROR)

    # 3. Header gate — must happen before any iteration over rows.
    expected_columns = ("date", *series_attrs)
    if tuple(frame.columns) != expected_columns:
        return _failure(HEADER_MISMATCH_ERROR)

    # 4. Row-count gate.
    if len(frame) > MAX_IMPORT_ROWS:
        return _failure(TOO_MANY_ROWS_ERROR)

    # 5. Row loop.
    rows: list[dict] = []
    duplicate_count = 0
    invalid_count = 0
    seen_dates = list(existing_dates)

    for record in frame.to_dict(orient="records"):
        date_ok, iso_date, date_error = validate_date(
            str(record["date"]), seen_dates, own_original_date=None
        )
        if not date_ok:
            if date_error == DATE_DUPLICATE_ERROR:
                duplicate_count += 1
            else:
                invalid_count += 1
            continue

        values: dict = {}
        row_invalid = False
        for attr in series_attrs:
            numeric_ok, value, _ = validate_numeric(str(record[attr]))
            if not numeric_ok:
                invalid_count += 1
                row_invalid = True
                break
            values[attr] = value

        if row_invalid:
            continue

        rows.append({"date": iso_date, **values})
        seen_dates.append(iso_date)

    # 6. Success.
    return ImportParseResult(
        ok=True,
        error="",
        rows=rows,
        added_count=len(rows),
        duplicate_count=duplicate_count,
        invalid_count=invalid_count,
    )
