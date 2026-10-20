"""
app/rerank.py - Re-ranking with Reciprocal Rank Fusion (RRF).   TODO 5, 6, 7, 8

MQR finds MORE chunks (better recall) but now we have 10-20 of them.
Sending all of them to the LLM costs money and adds noise. So we rank the
pool twice and fuse the two rankings:

    pool from MQR (≈15 chunks)
        ├─ semantic rank  : cosine(query vectors, chunk vector)  - understands meaning
        └─ BM25 rank      : keyword match (exact words / codes)  - understands "PAY-E4035"
                        │
                        ▼
    RRF score(chunk) = Σ over rankings   1 / (k + rank)        rank starts at 1, k = 60
                        │
                        ▼
    top FINAL_K (5) chunks -> LLM

Why RRF? Cosine scores (0.71, 0.69 ...) and BM25 scores (12.4, 3.1 ...) are on
different scales, so you cannot just add them. RRF only uses the POSITION in
each list, so no score normalisation is needed. A chunk that is near the top
of BOTH lists wins. (LangChain's `EnsembleRetriever` uses the same formula.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np # type: ignore
from langchain_core.documents import Document # type: ignore
from rank_bm25 import BM25Okapi # type: ignore

from .basic_rag import with_meta
from .config import RagConfig
from .mqr import MQRResult, mqr_retrieve
from .vector_store import InMemoryVectorStore

STOPWORDS = {
    "a", "an", "the", "is", "are", "am", "was", "were", "be", "to", "of", "and", "or", "in", "on",
    "for", "with", "at", "by", "from", "do", "does", "did", "i", "my", "me", "we", "our", "you",
    "your", "it", "this", "that", "what", "how", "can", "should", "if", "any", "there", "get",
}
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """
    PROVIDED. Lower-case word tokens for BM25, stopwords removed.
    Hyphenated identifiers are kept whole AND split, so "PAY-E4031?" gives
    ["pay-e4031", "pay", "e4031"]: an exact code match scores highest, a
    partial one still counts.
    """
    tokens: list[str] = []
    for tok in _TOKEN.findall((text or "").lower()):
        if tok in STOPWORDS:
            continue
        tokens.append(tok)
        if "-" in tok:
            tokens.extend(p for p in tok.split("-") if p and p not in STOPWORDS)
    return tokens


@dataclass
class RRFResult:
    mqr: MQRResult
    semantic: list[Document] = field(default_factory=list)  # pool ordered by semantic score
    bm25: list[Document] = field(default_factory=list)      # pool ordered by BM25 score
    fused: list[Document] = field(default_factory=list)     # top FINAL_K after RRF


# ---------------------------------------------------------------------------
# TODO 5 - bm25_rank()
# ---------------------------------------------------------------------------
def bm25_rank(queries: list[str], docs: list[Document]) -> list[Document]:
    """
    Order `docs` by BM25 keyword relevance to the queries, best first.

    * query tokens = tokenize() of ALL queries joined with a space
      (original + LLM rewrites = query expansion)
    * corpus = [tokenize(d.page_content) for d in docs]; use rank_bm25.BM25Okapi
    * Return EVERY doc (never drop any), each as with_meta(doc, bm25_score=float(score)).
    * Ties keep the input order (use a stable sort).
    * Edge cases: docs == [] -> [];  no query tokens -> all docs in input order with bm25_score 0.0.
    """
    raise NotImplementedError("TODO 5: implement bm25_rank() in app/rerank.py")


# ---------------------------------------------------------------------------
# TODO 6 - semantic_rank()
# ---------------------------------------------------------------------------
def semantic_rank(store: InMemoryVectorStore, queries: list[str], docs: list[Document]) -> list[Document]:
    """
    Order `docs` by meaning, best first.

    * score(doc) = MAX over queries of  dot(store.embed_query(q), store.vector_for(chunk_id))
      (vectors are unit length, so dot product == cosine similarity)
    * store.embed_query() is cached, so the queries MQR already searched cost
      no new embedding request. Do NOT call store.search() here.
    * Return every doc as with_meta(doc, semantic_score=float(score)); stable sort.
    * docs == [] or queries == [] -> docs unchanged (as a new list).
    """
    raise NotImplementedError("TODO 6: implement semantic_rank() in app/rerank.py")


# ---------------------------------------------------------------------------
# TODO 7 - reciprocal_rank_fusion()
# ---------------------------------------------------------------------------
def reciprocal_rank_fusion(
    ranked_lists: list[list[Document]], k: int = 60, top_n: int | None = None
) -> list[Document]:
    """
    Fuse several rankings into one.

        rrf_score(doc) = Σ_lists  1 / (k + rank_in_that_list)      rank is 1-based

    Rules (the tests check every one):
      * k < 0 -> raise ValueError.
      * A doc missing from a list simply gets nothing from that list.
      * If the same chunk_id appears twice in ONE list, only its first (best)
        position counts.
      * Sort by rrf_score, highest first. TIES: the doc seen first wins, reading
        list 0 top-to-bottom, then list 1 top-to-bottom, and so on.
      * top_n=None -> return all; otherwise at most top_n (top_n <= 0 -> []).
      * Return copies: with_meta(first_seen_doc, rrf_score=score, rrf_ranks=[rank or None per list])
        Use the FIRST-SEEN Document object as the base so its metadata
        (e.g. semantic_score from list 0) is kept.
      * [] or lists that are all empty -> [].
    """
    raise NotImplementedError("TODO 7: implement reciprocal_rank_fusion() in app/rerank.py")


# ---------------------------------------------------------------------------
# TODO 8 - mqr_rrf_retrieve()
# ---------------------------------------------------------------------------
def mqr_rrf_retrieve(
    store: InMemoryVectorStore,
    question: str,
    cfg: RagConfig,
    generated: list[str] | None = None,
) -> RRFResult:
    """
    MQR for recall, RRF for precision.

    1. mqr = mqr_retrieve(store, question, cfg, generated)
    2. semantic = semantic_rank(store, mqr.queries, mqr.docs)
    3. bm25     = bm25_rank(mqr.queries, mqr.docs)
    4. fused    = reciprocal_rank_fusion([semantic, bm25], k=cfg.rrf_k, top_n=cfg.final_k)
    5. return RRFResult(mqr=mqr, semantic=semantic, bm25=bm25, fused=fused)
    """
    raise NotImplementedError("TODO 8: implement mqr_rrf_retrieve() in app/rerank.py")
