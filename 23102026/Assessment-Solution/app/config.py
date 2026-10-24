"""
app/config.py - settings that belong to the RAG lab.

LLM connection settings (mode, gateway, keys, model names) stay in
llm_client.py exactly as in the sample scripts. This file only adds the
RAG knobs. Importing llm_client first makes sure .env is loaded.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import llm_client  # noqa: F401  (side effect: loads .env)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)).strip() or default)


def _bool(name: str, default: bool) -> bool:
    return (os.getenv(name, str(default)).strip().lower() or str(default).lower()) in ("1", "true", "yes", "on")


@dataclass
class RagConfig:
    docs_dir: Path
    chunk_size: int
    chunk_overlap: int
    basic_k: int
    mqr_num_queries: int
    mqr_k: int
    mqr_include_original: bool
    rrf_k: int
    final_k: int
    max_context_chars: int


def load_config() -> RagConfig:
    docs = Path(os.getenv("RAG_DOCS_DIR", "data/docs"))
    if not docs.is_absolute():
        docs = PROJECT_ROOT / docs
    return RagConfig(
        docs_dir=docs,
        chunk_size=_int("CHUNK_SIZE", 500),
        chunk_overlap=_int("CHUNK_OVERLAP", 60),
        basic_k=_int("BASIC_K", 5),
        mqr_num_queries=_int("MQR_NUM_QUERIES", 3),
        mqr_k=_int("MQR_K", 5),
        mqr_include_original=_bool("MQR_INCLUDE_ORIGINAL", True),
        rrf_k=_int("RRF_K", 60),
        final_k=_int("FINAL_K", 5),
        max_context_chars=_int("MAX_CONTEXT_CHARS", 6000),
    )


config = load_config()
