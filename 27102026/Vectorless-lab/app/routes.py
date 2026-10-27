"""
app/routes.py - PROVIDED. The HTTP API the React frontend calls.

  GET  /api/health                 server up? which models? how many chunks?
  GET  /api/documents              files in the knowledge base + chunk counts
  GET  /api/documents/{name}/chunks  the chunks of one file
  POST /api/documents              upload a .md / .txt file, then re-index
  POST /api/reindex                rebuild the FAISS index from data/docs
  POST /api/chat                   {question, mode} -> answer + retrieval details
  POST /api/compare                {question} -> the same question in all 4 modes
  POST /api/evaluate               hit-rate / MRR / cost per mode on data/eval_set.json
  GET  /api/tree                   Lab 3: the tree index (titles, summaries) for the UI
  POST /api/tree/summarize         Lab 3: (re)write the summaries {mode: llm|extractive|none}
"""
from __future__ import annotations

import re

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from llm_client import settings as llm_settings

from .config import PROJECT_ROOT
from .llm import RagError
from .pipeline import MODES, evaluate, load_eval_set
from .schemas import ChatRequest, CompareRequest, EvaluateRequest, SummarizeRequest
from .vectorless.tree import tree_to_dict

router = APIRouter(prefix="/api")
MAX_UPLOAD_BYTES = 1_000_000


def error_response(err: RagError) -> JSONResponse:
    return JSONResponse(status_code=err.status, content={"detail": err.message, "hint": err.hint})


def svc(request: Request):
    return request.app.state.rag


@router.get("/health")
def health(request: Request):
    s = svc(request)
    return {
        "status": "ok",
        "llm_mode": llm_settings.mode,
        "chat_model": llm_settings.chat_model,
        "embed_model": llm_settings.embed_model,
        "vector_db": "FAISS (in-memory, IndexFlatIP)",
        "chunks": s.store.size,
        "documents": len({d.metadata["source"] for d in s.store.docs.values()}),
        "indexed_at": s.indexed_at,
        "index_error": s.index_error,
        "tree": s.tree_info(),
        "config": {
            "basic_k": s.cfg.basic_k,
            "mqr_num_queries": s.cfg.mqr_num_queries,
            "mqr_k": s.cfg.mqr_k,
            "mqr_include_original": s.cfg.mqr_include_original,
            "rrf_k": s.cfg.rrf_k,
            "final_k": s.cfg.final_k,
            "max_context_chars": s.cfg.max_context_chars,
            "chunk_size": s.cfg.chunk_size,
            "vectorless_max_docs": s.cfg.vectorless_max_docs,
            "vectorless_max_sections": s.cfg.vectorless_max_sections,
            "vectorless_max_steps": s.cfg.vectorless_max_steps,
            "vectorless_summaries": s.summary_mode,
        },
    }


@router.get("/documents")
def documents(request: Request):
    return {"documents": svc(request).documents()}


@router.get("/documents/{name}/chunks")
def document_chunks(name: str, request: Request):
    chunks = svc(request).chunks(name)
    if not chunks:
        raise HTTPException(404, f"No chunks for {name!r}")
    return {"source": name, "chunks": chunks}


@router.post("/documents")
async def upload_document(request: Request, file: UploadFile = File(...)):
    s = svc(request)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", (file.filename or "").split("/")[-1].split("\\")[-1])
    if not name.lower().endswith((".md", ".txt")) or name.startswith("."):
        raise HTTPException(415, "Only .md and .txt files are supported.")
    data = await file.read()
    if not data.strip():
        raise HTTPException(400, "The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 1 MB.")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "File must be UTF-8 text.") from None
    (s.cfg.docs_dir / name).write_bytes(data)
    try:
        chunks = s.reindex()
    except RagError as err:
        return error_response(err)
    return {"saved": name, "chunks": chunks}


@router.post("/reindex")
def reindex(request: Request):
    try:
        return {"chunks": svc(request).reindex()}
    except RagError as err:
        return error_response(err)


@router.post("/chat")
def chat(body: ChatRequest, request: Request):
    try:
        return svc(request).run(body.mode, body.question)
    except RagError as err:
        return error_response(err)


@router.post("/compare")
def compare(body: CompareRequest, request: Request):
    out = {}
    for mode in MODES:
        try:
            out[mode] = svc(request).run(mode, body.question)
        except RagError as err:
            out[mode] = {"error": err.message, "hint": err.hint, "status": err.status}
    return out


@router.post("/evaluate")
def run_evaluation(request: Request, body: EvaluateRequest | None = None):
    modes = tuple((body or EvaluateRequest()).modes)
    try:
        questions = load_eval_set(PROJECT_ROOT / "data" / "eval_set.json")
        return evaluate(svc(request), questions, modes)
    except RagError as err:
        return error_response(err)


# --------------------------------------------------------------------------- #
# Lab 3: the tree index behind vectorless RAG
# --------------------------------------------------------------------------- #
def _tree_payload(s) -> dict:
    return {**s.tree_info(), "tree": tree_to_dict(s.tree.root)}


@router.get("/tree")
def tree(request: Request):
    s = svc(request)
    try:
        s._require_tree()
    except NotImplementedError as err:
        return error_response(RagError(501, f"Tree index not ready yet: {err}", "Implement Lab 3 TODO V1 and run pytest."))
    except RagError as err:
        return error_response(err)
    return _tree_payload(s)


@router.post("/tree/summarize")
def tree_summarize(request: Request, body: SummarizeRequest | None = None):
    """Write the signposts now (so the first vectorless question is not slow), or switch mode."""
    s = svc(request)
    mode = (body or SummarizeRequest()).mode
    try:
        calls = s.ensure_tree_summaries(mode)
    except NotImplementedError as err:
        return error_response(RagError(501, f"Tree index not ready yet: {err}", "Implement Lab 3 TODO V1-V2 and run pytest."))
    except RagError as err:
        return error_response(err)
    return {**_tree_payload(s), "llm_calls": calls}
