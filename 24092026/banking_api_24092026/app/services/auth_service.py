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
        # TODO Task 1:
        #   1. normalise username to lower-case
        #   2. if it exists -> raise UsernameTakenError(username)       (409)
        #   3. save User(username, hashed_password=hash_password(...), role=Role.CUSTOMER)
        raise NotImplementedError("Task 1: register")

    # ---------- Task 2 ----------
    def login(self, username: str, password: str) -> dict:
        # TODO Task 2:
        #   1. look the user up
        #   2. ALWAYS verify one hash (the user's, or DUMMY_HASH if not found)
        #   3. unknown user / wrong password / inactive -> the SAME
        #      NotAuthenticatedError("Incorrect username or password")
        #   4. return {"access_token": ..., "token_type": "bearer",
        #              "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}
        raise NotImplementedError("Task 2: login")

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
    """Create the bootstrap admin from settings, once. Called at startup. (PROVIDED)"""
    if not (settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD):
        return None
    repo = UserRepository(db)
    existing = repo.get_by_username(settings.ADMIN_USERNAME)
    if existing:
        return existing
    try:
        hashed = hash_password(settings.ADMIN_PASSWORD)
    except NotImplementedError:
        print("[seed_admin] hash_password() not implemented yet (Task 1) - admin not created")
        return None
    return repo.create(User(username=settings.ADMIN_USERNAME.lower(),
                            hashed_password=hashed, role=Role.ADMIN))
