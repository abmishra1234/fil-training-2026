"""API 2 - GET /api/v1/expenses : filter, sort and paginate correctly."""
import re
from datetime import datetime

import pytest

import oracle
from harness import SEED

cat = pytest.mark.cat
SEED_BY_ID = {e["id"]: e for e in SEED["expenses"]}


def check(api, username, params):
    r = api.list(username, params)
    assert r.status_code == 200, f"{params}: {r.status_code} {r.text[:200]}"
    body = r.json()
    exp = oracle.query(username, params)
    got = [i["id"] for i in body["items"]]
    assert body["total"] == exp["total"], f"{params}: total {body['total']} != {exp['total']}"
    assert got == exp["ids"], f"{params}:\n got      {got}\n expected {exp['ids']}"
    return body


@cat("FILTER")
def test_filter_01_defaults(api):
    """FILTER-01 No params: page=1, page_size=20, sorted by newest submitted_at, total=30"""
    body = check(api, "farah", {})
    assert body["page"] == 1 and body["page_size"] == 20 and len(body["items"]) == 20


@cat("FILTER")
@pytest.mark.parametrize("status", ["SUBMITTED", "PENDING_FINANCE", "APPROVED", "REJECTED",
                                    "SUBMITTED,REJECTED", "APPROVED,REJECTED,PENDING_FINANCE"])
def test_filter_02_status(api, status):
    """FILTER-02 status filter (single and comma-separated list)"""
    check(api, "farah", {"status": status, "page_size": "100"})


@cat("FILTER")
@pytest.mark.parametrize("category", ["TRAVEL", "MEALS", "LODGING", "TRAINING", "OFFICE_SUPPLIES", "INTERNET"])
def test_filter_03_category(api, category):
    """FILTER-03 category filter"""
    check(api, "farah", {"category": category, "page_size": "100"})


@cat("FILTER")
@pytest.mark.parametrize("params", [{"from_date": "2026-08-01"}, {"to_date": "2026-07-04"},
                                    {"from_date": "2026-07-05", "to_date": "2026-07-05"},
                                    {"from_date": "2026-07-01", "to_date": "2026-07-31"},
                                    {"from_date": "2026-06-15", "to_date": "2026-06-15"},
                                    {"from_date": "2027-01-01"}])
def test_filter_04_date_range_inclusive(api, params):
    """FILTER-04 from_date / to_date on expense_date, both bounds inclusive"""
    check(api, "farah", {**params, "page_size": "100"})


@cat("FILTER")
def test_filter_05_single_day_boundary(api):
    """FILTER-05 from_date == to_date == 2026-07-05 returns exactly claims 1002 and 1029"""
    body = check(api, "farah", {"from_date": "2026-07-05", "to_date": "2026-07-05", "sort": "expense_date"})
    assert [i["id"] for i in body["items"]] == [1002, 1029]


@cat("FILTER")
@pytest.mark.parametrize("params", [{"min_amount": "5000000", "max_amount": "5000000"}, {"min_amount": "5000001"},
                                    {"max_amount": "1"}, {"min_amount": "0"}, {"max_amount": "99900"},
                                    {"min_amount": "100000", "max_amount": "1000000"},
                                    {"min_amount": "100000000"}])
def test_filter_06_amount_range_inclusive(api, params):
    """FILTER-06 min_amount / max_amount in paise, both bounds inclusive"""
    check(api, "farah", {**params, "page_size": "100"})


@cat("FILTER")
@pytest.mark.parametrize("q", ["hotel", "HOTEL", "HoTeL", "broadband", "Team lunch", "flight", "zzz-no-match"])
def test_filter_07_text_search_case_insensitive(api, q):
    """FILTER-07 q = case-insensitive substring match on description"""
    check(api, "farah", {"q": q, "page_size": "100"})


@cat("FILTER")
@pytest.mark.parametrize("q,expected", [("%", [1002, 1016]), ("_", [1007, 1016, 1027]), ("50%", [1002]),
                                        ("100%_", [1016]), ("o'brien", [1008]), ("' OR '1'='1", []),
                                        ("%' --", []), ("\\", []), ("*", []), (".*", [])])
def test_filter_08_search_is_literal(api, q, expected):
    """FILTER-08 Wildcards (% _ * regex) and quotes in q are matched LITERALLY"""
    r = api.list("farah", {"q": q, "page_size": "100", "sort": "expense_date"})
    assert r.status_code == 200, r.text[:200]
    assert sorted(i["id"] for i in r.json()["items"]) == expected


