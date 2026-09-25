"""python -m app.seed  — TODO (DEV-05): idempotent demo data.
1 admin, 2 drivers, 8 employees across 2 zones, 3 cabs (capacities 4, 4, 6).
Running it twice must not create duplicates (check by email / registration_no first)."""
from app.database import Base, SessionLocal, engine  # noqa: F401


def run():
    Base.metadata.create_all(bind=engine)
    raise NotImplementedError("DEV-05")


if __name__ == "__main__":
    run()
