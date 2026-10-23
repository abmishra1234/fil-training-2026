"""
judge_tests/adapter.py - THE ONLY FILE YOU EDIT IN judge_tests/.

The judge tests do not know your module, class or field names. Fill in every
function below so it calls YOUR implementation. Keep the names and the return
shapes exactly as documented.

Rules
  * Every function should be 1-5 lines that call your code. If you need much
    more, that is a hint about your design (see the brief: new secret types must
    be addable without changing the gateway core).
  * Do NOT put detection logic, special cases or test strings here. The trainer
    reads this file before your report; logic here voids the affected tests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

# from app.<your_module> import ...        <-- import your gateway here

# ---------------------------------------------------------------- 1. names
# The finding keys your gateway uses for the three secret types of the brief.
TYPE_CREDENTIAL = "CREDENTIAL"
TYPE_CARD = "PAYMENT_CARD"     # change if you named it differently (e.g. "CARD")
TYPE_CODENAME = "CODENAME"


# ---------------------------------------------------------------- 2. passages and results
def make_passage(chunk_id: str, text: str):
    """Build ONE of your Passage objects with this chunk_id and text."""
    raise NotImplementedError("adapter.make_passage: map to your Passage type")


def check(query: str, passages: list):
    """The minimum interface from the brief, using your DEFAULT config file."""
    raise NotImplementedError("adapter.check: call your gateway's check(query, passages)")


def result_view(result) -> dict:
    """
    Turn YOUR GatewayResult into plain values:
        decision : "ALLOW" | "BLOCK_QUERY" | "BLOCK_CONTEXT" | "BLOCK_ERROR"   (a str)
        safe     : the passage OBJECTS allowed through, in order (the same objects you were given)
        safe_ids : their chunk_ids (list of str)
        dropped  : chunk_ids that were dropped (list of str)
        findings : {secret_type: count}
    """
    raise NotImplementedError("adapter.result_view: read the fields of your result")


# ---------------------------------------------------------------- 3. configuration
def write_codename_config(directory: Path, codenames: list[str]) -> Path:
    """Write a gateway config file IN YOUR FORMAT that lists exactly `codenames`. Return its path."""
    raise NotImplementedError("adapter.write_codename_config: write your config format")


# ---------------------------------------------------------------- 4. extensibility
def make_custom_detector(secret_type: str, count_fn: Callable[[str], int]):
    """
    A NEW secret type, created the way your design intends new types to be added.
    count_fn(text) returns how many secrets of this type are in `text`. It may
    raise: the judge uses that to test that your gateway fails closed.
    """
    raise NotImplementedError("adapter.make_custom_detector: wrap count_fn in your detector type")


def make_gateway(codenames_path: Path | None = None, extra_detectors: list | None = None):
    """
    A gateway object with .check(query, passages), built from the config file at
    `codenames_path` (None = your default config) plus `extra_detectors`
    (objects returned by make_custom_detector).
    """
    raise NotImplementedError("adapter.make_gateway: build your gateway")


# ---------------------------------------------------------------- 5. the RAG app
def make_rag_service(cfg, embeddings=None, gateway=None):
    """
    Your app.pipeline.RagService for RagConfig `cfg`. When `gateway` is not None
    the service must use THAT gateway (dependency injection).
    """
    raise NotImplementedError("adapter.make_rag_service: build your RagService")


def make_agent_service(rag):
    """Your app.agent.service.AgentService on top of `rag`, using the same gateway as `rag`."""
    raise NotImplementedError("adapter.make_agent_service: build your AgentService")
