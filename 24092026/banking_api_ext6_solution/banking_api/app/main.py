from fastapi import FastAPI
from .routers.account_router import router as account_router
from .api.v1 import router as v1_router                                   # Task 1
from .core.middleware import register_middleware                          # Task 1B / 5
from .core.error_handlers import register_exception_handlers              # Task 5
from .models import account, transaction, scheduled_payment, idempotency, user  # noqa: F401 - register tables
from .services.auth_service import seed_admin                             # Ext 6
from .database import Base, SessionLocal, engine
from .config import settings

app = FastAPI(title=settings.APP_NAME)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:          # Ext 6: make sure the bootstrap admin exists
        seed_admin(db)

@app.get("/")
def root():
    return {"app": settings.APP_NAME,
            "message": "Welcome to the Personal Banking API"}

register_middleware(app)                # Task 1B + 5: X-Request-ID, Deprecation headers
register_exception_handlers(app)        # Task 5: one error format for /api/v1

app.include_router(v1_router)           # Task 1: NEW  -> /api/v1/...
app.include_router(account_router)      # UNCHANGED    -> /accounts/... (legacy)
