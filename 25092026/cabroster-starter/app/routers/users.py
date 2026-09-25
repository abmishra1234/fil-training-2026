"""User management (DEV-07). ADMIN only."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import PageParams, require_roles
from app.database import get_db
from app.models import Role, User, Zone
from app.schemas import UserCreateByAdmin, UserStatusUpdate

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_roles(Role.ADMIN)


@router.post("", status_code=201, summary="Create driver/admin")  # TODO response_model
def create_user(data: UserCreateByAdmin, db: Session = Depends(get_db), _=Depends(admin_only)):
    """U1: duplicate email / license_no -> 409."""
    raise NotImplementedError("DEV-07")


@router.get("", summary="List users")  # TODO response_model=Page[UserRead]
def list_users(
    role: Optional[Role] = None, zone: Optional[Zone] = None, is_active: Optional[bool] = None,
    q: Optional[str] = None,
    sort_by: Literal["full_name", "created_at", "email"] = "created_at",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), db: Session = Depends(get_db), _=Depends(admin_only),
):
    """U2: q searches full_name, email, employee_code (case-insensitive)."""
    raise NotImplementedError("DEV-07")


@router.get("/{user_id}", summary="Get user")
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    raise NotImplementedError("DEV-07")


@router.patch("/{user_id}/status", summary="Activate / deactivate user")
def set_status(user_id: int, data: UserStatusUpdate, db: Session = Depends(get_db), me: User = Depends(admin_only)):
    """U4: 404 unknown; admin cannot change own status -> 409."""
    raise NotImplementedError("DEV-07")
