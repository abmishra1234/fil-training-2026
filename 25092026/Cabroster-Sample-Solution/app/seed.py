"""python -m app.seed  — idempotent demo data."""
from sqlalchemy import select

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import Cab, Role, User, Zone

USERS = [
    dict(full_name="Transport Admin", email="admin@cabroster.in", phone="9800000001", role=Role.ADMIN),
    dict(full_name="Ravi Driver", email="ravi.driver@cabroster.in", phone="9800000002", role=Role.DRIVER, license_no="KA0120190001"),
    dict(full_name="Suresh Driver", email="suresh.driver@cabroster.in", phone="9800000003", role=Role.DRIVER, license_no="KA0120190002"),
] + [
    dict(full_name=f"Employee {i}", email=f"emp{i}@cabroster.in", phone=f"98100000{i:02d}", role=Role.EMPLOYEE,
         employee_code=f"EMP{i:03d}", home_address=f"{i}, Main Road", zone=Zone.EAST if i <= 4 else Zone.WEST)
    for i in range(1, 9)
]
CABS = [("KA01AB1234", "Maruti Dzire", 4), ("KA01AB5678", "Hyundai Aura", 4), ("KA02CD9012", "Toyota Innova", 6)]


def run():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for u in USERS:
            if not db.scalar(select(User.id).where(User.email == u["email"])):
                db.add(User(**u, hashed_password=hash_password("Password1")))
        for reg, model, cap in CABS:
            if not db.scalar(select(Cab.id).where(Cab.registration_no == reg)):
                db.add(Cab(registration_no=reg, model=model, capacity=cap))
        db.commit()
    print("Seed complete. All seeded users have password: Password1")


if __name__ == "__main__":
    run()
