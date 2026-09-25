"""FULL SUITE — Cab management (C1–C4, DEV-08, DEV-16)."""
import pytest

from support import MON, TUE, ids, ist

pytestmark = pytest.mark.full


@pytest.mark.parametrize("reg", ["KA1AB1234", "KA01ABC1234", "1A01AB1234", "KA01AB123", "KA01AB12345",
                                 "KA-01-AB-1234", "", "KA01 AB 1234"])
def test_invalid_registration(api, reg):
    """[F-CAB-01] POST /cabs | 4.2 regex ^[A-Z]{2}\\d{2}[A-Z]{1,2}\\d{4}$
    Eight malformed registration numbers.
    Expect: 422"""
    assert api.post("/cabs", api.cab_payload(registration_no=reg), api.admin.h).status_code == 422


@pytest.mark.parametrize("reg,stored", [("KA01A1234", "KA01A1234"), ("mh12de3456", "MH12DE3456")])
def test_valid_registration_variants(api, reg, stored):
    """[F-CAB-02] POST /cabs | 4.2
    Single-letter series 'KA01A1234'; lower-case input 'mh12de3456'.
    Expect: 201 and registration stored upper-case"""
    r = api.post("/cabs", api.cab_payload(registration_no=reg), api.admin.h)
    assert r.status_code == 201 and r.json()["registration_no"] == stored


def test_duplicate_registration_after_normalisation(api):
    """[F-CAB-03] POST /cabs | C1
    Create 'KA01AB1111' then 'ka01ab1111'.
    Expect: second call 409"""
    api.cab(registration_no="KA01AB1111")
    assert api.post("/cabs", api.cab_payload(registration_no="ka01ab1111"), api.admin.h).status_code == 409


@pytest.mark.parametrize("cap,code", [(0, 422), (-1, 422), (13, 422), (1, 201), (12, 201), ("four", 422)])
def test_capacity_bounds(api, cap, code):
    """[F-CAB-04] POST /cabs | 4.2 capacity 1–12
    Capacity 0, -1, 13, 1, 12, 'four'.
    Expect: 422 outside 1–12 or non-integer; 201 at the boundaries"""
    assert api.post("/cabs", api.cab_payload(capacity=cap), api.admin.h).status_code == code


@pytest.mark.parametrize("body", [{"model": ...}, {"model": "M" * 51}, {"capacity": ...}, {"registration_no": ...}])
def test_cab_required_fields(api, body):
    """[F-CAB-05] POST /cabs | 4.2
    Missing model / 51-char model / missing capacity / missing registration.
    Expect: 422"""
    payload = {k: v for k, v in api.cab_payload(**body).items() if v is not ...}
    assert api.post("/cabs", payload, api.admin.h).status_code == 422


def test_new_cab_is_active(api):
    """[F-CAB-06] POST /cabs | 4.2 default is_active
    Create a cab without is_active.
    Expect: is_active true and id/created_at present"""
    cab = api.cab()
    assert cab["is_active"] is True and {"id", "created_at", "model", "capacity"} <= cab.keys()


def test_get_and_patch_unknown_cab(api):
    """[F-CAB-07] GET/PATCH /cabs/{id} | C3, C4
    Unknown cab id.
    Expect: 404 for both"""
    assert api.get("/cabs/9999", api.admin.h).status_code == 404
    assert api.patch("/cabs/9999", {"model": "X"}, api.admin.h).status_code == 404


@pytest.mark.parametrize("body", [{"capacity": 0}, {"capacity": 13}, {"model": ""}])
def test_patch_validation(api, body):
    """[F-CAB-08] PATCH /cabs/{id} | C4
    Invalid capacity or empty model.
    Expect: 422"""
    cab = api.cab()
    assert api.patch(f"/cabs/{cab['id']}", body, api.admin.h).status_code == 422


def test_patch_partial_keeps_other_fields(api):
    """[F-CAB-09] PATCH /cabs/{id} | C4
    Patch only the model.
    Expect: capacity and registration unchanged"""
    cab = api.cab(6)
    r = api.patch(f"/cabs/{cab['id']}", {"model": "Ertiga"}, api.admin.h).json()
    assert r["capacity"] == 6 and r["registration_no"] == cab["registration_no"] and r["model"] == "Ertiga"


def test_reduce_capacity_below_assigned_seats(api):
    """[F-CAB-10] PATCH /cabs/{id} | C4
    Cab (cap 4) has 3 passengers on a SCHEDULED trip; set capacity 2, then 3.
    Expect: capacity 2 -> 409 (unchanged); capacity 3 -> 200"""
    trip, *_ = api.scheduled_trip(passengers=3, capacity=4)
    cab_id = trip["cab_id"]
    assert api.patch(f"/cabs/{cab_id}", {"capacity": 2}, api.admin.h).status_code == 409
    assert api.get(f"/cabs/{cab_id}", api.admin.h).json()["capacity"] == 4
    assert api.patch(f"/cabs/{cab_id}", {"capacity": 3}, api.admin.h).status_code == 200


