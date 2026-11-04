"""FR-03 to FR-06 - hybrid retrieval.  >>> YOU BUILD THIS (Day 2-3) <<<

Pipeline: question -> (MQR: 3 LLM rewrites + original) -> for each query: BM25 top-k and FAISS top-k
-> Reciprocal Rank Fusion over all ranked lists -> metadata filter (fund_id, doc_type, status, as_of_date)
-> optional LLM grading/rerank of top 10 -> top-k chunks.

RRF score for document d:   score(d) = sum over ranked lists L of  1 / (k + rank_L(d)),  k = 60, rank starts at 1.
"""
from __future__ import annotations

from ..schemas import Chunk


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse ranked lists of chunk_ids. Return [(chunk_id, score)] sorted by score desc."""
    raise NotImplementedError("TODO Day 3")


class HybridRetriever:
    def __init__(self, chunks: list[Chunk]):
        raise NotImplementedError("TODO: build BM25 (rank_bm25) and FAISS (IndexFlatIP on normalised embeddings); persist to settings.index_dir")

    def multi_query(self, question: str, n: int = 3) -> list[str]:
        raise NotImplementedError("TODO Day 3: FR-04, temperature 0, return original + n rewrites")

    def search(self, question: str, k: int = 8, filters: dict | None = None) -> list[Chunk]:
        raise NotImplementedError
