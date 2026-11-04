"""Shared data contracts (Pydantic v2). These shapes are FIXED: the API, the UI and the
evaluation scripts all depend on them. You may ADD optional fields; do not rename or remove fields.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Route = Literal["fact", "compare", "policy", "draft", "out_of_scope"]
DocType = Literal["factsheet", "kid", "commentary", "policy", "rules", "client_email", "fund_data"]
ReviewStatus = Literal["n/a", "pending_review", "approved", "edited_and_approved", "rejected", "escalated"]


class Chunk(BaseModel):
    """One retrievable unit. FR-01 metadata is mandatory."""
    chunk_id: str                      # e.g. "FS-F01::4" or "POL-01-v3.0::§4.2"
    doc_id: str                        # e.g. "FS-F01", "POL-01-v3.0", "KID-F07"
    doc_type: DocType
    fund_id: str | None = None         # "F01".."F08" or "ALL"
    share_class: str | None = None     # "A-Acc-USD" or "ALL"
    section: str                       # heading or clause, e.g. "3. Share class information" or "§4.2"
    as_of_date: str                    # ISO date
    version: str = "1.0"
    status: str = "ACTIVE"             # ACTIVE | SUPERSEDED (policies)
    text: str


class Citation(BaseModel):
    doc_id: str
    section: str
    chunk_id: str | None = None
    as_of_date: str | None = None
    text: str | None = None            # the supporting chunk text (used by the evaluation judge)


class AnswerOutput(BaseModel):
    """FR-09 structured output for /ask."""
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    route: Route
    refused: bool = False
    freshness_warning: str | None = None   # set when a cited source is >90 days older than the newest version
    tools_called: list[str] = Field(default_factory=list)
    retrieved_doc_ids: list[str] = Field(default_factory=list)   # ordered, after fusion/rerank (for hit@5)
    review_id: str | None = None
    review_status: ReviewStatus = "n/a"
    llm_calls: int = 0
    latency_ms: int = 0


class FundRecord(BaseModel):
    fund_id: str
    fund_name: str
    share_class: str
    isin: str
    values: dict[str, str | float | int | None]
    as_of_date: str
    source_doc_id: str = "DATA-FUND-MASTER"


class ComplianceFinding(BaseModel):
    rule_id: str
    span: str
    severity: Literal["block", "warn"] = "block"


class ComplianceResult(BaseModel):
    passed: bool
    violated_rule_ids: list[str] = Field(default_factory=list)
    findings: list[ComplianceFinding] = Field(default_factory=list)


class ReviewItem(BaseModel):
    review_id: str
    email_ref: str | None = None
    question: str
    draft: str
    citations: list[Citation] = Field(default_factory=list)
    compliance: ComplianceResult
    revision_count: int = 0
    status: ReviewStatus = "pending_review"
    reviewer: str | None = None
    reviewer_reason: str | None = None
    final_text: str | None = None
    created_at: str
    decided_at: str | None = None


# ------------------------------------------------------------------ API request bodies
class AskRequest(BaseModel):
    question: str
    session_id: str = "default"


class DraftRequest(BaseModel):
    instruction: str = "Draft a reply to this client email."
    email_ref: str | None = None       # e.g. "EML-001" (loaded from corpus/client_emails)
    email_text: str | None = None      # or paste the email text directly
    session_id: str = "default"


class ReviewDecision(BaseModel):
    action: Literal["approve", "edit", "reject"]
    reviewer: str
    reason: str | None = None
    edited_text: str | None = None
