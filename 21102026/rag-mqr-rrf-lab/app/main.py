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

from llm_client import describe

from .config import PROJECT_ROOT
from .llm import RagError
from .pipeline import RagService
from .routes import router

log = logging.getLogger("rag-lab")
DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag = RagService()
    print("LLM     :", describe())
    try:
        n = app.state.rag.reindex()
        print(f"Index   : {n} chunks in FAISS (in memory)")
    except RagError as err:  # start anyway so the UI can show the problem
        print(f"Index   : FAILED - {err.message} {err.hint}")
    yield


app = FastAPI(title="RAG Lab: Basic RAG -> MQR -> RRF", version="1.0", lifespan=lifespan)
app.add_middleware(  # for `npm run dev` on port 5173
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)

if (DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def no_frontend():
        return "<h3>Frontend not built.</h3><p>Run <code>cd frontend && npm install && npm run build</code>, or use <a href='/docs'>/docs</a>.</p>"
