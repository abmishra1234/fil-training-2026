"""Auth contracts (Extension 6)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    # extra="forbid": a client sending {"role": "ADMIN"} gets 422 instead of
    # silently becoming an admin (mass-assignment protection).
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    # NIST SP 800-63B-4: >= 15 chars when the password is the only factor; allow long passphrases.
    password: str = Field(min_length=15, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)     # hashed_password is NOT listed -> never leaks


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int                                     # seconds


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool
