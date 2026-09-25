"""FastAPI dependencies that answer the two security questions (Extension 6).

    get_current_user   -> AuthN : WHO is calling?              (Task 3)
    require_role(...)  -> AuthZ : is your ROLE allowed?         (Task 6)
    AccountAccess      -> AuthZ : do you OWN this account?      (Task 5)

Dependency chain for a protected route:
    get_db -> UserRepository -> get_current_user -> require_role / AccountAccess -> route
"""
from typing import Optional

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ..models.account import Account
from ..models.user import Role, User
from ..repositories.account_repository import AccountRepository
from ..repositories.user_repository import UserRepository
from .errors import AccountNotFoundError, ForbiddenError, NotAuthenticatedError
from .security import decode_access_token

# tokenUrl powers the "Authorize" button in Swagger UI.
# auto_error=False -> we raise our OWN 401 so it uses the standard error envelope.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


# ---------------------------------------------------------------- Task 3 (AuthN)
def get_current_user(token: Optional[str] = Depends(oauth2_scheme),
                     users: UserRepository = Depends()) -> User:
    if not token:
        raise NotAuthenticatedError("Not authenticated")
    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        # Expired, tampered, wrong algorithm, wrong issuer, garbage... all the same to the client.
        raise NotAuthenticatedError("Invalid or expired token")
    # Stateless does not mean blind: re-load the user so a disabled user is locked out now.
    user = users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise NotAuthenticatedError("Invalid or expired token")
    return user


# ---------------------------------------------------------------- Task 6 (RBAC)
def require_role(*allowed_roles: str):
    """Dependency FACTORY: Depends(require_role(Role.ADMIN))."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError("Insufficient role for this operation",
                                 {"required_roles": list(allowed_roles), "your_role": user.role})
        return user
    return checker


# ---------------------------------------------------------------- Task 5 (ownership)
class AccountAccess:
    """Object-level authorization - the #1 API risk (OWASP API1:2023 BOLA).

    VIEW    : owner or ADMIN              (read balances, history, schedules)
    OPERATE : owner only                  (move money, create/modify schedules)
    Customers probing someone else's account get 404, so they cannot even
    learn which account ids exist.
    """
    def __init__(self, user: User = Depends(get_current_user),
                 accounts: AccountRepository = Depends()):
        self.user = user
        self.accounts = accounts

    def _load(self, account_id: int) -> Account:
        account = self.accounts.get_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(account_id)
        return account

    def view(self, account_id: int) -> Account:
        account = self._load(account_id)
        if account.owner_id == self.user.id or self.user.role == Role.ADMIN:
            return account
        raise AccountNotFoundError(account_id)          # hide existence

    def operate(self, account_id: int) -> Account:
        account = self._load(account_id)
        if account.owner_id == self.user.id:
            return account
        if self.user.role == Role.ADMIN:                  # admin knows it exists -> 403
            raise ForbiddenError("Admins cannot move money on customer accounts",
                                 {"account_id": account_id})
        raise AccountNotFoundError(account_id)


# Small wrappers so a route can say  dependencies=[Depends(can_view_account)]
# FastAPI fills `account_id` from the path automatically.
def can_view_account(account_id: int, access: AccountAccess = Depends()) -> Account:
    return access.view(account_id)


def can_operate_account(account_id: int, access: AccountAccess = Depends()) -> Account:
    return access.operate(account_id)
