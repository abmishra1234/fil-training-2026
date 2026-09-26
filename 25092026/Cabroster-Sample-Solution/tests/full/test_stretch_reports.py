"""STRETCH — Daily summary report (R1, DEV-17). Excluded from the pass mark: run with -m stretch."""
import pytest

from support import MON, TUE

pytestmark = [pytest.mark.full, pytest.mark.stretch]


def test_report_rbac(api):
    """[X-RPT-01] GET /reports/daily-summary | R1, Section 3
    No token; employee; driver; admin.
    Expect: 401, 403, 403, 200"""
    p = {"travel_date": str(MON)}
    assert api.get("/reports/daily-summary", None, **p).status_code == 401
    assert api.get("/reports/daily-summary", api.employee().h, **p).status_code == 403
    assert api.get("/reports/daily-summary", api.driver().h, **p).status_code == 403
    assert api.get("/reports/daily-summary", api.admin.h, **p).status_code == 200


def test_report_requires_valid_date(api):
    """[X-RPT-02] GET /reports/daily-summary | R1
    Missing travel_date; malformed travel_date.
    Expect: 422"""
    assert api.get("/reports/daily-summary", api.admin.h).status_code == 422
    assert api.get("/reports/daily-summary", api.admin.h, travel_date="soon").status_code == 422


def test_report_empty_day(api):
    """[X-RPT-03] GET /reports/daily-summary | R1
    Day with no activity.
    Expect: both slots present with all counts 0 and utilisation_pct 0"""
    r = api.get("/reports/daily-summary", api.admin.h, travel_date=str(TUE)).json()
    for slot in ("PICKUP", "DROP"):
        s = r["slots"][slot]
        assert s["total_bookings"] == 0 and s["trips"] == 0 and s["utilisation_pct"] == 0


def test_report_counts(api):
    """[X-RPT-04] GET /reports/daily-summary | R1 definitions (Test Contract)
    MON PICKUP: 4-seat trip with 3 assigned (2 boarded→completed, 1 no-show), 1 unassigned, 1 cancelled; cancelled 6-seat trip.
    Expect: total 5, assigned 0, unassigned 1, cancelled 1, boarded 2, no_show 1, trips 1, capacity 4, utilisation 50.0"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=3, capacity=4)
    api.book(api.employee())                                   # unassigned
    e = api.employee()
    c = api.book(e)
    api.patch(f"/bookings/{c['id']}/cancel", None, e.h)        # cancelled
    t2 = api.trip(capacity=6)
    api.patch(f"/trips/{t2['id']}/cancel", None, api.admin.h)  # cancelled trip: not counted
    api.start_trip(trip["id"], drv)
    for b in bookings[:2]:
        api.patch(f"/driver/trips/{trip['id']}/bookings/{b['id']}", {"status": "BOARDED"}, drv.h)
    api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    s = api.get("/reports/daily-summary", api.admin.h, travel_date=str(MON)).json()["slots"]["PICKUP"]
    assert (s["total_bookings"], s["assigned"], s["unassigned"], s["cancelled"], s["boarded"], s["no_show"],
            s["trips"], s["total_capacity"]) == (5, 0, 1, 1, 2, 1, 1, 4)
    assert s["utilisation_pct"] == 50.0


def test_report_utilisation_rounding(api):
    """[X-RPT-05] GET /reports/daily-summary | R1 rounding to 1 decimal
    6-seat trip, 1 boarded.
    Expect: utilisation_pct 16.7"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1, capacity=6)
    api.start_trip(trip["id"], drv)
    api.patch(f"/driver/trips/{trip['id']}/bookings/{bookings[0]['id']}", {"status": "BOARDED"}, drv.h)
    s = api.get("/reports/daily-summary", api.admin.h, travel_date=str(MON)).json()["slots"]["PICKUP"]
    assert s["boarded"] == 1 and s["utilisation_pct"] == 16.7
