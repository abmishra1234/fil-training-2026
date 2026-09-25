"""HTTP middleware (Task 1 part B and Task 5)."""
import uuid

from fastapi import FastAPI, Request

V1_PREFIX = "/api/v1"
LEGACY_PREFIX = "/accounts"
# RFC 9745: Deprecation is a structured date "@<unix-seconds>" (here 2026-10-01 UTC).
DEPRECATED_SINCE = "@1790812800"
# RFC 8594: Sunset is an HTTP-date after which the legacy path may stop working.
SUNSET_DATE = "Thu, 31 Dec 2026 23:59:59 GMT"


def register_middleware(app: FastAPI) -> None:

    @app.middleware("http")
    async def request_id_and_deprecation(request: Request, call_next):
        # 1) Correlation id: reuse the caller's X-Request-ID or mint one.
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        # 2) Tell legacy clients (politely) that unversioned paths are going away.
        if request.url.path.startswith(LEGACY_PREFIX):
            response.headers["Deprecation"] = DEPRECATED_SINCE
            response.headers["Sunset"] = SUNSET_DATE
            successor = V1_PREFIX + request.url.path
            response.headers["Link"] = f'<{successor}>; rel="successor-version"'
        return response
