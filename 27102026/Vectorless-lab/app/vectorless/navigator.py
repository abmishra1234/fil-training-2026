"""
app/vectorless/navigator.py - RETRIEVAL AS REASONING.                 TODO V3, V4

Vector RAG asks: "which chunks SOUND most like the question?"  (cosine)
Vectorless RAG asks: "WHERE in this handbook would the answer live?" (LLM reasoning)

    question ─► level 1: LLM sees the 12 documents (id, title, summary)
                         picks ≤ VECTORLESS_MAX_DOCS        "04: payment error codes"
             ─► level 2: LLM sees the sections of those documents
                         picks ≤ VECTORLESS_MAX_SECTIONS    "04.4: PAY-E4035 ..."
             ─► leaves picked = evidence (FULL section text, never cut mid-sentence)
             ─► Lab 1's grounded prompt writes the answer with [n] citations

Every navigation step is one chat call, with a written "thinking" line:
the path IS the explanation of why each passage was retrieved.

If the LLM reply cannot be used (no JSON, only invented ids, gateway error), we
fall back to BM25 (keyword search: still vectorless) over what is left, so a
bad reply never returns nothing.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from langchain_core.documents import Document # type: ignore

from ..agent.parsing import parse_json
from ..config import RagConfig
from ..llm import RagError, chat_complete
from ..rerank import bm25_rank
from . import prompts
from .tree import TreeIndex, TreeNode, node_document


@dataclass
class NavStep:
    level: int
    shown: list[str]                    # node ids the LLM saw
    picked: list[str]                   # valid node ids it chose
    thinking: str = ""
    ok: bool = True                     # False = reply unusable -> fallback
    ms: int = 0


@dataclass
class TreeSearchResult:
    nodes: list[TreeNode] = field(default_factory=list)   # the evidence, in pick order
    steps: list[NavStep] = field(default_factory=list)
    llm_calls: int = 0
    fallback: str = ""                  # "" or "bm25"


# ---------------------------------------------------------------------------
# PROVIDED - what the LLM sees at each level
# ---------------------------------------------------------------------------
def skeleton(nodes: list[TreeNode]) -> str:
    """
    One line per node: id, title, (parent document for sections), size, summary.

      [04] Payments Platform Error Codes (ENG-RUN-PAY) · 6 sections: Error codes raised by ...
      [04.4] PAY-E4035 - Signature mismatch on bank file (in: Payments Platform ...): The bank ...
    """
    lines = []
    for n in nodes:
        where = f" (in: {n.doc_title})" if n.kind == "section" else ""
        size = f" · {len(n.children)} sections" if n.children else (" · single page" if n.kind == "document" else "")
        summary = f": {n.summary}" if n.summary else ""
        lines.append(f"[{n.node_id}] {n.title}{where}{size}{summary}")
    return "\n".join(lines)


def _canon(node_id) -> str:
    """'04' / '4' / 4 / '[04.2]' / ' 4.2 ' -> '4.2'-style key, so the LLM's format does not matter."""
    s = str(node_id).strip().strip("[]()").strip()
    parts = s.split(".")
    if all(p.isdigit() for p in parts if p) and s:
        return ".".join(str(int(p)) for p in parts if p)
    return s.lower()


# ---------------------------------------------------------------------------
# TODO V3 - parse_selection()
# ---------------------------------------------------------------------------
def parse_selection(reply: str | None, allowed: list[str], max_pick: int) -> tuple[list[str], str, bool]:
    """
    Turn the navigator's reply into a list of VALID node ids.

    Returns (ids, thinking, ok):
      * data = parse_json(reply). None, or "node_ids" missing / not a list -> ([], "", False)
      * thinking = str(data.get("thinking", "")).strip()
      * Each item of data["node_ids"] may be "04", "4", 4, "[04]" or " 04.2 ":
        match it to an id in `allowed` with _canon() (compare _canon(item) to
        _canon(allowed_id)) and return the id exactly as written in `allowed`.
      * Drop ids that are not in `allowed` (the LLM invented them) and duplicates.
      * Keep the LLM's order. At most max_pick ids (max_pick <= 0 -> none).
      * ok = True only if at least one valid id is left.
    """
    # >>> SOLUTION lab3
    data = parse_json(reply)
    if not data or not isinstance(data.get("node_ids"), list):
        return [], "", False
    thinking = str(data.get("thinking", "") or "").strip()
    lookup = {_canon(a): a for a in allowed}
    ids: list[str] = []
    for item in data["node_ids"]:
        if isinstance(item, bool):
            continue
        hit = lookup.get(_canon(item))
        if hit is not None and hit not in ids:
            ids.append(hit)
    ids = ids[: max(max_pick, 0)]
    return ids, thinking, bool(ids)
    # <<< SOLUTION
    # >>> STARTER lab3
    # raise NotImplementedError("TODO V3: implement parse_selection() in app/vectorless/navigator.py")
    # <<< STARTER


