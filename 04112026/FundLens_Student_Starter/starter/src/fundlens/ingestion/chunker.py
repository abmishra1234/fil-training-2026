"""FR-01 / FR-02 - ingestion and structure-aware chunking.  >>> YOU BUILD THIS (Day 1-2) <<<

Requirements recap
- Load md (factsheets, commentaries, policies), txt (client emails - usually NOT indexed for Q&A, see FAQ),
  text-layer PDF (KIDs) and the fund master CSV.
- Chunk by structure: markdown "## " headings; policy clauses "4.2 ..." become their own chunk with section "§4.2";
  keep tables whole inside their section. Target 300-800 tokens, small overlap.
- Every chunk is a fundlens.schemas.Chunk with doc_id, doc_type, fund_id, share_class, section, as_of_date, version, status.
- FR-02: re-ingesting a changed document replaces its old chunks (key on doc_id); SUPERSEDED policy versions are kept
  but marked status="SUPERSEDED" so retrieval can filter or down-rank them.
"""
from __future__ import annotations

from ..schemas import Chunk


def chunk_markdown(front_matter: dict, body: str) -> list[Chunk]:
    raise NotImplementedError("TODO Day 2: split by headings / clauses and attach metadata")


def chunk_kid_pdf(text: str) -> list[Chunk]:
    raise NotImplementedError("TODO Day 2: parse the doc_id line, then split on the numbered KID sections")


def fund_master_rows_as_chunks() -> list[Chunk]:
    """Optional: one small text chunk per fund/share class so BM25 can find ISINs and names.
    Numbers for answers must still come from the fund_lookup tool (FR-11)."""
    raise NotImplementedError


def build_all_chunks() -> list[Chunk]:
    raise NotImplementedError
