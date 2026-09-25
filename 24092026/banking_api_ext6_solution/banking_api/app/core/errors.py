"""Domain exceptions for the banking API (Task 5).

Services raise these. They never build HTTP responses themselves;
the global handlers in error_handlers.py turn them into JSON.
"""
from typing import Any, Dict, Optional


class BankingError(Exception):
    """Base class. Every subclass says which HTTP status and error code it maps to."""
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidRequestError(BankingError):
    status_code = 400
    code = "invalid_request"


class AccountNotFoundError(BankingError):
    status_code = 404
    code = "account_not_found"

    def __init__(self, account_id: int):
        super().__init__("Account not found", {"account_id": account_id})


class ResourceNotFoundError(BankingError):
    status_code = 404
    code = "resource_not_found"


class InsufficientFundsError(BankingError):
    # 400 keeps the legacy contract. A v2 could move this to 422.
    status_code = 400
    code = "insufficient_funds"

    def __init__(self, current_balance: float, requested_amount: float):
        super().__init__("Insufficient funds", {
            "current_balance": round(current_balance, 2),
            "requested_amount": round(requested_amount, 2),
        })


class KYCRequiredError(BankingError):
    status_code = 403
    code = "kyc_required"

    def __init__(self, account_id: int):
        super().__init__("Account must be KYC compliant for this operation",
                         {"account_id": account_id})


class IdempotencyKeyReusedError(BankingError):
    # IETF draft 'Idempotency-Key' header spec recommends 422 for key reuse
    # with a different payload.
    status_code = 422
    code = "idempotency_key_reused"

    def __init__(self, key: str):
        super().__init__("Idempotency-Key was already used with a different request body",
                         {"idempotency_key": key})


# ---------------- Extension 6: authentication & authorization ----------------

class NotAuthenticatedError(BankingError):
    """401 - we do not know who you are (no token, bad token, expired token)."""
    status_code = 401
    code = "not_authenticated"
    # RFC 6750: a 401 for a Bearer-protected resource must say how to authenticate.
    headers = {"WWW-Authenticate": "Bearer"}

    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message)


class ForbiddenError(BankingError):
    """403 - we know who you are, but you are not allowed to do this."""
    status_code = 403
    code = "forbidden"


class UsernameTakenError(BankingError):
    status_code = 409
    code = "username_taken"

    def __init__(self, username: str):
        super().__init__("Username is already registered", {"username": username})
