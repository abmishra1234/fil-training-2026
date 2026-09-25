"""Auth & profile endpoints (DEV-04). Paths and status codes are fixed by the spec — do not change them."""
from fastapi import APIRouter, Depends, HTTPException, status  # noqa: F401
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import ProfileUpdate, Token, UserRead, UserRegister  # noqa: F401

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, summary="Register as employee")  # TODO response_model=UserRead
def register(data: UserRegister, db: Session = Depends(get_db)):
    """A1: duplicate email or employee_code -> 409. Role is always EMPLOYEE."""
    raise NotImplementedError("DEV-04 register")


@router.post("/login", response_model=Token, summary="Login (OAuth2 password flow)")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """A2: username = email (case-insensitive). Wrong creds or inactive -> 401."""
    raise NotImplementedError("DEV-04 login")


@router.get("/me", response_model=UserRead, summary="Current user profile")
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", summary="Update own profile")  # TODO response_model=UserRead
def update_me(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A4: phone / home_address / zone. DRIVER may change phone only (else 422)."""
    raise NotImplementedError("DEV-04 update_me")
