"""/api/v1/admin/... - ADMIN role only (Extension 6 - Task 6)."""
from typing import List

from fastapi import APIRouter, Depends

from ..core.auth import require_role
from ..models.user import Role
from ..schemas.auth_schema import UserOut, UserStatusUpdate
from ..services.auth_service import AuthService

# Router-level dependency: EVERY route below requires the ADMIN role.
router = APIRouter(prefix="/admin", tags=["Admin"],
                   dependencies=[Depends(require_role(Role.ADMIN))])


@router.get("/users", response_model=List[UserOut])
def list_users(service: AuthService = Depends()):
    return service.list_users()


@router.patch("/users/{user_id}", response_model=UserOut)
def set_user_status(user_id: int, patch: UserStatusUpdate, service: AuthService = Depends()):
    return service.set_active(user_id, patch.is_active)
