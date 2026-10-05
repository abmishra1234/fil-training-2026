"""Application factory: middleware, error envelope, routers."""
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings
from .errors import ApiError
from .logging_utils import log_event, request_id_var
from .routers_auth import LoginGuard
from .routers_auth import router as auth_router
from .routers_expenses import router as expenses_router
from .store import Store

REQUEST_ID_RE = re.compile(r"[A-Za-z0-9-]{8,64}")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}
HTTP_CODES = {404: ("not_found", "Resource not found"),
              405: ("method_not_allowed", "Method not allowed"),
              400: ("validation_error", "Invalid request")}


def envelope(status: int, code: str, message: str, headers=None, details=None) -> JSONResponse:
    err = {"code": code, "message": message, "correlation_id": request_id_var.get()}
    if details:
        err["details"] = details
    return JSONResponse({"error": err}, status_code=status, headers=headers)


def create_app(settings: Settings) -> FastAPI:
    docs = not settings.is_prod                    # A02: no API explorer in production
    app = FastAPI(title="Expense Claims API", docs_url="/docs" if docs else None,
                  redoc_url=None, openapi_url="/openapi.json" if docs else None)
    app.state.settings = settings
    app.state.store = Store(settings.seed_file)
    app.state.login_guard = LoginGuard(settings)

    app.include_router(auth_router)
    app.include_router(expenses_router)

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError):
        return envelope(exc.status, exc.code, exc.message, exc.headers, exc.details)

    @app.exception_handler(RequestValidationError)
    async def fastapi_validation(_: Request, exc: RequestValidationError):
        return envelope(400, "validation_error", "Invalid request")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        code, msg = HTTP_CODES.get(exc.status_code, ("error", "Request failed"))
        return envelope(exc.status_code, code, msg, getattr(exc, "headers", None))

    # CORS: explicit allow-list only (A02)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_allowed_origins),
                       allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
                       allow_credentials=False, max_age=600)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if REQUEST_ID_RE.fullmatch(incoming) else str(uuid.uuid4())
        token = request_id_var.set(rid)
        try:
            try:
                response = await call_next(request)
            except Exception as exc:                  # A10: fail closed, generic 500
                log_event("internal_error", "ERROR", error_type=type(exc).__name__,
                          path=request.url.path)
                response = envelope(500, "internal_error", "Internal server error")
            response.headers["X-Request-ID"] = rid
            is_docs = docs and request.url.path in ("/docs", "/openapi.json")
            for k, v in SECURITY_HEADERS.items():
                if not (is_docs and k == "Content-Security-Policy"):
                    response.headers[k] = v
            return response
        finally:
            request_id_var.reset(token)

    log_event("startup", app_env=settings.app_env, port=settings.port)
    return app
