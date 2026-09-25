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


@router.post("/token", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), service: AuthService = Depends()):
    # OAuth2 password flow: body is FORM data (username=..&password=..), not JSON.
    return service.login(form.username, form.password)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
