"""
app/gateway/core.py - the Mini AI Gateway. Sits just before every LLM call.

    query ─► retriever ─► passages ─► [ MiniAIGateway.check ] ─► LLM ─► answer
                                              │
                                              └─► BLOCK_QUERY / BLOCK_CONTEXT / BLOCK_ERROR / drop passage

The core knows NOTHING about credentials, cards or codenames. It runs whatever
SecretDetector objects it was given (Dependency Inversion), so a new secret type
never changes this file (Open/Closed).

Rules
  1. Query first. A secret in the query blocks the request; passages are not even scanned.
  2. Each passage is scanned; a passage with any finding is dropped (chunk_id kept, text never).
  3. Passages given but none survive -> BLOCK_CONTEXT.
  4. ANY exception -> BLOCK_ERROR with no passages (fail closed). Only the exception
     CLASS name is logged: an exception message can contain the text it choked on.
  5. Logs carry decision, ids, types and counts. Never the text.
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Iterable, Sequence

from .detectors import SecretDetector
from .models import Decision, GatewayResult, Passage

log = logging.getLogger("ai_gateway")


class MiniAIGateway:
    def __init__(self, detectors: Iterable[SecretDetector], logger: logging.Logger | None = None):
        self._detectors: tuple[SecretDetector, ...] = tuple(detectors)
        if not self._detectors:
            raise ValueError("MiniAIGateway needs at least one detector")
        types = [d.secret_type for d in self._detectors]
        if any(not t for t in types):
            raise ValueError("every detector needs a secret_type")
        self._log = logger or log

    @property
    def secret_types(self) -> list[str]:
        return [d.secret_type for d in self._detectors]

    def with_detector(self, detector: SecretDetector) -> "MiniAIGateway":
        """A NEW gateway with one more detector (the existing one is immutable, thread-safe)."""
        return MiniAIGateway([*self._detectors, detector], self._log)

    # ------------------------------------------------------------------ scan
    def scan(self, text: str) -> Counter:
        """secret type -> count for one text. Raises TypeError for non-text (-> fail closed)."""
        if not isinstance(text, str):
            raise TypeError("text must be str")
        found: Counter = Counter()
        for det in self._detectors:
            n = det.count(text)
            if n:
                found[det.secret_type] += n
        return found

    # ----------------------------------------------------------------- check
    def check(self, query: str, passages: Sequence[Passage] | None) -> GatewayResult:
        t0 = time.perf_counter()
        try:
            passages = list(passages or [])
            query_hits = self.scan(query if query is not None else "")
            if query_hits:
                return self._done(t0, Decision.BLOCK_QUERY, [], [], query_hits, len(passages), where="query")

            safe: list[Passage] = []
            dropped: list[str] = []
            findings: Counter = Counter()
            for p in passages:
                hits = self.scan(p.text)
                if hits:
                    dropped.append(str(p.chunk_id))
                    findings.update(hits)
                else:
                    safe.append(p)

            decision = Decision.BLOCK_CONTEXT if passages and not safe else Decision.ALLOW
            return self._done(t0, decision, safe, dropped, findings, len(passages), where="passages")
        except Exception as err:  # noqa: BLE001  - fail closed on ANYTHING
            ms = (time.perf_counter() - t0) * 1000
            self._log.error("ai_gateway decision=BLOCK_ERROR error_type=%s elapsed_ms=%.2f", type(err).__name__, ms)
            return GatewayResult(Decision.BLOCK_ERROR, [], [], {}, ms, type(err).__name__)

    def _done(self, t0, decision, safe, dropped, findings, n_passages, where) -> GatewayResult:
        ms = (time.perf_counter() - t0) * 1000
        counts = dict(sorted(findings.items()))
        level = logging.INFO if decision == Decision.ALLOW and not dropped else logging.WARNING
        # ids, types and counts ONLY - this line is safe to ship to any log store
        self._log.log(level, "ai_gateway decision=%s scanned=%s passages=%d dropped=%d findings=%s elapsed_ms=%.2f",
                      decision, where, n_passages, len(dropped), counts, ms)
        return GatewayResult(decision, safe, dropped, counts, ms)
