"""FR-19 FastAPI service. /health works out of the box; the rest are yours (contracts in docs/04_api_contract.md).

Run:  uvicorn fundlens.api.main:app --reload --port 8000   (from the starter folder, with src on PYTHONPATH - see Makefile)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ..config import settings
from ..schemas import AnswerOutput, AskRequest, DraftRequest, ReviewDecision, ReviewItem

app = FastAPI(title="FundLens API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_mode": settings.llm_mode, "kit_dir": str(settings.kit_dir),
            "corpus_found": settings.corpus_dir.exists()}


@app.post("/ask", response_model=AnswerOutput)
async def ask(req: AskRequest) -> AnswerOutput:
    raise HTTPException(501, "TODO: run the agent graph for Q&A routes")


@app.post("/draft", response_model=AnswerOutput)
async def draft(req: DraftRequest) -> AnswerOutput:
    raise HTTPException(501, "TODO: run the draft route; return review_id with review_status=pending_review")


@app.get("/review", response_model=list[ReviewItem])
async def list_reviews(status: str = "pending_review") -> list[ReviewItem]:
    raise HTTPException(501, "TODO")


@app.post("/review/{review_id}", response_model=ReviewItem)
async def decide(review_id: str, decision: ReviewDecision) -> ReviewItem:
    raise HTTPException(501, "TODO: resume the paused graph with the reviewer decision")


@app.post("/ingest")
async def ingest() -> dict:
    raise HTTPException(501, "TODO: (re)build chunks and indexes; idempotent (FR-02)")
