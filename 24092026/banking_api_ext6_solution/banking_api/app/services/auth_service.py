"""Registration and login rules (Extension 6 - Tasks 1-2)."""
from typing import Optional

from fastapi import Depends

from ..config import settings
from ..core.errors import NotAuthenticatedError, ResourceNotFoundError, UsernameTakenError
from ..core.security import (DUMMY_HASH, create_access_token, hash_password,
                             verify_password)
from ..models.user import Role, User
from ..repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, repo: UserRepository = Depends()):
        self.repo = repo

    # ---------- Task 1 ----------
    def register(self, username: str, password: str) -> User:
        username = username.lower()
        if self.repo.get_by_username(username):
            raise UsernameTakenError(username)
        # Role is decided by the SERVER, never by the request body.
        return self.repo.create(User(username=username,
                                     hashed_password=hash_password(password),
                                     role=Role.CUSTOMER))

    # ---------- Task 2 ----------
    def login(self, username: str, password: str) -> dict:
        user = self.repo.get_by_username(username)
        # Always run ONE hash verification, even for unknown users (timing-safe).
        ok = verify_password(password, user.hashed_password if user else DUMMY_HASH)
        if not user or not ok or not user.is_active:
            # One generic message: never reveal WHICH part was wrong.
            raise NotAuthenticatedError("Incorrect username or password")
        return {"access_token": create_access_token(user.id, user.role),
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}

    # ---------- Task 6 (admin) ----------
    def list_users(self):
        return self.repo.list_all()

    def set_active(self, user_id: int, is_active: bool) -> User:
        user = self.repo.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError("User not found", {"user_id": user_id})
        user.is_active = is_active
        return self.repo.save(user)


def seed_admin(db) -> Optional[User]:
    """Create the bootstrap admin from settings, once. Called at startup."""
    if not (settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD):
        return None
    repo = UserRepository(db)
    existing = repo.get_by_username(settings.ADMIN_USERNAME)
    if existing:
        return existing
    return repo.create(User(username=settings.ADMIN_USERNAME.lower(),
                            hashed_password=hash_password(settings.ADMIN_PASSWORD),
                            role=Role.ADMIN))