@cat("FILTER")
@pytest.mark.parametrize("params", [
    {"status": "SUBMITTED", "category": "TRAVEL", "min_amount": "100000", "sort": "amount_paise"},
    {"status": "SUBMITTED,PENDING_FINANCE", "from_date": "2026-07-01", "to_date": "2026-08-31", "sort": "-amount_paise"},
    {"category": "MEALS", "q": "lunch", "sort": "expense_date"},
    {"employee_id": "1", "status": "SUBMITTED", "sort": "-expense_date"},
    {"employee_id": "2", "min_amount": "5000000", "max_amount": "5000001"},
])
def test_filter_09_combined_filters_are_anded(api, params):
    """FILTER-09 Multiple filters combine with AND"""
    check(api, "farah", {**params, "page_size": "100"})


@cat("FILTER")
@pytest.mark.parametrize("sort", ["expense_date", "-expense_date", "amount_paise", "-amount_paise",
                                  "submitted_at", "-submitted_at"])
def test_filter_10_sorting_with_stable_tie_break(api, sort):
    """FILTER-10 All 6 sort keys; ties broken by id ascending"""
    check(api, "farah", {"sort": sort, "page_size": "100"})


@cat("FILTER")
def test_filter_11_pagination_walk(api):
    """FILTER-11 Walking pages (size 7) returns every claim exactly once, in order"""
    seen = []
    for page in range(1, 6):
        body = check(api, "farah", {"page": str(page), "page_size": "7", "sort": "amount_paise"})
        assert body["page"] == page and body["page_size"] == 7 and body["total"] == 30
        seen += [i["id"] for i in body["items"]]
    assert len(seen) == 30 and len(set(seen)) == 30


@cat("FILTER")
def test_filter_12_page_beyond_end(api):
    """FILTER-12 Page past the end -> 200 with empty items and the real total"""
    body = check(api, "farah", {"page": "6", "page_size": "7"})
    assert body["items"] == [] and body["total"] == 30
    body = check(api, "farah", {"page": "10000"})
    assert body["items"] == []


@cat("FILTER")
@pytest.mark.parametrize("size", ["1", "100"])
def test_filter_13_page_size_bounds(api, size):
    """FILTER-13 page_size boundaries 1 and 100 are accepted"""
    check(api, "farah", {"page_size": size})


@cat("FILTER")
def test_filter_14_empty_result(api):
    """FILTER-14 A filter matching nothing -> 200, items [], total 0"""
    body = check(api, "farah", {"category": "INTERNET", "min_amount": "1000000"})
    assert body["items"] == [] and body["total"] == 0


@cat("FILTER")
def test_filter_15_response_shape_and_types(api):
    """FILTER-15 Response shape {items,page,page_size,total} and item field types"""
    r = api.list("farah", {"page_size": "100"})
    body = r.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert r.headers.get("content-type", "").startswith("application/json")
    for i in body["items"]:
        s = SEED_BY_ID[i["id"]]
        assert isinstance(i["id"], int) and isinstance(i["employee_id"], int)
        assert isinstance(i["amount_paise"], int) and not isinstance(i["amount_paise"], bool)
        assert i["amount_paise"] == s["amount_paise"] and i["currency"] == "INR"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", i["expense_date"]) and i["expense_date"] == s["expense_date"]
        got = datetime.fromisoformat(i["submitted_at"].replace("Z", "+00:00"))
        want = datetime.fromisoformat(s["submitted_at"].replace("Z", "+00:00"))
        assert got == want, f"submitted_at {i['submitted_at']} != {s['submitted_at']}"
        assert got.utcoffset() is not None, "submitted_at must carry a timezone (UTC)"
        assert i["description"] == s["description"]


@cat("FILTER")
@pytest.mark.parametrize("username,params", [("priya", {"status": "SUBMITTED"}), ("priya", {"sort": "amount_paise"}),
                                             ("vikram", {"category": "TRAVEL"}), ("asha", {"q": "lunch"}),
                                             ("vikram", {"status": "PENDING_FINANCE", "sort": "-amount_paise"})])
def test_filter_16_filters_apply_within_scope(api, username, params):
    """FILTER-16 Filters combined with role scope (manager/employee) match the oracle"""
    check(api, username, {**params, "page_size": "100"})


@cat("FILTER")
@pytest.mark.parametrize("params", [{"page_size": "100"}, {"q": "50", "page_size": "50"}, {"min_amount": "100000000"},
                                    {"page": "10000"}, {"q": "x" * 50}])
def test_filter_17_boundary_values_accepted(api, params):
    """FILTER-17 Maximum legal values (q=50 chars, page=10000, amount=100000000) -> 200"""
    assert api.list("farah", params).status_code == 200


@cat("INPUT")
def test_input_10_stored_markup_returned_as_json_data(api):
    """INPUT-10 Stored '<script>' text is returned as JSON data, never rendered as HTML"""
    r = api.list("farah", {"q": "<script>"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["items"][0]["description"] == SEED_BY_ID[1006]["description"]
