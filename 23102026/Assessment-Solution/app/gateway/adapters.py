"""
app/gateway/adapters.py - translate between the app's chunk types and gateway Passages.

The gateway only understands Passage(chunk_id, text). The RAG pipeline uses
LangChain Documents; the agent uses Evidence dicts. These small adapters keep
the gateway independent of both (it could guard any other app unchanged).
"""
from __future__ import annotations

from typing import Iterable, Protocol

from langchain_core.documents import Document # type: ignore

from .models import Decision, GatewayResult, Passage


class Guard(Protocol):
    """What callers depend on: anything with check(query, passages) -> GatewayResult."""

    def check(self, query: str, passages: list[Passage]) -> GatewayResult: ...


def document_to_passage(doc: Document) -> Passage:
    md = doc.metadata or {}
    return Passage(chunk_id=str(md.get("chunk_id", "")), text=doc.page_content, source=str(md.get("source", "")))


def documents_to_passages(docs: Iterable[Document]) -> list[Passage]:
    return [document_to_passage(d) for d in docs]


def keep_safe(items: list, result: GatewayResult, chunk_id=lambda d: d.metadata.get("chunk_id")) -> list:
    """The original objects (Documents, Evidence, ...) whose chunk survived. Empty unless ALLOW."""
    if not result.allowed:
        return []
    ok = {p.chunk_id for p in result.safe_passages}
    return [x for x in items if str(chunk_id(x)) in ok]


def guarded_check(gateway: Guard, query: str, docs: Iterable[Document]) -> GatewayResult:
    """Call ANY gateway on Documents. A gateway that raises or returns garbage still fails closed."""
    try:
        result = gateway.check(query, documents_to_passages(docs))
        if not isinstance(result, GatewayResult):
            raise TypeError("gateway returned an unexpected type")
        return result
    except Exception as err:  # noqa: BLE001
        return GatewayResult(Decision.BLOCK_ERROR, [], [], {}, 0.0, type(err).__name__)
