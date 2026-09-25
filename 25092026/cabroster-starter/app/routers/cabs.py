"""Cab management (DEV-08, DEV-16). ADMIN only (router-level dependency)."""
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import PageParams, require_roles
from app.database import get_db
from app.models import Role, Slot
from app.schemas import CabCreate, CabUpdate

router = APIRouter(prefix="/cabs", tags=["cabs"], dependencies=[Depends(require_roles(Role.ADMIN))])


@router.post("", status_code=201, summary="Create cab")
def create_cab(data: CabCreate, db: Session = Depends(get_db)):
    """C1: duplicate registration_no (after upper-casing) -> 409."""
    raise NotImplementedError("DEV-08")


@router.get("", summary="List cabs")
def list_cabs(
    is_active: Optional[bool] = None, min_capacity: Optional[int] = Query(None, ge=1),
    q: Optional[str] = None, available_on: Optional[date] = None, slot: Optional[Slot] = None,
    sort_by: Literal["registration_no", "capacity", "created_at"] = "registration_no",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), db: Session = Depends(get_db),
):
    """C2: available_on + slot must come together (else 422) — DEV-16."""
    raise NotImplementedError("DEV-08")


@router.get("/{cab_id}", summary="Get cab")
def get_cab(cab_id: int, db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-08")


@router.patch("/{cab_id}", summary="Update cab")
def update_cab(cab_id: int, data: CabUpdate, db: Session = Depends(get_db)):
    """C4: capacity below seats on a SCHEDULED trip -> 409."""
    raise NotImplementedError("DEV-08")
