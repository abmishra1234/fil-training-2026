"""CabRoster test harness.

Relies ONLY on the hook points listed in the spec's "Test Contract" appendix:
    app.main.app                      FastAPI instance
    app.database.Base / SessionLocal / get_db
    app.core.deps.get_now             current-time dependency (used via Depends)
    app.core.security.hash_password   str -> str
    app.models.User, app.models.Role  to insert the very first ADMIN
    app.config.settings               JWT_SECRET_KEY, JWT_ALGORITHM (HS256)
Everything else is exercised as a black box over HTTP.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.core.deps import get_now
from app.core.security import hash_password
from app.database import Base, SessionLocal, get_db
from app.main import app
from app.models import Role, User
from support import ADMIN_EMAIL, ADMIN_PASSWORD, DEFAULT_NOW, Api, Clock

_admin_hash_cache = {}


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    original_bind = SessionLocal.kw.get("bind")
    SessionLocal.configure(bind=eng)
    yield eng
    SessionLocal.configure(bind=original_bind)
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def clock():
    return Clock(DEFAULT_NOW)


@pytest.fixture
def client(engine, clock):
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_now] = lambda: clock.now
    # raise_server_exceptions=False: an unhandled error becomes a 500 response => a clean test failure
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_id(engine):
    if "h" not in _admin_hash_cache:
        _admin_hash_cache["h"] = hash_password(ADMIN_PASSWORD)
    with SessionLocal() as s:
        u = User(full_name="Root Admin", email=ADMIN_EMAIL, phone="9000000001",
                 hashed_password=_admin_hash_cache["h"], role=Role.ADMIN, is_active=True)
        s.add(u)
        s.commit()
        return u.id


@pytest.fixture
def api(client, clock, admin_id):
    return Api(client, clock)
