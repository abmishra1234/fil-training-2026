"""Strict request parsing: content type, size limit, JSON shape (A05/A06/A10)."""
import json

from fastapi import Request

from .errors import ApiError, validation


def _reject_constant(name):
    raise ValueError(f"invalid JSON constant {name}")


async def read_json_object(request: Request, max_bytes: int) -> dict:
    ctype = request.headers.get("content-type", "")
    if ctype.split(";")[0].strip().lower() != "application/json":
        raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise ApiError(413, "payload_too_large", "Request body is too large")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise ApiError(413, "payload_too_large", "Request body is too large")
    try:
        data = json.loads(body.decode("utf-8"), parse_constant=_reject_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise validation("Request body must be valid JSON") from None
    if not isinstance(data, dict):
        raise validation("Request body must be a JSON object")
    return data


def has_control_chars(s: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in s)


def reject_unknown_fields(data: dict, allowed: set):
    extra = sorted(set(data) - allowed)
    if extra:                                    # mass-assignment protection
        raise validation("Unknown field(s): " + ", ".join(extra)[:100], field=extra[0][:50])
