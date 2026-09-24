"""Data access for users (Extension 6 - Task 1)."""
from typing import List, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User


class UserRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username.lower()).first()

    def list_all(self) -> List[User]:
        return self.db.query(User).order_by(User.id).all()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user
