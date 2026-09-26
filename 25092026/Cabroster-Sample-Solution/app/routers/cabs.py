from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import PageParams, require_roles
from app.core.query import apply_sort, paginate
from app.database import get_db
from app.models import Cab, Role, Slot, Trip, TripStatus
from app.schemas import CabCreate, CabRead, CabUpdate, Page
from app.services.mappers import seats_booked

router = APIRouter(prefix="/cabs", tags=["cabs"], dependencies=[Depends(require_roles(Role.ADMIN))])


@router.post("", response_model=CabRead, status_code=201, summary="Create cab")
def create_cab(data: CabCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Cab.id).where(Cab.registration_no == data.registration_no)):
        raise HTTPException(409, detail="Registration number already exists")
    cab = Cab(**data.model_dump(), is_active=True)
    db.add(cab)
    db.commit()
    db.refresh(cab)
    return cab


@router.get("", response_model=Page[CabRead], summary="List cabs")
def list_cabs(
    is_active: Optional[bool] = None, min_capacity: Optional[int] = Query(None, ge=1),
    q: Optional[str] = None, available_on: Optional[date] = None, slot: Optional[Slot] = None,
    sort_by: Literal["registration_no", "capacity", "created_at"] = "registration_no",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), db: Session = Depends(get_db),
):
    stmt = select(Cab)
    if is_active is not None:
        stmt = stmt.where(Cab.is_active == is_active)
    if min_capacity is not None:
        stmt = stmt.where(Cab.capacity >= min_capacity)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Cab.registration_no.ilike(like), Cab.model.ilike(like)))
    if (available_on is None) != (slot is None):
        raise HTTPException(422, detail="available_on and slot must be supplied together")
    if available_on is not None:
        busy = select(Trip.cab_id).where(Trip.travel_date == available_on, Trip.slot == slot,
                                         Trip.status != TripStatus.CANCELLED)
        stmt = stmt.where(Cab.is_active.is_(True), Cab.id.not_in(busy))
    stmt = apply_sort(stmt, sort_by, order, {"registration_no": Cab.registration_no, "capacity": Cab.capacity,
                                             "created_at": Cab.created_at}, Cab.id)
    return paginate(db, stmt, pg.page, pg.size)


def _get(db: Session, cab_id: int) -> Cab:
    cab = db.get(Cab, cab_id)
    if cab is None:
        raise HTTPException(404, detail="Cab not found")
    return cab


@router.get("/{cab_id}", response_model=CabRead, summary="Get cab")
def get_cab(cab_id: int, db: Session = Depends(get_db)):
    return _get(db, cab_id)


@router.patch("/{cab_id}", response_model=CabRead, summary="Update cab")
def update_cab(cab_id: int, data: CabUpdate, db: Session = Depends(get_db)):
    cab = _get(db, cab_id)
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        if v is None:
            raise HTTPException(422, detail=f"{k} cannot be null")
    if "capacity" in changes:
        trips = db.scalars(select(Trip).where(Trip.cab_id == cab.id, Trip.status == TripStatus.SCHEDULED)).all()
        if any(seats_booked(t) > changes["capacity"] for t in trips):
            raise HTTPException(409, detail="Capacity is lower than seats already assigned on a scheduled trip")
    for k, v in changes.items():
        setattr(cab, k, v)
    db.commit()
    db.refresh(cab)
    return cab
