from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import Role, User
from app.schemas import ProfileUpdate, Token, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201, summary="Register as employee")
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(409, detail="Email already registered")
    if db.scalar(select(User.id).where(User.employee_code == data.employee_code)):
        raise HTTPException(409, detail="Employee code already registered")
    user = User(
        full_name=data.full_name, email=data.email, phone=data.phone,
        hashed_password=hash_password(data.password), role=Role.EMPLOYEE,
        employee_code=data.employee_code, home_address=data.home_address, zone=data.zone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Login (OAuth2 password flow)")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))
    if user is None or not verify_password(form.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(user.id, user.role.value), role=user.role)


@router.get("/me", response_model=UserRead, summary="Current user profile")
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserRead, summary="Update own profile")
def update_me(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    changes = data.model_dump(exclude_unset=True)
    if user.role == Role.DRIVER and ({"home_address", "zone"} & changes.keys()):
        raise HTTPException(422, detail="Drivers can only update phone")
    for k, v in changes.items():
        if v is None:
            raise HTTPException(422, detail=f"{k} cannot be null")
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user
