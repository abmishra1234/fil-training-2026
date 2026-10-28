"""
app/main.py - PROVIDED. Start with:   uvicorn app.main:app --reload --port 8000

  http://127.0.0.1:8000        the React app (pre-built copy in frontend/dist)
  http://127.0.0.1:8000/docs   Swagger: try every endpoint by hand
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import llm_client
from llm_client import describe, describe_observability

from .config import PROJECT_ROOT
from .llm import RagError
from .pipeline import RagService
from .routes import router
from .agent.routes import router as agent_router
from .agent.service import AgentService

log = logging.getLogger("rag-lab")
DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm_client.init_observability()  # OBS_MODE in .env: fil | otlp | off
    print("LLM     :", describe())
    print("Traces  :", describe_observability())
    app.state.rag = RagService()
    try:
        with llm_client.span("startup.reindex", kind="chain"):  # one trace for the startup embeddings
            n = app.state.rag.reindex()
        print(f"Index   : {n} chunks in FAISS (in memory)")
    except RagError as err:  # start anyway so the UI can show the problem
        print(f"Index   : FAILED - {err.message} {err.hint}")
    app.state.agent = AgentService(app.state.rag)  # Lab 2: LangGraph agent on top of the same index
    yield
    llm_client.flush_observability()  # do not lose the last spans on shutdown


class ObservabilityMiddleware:
    """
    Pure ASGI middleware: one root span per /api request, e.g. "POST /api/chat".
    Every pipeline step and LLM call made while serving the request nests under it,
    so one request = one trace in LangSmith. Unlike @app.middleware("http") it also
    covers streamed bodies (/api/agent/stream), because the span closes after the
    last byte is sent.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api"):
            return await self.app(scope, receive, send)
        meta = {"http.route": scope["path"], "http.method": scope["method"]}
        session = dict(scope.get("headers") or []).get(b"x-session-id")
        with llm_client.obs_context(**({"session_id": session.decode()} if session else {})):
            # Newer FastAPI versions already open an OpenTelemetry server span for the request.
            # Reuse it (just add LangSmith attributes) instead of nesting a duplicate.
            server_span = _current_recording_span()
            if server_span is not None:
                llm_client._apply_context(server_span, "chain", meta)
                return await self.app(scope, receive, _status_recorder(send, server_span))
            with llm_client.span(f"{scope['method']} {scope['path']}", kind="chain", metadata=meta) as sp:
                await self.app(scope, receive, _status_recorder(send, sp))


def _current_recording_span():
    try:
        from opentelemetry import trace
    except ImportError:
        return None
    cur = trace.get_current_span()
    return cur if cur.get_span_context().is_valid and cur.is_recording() else None


def _status_recorder(send, sp):
    async def send_wrapper(message):
        if sp is not None and message["type"] == "http.response.start":
            sp.set_attribute("http.status_code", message["status"])
            if message["status"] >= 500:
                from opentelemetry.trace import Status, StatusCode
                sp.set_status(Status(StatusCode.ERROR, f"HTTP {message['status']}"))
        await send(message)
    return send_wrapper


app = FastAPI(title="RAG Lab: Basic RAG -> MQR -> RRF -> Agentic RAG", version="1.0", lifespan=lifespan)
app.add_middleware(  # for `npm run dev` on port 5173
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)
app.add_middleware(ObservabilityMiddleware)
app.include_router(router)
app.include_router(agent_router)

if (DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def no_frontend():
        return "<h3>Frontend not built.</h3><p>Run <code>cd frontend && npm install && npm run build</code>, or use <a href='/docs'>/docs</a>.</p>"
