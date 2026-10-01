"""API 3 - strict input validation and mass-assignment protection."""
import pytest

from checks import assert_envelope, assert_no_leak

cat = pytest.mark.cat


@cat("INPUT")
@pytest.mark.parametrize("eid", ["abc", "0", "-1", "1001.5", "1001%20OR%201=1", "99999999999999999999",
                                 "1001;DROP", "1e3", "%27"])
def test_input_20_bad_path_id(api, eid):
    """INPUT-20 Non-positive / non-integer / oversized claim id -> 400 validation_error"""
    r = api.decide("priya", eid)
    assert_envelope(r, 400, "validation_error")
    assert_no_leak(r)


BAD_BODIES = {
    "empty_object": {},
    "decision_missing": {"comment": "looks fine to me"},
    "decision_lowercase": {"decision": "approve"},
    "decision_past_tense": {"decision": "APPROVED"},
    "decision_empty": {"decision": ""},
    "decision_null": {"decision": None},
    "decision_number": {"decision": 1},
    "decision_bool": {"decision": True},
    "decision_array": {"decision": ["APPROVE"]},
    "decision_object": {"decision": {"value": "APPROVE"}},
    "comment_too_long": {"decision": "APPROVE", "comment": "x" * 501},
    "comment_number": {"decision": "APPROVE", "comment": 42},
    "comment_array": {"decision": "APPROVE", "comment": ["ok"]},
}


@cat("INPUT")
@pytest.mark.parametrize("case", list(BAD_BODIES))
def test_input_21_bad_decision_body(api, case):
    """INPUT-21 Invalid decision body -> 400 validation_error; claim unchanged"""
    assert_envelope(api.decide("priya", 1002, BAD_BODIES[case]), 400, "validation_error")


MASS = {"status": "APPROVED", "amount_paise": 1, "employee_id": 4, "approver_id": 4, "id": 1,
        "role": "FINANCE_ADMIN", "currency": "USD"}


@cat("INPUT")
@pytest.mark.parametrize("field", list(MASS))
def test_input_22_mass_assignment_rejected(api, field):
    """INPUT-22 Unknown/extra fields in the body -> 400 (no mass assignment)"""
    r = api.decide("priya", 1002, {"decision": "APPROVE", field: MASS[field]})
    assert_envelope(r, 400, "validation_error")


@cat("INPUT")
def test_input_23_claim_untouched_after_bad_requests(api):
    """INPUT-23 After all rejected requests claim 1002 is still SUBMITTED with its original amount"""
    item = next(i for i in api.list_all("farah") if i["id"] == 1002)
    assert item["status"] == "SUBMITTED" and item["amount_paise"] == 85000 and item["currency"] == "INR"


@cat("INPUT")
@pytest.mark.parametrize("raw", [b"{", b"[]", b'"APPROVE"', b"null", b'{"decision": "APPROVE",}',
                                 b'{"decision": NaN}', b'{"decision": "APPROVE", "comment": Infinity}', b""])
def test_input_24_malformed_json(api, raw):
    """INPUT-24 Malformed JSON / non-object / NaN / empty body -> 400"""
    r = api.decide("priya", 1002, raw=raw, headers={"Content-Type": "application/json"})
    assert_envelope(r, 400, "validation_error")


@cat("INPUT")
@pytest.mark.parametrize("ctype", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x"])
def test_input_25_wrong_content_type(api, ctype):
    """INPUT-25 Non-JSON Content-Type on the decision API -> 415"""
    r = api.decide("priya", 1002, raw=b'{"decision":"APPROVE"}', headers={"Content-Type": ctype})
    assert_envelope(r, 415, "unsupported_media_type")


@cat("INPUT")
def test_input_26_comment_boundary_500_accepted(api):
    """INPUT-26 A 500-character comment is accepted (boundary)"""
    r = api.decide("vikram", 1030, {"decision": "APPROVE", "comment": "c" * 500})
    assert r.status_code == 200, r.text[:200]


@cat("INPUT")
def test_input_27_unicode_comment_accepted(api):
    """INPUT-27 Unicode comment (Hindi + emoji) within limits is accepted"""
    r = api.decide("priya", 1022, {"decision": "REJECT", "comment": "बिल संलग्न नहीं है - please attach 🧾"})
    assert r.status_code == 200, r.text[:200]
