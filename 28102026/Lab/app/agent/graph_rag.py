"""
app/agent/graph_rag.py - PROVIDED. "Graph RAG lite": an entity graph over the chunks.

The problem it solves
---------------------
Vector / BM25 retrieval treats every chunk as an island and returns the top-k.
Two kinds of questions break that:

  1. AGGREGATION  "What rules apply to graduate trainees?"
     The facts are spread over 5 different documents (leave, hybrid working,
     on-call, learning budget, academy). Top-5 similarity search returns the 5
     chunks most similar to the *wording*, often 3 from one document.
  2. RELATIONSHIPS "What does PAY-E4035 have to do with the HSM?"
     The link (PAY-E4035 -> re-sign with HSM key; HSM = Hardware Security Module)
     lives in the structure between chunks, not in one chunk.

What we build here (cheap, no LLM calls)
----------------------------------------
  node  = an entity (error code, system, role, policy term)
  edge  = two entities mentioned in the same chunk (weight = how many chunks)
  index = entity -> every chunk that mentions it

So `lookup("graduate trainee")` returns ALL chunks that mention it, across all
documents, plus its strongest neighbours in the graph.

What "real" Graph RAG (e.g. Microsoft GraphRAG) adds
----------------------------------------------------
An LLM extracts typed (entity, relation, entity) triples from every chunk,
clusters the graph into communities and pre-writes a summary per community.
"Local search" walks from an entity; "global search" answers corpus-wide
questions from the community summaries. Much better, but it costs LLM calls
over the whole corpus and must be rebuilt when documents change.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from langchain_core.documents import Document # type: ignore

# canonical name -> aliases (lower-case regex fragments). Extend for your own docs.
KNOWN_ENTITIES: dict[str, list[str]] = {
    "graduate trainee": [r"graduate trainees?", r"grad trainees?"],
    "intern": [r"interns?"],
    "new joiner": [r"new joiners?"],
    "on-call": [r"on-call", r"pager"],
    "reporting manager": [r"reporting manager", r"skip-level manager"],
    "Incident Commander": [r"incident commander"],
    "treasury desk": [r"treasury desk"],
    "Sev-1": [r"sev-1"],
    "Sev-2": [r"sev-2"],
    "Sev-3": [r"sev-3"],
    "change freeze": [r"change freeze"],
    "release train": [r"release train"],
    "per diem": [r"per diem"],
    "earned leave": [r"earned[- ]leave"],
    "sick leave": [r"sick leave"],
    "anchor days": [r"anchor days?"],
    "MFA": [r"\bmfa\b", r"multi-factor"],
    "CAB": [r"\bcab\b", r"change advisory board"],
    "HSM": [r"\bhsm\b", r"hardware security module"],
    "KYC": [r"\bkyc\b", r"know your customer"],
    "UTR": [r"\butr\b", r"unique transaction reference"],
    "RTO": [r"\brto\b", r"recovery time objective"],
    "RPO": [r"\brpo\b", r"recovery point objective"],
    "idempotency key": [r"idempotency key"],
    "full and final settlement": [r"full and final settlement"],
}
_CODE = re.compile(r"\b(?:PAY|AUTH)-E\d{4}\b")
_PRODUCT = re.compile(r"\b(?:[A-Z][a-z]+){2,}\b")  # CamelCase product names: TripNova, PeopleDesk ...
_ALIAS_RX = {name: re.compile("|".join(f"(?:{a})" for a in aliases), re.IGNORECASE) for name, aliases in KNOWN_ENTITIES.items()}


IGNORE = {"NovaPay"}  # the company name is in almost every chunk: a useless hub node


def extract_entities(text: str) -> set[str]:
    found = set(_CODE.findall(text))
    found |= {m for m in _PRODUCT.findall(text) if m not in IGNORE}
    found |= {name for name, rx in _ALIAS_RX.items() if rx.search(text)}
    return found


@dataclass
class EntityGraph:
    chunks_by_entity: dict[str, list[str]] = field(default_factory=dict)  # entity -> chunk_ids (corpus order)
    edges: dict[str, Counter] = field(default_factory=dict)                # entity -> Counter(neighbour -> weight)
    docs: dict[str, Document] = field(default_factory=dict)

    @classmethod
    def build(cls, docs: list[Document]) -> "EntityGraph":
        by_entity: dict[str, list[str]] = defaultdict(list)
        edges: dict[str, Counter] = defaultdict(Counter)
        store: dict[str, Document] = {}
        for d in docs:
            cid = d.metadata["chunk_id"]
            store[cid] = d
            ents = sorted(extract_entities(d.page_content))
            for e in ents:
                by_entity[e].append(cid)
            for a in ents:
                for b in ents:
                    if a != b:
                        edges[a][b] += 1
        return cls(dict(by_entity), dict(edges), store)

    # ------------------------------------------------------------- queries
    @property
    def entities(self) -> list[str]:
        return sorted(self.chunks_by_entity, key=lambda e: (-len(self.chunks_by_entity[e]), e.lower()))

    def resolve(self, name: str) -> str | None:
        """Map what the user/LLM wrote to a graph node: exact, case-insensitive, alias, then substring."""
        if not name or not name.strip():
            return None
        q = name.strip()
        if q in self.chunks_by_entity:
            return q
        low = {e.lower(): e for e in self.chunks_by_entity}
        if q.lower() in low:
            return low[q.lower()]
        for canon, rx in _ALIAS_RX.items():
            if canon in self.chunks_by_entity and rx.fullmatch(q):
                return canon
        hits = [e for e in self.chunks_by_entity if q.lower() in e.lower() or e.lower() in q.lower()]
        return min(hits, key=len) if hits else None

    def neighbours(self, entity: str, n: int = 6) -> list[tuple[str, int]]:
        return self.edges.get(entity, Counter()).most_common(n)

    def lookup(self, name: str, limit: int = 8) -> dict | None:
        """
        All chunks that mention the entity (one per document first, so the answer
        covers every document), plus the strongest neighbours.
        """
        ent = self.resolve(name)
        if ent is None:
            return None
        ids = self.chunks_by_entity[ent]
        first_per_doc, rest, seen_src = [], [], set()
        for cid in ids:
            src = self.docs[cid].metadata["source"]
            (rest if src in seen_src else first_per_doc).append(cid)
            seen_src.add(src)
        ordered = (first_per_doc + rest)[:limit]
        return {
            "entity": ent,
            "mentions": len(ids),
            "documents": sorted(seen_src),
            "neighbours": self.neighbours(ent),
            "chunks": [self.docs[c] for c in ordered],
        }