def test_reduce_capacity_allowed_when_trip_completed(api):
    """[F-CAB-11] PATCH /cabs/{id} | C4 (only SCHEDULED trips count)
    Cab's only trip with 3 passengers is COMPLETED; set capacity 1.
    Expect: 200"""
    trip, drv, _, _ = api.scheduled_trip(passengers=3, capacity=4)
    api.start_trip(trip["id"], drv)
    api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert api.patch(f"/cabs/{trip['cab_id']}", {"capacity": 1}, api.admin.h).status_code == 200


def test_deactivate_cab(api):
    """[F-CAB-12] PATCH /cabs/{id} | C4, BR-17
    Deactivate a cab, then filter lists and try to use it for a trip.
    Expect: shows under is_active=false only; trip creation 422"""
    cab = api.cab()
    other = api.cab()
    assert api.patch(f"/cabs/{cab['id']}", {"is_active": False}, api.admin.h).json()["is_active"] is False
    assert ids(api.get("/cabs", api.admin.h, is_active="false").json()) == [cab["id"]]
    assert ids(api.get("/cabs", api.admin.h, is_active="true").json()) == [other["id"]]
    assert api.trip_resp(cab["id"], api.driver().id).status_code == 422


def test_list_filters_min_capacity_and_q(api):
    """[F-CAB-13] GET /cabs | C2 min_capacity, q
    Cabs: 4-seat Dzire, 6-seat Innova, 7-seat Ertiga.
    Expect: min_capacity=6 -> Innova+Ertiga; q='innova' (any case) -> Innova; q=reg fragment -> that cab"""
    api.cab(4, model="Dzire")
    inn = api.cab(6, model="Toyota Innova", registration_no="MH12XY0006")
    ert = api.cab(7, model="Ertiga")
    assert set(ids(api.get("/cabs", api.admin.h, min_capacity=6).json())) == {inn["id"], ert["id"]}
    assert ids(api.get("/cabs", api.admin.h, q="INNOVA").json()) == [inn["id"]]
    assert ids(api.get("/cabs", api.admin.h, q="mh12").json()) == [inn["id"]]


def test_list_sorting(api):
    """[F-CAB-14] GET /cabs | C2 sort
    Default sort (registration_no asc), capacity desc, created_at desc.
    Expect: correct order each time"""
    c1 = api.cab(4, registration_no="TN09AA0001")
    c2 = api.cab(6, registration_no="AP09AA0001")
    c3 = api.cab(5, registration_no="KL09AA0001")
    assert ids(api.get("/cabs", api.admin.h).json()) == [c2["id"], c3["id"], c1["id"]]
    assert ids(api.get("/cabs", api.admin.h, sort_by="capacity", order="desc").json()) == [c2["id"], c3["id"], c1["id"]]
    assert ids(api.get("/cabs", api.admin.h, sort_by="capacity").json()) == [c1["id"], c3["id"], c2["id"]]


@pytest.mark.parametrize("params", [{"sort_by": "model"}, {"order": "DESCENDING"}, {"min_capacity": "big"}])
def test_list_invalid_params(api, params):
    """[F-CAB-15] GET /cabs | 5.3
    Non-whitelisted sort_by, invalid order, non-integer min_capacity.
    Expect: 422"""
    assert api.get("/cabs", api.admin.h, **params).status_code == 422


def test_available_on_filter(api):
    """[F-CAB-16] GET /cabs | C2 available_on + slot (DEV-16)
    busy cab on MON PICKUP; cab with DROP trip only; cab whose trip was cancelled; inactive cab; free cab.
    Expect: available_on=MON&slot=PICKUP returns exactly: drop-only cab, cancelled-trip cab, free cab"""
    busy = api.cab()
    drop_only = api.cab()
    cancelled = api.cab()
    inactive = api.cab()
    free = api.cab()
    api.trip(busy["id"])
    api.trip(drop_only["id"], slot="DROP")
    t = api.trip(cancelled["id"])
    api.patch(f"/trips/{t['id']}/cancel", None, api.admin.h)
    api.patch(f"/cabs/{inactive['id']}", {"is_active": False}, api.admin.h)
    r = api.get("/cabs", api.admin.h, available_on=str(MON), slot="PICKUP").json()
    assert set(ids(r)) == {drop_only["id"], cancelled["id"], free["id"]} and r["total"] == 3
    # a different date: every active cab is free
    r2 = api.get("/cabs", api.admin.h, available_on=str(TUE), slot="PICKUP").json()
    assert r2["total"] == 4


@pytest.mark.parametrize("params", [{"available_on": str(MON)}, {"slot": "PICKUP"}])
def test_available_on_requires_both(api, params):
    """[F-CAB-17] GET /cabs | C2
    Supply only one of available_on / slot.
    Expect: 422"""
    assert api.get("/cabs", api.admin.h, **params).status_code == 422
