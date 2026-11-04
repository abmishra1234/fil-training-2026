"""Small helpers to read the kit's corpus. Plumbing only - chunking, indexing and retrieval are yours to build."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from .config import settings

_FM = re.compile(r"^---\n(.*?)\n---\n", re.S)


def read_markdown(path: Path) -> tuple[dict, str]:
    """Return (front_matter_dict, body_text) for a corpus markdown file."""
    raw = path.read_text(encoding="utf-8")
    m = _FM.match(raw)
    if not m:
        return {}, raw
    return yaml.safe_load(m.group(1)) or {}, raw[m.end():]


def read_email(path: Path) -> tuple[dict, str]:
    """Client emails start with '# key: value' comment lines, then the email."""
    meta, body = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ") and ":" in line and not body:
            k, v = line[2:].split(":", 1)
            meta[k.strip()] = v.strip()
        else:
            body.append(line)
    return meta, "\n".join(body).strip()


def read_pdf_text(path: Path) -> str:
    """KIDs are text-layer PDFs (no OCR needed). The first lines carry doc_id / as_of_date metadata."""
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)


def list_corpus() -> dict[str, list[Path]]:
    c = settings.corpus_dir
    return {
        "factsheet": sorted((c / "factsheets").glob("*.md")),
        "kid": sorted((c / "kids").glob("*.pdf")),
        "commentary": sorted((c / "commentaries").glob("*.md")),
        "policy": sorted((c / "policies").glob("*.md")),
        "client_email": sorted((c / "client_emails").glob("*.txt")),
        "rules": sorted((c / "rules").glob("*.yaml")),
    }


def load_email(email_ref: str) -> str:
    p = settings.corpus_dir / "client_emails" / f"{email_ref}.txt"
    return read_email(p)[1]
