"""
app/generation.py - Better GENERATION for the improved pipeline.   TODO 9, 10

Better retrieval is half the job. The basic prompt just pastes chunks and
says "answer using the context". The improved prompt:

  * numbers every chunk  [1] [2] ...  and says where it came from
  * keeps RRF order (best chunk first: models pay most attention to the start)
  * stays inside a character budget (cost control)
  * forces citations  -> you can check every fact
  * tells the model to admit "I could not find this" instead of guessing

    fused chunks ─► build_context_block() ─► GROUNDED_PROMPT ─► gpt-6-luna
                                                                    │
                       sources marked "cited" ◄─ extract_citations() ◄┘
"""
from __future__ import annotations

import re

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .basic_rag import gateway_llm

NOT_FOUND = "I could not find this in the handbook."

GROUNDED_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the NovaPay internal helpdesk assistant.\n"
            "Answer ONLY from the numbered context passages.\n"
            "After every fact, cite the passage number(s) in square brackets, like [1] or [2][3].\n"
            "Copy error codes, amounts, dates and names exactly as written.\n"
            "If the passages do not contain the answer, reply exactly: " + NOT_FOUND + "\n"
            "If only part of the question is answered, answer that part and say what is missing.\n"
            "Be brief: at most 6 short sentences or bullet points.",
        ),
        ("human", "Context passages:\n{context}\n\nQuestion: {question}"),
    ]
)


# ---------------------------------------------------------------------------
# TODO 9 - build_context_block()
# ---------------------------------------------------------------------------
def build_context_block(docs: list[Document], max_chars: int) -> tuple[str, list[Document]]:
    """
    Turn ranked chunks into a numbered context string, within a budget.

    Each passage is formatted as (n starts at 1 and counts only USED chunks):

        [n] (source: <metadata['source']>)
        <page_content>

    and passages are joined with ONE blank line ("\\n\\n").

    Budget rules:
      * Walk the docs in the given (ranked) order.
      * A passage that would push the total length (len of the joined string)
        above max_chars is SKIPPED; keep trying the next, smaller ones.
      * The FIRST doc is always used, even if alone it is longer than
        max_chars; then cut its page_content so the block is exactly max_chars long.
      * docs == [] -> ("", []).

    Return (context_string, used_docs).
    """
    # >>> SOLUTION
    if not docs:
        return "", []

    def fmt(n: int, d: Document) -> str:
        return f"[{n}] (source: {d.metadata.get('source', '?')})\n{d.page_content}"

    first = fmt(1, docs[0])
    if len(first) > max_chars:
        first = first[: max(max_chars, 0)]
    parts, used = [first], [docs[0]]
    total = len(first)
    for d in docs[1:]:
        p = fmt(len(used) + 1, d)
        if total + 2 + len(p) <= max_chars:
            parts.append(p)
            used.append(d)
            total += 2 + len(p)
    return "\n\n".join(parts), used
    # <<< SOLUTION
    # >>> STARTER
    # raise NotImplementedError("TODO 9: implement build_context_block() in app/generation.py")
    # <<< STARTER


# ---------------------------------------------------------------------------
# TODO 10 - extract_citations()
# ---------------------------------------------------------------------------
def extract_citations(answer: str, n_passages: int) -> list[int]:
    """
    Which passages did the model cite?

      "Move it to next day [1][3]. See [3], [7] and [1, 2]."  n_passages=4  -> [1, 2, 3]

    * Accept [1], [1][3] and comma lists inside one bracket: [1, 2] / [1,2].
    * Ignore numbers outside 1..n_passages (the model invented [7] or wrote [0]).
    * Ignore brackets that are not pure number lists, e.g. [see 2] or [a].
    * Return sorted, unique ints. Empty / None answer -> [].
    """
    # >>> SOLUTION
    if not answer:
        return []
    found: set[int] = set()
    for group in re.findall(r"\[(\s*\d+(?:\s*,\s*\d+)*\s*)\]", answer):
        for num in group.split(","):
            n = int(num)
            if 1 <= n <= n_passages:
                found.add(n)
    return sorted(found)
    # <<< SOLUTION
    # >>> STARTER
    # raise NotImplementedError("TODO 10: implement extract_citations() in app/generation.py")
    # <<< STARTER


def generate_grounded_answer(question: str, docs: list[Document], max_chars: int) -> dict:
    """PROVIDED. Uses TODO 9 + 10. Returns {answer, used_docs, citations, context_chars}."""
    context, used = build_context_block(docs, max_chars)
    if not used:
        return {"answer": NOT_FOUND, "used_docs": [], "citations": [], "context_chars": 0}
    chain = GROUNDED_PROMPT | gateway_llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question}) or NOT_FOUND
    return {
        "answer": answer,
        "used_docs": used,
        "citations": extract_citations(answer, len(used)),
        "context_chars": len(context),
    }
