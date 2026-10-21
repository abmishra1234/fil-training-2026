"""
app/agent/routes.py - PROVIDED. HTTP API for the agent (Lab 2).

  POST /api/agent/chat      {question, thread_id?}         -> final result (or a clarification request)
  POST /api/agent/resume    {thread_id, answer}            -> continue after a clarification
  POST /api/agent/stream    {question? | resume?, thread_id?} -> Server-Sent Events, one per node step
  GET  /api/agent/graph                                    -> Mermaid diagram of the compiled graph
  GET  /api/agent/scenarios                                -> demo questions (data/agent_scenarios.json)
  GET  /api/graph/entities                                 -> Graph RAG lite: entities by degree
  GET  /api/graph/entity/{name}                            -> one entity: documents, neighbours, chunks
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request # type: ignore
from fastapi.responses import JSONResponse, StreamingResponse # type: ignore
from pydantic import BaseModel, Field, field_validator, model_validator # type: ignore

from ..config import PROJECT_ROOT
from ..llm import RagError

router = APIRouter(prefix="/api")


class AgentChat(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    thread_id: str | None = Field(None, max_length=100)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()


class AgentResume(BaseModel):
    thread_id: str = Field(..., min_length=1, max_length=100)
    answer: str = Field(..., min_length=1, max_length=500)


class AgentStream(BaseModel):
    question: str | None = Field(None, max_length=1000)
    resume: str | None = Field(None, max_length=500)
    thread_id: str | None = Field(None, max_length=100)

    @model_validator(mode="after")
    def one_of(self):
        if not (self.question and self.question.strip()) and not (self.resume and self.resume.strip()):
            raise ValueError("send a question or a resume answer")
        if self.resume and not self.thread_id:
            raise ValueError("resume needs the thread_id")
        return self


def _err(err: RagError) -> JSONResponse:
    return JSONResponse(status_code=err.status, content={"detail": err.message, "hint": err.hint})


def agent(request: Request):
    return request.app.state.agent


@router.post("/agent/chat")
def agent_chat(body: AgentChat, request: Request):
    try:
        return agent(request).ask(body.question, body.thread_id)
    except RagError as err:
        return _err(err)


@router.post("/agent/resume")
def agent_resume(body: AgentResume, request: Request):
    try:
        return agent(request).resume(body.thread_id, body.answer.strip())
    except RagError as err:
        return _err(err)


@router.post("/agent/stream")
def agent_stream(body: AgentStream, request: Request):
    svc = agent(request)
    try:
        svc.rag._require_index()
        svc._require_graph()
    except RagError as err:
        return _err(err)
    resume = body.resume.strip() if body.resume else None
    if resume is not None and not svc._pending_interrupt(body.thread_id):
        return _err(RagError(409, "This conversation is not waiting for a clarification.", "Send a normal question."))

    def events():
        for ev in svc.stream(body.question.strip() if body.question else None, body.thread_id, resume):
            yield f"data: {json.dumps(ev, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/agent/graph")
def agent_graph(request: Request):
    try:
        return {"mermaid": agent(request).mermaid()}
    except RagError as err:
        return _err(err)


@router.get("/agent/scenarios")
def agent_scenarios():
    return json.loads((PROJECT_ROOT / "data" / "agent_scenarios.json").read_text(encoding="utf-8"))


@router.get("/graph/entities")
def graph_entities(request: Request, limit: int = 60):
    svc = agent(request)
    svc._ensure()
    g = svc.entity_graph
    return {"entities": [{"entity": e, "mentions": len(g.chunks_by_entity[e]), "degree": len(g.edges.get(e, {}))} for e in g.entities[:limit]]}


@router.get("/graph/entity/{name}")
def graph_entity(name: str, request: Request):
    svc = agent(request)
    svc._ensure()
    found = svc.entity_graph.lookup(name, limit=20)
    if not found:
        raise HTTPException(404, f"Unknown entity {name!r}")
    return {**{k: found[k] for k in ("entity", "mentions", "documents", "neighbours")},
            "chunks": [{"chunk_id": d.metadata["chunk_id"], "source": d.metadata["source"], "text": d.page_content} for d in found["chunks"]]}
