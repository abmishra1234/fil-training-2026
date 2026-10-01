"""API 2 - strict query validation (A05 Injection / HTTP parameter pollution)."""
import pytest

from checks import assert_envelope, assert_no_leak

cat = pytest.mark.cat

BAD = [
    ("status_lowercase", "status=approved"), ("status_empty", "status="), ("status_trailing_comma", "status=SUBMITTED,"),
    ("status_unknown", "status=PAID"), ("status_sql", "status=SUBMITTED'%20OR%20'1'='1"),
    ("category_lowercase", "category=travel"), ("category_unknown", "category=FOOD"),
    ("employee_zero", "employee_id=0"), ("employee_negative", "employee_id=-1"), ("employee_text", "employee_id=abc"),
    ("employee_decimal", "employee_id=1.5"), ("employee_huge", "employee_id=99999999999"),
    ("employee_sql", "employee_id=1%20OR%201=1"),
    ("date_bad_month", "from_date=2026-13-01"), ("date_feb_30", "from_date=2026-02-30"),
    ("date_ddmmyyyy", "from_date=01-07-2026"), ("date_short", "to_date=2026-7-1"),
    ("date_with_time", "to_date=2026-07-01T00:00:00"), ("date_sql", "from_date=2026-07-01'%20OR%201=1--"),
    ("date_reversed_range", "from_date=2026-08-01&to_date=2026-07-01"),
    ("amount_negative", "min_amount=-1"), ("amount_text", "max_amount=abc"), ("amount_exponent", "min_amount=1e3"),
    ("amount_decimal", "min_amount=1.5"), ("amount_too_big", "max_amount=100000001"),
    ("amount_reversed_range", "min_amount=500&max_amount=100"),
    ("q_empty", "q="), ("q_51_chars", "q=" + "x" * 51), ("q_null_byte", "q=abc%00def"), ("q_newline", "q=abc%0Adef"),
    ("sort_unknown_field", "sort=password_hash"), ("sort_alias", "sort=amount"),
    ("sort_sql", "sort=amount_paise;DROP%20TABLE%20expenses"), ("sort_double_minus", "sort=--amount_paise"),
    ("sort_plus", "sort=%2Bamount_paise"), ("sort_sql_case", "sort=(CASE%20WHEN%201=1%20THEN%20id%20END)"),
    ("page_zero", "page=0"), ("page_negative", "page=-1"), ("page_text", "page=abc"), ("page_too_big", "page=10001"),
    ("page_size_zero", "page_size=0"), ("page_size_101", "page_size=101"), ("page_size_text", "page_size=ten"),
    ("unknown_param", "foo=bar"), ("unknown_role_param", "role=FINANCE_ADMIN"), ("unknown_scope_param", "all=true"),
    ("duplicate_status", "status=SUBMITTED&status=APPROVED"), ("duplicate_page", "page=1&page=2"),
    ("duplicate_employee", "employee_id=1&employee_id=2"),
]


@cat("INPUT")
@pytest.mark.parametrize("name,qs", BAD, ids=[b[0] for b in BAD])
def test_input_11_invalid_query_rejected(api, name, qs):
    """INPUT-11 Invalid, unknown or duplicated query parameters -> 400 validation_error"""
    r = api.http.get("/api/v1/expenses?" + qs, headers=api.auth("farah"))
    assert_envelope(r, 400, "validation_error")
    assert_no_leak(r)


@cat("INPUT")
def test_input_12_validation_error_names_the_field(api):
    """INPUT-12 Validation errors tell the client WHAT was wrong (message mentions the parameter)"""
    r = api.http.get("/api/v1/expenses?page_size=500", headers=api.auth("farah"))
    err = assert_envelope(r, 400, "validation_error")
    assert "page_size" in (err["message"] + str(err.get("details", ""))), err


@cat("INPUT")
def test_input_13_employee_sees_400_not_data(api):
    """INPUT-13 Validation also applies to employees (no bypass by role)"""
    r = api.http.get("/api/v1/expenses?sort=password_hash", headers=api.auth("asha"))
    assert_envelope(r, 400, "validation_error")
