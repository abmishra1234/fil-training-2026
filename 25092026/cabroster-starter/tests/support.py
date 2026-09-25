"""Shared constants and the `Api` helper used by both suites.

Every test runs against a fresh in-memory database and a fake clock.
The default fake "now" is Friday 25-Sep-2026 10:00 IST, so Monday 28-Sep-2026
is the natural next working day to travel on.
"""
import base64
import hashlib
import hmac
import itertools
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

API = "/api/v1"
IST = timezone(timedelta(hours=5, minutes=30))


def ist(y, m, d, hh=0, mm=0, ss=0) -> datetime:
    return datetime(y, m, d, hh, mm, ss, tzinfo=IST)


# ---- calendar used across tests (Sep/Oct 2026) ----
THU_PAST = date(2026, 9, 24)
FRI = date(2026, 9, 25)
SAT = date(2026, 9, 26)
SUN = date(2026, 9, 27)
MON = date(2026, 9, 28)
TUE = date(2026, 9, 29)
WED = date(2026, 9, 30)
THU = date(2026, 10, 1)
FRI2 = date(2026, 10, 2)
DEFAULT_NOW = ist(2026, 9, 25, 10, 0)

PASSWORD = "Passw0rd99"
ADMIN_EMAIL = "root.admin@acmecorp.in"
ADMIN_PASSWORD = "Admin12345"


class Clock:
    """Mutable fake clock injected through the `get_now` dependency."""

    def __init__(self, now: datetime):
        self.now = now

    def set(self, dt: datetime) -> None:
        assert dt.tzinfo is not None, "always use ist(...)"
        self.now = dt


@dataclass
class Actor:
    id: int
    email: str
    h: dict
    data: dict = field(default_factory=dict)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def jwt_payload(token: str) -> dict:
    """Decode a JWT payload WITHOUT verifying it (test inspection only)."""
    part = token.split(".")[1]
    part += "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part))


def make_hs256_token(payload: dict, secret: str) -> str:
    """Build an HS256 JWT by hand, so tests do not depend on any JWT library."""
    def b64(obj) -> str:
        raw = json.dumps(obj, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    signing_input = f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64(payload)}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"


def ids(resp_json) -> list:
    return [x["id"] for x in resp_json["items"]]