# ---------------------------------------------------------------------------
# PROVIDED - the safety net
# ---------------------------------------------------------------------------
def bm25_fallback(question: str, candidates: list[TreeNode], k: int) -> list[TreeNode]:
    """Keyword search over the candidate LEAVES (Lab 1's bm25_rank). Score 0 = not returned."""
    leaves: list[TreeNode] = []
    for c in candidates:
        for leaf in ([c] if c.is_leaf else c.leaves()):
            if leaf not in leaves:
                leaves.append(leaf)
    if not leaves or k <= 0:
        return []
    by_cid = {f"{n.source}::{n.node_id}": n for n in leaves}
    docs = [Document(page_content=f"{n.doc_title} > {n.title}\n{n.text}", metadata={"chunk_id": cid})
            for cid, n in by_cid.items()]
    ranked = [d for d in bm25_rank([question], docs) if d.metadata["bm25_score"] > 0]
    return [by_cid[d.metadata["chunk_id"]] for d in ranked[:k]]


# ---------------------------------------------------------------------------
# TODO V4 - tree_search()
# ---------------------------------------------------------------------------
def tree_search(question: str, tree: TreeIndex, max_docs: int = 3, max_sections: int = 4,
                max_steps: int = 3) -> TreeSearchResult:
    """
    The navigation loop. NO embeddings: only chat_complete() and the tree.

        frontier = tree.root.children          (the documents)
        for level = 1 .. max_steps:
            stop if the frontier is empty
            max_pick = max_docs at level 1, max_sections at deeper levels
            reply = chat_complete([
                {"role": "system", "content": prompts.TREE_NAVIGATE.format(max_pick=max_pick)},
                {"role": "user",   "content": f"Question: {question}\\n\\n"
                                              f"Level {level}: nodes you can open\\n{skeleton(frontier)}"},
            ])                                   count it in result.llm_calls (also when it fails);
                                                 a RagError counts as reply = ""
            ids, thinking, ok = parse_selection(reply, [ids of the frontier], max_pick)
            append NavStep(level, shown=frontier ids, picked=ids, thinking=thinking, ok=ok,
                           ms=duration of this step in milliseconds)
            if not ok: stop (the fallback below takes over)
            picked LEAVES  -> add to result.nodes (evidence)
            picked INNER nodes:
              - none, or this was the last allowed step (level == max_steps):
                    add the inner nodes themselves to result.nodes (a whole document) and stop
              - otherwise the next frontier = all children of the picked inner nodes

    Fallback: if result.nodes is still empty at the end, use
        bm25_fallback(question, <the frontier the LLM failed on, or the last one it saw>, max_sections)
    and set result.fallback = "bm25" (even when BM25 finds nothing).
    Blank question -> an empty TreeSearchResult without any LLM call.
    """
    # >>> SOLUTION lab3
    result = TreeSearchResult()
    if not question or not question.strip():
        return result
    frontier = list(tree.root.children)
    for level in range(1, max_steps + 1):
        if not frontier:
            break
        t0 = time.perf_counter()
        max_pick = max_docs if level == 1 else max_sections
        try:
            reply = chat_complete([
                {"role": "system", "content": prompts.TREE_NAVIGATE.format(max_pick=max_pick)},
                {"role": "user", "content": f"Question: {question}\n\nLevel {level}: nodes you can open\n{skeleton(frontier)}"},
            ])
        except RagError:
            reply = ""
        result.llm_calls += 1
        ids, thinking, ok = parse_selection(reply, [n.node_id for n in frontier], max_pick)
        result.steps.append(NavStep(level, [n.node_id for n in frontier], ids, thinking, ok,
                                    round((time.perf_counter() - t0) * 1000)))
        if not ok:
            break
        picked = [tree.find(i) for i in ids]
        result.nodes += [n for n in picked if n.is_leaf]
        inner = [n for n in picked if not n.is_leaf]
        if not inner or level == max_steps:
            result.nodes += inner
            break
        frontier = [c for n in inner for c in n.children]
    if not result.nodes:
        result.nodes = bm25_fallback(question, frontier, max_sections)
        result.fallback = "bm25"
    return result
    # <<< SOLUTION
    # >>> STARTER lab3
    # raise NotImplementedError("TODO V4: implement tree_search() in app/vectorless/navigator.py")
    # <<< STARTER


def tree_retrieve(tree: TreeIndex, question: str, cfg: RagConfig) -> tuple[list[Document], TreeSearchResult]:
    """PROVIDED. tree_search() with the .env limits, as Documents for the Lab 1 generator / evaluation."""
    res = tree_search(question, tree, cfg.vectorless_max_docs, cfg.vectorless_max_sections, cfg.vectorless_max_steps)
    return [node_document(n) for n in res.nodes], res

