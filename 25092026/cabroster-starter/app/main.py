from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, bookings, cabs, driver, reports, trips, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="CabRoster", version="1.0.0", lifespan=lifespan)

for r in (auth.router, users.router, cabs.router, bookings.router, trips.router, driver.router, reports.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/health", tags=["health"], summary="Health check")
def health():
    return {"status": "ok"}
