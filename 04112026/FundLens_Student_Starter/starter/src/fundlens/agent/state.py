"""LangGraph state - minimum fields from the requirements. You may add fields."""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    question: str
    masked_question: str
    email_ref: str | None
    route: str                      # fact | compare | policy | draft | out_of_scope
    sub_queries: list[str]
    retrieved_chunks: list[dict]
    tool_results: list[dict]
    answer: str
    citations: list[dict]
    groundedness_score: float
    draft: str
    compliance_result: dict
    revision_count: int             # max 3 (FR-13)
    retry_count: int                # max 2 (FR-12)
    review_status: str              # never "approved" without a reviewer action (HITL integrity)
    audit_events: list[dict[str, Any]]
