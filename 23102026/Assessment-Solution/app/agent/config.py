"""app/agent/config.py - PROVIDED. Agent knobs from .env (see the 'Agentic RAG' block)."""
from __future__ import annotations

import os
from dataclasses import dataclass

import llm_client  # noqa: F401  (loads .env)


def _int(name: str, default: int) -> int:
    return int((os.getenv(name) or str(default)).strip())


@dataclass
class AgentConfig:
    search_mode: str = "hybrid"      # hybrid | mqr_rrf
    max_subquestions: int = 3
    max_rounds: int = 2
    max_regenerations: int = 1
    check_answer: bool = True
    max_context_chunks: int = 8
    history_messages: int = 6
    recursion_limit: int = 40


def load_agent_config() -> AgentConfig:
    return AgentConfig(
        search_mode=(os.getenv("AGENT_SEARCH_MODE") or "hybrid").strip().lower(),
        max_subquestions=_int("AGENT_MAX_SUBQUESTIONS", 3),
        max_rounds=_int("AGENT_MAX_ROUNDS", 2),
        max_regenerations=_int("AGENT_MAX_REGENERATIONS", 1),
        check_answer=(os.getenv("AGENT_CHECK_ANSWER") or "true").strip().lower() in ("1", "true", "yes", "on"),
        max_context_chunks=_int("AGENT_MAX_CONTEXT_CHUNKS", 8),
        history_messages=_int("AGENT_HISTORY_MESSAGES", 6),
        recursion_limit=_int("AGENT_RECURSION_LIMIT", 40),
    )