class Api:
    """Thin helper around TestClient that knows the CabRoster contract."""

    _seq = itertools.count(1)

    def __init__(self, client, clock: Clock):
        self.c = client
        self.clock = clock
        self._admin = None

    # ---- raw HTTP (paths are relative to /api/v1) ----
    def get(self, path, h=None, **params):
        return self.c.get(API + path, headers=h, params=params or None)

    def post(self, path, json=None, h=None):
        return self.c.post(API + path, json=json, headers=h)

    def patch(self, path, json=None, h=None):
        return self.c.patch(API + path, json=json, headers=h)

    def delete(self, path, h=None):
        return self.c.delete(API + path, headers=h)

    # ---- auth ----
    def login_resp(self, email, password=PASSWORD):
        return self.c.post(API + "/auth/login", data={"username": email, "password": password})

    def login(self, email, password=PASSWORD) -> dict:
        r = self.login_resp(email, password)
        assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
        return bearer(r.json()["access_token"])

    @property
    def admin(self) -> Actor:
        if self._admin is None:
            h = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
            me = self.get("/auth/me", h).json()
            self._admin = Actor(me["id"], ADMIN_EMAIL, h, me)
        return self._admin

    # ---- factories ----
    def n(self) -> int:
        return next(self._seq)

    def employee_payload(self, **overrides) -> dict:
        n = self.n()
        body = {
            "full_name": f"Employee {n}",
            "email": f"emp{n}@acmecorp.in",
            "phone": f"9{n:09d}",
            "password": PASSWORD,
            "employee_code": f"EMP{n:05d}",
            "home_address": f"{n}, 5th Cross, Indiranagar",
            "zone": "EAST",
        }
        body.update(overrides)
        return {k: v for k, v in body.items() if v is not ...}

    def register(self, **overrides):
        return self.c.post(API + "/auth/register", json=self.employee_payload(**overrides))

    def employee(self, **overrides) -> Actor:
        r = self.register(**overrides)
        assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
        data = r.json()
        pw = overrides.get("password", PASSWORD)
        return Actor(data["id"], data["email"], self.login(data["email"], pw), data)

    def staff_payload(self, role="DRIVER", **overrides) -> dict:
        n = self.n()
        body = {
            "full_name": f"{role.title()} {n}",
            "email": f"{role.lower()}{n}@acmecorp.in",
            "phone": f"8{n:09d}",
            "password": PASSWORD,
            "role": role,
            "license_no": f"DL{n:08d}" if role == "DRIVER" else None,
        }
        body.update(overrides)
        return {k: v for k, v in body.items() if v is not None and v is not ...}

    def create_staff(self, role="DRIVER", **overrides):
        return self.post("/users", self.staff_payload(role, **overrides), self.admin.h)

    def driver(self, **overrides) -> Actor:
        r = self.create_staff("DRIVER", **overrides)
        assert r.status_code == 201, f"create driver failed: {r.status_code} {r.text}"
        data = r.json()
        return Actor(data["id"], data["email"], self.login(data["email"]), data)

    def cab_payload(self, capacity=4, **overrides) -> dict:
        n = self.n()
        body = {"registration_no": f"KA01AB{n:04d}", "model": "Maruti Dzire", "capacity": capacity}
        body.update(overrides)
        return body

    def cab(self, capacity=4, **overrides) -> dict:
        r = self.post("/cabs", self.cab_payload(capacity, **overrides), self.admin.h)
        assert r.status_code == 201, f"create cab failed: {r.status_code} {r.text}"
        return r.json()

    def book_resp(self, actor: Actor, travel_date=MON, slot="PICKUP"):
        return self.post("/bookings", {"travel_date": str(travel_date), "slot": slot}, actor.h)

    def book(self, actor: Actor, travel_date=MON, slot="PICKUP") -> dict:
        r = self.book_resp(actor, travel_date, slot)
        assert r.status_code == 201, f"booking failed: {r.status_code} {r.text}"
        return r.json()

    def trip_resp(self, cab_id, driver_id, travel_date=MON, slot="PICKUP", zone="EAST"):
        return self.post("/trips", {"travel_date": str(travel_date), "slot": slot, "zone": zone,
                                    "cab_id": cab_id, "driver_id": driver_id}, self.admin.h)

    def trip(self, cab_id=None, driver_id=None, travel_date=MON, slot="PICKUP", zone="EAST", capacity=4) -> dict:
        cab_id = cab_id or self.cab(capacity)["id"]
        driver_id = driver_id or self.driver().id
        r = self.trip_resp(cab_id, driver_id, travel_date, slot, zone)
        assert r.status_code == 201, f"create trip failed: {r.status_code} {r.text}"
        return r.json()

    def assign(self, trip_id, booking_ids):
        return self.post(f"/trips/{trip_id}/bookings", {"booking_ids": booking_ids}, self.admin.h)

    def booking(self, booking_id) -> dict:
        r = self.get(f"/bookings/{booking_id}", self.admin.h)
        assert r.status_code == 200, r.text
        return r.json()

    def trip_detail(self, trip_id) -> dict:
        r = self.get(f"/trips/{trip_id}", self.admin.h)
        assert r.status_code == 200, r.text
        return r.json()

    # ---- composite scenario: a scheduled trip with N assigned passengers ----
    def scheduled_trip(self, passengers=2, capacity=4, travel_date=MON, slot="PICKUP", zone="EAST"):
        drv = self.driver()
        trip = self.trip(driver_id=drv.id, travel_date=travel_date, slot=slot, zone=zone, capacity=capacity)
        emps, bookings = [], []
        for _ in range(passengers):
            e = self.employee(zone=zone)
            emps.append(e)
            bookings.append(self.book(e, travel_date, slot))
        if bookings:
            r = self.assign(trip["id"], [b["id"] for b in bookings])
            assert r.status_code == 200, f"assign failed: {r.status_code} {r.text}"
        return trip, drv, emps, bookings

    def start_trip(self, trip_id, drv: Actor, at=None):
        self.clock.set(at or ist(2026, 9, 28, 6, 5))
        r = self.patch(f"/driver/trips/{trip_id}/start", None, drv.h)
        assert r.status_code == 200, f"start failed: {r.status_code} {r.text}"
        return r.json()
