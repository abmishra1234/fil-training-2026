"""
app/ingest.py - PROVIDED. Turn .md / .txt files into LangChain Documents (chunks).

Two-step split (a common LangChain pattern):
  1. MarkdownHeaderTextSplitter  - one piece per "#"/"##" section, keeps the headings
  2. RecursiveCharacterTextSplitter - cuts long sections to CHUNK_SIZE characters

Each chunk starts with "<doc title> > <section>" so that both the embedding
and BM25 know what the chunk is about, and gets a stable id:
    chunk_id = "<file name>#<n>"      e.g. "04_payment_error_codes.md#2"
"""
from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

ALLOWED_SUFFIXES = {".md", ".txt"}


def split_text(text: str, source: str, chunk_size: int, chunk_overlap: int) -> list[Document]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "title"), ("##", "section")], strip_headers=True
    )
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    sections = header_splitter.split_text(text) if source.endswith(".md") else [Document(page_content=text)]
    chunks: list[Document] = []
    for sec in sections:
        title = sec.metadata.get("title") or Path(source).stem
        section = sec.metadata.get("section", "")
        heading = f"{title} > {section}" if section else title
        for piece in char_splitter.split_text(sec.page_content):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                Document(
                    page_content=f"{heading}\n{piece}",
                    metadata={
                        "chunk_id": f"{source}#{len(chunks)}",
                        "source": source,
                        "title": title,
                        "section": section,
                    },
                )
            )
    return chunks


def load_folder(folder: Path, chunk_size: int, chunk_overlap: int) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() in ALLOWED_SUFFIXES and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            docs.extend(split_text(text, path.name, chunk_size, chunk_overlap))
    return docs
