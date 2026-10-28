"""
app/pipeline.py - PROVIDED. Runs one question through one of three modes and
returns everything the UI's "Retrieval inspector" needs.

  basic    : FAISS top-5                    -> naive prompt     (basic_rag.py)
  mqr      : MQR union (all chunks)         -> grounded prompt  (TODO 1-4, 9-10)
  mqr_rrf  : MQR union -> RRF top-5         -> grounded prompt  (TODO 1-10)
  vectorless: LLM navigates the tree index  -> grounded prompt  (Lab 3, TODO V1-V4)
              no embeddings, no FAISS: see app/vectorless/
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone

from langchain_core.documents import Document

from llm_client import traced

from .basic_rag import basic_retrieve, build_basic_chain
from .config import RagConfig, config
from .generation import generate_grounded_answer
from .ingest import load_folder
from .llm import USAGE, GatewayEmbeddings, RagError
from .mqr import generate_queries, mqr_retrieve
from .rerank import mqr_rrf_retrieve
from .vector_store import InMemoryVectorStore
from .vectorless.navigator import TreeSearchResult, tree_retrieve
from .vectorless.tree import TreeIndex, build_tree, summarize_tree

MODES = ("basic", "mqr", "mqr_rrf", "vectorless")
MODE_TODOS = {"mqr": "TODO 1-4 and 9-10", "mqr_rrf": "TODO 1-10", "vectorless": "Lab 3 TODO V1-V4"}
SUMMARY_MODES = ("llm", "extractive", "none")


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
        # ---- Lab 3: the tree index (vectorless RAG) ----
        self.tree: TreeIndex | None = None
        self.tree_error: str | None = None
        self.summary_mode = self.cfg.vectorless_summaries if self.cfg.vectorless_summaries in SUMMARY_MODES else "llm"
        self._tree_lock = threading.Lock()
        self.last_nav: TreeSearchResult | None = None

    # ----------------------------------------------------------------- index
    def reindex(self) -> int:
        with self._lock:
            self._gen_cache.clear()
            self._build_tree()  # free (just parsing) and independent of the embedding model
            try:
                docs = load_folder(self.cfg.docs_dir, self.cfg.chunk_size, self.cfg.chunk_overlap)
                self.store.build(docs)
                self.index_error = None
                self.indexed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            except RagError as err:
                self.index_error = f"{err.message} {err.hint}".strip()
                raise
            return self.store.size

    # ------------------------------------------------------- Lab 3: tree index
    def _build_tree(self) -> None:
        """Parse data/docs into the tree. Summaries are written lazily, on first vectorless use."""
        try:
            self.tree, self.tree_error = build_tree(self.cfg.docs_dir), None
        except NotImplementedError as err:  # student starter: TODO V1 not done yet
            self.tree, self.tree_error = None, str(err)

    def _require_tree(self) -> TreeIndex:
        if self.tree is None:
            if self.tree_error:
                raise NotImplementedError(self.tree_error)
            self._build_tree()
            if self.tree is None:
                raise NotImplementedError(self.tree_error or "tree index not built")
        if not self.tree.documents:
            raise RagError(503, "The tree index is empty.", "Add .md / .txt files to data/docs and re-index.")
        return self.tree

    def ensure_tree_summaries(self, mode: str | None = None) -> int:
        """
        Write the signposts once (or again with another mode). Returns the LLM calls spent NOW:
        12 the first time with mode=llm, 0 when they exist or come from the disk cache.
        """
        tree = self._require_tree()
        with self._tree_lock:
            if mode is not None:
                if mode not in SUMMARY_MODES:
                    raise RagError(400, f"Unknown summary mode {mode!r}", f"Use one of {SUMMARY_MODES}")
                self.summary_mode = mode
            if tree.summaries == self.summary_mode:
                return 0
            return summarize_tree(tree, self.summary_mode, self.cfg.vectorless_cache)

    def tree_info(self) -> dict:
        t = self.tree
        if t is None:
            return {"status": "todo" if self.tree_error else "empty", "error": self.tree_error or ""}
        return {
            "status": "ok", "documents": len(t.documents), "nodes": len(t.by_id) - 1,
            "leaves": len(t.root.leaves()), "summaries": t.summaries, "summary_mode": self.summary_mode,
        }

    def reset_caches(self) -> None:
        """Forget MQR rewrites and query vectors, so the next run pays its own way (fair cost numbers)."""
        self._gen_cache.clear()
        self.store._query_cache.clear()

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
    @traced("rag.retrieve", kind="retriever")
    def retrieve(self, mode: str, question: str) -> list[Document]:
        """Only the chunks that would be sent to the LLM (used by evaluation)."""
        try:
            if mode == "vectorless":  # needs no embeddings, so no FAISS index either
                self.ensure_tree_summaries()
                docs, self.last_nav = tree_retrieve(self.tree, question, self.cfg)
                return docs
            self._require_index()
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
    @traced("rag.run")
    def run(self, mode: str, question: str) -> dict:
        if mode not in MODES:
            raise RagError(400, f"Unknown mode {mode!r}", f"Use one of {MODES}")
        if mode != "vectorless":
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
            if mode == "vectorless":
                self._run_vectorless(question, out, lap, t0)
            elif mode == "basic":
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

        out["chunks_retrieved"] = len(out["pool"]) if mode != "vectorless" else out.pop("_picked")
        out["chunks_sent"] = len(out["sources"])
        out["approx_prompt_tokens"] = round(out["context_chars"] / 4)
        out["embedding_calls"] = getattr(self.embeddings, "calls", 0) - emb_before
        out["timings_ms"] = {**timings, "total": round((time.perf_counter() - t0) * 1000)}
        return out

    def _run_vectorless(self, question: str, out: dict, lap, t0: float) -> None:
        """Lab 3: summaries (once) -> LLM navigation of the tree -> Lab 1 grounded generation."""
        index_calls = self.ensure_tree_summaries()
        t = lap("tree_summaries", t0) if index_calls else t0
        docs, nav = tree_retrieve(self.tree, question, self.cfg)
        t = lap("navigate", t)
        gen = generate_grounded_answer(question, docs, self.cfg.max_context_chars)
        lap("generate", t)
        cited_ids = {gen["used_docs"][i - 1].metadata["chunk_id"] for i in gen["citations"]}
        used_ids = [d.metadata["chunk_id"] for d in gen["used_docs"]]
        out.update(
            answer=gen["answer"],
            queries=[question],
            generated_queries=[],
            llm_failed=bool(nav.fallback),
            fallback=nav.fallback,
            sources=[_source(d, d.metadata["chunk_id"] in cited_ids) for d in gen["used_docs"]],
            citations=gen["citations"],
            context_chars=gen["context_chars"],
            llm_calls=nav.llm_calls + (1 if gen["used_docs"] else 0),
            index_llm_calls=index_calls,
            tree_summaries=self.tree.summaries,
            tree_path=self._tree_path(nav),
            pool=self._tree_pool(nav, used_ids),
            nodes_seen=sum(len(s.shown) for s in nav.steps),
            _picked=len(docs),
        )

    def _tree_path(self, nav: TreeSearchResult) -> list[dict]:
        tree = self.tree
        steps = [
            {"level": s.level, "ok": s.ok, "thinking": s.thinking, "ms": s.ms, "shown": len(s.shown),
             "picked": [{"node_id": i, "title": tree.find(i).title, "kind": tree.find(i).kind} for i in s.picked]}
            for s in nav.steps
        ]
        if nav.fallback:
            steps.append({"level": len(nav.steps) + 1, "ok": True, "fallback": nav.fallback, "ms": 0, "shown": 0,
                          "thinking": "Navigator reply unusable: BM25 keyword search over the remaining sections.",
                          "picked": [{"node_id": n.node_id, "title": n.title, "kind": n.kind} for n in nav.nodes]})
        return steps

    def _tree_pool(self, nav: TreeSearchResult, used_ids: list[str]) -> list[dict]:
        """Every node the navigator SAW, grouped by level: was it picked, did it reach the LLM?"""
        tree, rows, seen = self.tree, [], set()
        evidence = {n.node_id for n in nav.nodes}
        levels = [(s.level, s.shown, set(s.picked)) for s in nav.steps]
        if nav.fallback:
            levels.append(("bm25", [n.node_id for n in nav.nodes], evidence))
        for level, shown, picked in levels:
            for nid in shown:
                if nid in seen:
                    continue
                seen.add(nid)
                n = tree.find(nid)
                cid = f"{n.source}::{n.node_id}"
                rows.append({
                    "chunk_id": cid, "node_id": n.node_id, "source": n.source, "kind": n.kind,
                    "section": n.title if n.kind == "section" else "", "title": n.title,
                    "text": n.summary, "summary_source": n.summary_source, "level": level,
                    "picked": nid in picked, "evidence": nid in evidence, "selected": cid in used_ids,
                    "found_by": [],
                })
        return rows

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
    """
    Retrieval quality AND cost per mode. Each mode runs over all questions with
    cold caches (no MQR rewrite or query vector borrowed from another mode), so
    LLM calls, embedding calls and latency are each mode's own.
    """
    rows = [{"id": q["id"], "type": q["type"], "question": q["question"], "must_contain": q["must_contain"]}
            for q in questions]
    out = {}
    for m in modes:
        service.reset_caches()
        s = {"hits": 0, "rr_sum": 0.0, "chunks": 0, "chars": 0, "n": 0, "status": "ok", "by_type": {},
             "llm": 0, "emb": 0, "ms": 0, "fallbacks": 0, "index_llm_calls": 0, "message": ""}
        if m == "vectorless":
            try:
                s["index_llm_calls"] = service.ensure_tree_summaries()  # one-off, reported apart
            except NotImplementedError as err:
                s["status"], s["message"] = "todo", _todo_error(m, err).message
        for row, q in zip(rows, questions):
            if s["status"] != "ok":
                row[m] = None
                continue
            chat0, emb0, t0 = USAGE["chat"], getattr(service.embeddings, "calls", 0), time.perf_counter()
            try:
                docs = service.retrieve(m, q["question"])
            except RagError as err:
                if err.status == 501:
                    s["status"], s["message"] = "todo", err.message
                    row[m] = None
                    continue
                raise
            ms = round((time.perf_counter() - t0) * 1000)
            llm = USAGE["chat"] - chat0
            emb = getattr(service.embeddings, "calls", 0) - emb0
            needle = q["must_contain"].lower()
            rank = next((i + 1 for i, d in enumerate(docs) if needle in d.page_content.lower()), None)
            fallback = bool(m == "vectorless" and service.last_nav and service.last_nav.fallback)
            row[m] = {"hit": rank is not None, "rank": rank, "chunks": len(docs), "llm": llm, "emb": emb,
                      "ms": ms, "fallback": fallback}
            s["n"] += 1
            s["chunks"] += len(docs)
            s["chars"] += sum(len(d.page_content) for d in docs)
            s["llm"] += llm
            s["emb"] += emb
            s["ms"] += ms
            s["fallbacks"] += 1 if fallback else 0
            if rank:
                s["hits"] += 1
                s["rr_sum"] += 1.0 / rank
            t = s["by_type"].setdefault(q["type"], {"hits": 0, "n": 0})
            t["n"] += 1
            t["hits"] += 1 if rank else 0
        n = s["n"] or 1
        done = s["n"] > 0
        out[m] = {
            "status": s["status"],
            "message": s["message"],
            "hit_rate": round(s["hits"] / n, 3) if done else None,
            "mrr": round(s["rr_sum"] / n, 3) if done else None,
            "avg_chunks_sent": round(s["chunks"] / n, 1) if done else None,
            "avg_context_chars": round(s["chars"] / n) if done else None,
            "llm_calls_per_q": round(s["llm"] / n, 2) if done else None,
            "embedding_calls_per_q": round(s["emb"] / n, 2) if done else None,
            "avg_ms": round(s["ms"] / n) if done else None,
            "fallbacks": s["fallbacks"],
            "index_llm_calls": s["index_llm_calls"],
            "questions": s["n"],
            "by_type": {k: round(v["hits"] / v["n"], 3) for k, v in s["by_type"].items()},
        }
    return {"summary": out, "rows": rows}
