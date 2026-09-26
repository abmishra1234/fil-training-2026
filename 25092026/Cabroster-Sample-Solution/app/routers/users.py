from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import PageParams, require_roles
from app.core.query import apply_sort, paginate
from app.core.security import hash_password
from app.database import get_db
from app.models import Role, User, Zone
from app.schemas import Page, UserCreateByAdmin, UserRead, UserStatusUpdate

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_roles(Role.ADMIN)


@router.post("", response_model=UserRead, status_code=201, summary="Create driver/admin")
def create_user(data: UserCreateByAdmin, db: Session = Depends(get_db), _=Depends(admin_only)):
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(409, detail="Email already registered")
    if data.license_no and db.scalar(select(User.id).where(User.license_no == data.license_no)):
        raise HTTPException(409, detail="License number already registered")
    user = User(full_name=data.full_name, email=data.email, phone=data.phone,
                hashed_password=hash_password(data.password), role=data.role, license_no=data.license_no)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=Page[UserRead], summary="List users")
def list_users(
    role: Optional[Role] = None, zone: Optional[Zone] = None, is_active: Optional[bool] = None,
    q: Optional[str] = None,
    sort_by: Literal["full_name", "created_at", "email"] = "created_at",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), db: Session = Depends(get_db), _=Depends(admin_only),
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if zone:
        stmt = stmt.where(User.zone == zone)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like), User.employee_code.ilike(like)))
    stmt = apply_sort(stmt, sort_by, order, {"full_name": User.full_name, "created_at": User.created_at,
                                             "email": User.email}, User.id)
    return paginate(db, stmt, pg.page, pg.size)


@router.get("/{user_id}", response_model=UserRead, summary="Get user")
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, detail="User not found")
    return user


@router.patch("/{user_id}/status", response_model=UserRead, summary="Activate / deactivate user")
def set_status(user_id: int, data: UserStatusUpdate, db: Session = Depends(get_db), me: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, detail="User not found")
    if user.id == me.id:
        raise HTTPException(409, detail="You cannot change your own status")
    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user
