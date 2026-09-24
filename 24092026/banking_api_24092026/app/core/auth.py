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

# PROVIDED. tokenUrl powers the "Authorize" button in Swagger UI.
# auto_error=False -> we raise our OWN 401 so it uses the standard error envelope.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


# ---------------------------------------------------------------- Task 3 (AuthN)
def get_current_user(token: Optional[str] = Depends(oauth2_scheme),
                     users: UserRepository = Depends()) -> User:
    # TODO Task 3:
    #   - no token                          -> NotAuthenticatedError("Not authenticated")
    #   - decode_access_token fails         -> NotAuthenticatedError("Invalid or expired token")
    #     (catch jwt.PyJWTError, ValueError, KeyError)
    #   - load the user by int(claims["sub"])
    #   - user missing or not is_active     -> NotAuthenticatedError(...)
    #   - return the User
    raise NotImplementedError("Task 3: get_current_user")


# ---------------------------------------------------------------- Task 6 (RBAC)
def require_role(*allowed_roles: str):
    """Dependency FACTORY: Depends(require_role(Role.ADMIN))."""
    def checker(user: User = Depends(get_current_user)) -> User:
        # TODO Task 6: role not in allowed_roles -> ForbiddenError(...)  (403)
        raise NotImplementedError("Task 6: require_role")
    return checker


# ---------------------------------------------------------------- Task 5 (ownership)
class AccountAccess:
    """Object-level authorization (OWASP API1:2023 BOLA).

    VIEW    : owner or ADMIN              -> else 404 (hide existence)
    OPERATE : owner only                  -> ADMIN gets 403, anyone else 404
    """
    def __init__(self, user: User = Depends(get_current_user),
                 accounts: AccountRepository = Depends()):
        self.user = user
        self.accounts = accounts

    def view(self, account_id: int) -> Account:
        # TODO Task 5
        raise NotImplementedError("Task 5: AccountAccess.view")

    def operate(self, account_id: int) -> Account:
        # TODO Task 5
        raise NotImplementedError("Task 5: AccountAccess.operate")


# PROVIDED wrappers so a route can say  dependencies=[Depends(can_view_account)]
# FastAPI fills `account_id` from the path automatically.
def can_view_account(account_id: int, access: AccountAccess = Depends()) -> Account:
    return access.view(account_id)


def can_operate_account(account_id: int, access: AccountAccess = Depends()) -> Account:
    return access.operate(account_id)
