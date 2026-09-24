"""Global exception handlers (Task 5).

Contract:
  * /api/v1/...  -> new standard envelope
        {"error": {"code", "message", "details", "request_id"}}
  * legacy paths -> unchanged FastAPI shape {"detail": ...}
    (changing the body shape would break existing clients)
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (http_exception_handler,
                                        request_validation_exception_handler)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import BankingError
from .middleware import V1_PREFIX

logger = logging.getLogger("banking_api")

STATUS_TO_CODE = {
    400: "bad_request", 401: "unauthorized", 403: "forbidden",
    404: "not_found", 405: "method_not_allowed", 409: "conflict",
    422: "validation_error", 429: "too_many_requests",
}


def _is_v1(request: Request) -> bool:
    return request.url.path.startswith(V1_PREFIX)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def error_body(request: Request, code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message,
                      "details": details or {}, "request_id": _request_id(request)}}


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(BankingError)
    async def banking_error_handler(request: Request, exc: BankingError):
        if _is_v1(request):
            body = error_body(request, exc.code, exc.message, exc.details)
        else:
            body = {"detail": exc.message}          # legacy shape
        # Ext 6: 401s must carry 'WWW-Authenticate: Bearer'
        return JSONResponse(status_code=exc.status_code, content=body,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if not _is_v1(request):
            return await http_exception_handler(request, exc)
        code = STATUS_TO_CODE.get(exc.status_code, "http_error")
        return JSONResponse(status_code=exc.status_code,
                            content=error_body(request, code, str(exc.detail)),
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        if not _is_v1(request):
            return await request_validation_exception_handler(request, exc)
        fields = [{"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
                  for err in exc.errors()]
        return JSONResponse(status_code=422, content=error_body(
            request, "validation_error", "Request validation failed", {"fields": fields}))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        # Log the full stack trace for us; never leak it to the client.
        logger.exception("Unhandled error [request_id=%s]", _request_id(request))
        return JSONResponse(status_code=500, content=error_body(
            request, "internal_error", "Something went wrong. Quote the request_id to support."))
