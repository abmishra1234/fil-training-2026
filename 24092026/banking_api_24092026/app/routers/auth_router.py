"""/api/v1/auth/... (Extension 6 - Tasks 1-3). v1 only."""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from ..core.auth import get_current_user
from ..models.user import User
from ..schemas.auth_schema import Token, UserCreate, UserOut
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, service: AuthService = Depends()):
    return service.register(payload.username, payload.password)


# TODO Task 2: POST /token
#   - body is OAuth2PasswordRequestForm (FORM data, not JSON)
#   - response_model=Token, delegate to service.login(...)


# TODO Task 3: GET /me  -> response_model=UserOut, returns Depends(get_current_user)
