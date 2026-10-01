"""Authorization: roles (RBAC), object ownership (BOLA/IDOR), separation of duties, data scope."""
import pytest

import oracle
from checks import assert_envelope

cat = pytest.mark.cat
REJECT = {"decision": "REJECT", "comment": "Not a valid business expense"}


# ------------------------------------------------------------------ RBAC on the decision API
@cat("RBAC")
@pytest.mark.parametrize("eid", [1002, 1007, 1013, 9999])
def test_rbac_02_employee_cannot_decide(api, eid):
    """RBAC-02 EMPLOYEE calling the decision API -> 403 (own, colleague's, other team's, unknown id)"""
    assert_envelope(api.decide("asha", eid), 403, "forbidden")


@cat("RBAC")
@pytest.mark.parametrize("eid", [1013, 1011, 9999])
def test_rbac_03_auditor_is_read_only(api, eid):
    """RBAC-03 AUDITOR can read everything but cannot decide -> 403"""
    assert_envelope(api.decide("meera", eid), 403, "forbidden")
    assert_envelope(api.decide("meera", eid, REJECT), 403, "forbidden")


@cat("RBAC")
def test_rbac_04_role_checked_before_validation(api):
    """RBAC-04 EMPLOYEE gets 403 even with an invalid id/body (role is checked first)"""
    r = api.decide("ravi", "abc", {"decision": "MAYBE"})
    assert_envelope(r, 403, "forbidden")


@cat("RBAC")
@pytest.mark.parametrize("username", ["farah", "meera"])
def test_rbac_05_finance_and_auditor_see_all(api, username):
    """RBAC-05 FINANCE_ADMIN and AUDITOR list all 30 claims"""
    r = api.list(username, {"page_size": "100"})
    assert r.status_code == 200 and r.json()["total"] == 30


@cat("RBAC")
def test_rbac_06_denied_attempts_change_nothing(api):
    """RBAC-06 After all denied attempts the claims are unchanged"""
    for eid in (1002, 1007, 1013, 1011):
        seed_status = next(e["status"] for e in oracle.EXPENSES if e["id"] == eid)
        assert api.status_of(eid) == seed_status


# ------------------------------------------------------------------ object level (BOLA)
@cat("OBJECT")
def test_object_01_manager_cannot_touch_other_team(api):
    """OBJECT-01 Manager deciding another team's claim -> 404 (existence hidden)"""
    assert_envelope(api.decide("priya", 1013), 404, "not_found")


@cat("OBJECT")
def test_object_02_other_team_indistinguishable_from_missing(api):
    """OBJECT-02 'Not yours' and 'does not exist' produce identical responses"""
    a = api.decide("priya", 1013).json()["error"]
    b = api.decide("priya", 9999).json()["error"]
    assert (a["code"], a["message"]) == (b["code"], b["message"])


@cat("OBJECT")
def test_object_03_no_skip_level_approval(api):
    """OBJECT-03 Skip-level manager (vikram -> asha's claim) -> 404; only the DIRECT manager decides"""
    assert_envelope(api.decide("vikram", 1001), 404, "not_found")


@cat("OBJECT")
def test_object_04_manager_self_approval_forbidden(api):
    """OBJECT-04 Manager deciding their OWN claim -> 403 self_approval_forbidden"""
    assert_envelope(api.decide("priya", 1017), 403, "self_approval_forbidden")
    assert_envelope(api.decide("priya", 1017, REJECT), 403, "self_approval_forbidden")


@cat("OBJECT")
def test_object_05_finance_self_approval_forbidden(api):
    """OBJECT-05 Finance admin deciding their OWN pending claim -> 403 self_approval_forbidden"""
    assert_envelope(api.decide("farah", 1020), 403, "self_approval_forbidden")


@cat("OBJECT")
def test_object_06_forbidden_objects_unchanged(api):
    """OBJECT-06 Claims targeted by denied requests keep their original status"""
    for eid, st in ((1013, "SUBMITTED"), (1001, "SUBMITTED"), (1017, "SUBMITTED"), (1020, "PENDING_FINANCE")):
        assert api.status_of(eid) == st


# ------------------------------------------------------------------ data scope on the list API
@cat("OBJECT")
@pytest.mark.parametrize("username,total", [("asha", 8), ("ravi", 7), ("neha", 5), ("kiran", 1), ("sunil", 2),
                                            ("priya", 21), ("vikram", 13)])
def test_object_07_list_scope_per_role(api, username, total):
    """OBJECT-07 List returns exactly the caller's scope (own / own + direct reports)"""
    items = api.list_all(username)
    assert len(items) == total
    assert sorted(i["id"] for i in items) == sorted(e["id"] for e in oracle.visible(username))


@cat("OBJECT")
@pytest.mark.parametrize("username,employee_id,expected", [("asha", 2, 0), ("asha", 1, 8), ("priya", 3, 0),
                                                           ("priya", 2, 7), ("vikram", 1, 0), ("ravi", 6, 0)])
def test_object_08_employee_filter_never_widens_scope(api, username, employee_id, expected):
    """OBJECT-08 employee_id filter only narrows the caller's scope (200 with 0 items, never others' data)"""
    r = api.list(username, {"employee_id": str(employee_id), "page_size": "100"})
    assert r.status_code == 200
    assert r.json()["total"] == expected


@cat("OBJECT")
def test_object_09_status_filter_never_widens_scope(api):
    """OBJECT-09 asha filtering by PENDING_FINANCE sees only her own claim 1026"""
    r = api.list("asha", {"status": "PENDING_FINANCE"})
    assert [i["id"] for i in r.json()["items"]] == [1026]


@cat("OBJECT")
@pytest.mark.parametrize("username", ["asha", "priya", "farah"])
def test_object_10_no_excess_data_exposure(api, username):
    """OBJECT-10 List items expose exactly the documented fields (no hashes, emails, internals)"""
    for item in api.list_all(username):
        assert set(item) == oracle.ITEM_FIELDS, f"unexpected fields {set(item) ^ oracle.ITEM_FIELDS}"
