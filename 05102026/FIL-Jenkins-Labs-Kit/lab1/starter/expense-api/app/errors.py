"""One error envelope for every failure. Messages are generic; internals stay in logs."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None, details=None):
        self.status, self.code, self.message = status, code, message
        self.headers = headers or {}
        self.details = details


def validation(message: str, field: str | None = None) -> ApiError:
    details = [{"field": field, "issue": message}] if field else None
    return ApiError(400, "validation_error", message, details=details)


def not_authenticated() -> ApiError:
    # Same message for missing / forged / expired / disabled - never say which check failed.
    return ApiError(401, "not_authenticated", "Authentication required",
                    headers={"WWW-Authenticate": "Bearer"})


def forbidden(message="You are not allowed to perform this action", code="forbidden") -> ApiError:
    return ApiError(403, code, message)


def not_found() -> ApiError:
    return ApiError(404, "not_found", "Resource not found")
