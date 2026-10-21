"""
app/pipeline.py - PROVIDED. Runs one question through one of three modes and
returns everything the UI's "Retrieval inspector" needs.

  basic    : FAISS top-5                    -> naive prompt     (basic_rag.py)
  mqr      : MQR union (all chunks)         -> grounded prompt  (TODO 1-4, 9-10)
  mqr_rrf  : MQR union -> RRF top-5         -> grounded prompt  (TODO 1-10)
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone

from langchain_core.documents import Document

from .basic_rag import basic_retrieve, build_basic_chain
from .config import RagConfig, config
from .generation import generate_grounded_answer
from .ingest import load_folder
from .llm import GatewayEmbeddings, RagError
from .mqr import generate_queries, mqr_retrieve
from .rerank import mqr_rrf_retrieve
from .vector_store import InMemoryVectorStore

MODES = ("basic", "mqr", "mqr_rrf")
MODE_TODOS = {"mqr": "TODO 1-4 and 9-10", "mqr_rrf": "TODO 1-10"}


def _todo_error(mode: str, err: NotImplementedError) -> RagError:
    return RagError(
        501,
        f"Mode '{mode}' is not ready yet: {err}",
        f"Implement {MODE_TODOS.get(mode, 'the TODOs')} and run pytest. Basic mode already works.",
    )


def _source(doc: Document, cited: bool = False) -> dict:
    md = doc.metadata
    return {
        "chunk_id": md.get("chunk_id"),
        "source": md.get("source"),
        "section": md.get("section", ""),
        "text": doc.page_content,
        "score": md.get("score"),
        "semantic_score": md.get("semantic_score"),
        "bm25_score": md.get("bm25_score"),
        "rrf_score": md.get("rrf_score"),
        "rrf_ranks": md.get("rrf_ranks"),
        "cited": cited,
    }


class RagService:
    def __init__(self, cfg: RagConfig | None = None, embeddings=None):
        self.cfg = cfg or config
        self.embeddings = embeddings or GatewayEmbeddings()
        self.store = InMemoryVectorStore(self.embeddings)
        self.index_error: str | None = None
        self.indexed_at: str | None = None
        self._gen_cache: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    # ----------------------------------------------------------------- index
    def reindex(self) -> int:
        with self._lock:
            self._gen_cache.clear()
            try:
                docs = load_folder(self.cfg.docs_dir, self.cfg.chunk_size, self.cfg.chunk_overlap)
                self.store.build(docs)
                self.index_error = None
                self.indexed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            except RagError as err:
                self.index_error = f"{err.message} {err.hint}".strip()
                raise
            return self.store.size

    def documents(self) -> list[dict]:
        counts: dict[str, int] = {}
        for doc in self.store.docs.values():
            counts[doc.metadata["source"]] = counts.get(doc.metadata["source"], 0) + 1
        files = sorted(p.name for p in self.cfg.docs_dir.glob("*") if p.suffix.lower() in (".md", ".txt"))
        return [{"source": f, "chunks": counts.get(f, 0)} for f in files]

    def chunks(self, source: str) -> list[dict]:
        return [_source(d) for d in self.store.docs.values() if d.metadata["source"] == source]

    def _require_index(self):
        if self.store.size == 0:
            raise RagError(503, "The index is empty.", self.index_error or "Click 'Re-index' on the Documents tab.")

    def _generated(self, question: str) -> list[str]:
        """MQR rewrites are cached per question, so Compare / Evaluate do not pay twice."""
        key = question.strip()
        if key not in self._gen_cache:
            self._gen_cache[key] = generate_queries(key, self.cfg.mqr_num_queries)
        return self._gen_cache[key]

    # ------------------------------------------------------------- retrieval
    def retrieve(self, mode: str, question: str) -> list[Document]:
        """Only the chunks that would be sent to the LLM (used by evaluation)."""
        self._require_index()
        try:
            if mode == "basic":
                return basic_retrieve(self.store, question, self.cfg.basic_k)
            if mode == "mqr":
                return mqr_retrieve(self.store, question, self.cfg, self._generated(question)).docs
            if mode == "mqr_rrf":
                return mqr_rrf_retrieve(self.store, question, self.cfg, self._generated(question)).fused
        except NotImplementedError as err:
            raise _todo_error(mode, err) from None
        raise RagError(400, f"Unknown mode {mode!r}", f"Use one of {MODES}")

    # ------------------------------------------------------------------- chat
    def run(self, mode: str, question: str) -> dict:
        if mode not in MODES:
            raise RagError(400, f"Unknown mode {mode!r}", f"Use one of {MODES}")
        self._require_index()
        question = question.strip()
        t0 = time.perf_counter()
        emb_before = getattr(self.embeddings, "calls", 0)
        timings: dict[str, int] = {}
        out: dict = {"mode": mode, "question": question, "queries": [], "generated_queries": [], "pool": []}

        def lap(name: str, since: float) -> float:
            now = time.perf_counter()
            timings[name] = round((now - since) * 1000)
            return now

        try:
            if mode == "basic":
                result = build_basic_chain(self.store, self.cfg.basic_k).invoke(question)
                t = lap("retrieve+generate", t0)
                docs = result["context"]
                out.update(
                    answer=result["answer"],
                    queries=[question],
                    sources=[_source(d) for d in docs],
                    pool=[{**_source(d), "found_by": [question], "selected": True} for d in docs],
                    citations=[],
                    context_chars=sum(len(d.page_content) for d in docs) + 2 * max(len(docs) - 1, 0),
                    llm_calls=1,
                )
            else:
                cached = question in self._gen_cache
                generated = self._generated(question)
                t = lap("query_generation", t0)
                if mode == "mqr":
                    mqr = mqr_retrieve(self.store, question, self.cfg, generated)
                    selected, rrf = mqr.docs, None
                    budget = 10**9  # MQR alone sends EVERYTHING it found: that is its cost problem
                else:
                    rrf = mqr_rrf_retrieve(self.store, question, self.cfg, generated)
                    mqr, selected = rrf.mqr, rrf.fused
                    budget = self.cfg.max_context_chars
                t = lap("retrieve" if mode == "mqr" else "retrieve+rerank", t)
                gen = generate_grounded_answer(question, selected, budget)
                lap("generate", t)

                cited_ids = {gen["used_docs"][i - 1].metadata["chunk_id"] for i in gen["citations"]}
                used_ids = [d.metadata["chunk_id"] for d in gen["used_docs"]]
                out.update(
                    answer=gen["answer"],
                    queries=mqr.queries,
                    generated_queries=mqr.generated,
                    llm_failed=mqr.llm_failed,
                    sources=[_source(d, d.metadata["chunk_id"] in cited_ids) for d in gen["used_docs"]],
                    citations=gen["citations"],
                    context_chars=gen["context_chars"],
                    llm_calls=1 + (0 if cached else 1),
                    pool=self._pool_table(mqr, rrf, used_ids),
                )
        except NotImplementedError as err:
            raise _todo_error(mode, err) from None

        out["chunks_retrieved"] = len(out["pool"])
        out["chunks_sent"] = len(out["sources"])
        out["approx_prompt_tokens"] = round(out["context_chars"] / 4)
        out["embedding_calls"] = getattr(self.embeddings, "calls", 0) - emb_before
        out["timings_ms"] = {**timings, "total": round((time.perf_counter() - t0) * 1000)}
        return out

    @staticmethod
    def _pool_table(mqr, rrf, used_ids: list[str]) -> list[dict]:
        found_by: dict[str, list[str]] = {}
        for q, docs in mqr.per_query.items():
            for d in docs:
                found_by.setdefault(d.metadata["chunk_id"], []).append(q)
        sem_rank, bm_rank, bm_score, fused_rank = {}, {}, {}, {}
        if rrf is not None:
            sem_rank = {d.metadata["chunk_id"]: i + 1 for i, d in enumerate(rrf.semantic)}
            bm_rank = {d.metadata["chunk_id"]: i + 1 for i, d in enumerate(rrf.bm25)}
            bm_score = {d.metadata["chunk_id"]: d.metadata.get("bm25_score") for d in rrf.bm25}
            fused_rank = {d.metadata["chunk_id"]: i + 1 for i, d in enumerate(rrf.fused)}
            sem_score = {d.metadata["chunk_id"]: d.metadata.get("semantic_score") for d in rrf.semantic}
        rows = []
        for d in mqr.docs:
            cid = d.metadata["chunk_id"]
            row = _source(d)
            row.update(
                found_by=found_by.get(cid, []),
                semantic_rank=sem_rank.get(cid),
                bm25_rank=bm_rank.get(cid),
                fused_rank=fused_rank.get(cid),
                selected=cid in used_ids,
            )
            if rrf is not None:
                row["bm25_score"] = bm_score.get(cid)
                row["semantic_score"] = sem_score.get(cid)
                fused = next((f for f in rrf.fused if f.metadata["chunk_id"] == cid), None)
                if fused is not None:
                    row["rrf_score"] = fused.metadata.get("rrf_score")
            rows.append(row)
        if rrf is not None:
            rows.sort(key=lambda r: (r["fused_rank"] is None, r["fused_rank"] or 0, r["semantic_rank"] or 0))
        return rows


# --------------------------------------------------------------------------- #
# Evaluation: retrieval quality per mode on data/eval_set.json (no answer generation)
# --------------------------------------------------------------------------- #
def load_eval_set(path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["questions"]


def evaluate(service: RagService, questions: list[dict], modes=MODES) -> dict:
    rows, summary = [], {}
    for m in modes:
        summary[m] = {"hits": 0, "rr_sum": 0.0, "chunks": 0, "n": 0, "status": "ok", "by_type": {}}
    for q in questions:
        row = {"id": q["id"], "type": q["type"], "question": q["question"], "must_contain": q["must_contain"]}
        for m in modes:
            s = summary[m]
            if s["status"] != "ok":
                row[m] = None
                continue
            try:
                docs = service.retrieve(m, q["question"])
            except RagError as err:
                if err.status == 501:
                    s["status"] = "todo"
                    s["message"] = err.message
                    row[m] = None
                    continue
                raise
            needle = q["must_contain"].lower()
            rank = next((i + 1 for i, d in enumerate(docs) if needle in d.page_content.lower()), None)
            row[m] = {"hit": rank is not None, "rank": rank, "chunks": len(docs)}
            s["n"] += 1
            s["chunks"] += len(docs)
            if rank:
                s["hits"] += 1
                s["rr_sum"] += 1.0 / rank
            t = s["by_type"].setdefault(q["type"], {"hits": 0, "n": 0})
            t["n"] += 1
            t["hits"] += 1 if rank else 0
        rows.append(row)
    out = {}
    for m, s in summary.items():
        n = s["n"] or 1
        out[m] = {
            "status": s["status"],
            "message": s.get("message", ""),
            "hit_rate": round(s["hits"] / n, 3) if s["n"] else None,
            "mrr": round(s["rr_sum"] / n, 3) if s["n"] else None,
            "avg_chunks_sent": round(s["chunks"] / n, 1) if s["n"] else None,
            "questions": s["n"],
            "by_type": {k: round(v["hits"] / v["n"], 3) for k, v in s["by_type"].items()},
        }
    return {"summary": out, "rows": rows}
