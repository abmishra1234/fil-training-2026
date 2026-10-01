"""API 3 - POST /api/v1/expenses/{id}/decision : approval workflow and idempotency (sequential retries)."""
import secrets

import pytest

import oracle
from checks import assert_envelope
from harness import SEED

cat = pytest.mark.cat
SEED_BY_ID = {e["id"]: e for e in SEED["expenses"]}
REJECT = {"decision": "REJECT", "comment": "Receipt missing for this claim"}


def ok(r, status):
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert set(body) == oracle.ITEM_FIELDS, f"decision response fields: {set(body)}"
    assert body["status"] == status
    return body


@cat("WORKFLOW")
def test_wf_01_manager_approves_small_claim(api):
    """WF-01 Direct manager approves a claim <= Rs 50,000 -> APPROVED (other fields unchanged)"""
    body = ok(api.decide("priya", 1001), "APPROVED")
    seed = SEED_BY_ID[1001]
    for k in ("id", "employee_id", "category", "amount_paise", "currency", "expense_date", "description"):
        assert body[k] == seed[k]


@cat("WORKFLOW")
def test_wf_02_threshold_is_inclusive(api):
    """WF-02 Exactly Rs 50,000 (5,000,000 paise) -> APPROVED by the manager alone"""
    ok(api.decide("priya", 1009), "APPROVED")


@cat("WORKFLOW")
def test_wf_03_above_threshold_needs_finance(api):
    """WF-03 One paisa above the threshold -> PENDING_FINANCE"""
    ok(api.decide("priya", 1010), "PENDING_FINANCE")


@cat("WORKFLOW")
def test_wf_04_two_step_approval(api):
    """WF-04 Rs 75,000: manager -> PENDING_FINANCE, then finance -> APPROVED"""
    ok(api.decide("priya", 1004), "PENDING_FINANCE")
    ok(api.decide("farah", 1004), "APPROVED")


@cat("WORKFLOW")
def test_wf_05_finance_rejects(api):
    """WF-05 Finance rejects a PENDING_FINANCE claim with a comment -> REJECTED"""
    ok(api.decide("farah", 1015, REJECT), "REJECTED")


@cat("WORKFLOW")
def test_wf_06_manager_rejects(api):
    """WF-06 Manager rejects a SUBMITTED claim with a comment -> REJECTED"""
    ok(api.decide("priya", 1007, REJECT), "REJECTED")


@cat("WORKFLOW")
def test_wf_07_manager_rejects_high_value_directly(api):
    """WF-07 Manager may reject a high-value claim outright (no finance step needed)"""
    ok(api.decide("vikram", 1028, REJECT), "REJECTED")


@cat("WORKFLOW")
@pytest.mark.parametrize("body", [{"decision": "REJECT"}, {"decision": "REJECT", "comment": "too short"},
                                  {"decision": "REJECT", "comment": " " * 12},
                                  {"decision": "REJECT", "comment": None}])
def test_wf_08_rejection_requires_reason(api, body):
    """WF-08 REJECT without a >= 10 character comment -> 400; claim stays SUBMITTED"""
    assert_envelope(api.decide("priya", 1008, body), 400, "validation_error")
    assert api.status_of(1008) == "SUBMITTED"


@cat("WORKFLOW")
@pytest.mark.parametrize("eid", [1003, 1005, 1011])
def test_wf_09_manager_only_acts_on_submitted(api, eid):
    """WF-09 Manager on APPROVED / REJECTED / PENDING_FINANCE claim -> 409 invalid_state"""
    assert_envelope(api.decide("priya", eid), 409, "invalid_state")


@cat("WORKFLOW")
@pytest.mark.parametrize("eid", [1013, 1014, 1027])
def test_wf_10_finance_only_acts_on_pending_finance(api, eid):
    """WF-10 Finance on SUBMITTED / APPROVED / REJECTED claim -> 409 invalid_state"""
    assert_envelope(api.decide("farah", eid), 409, "invalid_state")


@cat("WORKFLOW")
def test_wf_11_decided_claims_are_final(api):
    """WF-11 A decided claim cannot be re-decided with a new key (APPROVED -> REJECT = 409)"""
    assert_envelope(api.decide("priya", 1001, REJECT), 409, "invalid_state")
    assert_envelope(api.decide("farah", 1004, REJECT), 409, "invalid_state")
    assert api.status_of(1001) == "APPROVED"


@cat("WORKFLOW")
def test_wf_12_manager_of_manager(api):
    """WF-12 vikram decides for his direct reports priya (manager) and farah (finance)"""
    ok(api.decide("vikram", 1017), "APPROVED")
    ok(api.decide("vikram", 1021), "APPROVED")


@cat("WORKFLOW")
def test_wf_13_list_reflects_decisions(api):
    """WF-13 The list API shows the new status to the claim owner"""
    mine = {i["id"]: i["status"] for i in api.list_all("asha")}
    assert mine[1001] == "APPROVED" and mine[1004] == "APPROVED"
    r = api.list("ravi", {"status": "PENDING_FINANCE", "page_size": "100"})
    assert sorted(i["id"] for i in r.json()["items"]) == [1010, 1011]


# ------------------------------------------------------------------ idempotency
@cat("WORKFLOW")
def test_wf_14_idempotent_replay(api):
    """WF-14 Same Idempotency-Key + same body -> same 200 response, applied once"""
    key = "judge-idem-" + secrets.token_hex(6)
    first = ok(api.decide("priya", 1023, key=key), "APPROVED")
    again = api.decide("priya", 1023, key=key)
    assert again.status_code == 200 and again.json() == first


@cat("WORKFLOW")
def test_wf_15_idempotency_key_reuse_with_other_request(api):
    """WF-15 Same key with a different body or claim -> 409 idempotency_conflict"""
    key = "judge-reuse-" + secrets.token_hex(6)
    ok(api.decide("priya", 1029, key=key), "APPROVED")
    assert_envelope(api.decide("priya", 1029, REJECT, key=key), 409, "idempotency_conflict")
    assert_envelope(api.decide("priya", 1002, key=key), 409, "idempotency_conflict")
    assert api.status_of(1002) == "SUBMITTED"


@cat("WORKFLOW")
def test_wf_16_idempotency_keys_are_per_user(api):
    """WF-16 Keys are scoped per caller: another user may use the same key string"""
    key = "judge-shared-key-01"
    ok(api.decide("priya", 1006, key=key), "APPROVED")
    ok(api.decide("vikram", 1024, key=key), "APPROVED")


@cat("WORKFLOW")
@pytest.mark.parametrize("key", [None, "", "short", "k" * 65, "key with spaces", "<script>x</script>", "key_underscore!"])
def test_wf_17_idempotency_key_required_and_validated(api, key):
    """WF-17 Missing or malformed Idempotency-Key -> 400 (8-64 chars of A-Z a-z 0-9 -)"""
    h = dict(api.auth("priya"))
    if key is not None:
        h["Idempotency-Key"] = key
    r = api.http.post("/api/v1/expenses/1030/decision", json={"decision": "APPROVE"}, headers=h)
    assert_envelope(r, 400, "validation_error")
