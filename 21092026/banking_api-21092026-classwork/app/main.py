from fastapi import FastAPI # type: ignore
from .routers.account_router import router as account_router
from .database import Base, engine
from .config import settings

app = FastAPI(title=settings.APP_NAME)

@app.on_event("startup")
def on_startup():
    # Auto-create tables (for demo convenience)
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"app": settings.APP_NAME, "message": "Welcome to the Personal Banking API"}

app.include_router(account_router)
