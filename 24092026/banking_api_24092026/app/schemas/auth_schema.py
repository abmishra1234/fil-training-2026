"""Auth contracts (Extension 6)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    # TODO Task 1: reject unknown fields (so {"role": "ADMIN"} -> 422)
    # TODO Task 1: username 3-32 chars, only letters, digits, _ . -
    # TODO Task 1: password 15-128 chars (NIST SP 800-63B-4, password-only login)
    username: str
    password: str


class UserOut(BaseModel):
    # TODO Task 1: which fields may leave the server? (never the hash!)
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int                                     # seconds


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool
