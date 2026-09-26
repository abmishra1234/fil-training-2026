"""FULL SUITE — Pagination envelope & limits on every list endpoint (5.2, DEV-06)."""
import pytest

from support import MON, THU, TUE, WED, ids

pytestmark = pytest.mark.full

# (path, which actor calls it)
LISTS = [("/users", "admin"), ("/cabs", "admin"), ("/bookings", "admin"), ("/bookings/me", "employee"),
         ("/trips", "admin"), ("/driver/trips", "driver")]


def _actor(api, who):
    return {"admin": lambda: api.admin, "employee": api.employee, "driver": api.driver}[who]()


@pytest.mark.parametrize("path,who", LISTS)
@pytest.mark.parametrize("params", [{"size": 0}, {"size": 101}, {"page": 0}, {"page": -1}, {"size": "ten"}])
def test_invalid_page_params(api, path, who, params):
    """[F-PAG-01] all 6 list endpoints | 5.2 (page ≥ 1, size 1–100)
    size=0, size=101, page=0, page=-1, size='ten' on every list endpoint.
    Expect: 422 in all 30 combinations"""
    assert api.get(path, _actor(api, who).h, **params).status_code == 422


@pytest.mark.parametrize("path,who", LISTS)
def test_defaults_and_max_size(api, path, who):
    """[F-PAG-02] all 6 list endpoints | 5.2 defaults
    Call with no params, then size=100.
    Expect: page 1, size 10 by default; size=100 accepted"""
    h = _actor(api, who).h
    r = api.get(path, h).json()
    assert r["page"] == 1 and r["size"] == 10 and {"items", "total", "pages"} <= r.keys()
    assert api.get(path, h, size=100).status_code == 200


def test_envelope_math(api):
    """[F-PAG-03] GET /cabs | 5.2
    7 cabs, size=3: pages 1, 2, 3 and 4.
    Expect: total 7, pages 3; 3/3/1/0 items; page numbers echoed; no overlap and union = all 7"""
    all_ids = {api.cab()["id"] for _ in range(7)}
    seen = []
    for page, n in [(1, 3), (2, 3), (3, 1), (4, 0)]:
        r = api.get("/cabs", api.admin.h, page=page, size=3).json()
        assert (r["total"], r["pages"], r["page"], r["size"], len(r["items"])) == (7, 3, page, 3, n)
        seen += ids(r)
    assert len(seen) == 7 and set(seen) == all_ids


def test_empty_result_pages_zero(api):
    """[F-PAG-04] GET /cabs | 5.2
    No cabs exist.
    Expect: total 0, pages 0, items []"""
    r = api.get("/cabs", api.admin.h).json()
    assert r["total"] == 0 and r["pages"] == 0 and r["items"] == []


def test_exact_multiple(api):
    """[F-PAG-05] GET /cabs | 5.2 pages = ceil(total/size)
    6 cabs with size=3 and size=4.
    Expect: pages 2 in both cases"""
    for _ in range(6):
        api.cab()
    assert api.get("/cabs", api.admin.h, size=3).json()["pages"] == 2
    assert api.get("/cabs", api.admin.h, size=4).json()["pages"] == 2


def test_total_reflects_filters_not_page(api):
    """[F-PAG-06] GET /bookings/me | 5.2 + 5.4
    Employee books PICKUP+DROP for MON..THU (8), cancels 3 DROP bookings; filter status=BOOKED, size=2.
    Expect: total counts filtered rows (5), pages 3, 2 items on page 1"""
    e = api.employee()
    made = []
    for d in (MON, TUE, WED, THU):
        for s in ("PICKUP", "DROP"):
            made.append(api.book(e, d, s))
    for b in [m for m in made if m["slot"] == "DROP"][:3]:
        api.patch(f"/bookings/{b['id']}/cancel", None, e.h)
    r = api.get("/bookings/me", e.h, status="BOOKED", size=2).json()
    assert r["total"] == 5 and r["pages"] == 3 and len(r["items"]) == 2


def test_sorting_is_stable_across_pages(api):
    """[F-PAG-07] GET /cabs | 5.3 deterministic ordering
    10 cabs with identical capacity, sort_by=capacity, walk pages of 3.
    Expect: no duplicates / gaps (tie-break by id)"""
    all_ids = [api.cab(4)["id"] for _ in range(10)]
    seen = []
    for page in range(1, 5):
        seen += ids(api.get("/cabs", api.admin.h, sort_by="capacity", page=page, size=3).json())
    assert sorted(seen) == sorted(all_ids) and len(seen) == 10
