"""Idempotency-Key support for money-moving POSTs (Task 6)."""
import hashlib
import json
from typing import Optional

from fastapi import Depends

from ..core.errors import IdempotencyKeyReusedError
from ..models.idempotency import IdempotencyRecord
from ..repositories.idempotency_repository import IdempotencyRepository


def fingerprint(payload: dict) -> str:
    """Stable hash of the request body (sorted keys => same dict, same hash)."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class IdempotencyService:
    def __init__(self, repo: IdempotencyRepository = Depends()):
        self.repo = repo

    def lookup(self, key: str, endpoint: str, payload: dict) -> Optional[IdempotencyRecord]:
        """Return the stored response for a replay, None for a new key.
        Raises if the key was used before with a different body or endpoint."""
        record = self.repo.get(key)
        if record is None:
            return None
        if record.endpoint != endpoint or record.request_hash != fingerprint(payload):
            raise IdempotencyKeyReusedError(key)
        return record

    def remember(self, key: str, endpoint: str, payload: dict,
                 status_code: int, body: dict) -> None:
        self.repo.save(IdempotencyRecord(key=key, endpoint=endpoint,
                                         request_hash=fingerprint(payload),
                                         status_code=status_code,
                                         response_body=json.dumps(body)))
