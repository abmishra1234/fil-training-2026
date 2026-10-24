"""
app/vector_store.py - PROVIDED. In-memory vector DB using FAISS (by Meta AI).

FAISS = "Facebook AI Similarity Search", Meta's open-source vector search
library. We use `faiss.IndexFlatIP` (exact inner-product search) and keep
LangChain `Document` objects next to it. Vectors are L2-normalised, so
inner product == cosine similarity (-1..1).

    FAISS row 0, 1, 2 ...  <->  self._ids[0], [1], [2] ...  <->  self.docs[chunk_id]

Everything lives in RAM: restart the server and the index is rebuilt from
data/docs (about 1-2 embedding requests for this corpus).

We also keep our own {chunk_id: vector} dict. Re-ranking (TODO 6) needs
the vector of ANY candidate chunk without calling the embedding API again.
"""
from __future__ import annotations

import faiss
import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


def normalize(v) -> np.ndarray:
    arr = np.asarray(v, dtype="float32")
    norm = np.linalg.norm(arr, axis=-1, keepdims=True)
    norm[norm == 0] = 1.0
    return arr / norm


class InMemoryVectorStore:
    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
        self.index: faiss.IndexFlatIP | None = None
        self._ids: list[str] = []                 # FAISS row number -> chunk_id
        self.docs: dict[str, Document] = {}       # chunk_id -> Document
        self.vectors: dict[str, np.ndarray] = {}  # chunk_id -> unit vector
        self._query_cache: dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------ build
    def build(self, docs: list[Document]) -> None:
        self.index, self._ids, self.docs, self.vectors = None, [], {}, {}
        self._query_cache.clear()
        if not docs:
            return
        ids = [d.metadata["chunk_id"] for d in docs]
        if len(set(ids)) != len(ids):
            raise ValueError("chunk_id values must be unique")
        texts = [d.page_content for d in docs]
        vecs = normalize(self.embeddings.embed_documents(texts))
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(np.ascontiguousarray(vecs))
        self.index, self._ids = index, ids
        for cid, doc, vec in zip(ids, docs, vecs):
            self.docs[cid] = doc
            self.vectors[cid] = vec

    @property
    def size(self) -> int:
        return len(self.docs)

    # ----------------------------------------------------------------- search
    def embed_query(self, text: str) -> np.ndarray:
        """
        Unit vector for a query. Cached: the first call costs ONE embedding
        request, asking again for the same text is free. MQR searches with
        4 queries and re-ranking (TODO 6) needs those same 4 vectors again.
        """
        if text not in self._query_cache:
            if len(self._query_cache) > 2000:
                self._query_cache.clear()
            self._query_cache[text] = normalize(self.embeddings.embed_query(text))
        return self._query_cache[text]

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        """Top-k chunks for `query`, best first, as (Document, cosine score)."""
        if self.index is None or k <= 0:
            return []
        qv = self.embed_query(query).reshape(1, -1)
        scores, rows = self.index.search(qv, min(k, self.size))
        return [(self.docs[self._ids[r]], float(s)) for s, r in zip(scores[0], rows[0]) if r != -1]

    def vector_for(self, chunk_id: str) -> np.ndarray:
        return self.vectors[chunk_id]
