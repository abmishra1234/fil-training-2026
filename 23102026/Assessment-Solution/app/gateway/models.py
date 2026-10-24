"""
app/gateway/models.py - the data the gateway works with (no logic here).

    Passage        one retrieved chunk:  chunk_id + text
    Decision       ALLOW | BLOCK_QUERY | BLOCK_CONTEXT | BLOCK_ERROR
    GatewayResult  the verdict for ONE request (never contains secret text)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Decision(str, Enum):
    """What happens to the REQUEST. Compares equal to its plain string: Decision.ALLOW == "ALLOW"."""

    ALLOW = "ALLOW"                  # call the LLM with safe_passages (some may have been dropped)
    BLOCK_QUERY = "BLOCK_QUERY"      # secret in the user's query        -> no LLM call
    BLOCK_CONTEXT = "BLOCK_CONTEXT"  # every passage held a secret       -> no LLM call
    BLOCK_ERROR = "BLOCK_ERROR"      # the gateway itself failed         -> no LLM call (fail closed)

    def __str__(self) -> str:  # "ALLOW", not "Decision.ALLOW", in logs and JSON
        return self.value


QUERY_BLOCKED_REPLY = "Your request contains restricted content and was not processed."
CONTEXT_BLOCKED_REPLY = "I could not find this in the approved sources."
ERROR_REPLY = "The request could not be checked safely, so it was not processed. Please try again later."

REPLIES: dict[Decision, str] = {
    Decision.BLOCK_QUERY: QUERY_BLOCKED_REPLY,
    Decision.BLOCK_CONTEXT: CONTEXT_BLOCKED_REPLY,
    Decision.BLOCK_ERROR: ERROR_REPLY,
}

WITHHELD_TEXT = "[withheld by AI Gateway]"


@dataclass(frozen=True)
class Passage:
    chunk_id: str
    text: str
    source: str = ""


@dataclass(frozen=True)
class GatewayResult:
    decision: Decision
    safe_passages: list[Passage] = field(default_factory=list)   # passages allowed through, input order
    dropped: list[str] = field(default_factory=list)             # chunk_ids that were dropped, input order
    findings: dict[str, int] = field(default_factory=dict)       # secret type -> count, e.g. {"CREDENTIAL": 1}
    elapsed_ms: float = 0.0
    error: str = ""                                              # exception CLASS name only, never its message

    @property
    def allowed(self) -> bool:
        """True only for ALLOW. Callers must use this allow-list, never `!= BLOCK_...`."""
        return self.decision == Decision.ALLOW

    @property
    def reply(self) -> str | None:
        """The fixed user-facing reply for a blocked request (None when allowed)."""
        return None if self.allowed else REPLIES.get(self.decision, ERROR_REPLY)

    def to_public_dict(self) -> dict:
        """Safe to put in an API response or a log line: ids, types and counts only."""
        return {
            "decision": str(self.decision),
            "dropped": list(self.dropped),
            "findings": dict(self.findings),
            "elapsed_ms": round(self.elapsed_ms, 3),
            **({"error": self.error} if self.error else {}),
        }
