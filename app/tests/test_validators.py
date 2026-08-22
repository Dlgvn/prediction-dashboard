"""Tests for app.validators — D-01 (numeric) and D-02 (date) rules (DATA-04)."""

import inspect

import pytest

from app.validators import (
    DATE_DUPLICATE_ERROR,
    DATE_INVALID_ERROR,
    NUMERIC_ERROR,
    validate_date,
    validate_numeric,
)


def test_error_copy_matches_ui_spec_verbatim():
    assert NUMERIC_ERROR == "Enter a positive number or leave blank."
    assert DATE_INVALID_ERROR == "Enter a valid date."
    assert DATE_DUPLICATE_ERROR == "This month already has a row — edit it instead."


@pytest.mark.parametrize("raw", ["", "   "])
def test_validate_numeric_blank_means_null(raw):
    assert validate_numeric(raw) == (True, None, "")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("123", 123.0),
        ("0", 0.0),
        ("3.5", 3.5),
        ("1e3", 1000.0),
    ],
)
def test_validate_numeric_accepts_valid_numbers(raw, expected):
    ok, value, error = validate_numeric(raw)
    assert ok is True
    assert value == expected
    assert error == ""


def test_validate_numeric_tolerates_surrounding_whitespace():
    assert validate_numeric("  42  ") == (True, 42.0, "")


@pytest.mark.parametrize("raw", ["abc", "1,5", "--3", "1.2.3"])
def test_validate_numeric_rejects_non_numeric(raw):
    assert validate_numeric(raw) == (False, None, NUMERIC_ERROR)


@pytest.mark.parametrize("raw", ["-1", "-0.5"])
def test_validate_numeric_rejects_negative(raw):
    assert validate_numeric(raw) == (False, None, NUMERIC_ERROR)


def test_validate_numeric_zero_is_accepted():
    ok, value, error = validate_numeric("0")
    assert ok is True
    assert value == 0.0
    assert error == ""


@pytest.mark.parametrize("raw", ["nan", "inf"])
def test_validate_numeric_rejects_nan_and_inf(raw):
    assert validate_numeric(raw) == (False, None, NUMERIC_ERROR)


def test_validate_numeric_signature_has_exactly_one_positional_param():
    sig = inspect.signature(validate_numeric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


def test_validate_date_accepts_valid_new_date():
    assert validate_date("2026-03-01", ["2020-01-01"], None) == (
        True,
        "2026-03-01",
        "",
    )


def test_validate_date_rejects_unparseable():
    assert validate_date("not-a-date", [], None) == (False, "", DATE_INVALID_ERROR)


def test_validate_date_rejects_impossible_day_of_month():
    assert validate_date("2026-02-30", [], None) == (False, "", DATE_INVALID_ERROR)


def test_validate_date_rejects_empty_string():
    assert validate_date("", [], None) == (False, "", DATE_INVALID_ERROR)


def test_validate_date_rejects_duplicate_month():
    assert validate_date("2026-03-15", ["2026-03-01"], None) == (
        False,
        "",
        DATE_DUPLICATE_ERROR,
    )


def test_validate_date_allows_editing_own_row_within_same_month():
    assert validate_date("2026-03-15", ["2026-03-01"], "2026-03-01") == (
        True,
        "2026-03-15",
        "",
    )


def test_validate_date_allows_move_to_free_month_while_editing():
    assert validate_date(
        "2026-04-01", ["2026-03-01", "2026-05-01"], "2026-03-01"
    ) == (True, "2026-04-01", "")
