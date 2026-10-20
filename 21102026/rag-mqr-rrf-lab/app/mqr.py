"""
app/mqr.py - Multi-Query Retriever (MQR).                  TODO 1, 2, 3, 4

Idea: the user's words are often not the document's words. Ask the LLM to
rewrite the question into N search queries, search with every query, and
take the UNION of the results. More "nets in the water" -> higher recall.

    "Can I WFH on Fridays?"
        ├─ (original)  Can I WFH on Fridays?                       -> top-5
        ├─ LLM query 1 hybrid working policy remote days per week   -> top-5
        ├─ LLM query 2 work from home rules Friday anchor days      -> top-5
        └─ LLM query 3 office presence requirement days per week    -> top-5
                                         union (dedupe by chunk_id) -> ~10-18 chunks

LangChain ships this as `MultiQueryRetriever`. We build it by hand so that
you can see (and test) every step.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_core.documents import Document

from .basic_rag import with_meta
from .config import RagConfig
from .llm import RagError, chat_complete
from .vector_store import InMemoryVectorStore

MQR_PROMPT = """You help a search engine over an internal company handbook \
(HR policies, finance rules, engineering runbooks and error codes).

Write {n} different search queries that together find every passage needed to \
answer the user's question.

Rules:
- Rewrite slang, abbreviations and casual words into the formal words a policy \
document would use (for example "WFH" -> "work from home, hybrid working").
- Keep exact identifiers unchanged: error codes (like PAY-E4031), product names, numbers.
- If the question has several parts, cover each part in its own query.
- Output one query per line. No numbering, no explanations, no blank lines.

User question: {question}"""


@dataclass
class MQRResult:
    queries: list[str]                                   # every query searched (original first if included)
    per_query: dict[str, list[Document]] = field(default_factory=dict)
    docs: list[Document] = field(default_factory=list)   # the union, first-seen order
    generated: list[str] = field(default_factory=list)   # only the LLM-written queries
    llm_failed: bool = False


# ---------------------------------------------------------------------------
# TODO 1 - parse_queries()
# ---------------------------------------------------------------------------
_PREFIX = re.compile(r"^\s*(?:query\s*\d+\s*[:.)-]|\d+\s*[.):-]|[-*•>]+)\s*", re.IGNORECASE)


def _norm(text: str) -> str:
    return " ".join(text.lower().split()).rstrip("?.! ")


def parse_queries(raw: str, question: str, n: int) -> list[str]:
    """
    Turn the LLM's raw text into a clean list of at most `n` queries.

    LLMs do not always follow "one per line, no numbering". Handle:
      * numbering / bullets:  "1. foo", "2) foo", "- foo", "* foo", "• foo", "Query 3: foo"
      * wrapping quotes / backticks:  "\"foo\"", "`foo`"
      * blank lines and surrounding spaces
      * preamble lines that end with ':'   e.g. "Here are 3 queries:"
      * duplicates (compare case-insensitively, ignore extra spaces and a trailing ?/./!)
      * a line that is just the original question again -> drop it
    Keep the order the LLM gave. Return [] for empty / None input.

    HINT: _PREFIX (above) strips one leading number/bullet; _norm() gives a
          comparison key.
    """
    raise NotImplementedError("TODO 1: implement parse_queries() in app/mqr.py")


# ---------------------------------------------------------------------------
# TODO 2 - generate_queries()
# ---------------------------------------------------------------------------
def generate_queries(question: str, n: int) -> list[str]:
    """
    Ask the chat model (azure/gpt-6-luna) for `n` reformulated queries.

    * Blank question or n <= 0 -> return [] WITHOUT calling the model.
    * Build ONE user message from MQR_PROMPT.format(n=n, question=question)
      and call chat_complete([{"role": "user", "content": ...}]).
    * Parse the reply with parse_queries(reply, question, n).
    * If the model call fails (chat_complete raises RagError), return [].
      MQR must never break the chatbot: the caller falls back to the
      original question.
    """
    raise NotImplementedError("TODO 2: implement generate_queries() in app/mqr.py")


# ---------------------------------------------------------------------------
# TODO 3 - unique_union()
# ---------------------------------------------------------------------------
def unique_union(doc_lists: list[list[Document]]) -> list[Document]:
    """
    Merge several result lists into one, removing duplicates.

    * Two Documents are the same chunk when metadata["chunk_id"] is equal.
    * Keep the FIRST occurrence (it carries the score/query that found it first).
    * Order = first-seen order: all of list 0, then the new ones of list 1, ...
    * Empty input or empty lists -> [].
    """
    raise NotImplementedError("TODO 3: implement unique_union() in app/mqr.py")


# ---------------------------------------------------------------------------
# TODO 4 - mqr_retrieve()
# ---------------------------------------------------------------------------
def mqr_retrieve(
    store: InMemoryVectorStore,
    question: str,
    cfg: RagConfig,
    generated: list[str] | None = None,
) -> MQRResult:
    """
    The full Multi-Query Retriever.

    1. generated = generate_queries(question, cfg.mqr_num_queries)
       (skip this call when `generated` is passed in - the service caches it)
    2. queries = [question] + generated   if cfg.mqr_include_original
                 generated                otherwise
       If queries ends up EMPTY (LLM failed and original not included),
       fall back to [question] and set llm_failed=True.
       Also set llm_failed=True whenever generated is empty.
    3. For every query: hits = store.search(query, cfg.mqr_k)   -> [(Document, score)]
       turn each hit into with_meta(doc, score=float(score), query=query)
       and store the list in per_query[query].
    4. docs = unique_union([per_query[q] for q in queries])
    5. return MQRResult(queries=..., per_query=..., docs=..., generated=..., llm_failed=...)
    """
    raise NotImplementedError("TODO 4: implement mqr_retrieve() in app/mqr.py")
