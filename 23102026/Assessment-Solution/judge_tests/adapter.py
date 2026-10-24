"""
judge_tests/adapter.py - THE ONLY FILE YOU EDIT IN judge_tests/.

The judge tests do not know your module, class or field names. This file maps
the judge's small vocabulary onto YOUR implementation. The version below maps
onto the trainer's reference solution (app/gateway/). Change the imports and
the bodies so they call your code. Do not change the function names or what
they return.

Rules
  * Keep every function. If your design has no direct equivalent, write the
    3-4 lines that build it from what you have (that is part of the exercise:
    a well-designed gateway makes every function here a one-liner).
  * Do NOT add detection logic here. If a test fails, fix your gateway, not this file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------- your code
from app.gateway import (  # <-- change to your module
    MiniAIGateway,
    Passage,
    SecretDetector,
    build_gateway,
    check as _default_check,
)

# ---------------------------------------------------------------- 1. names
# The finding keys your gateway uses for the three secret types of the brief.
TYPE_CREDENTIAL = "CREDENTIAL"
TYPE_CARD = "PAYMENT_CARD"
TYPE_CODENAME = "CODENAME"


# ---------------------------------------------------------------- 2. passages and results
def make_passage(chunk_id: str, text: str):
    """Build ONE of your Passage objects."""
    return Passage(chunk_id=chunk_id, text=text)


def check(query: str, passages: list):
    """The minimum interface from the brief: your default gateway (default config file)."""
    return _default_check(query, passages)


def result_view(result) -> dict:
    """
    Normalise YOUR GatewayResult into plain values:
        decision : one of "ALLOW" | "BLOCK_QUERY" | "BLOCK_CONTEXT" | "BLOCK_ERROR"  (str)
        safe     : the passage OBJECTS allowed through, in order (the same objects you were given)
        safe_ids : their chunk_ids
        dropped  : chunk_ids that were dropped
        findings : {secret_type: count}
    """
    decision = getattr(result.decision, "value", result.decision)
    return {
        "decision": str(decision),
        "safe": list(result.safe_passages),
        "safe_ids": [p.chunk_id for p in result.safe_passages],
        "dropped": list(result.dropped),
        "findings": dict(result.findings),
    }


# ---------------------------------------------------------------- 3. configuration
def write_codename_config(directory: Path, codenames: list[str]) -> Path:
    """Write a gateway config file IN YOUR FORMAT that lists exactly `codenames`. Return its path."""
    import json

    path = Path(directory) / "gateway_test_config.json"
    path.write_text(json.dumps({"codenames": codenames}), encoding="utf-8")
    return path


# ---------------------------------------------------------------- 4. extensibility
def make_custom_detector(secret_type: str, count_fn: Callable[[str], int]):
    """
    A NEW secret type, plugged in the way your design intends (no gateway edits).
    count_fn(text) returns how many secrets of this type are in `text` (it may raise:
    the judge uses that to test fail-closed behaviour).
    """

    class _Custom(SecretDetector):
        def __init__(self):
            self.secret_type = secret_type

        def find(self, text):
            return [(0, 0)] * int(count_fn(text))

    return _Custom()


def make_gateway(codenames_path: Path | None = None, extra_detectors: list | None = None):
    """
    A gateway object with .check(query, passages), built from the config at
    `codenames_path` (None = your default config) plus `extra_detectors`.
    """
    return build_gateway(codenames_path, extra_detectors=extra_detectors or [])


# ---------------------------------------------------------------- 5. the RAG app
def make_rag_service(cfg, embeddings=None, gateway=None):
    """Your RagService for config `cfg`. If `gateway` is given, the service must use it."""
    from app.pipeline import RagService

    return RagService(cfg, embeddings, gateway=gateway)


def make_agent_service(rag):
    """Your AgentService on top of `rag` (it must use the same gateway as `rag`)."""
    from app.agent.service import AgentService

    return AgentService(rag)


assert MiniAIGateway  # (imported so a broken import fails loudly here, not in a test)
