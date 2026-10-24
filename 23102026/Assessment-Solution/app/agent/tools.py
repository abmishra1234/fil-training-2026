"""
app/agent/tools.py - the agent's TOOLS.                         TODO 1, 2

A tool is just a function the agent may decide to call. Ours wrap what we
already built in Lab 1, so nothing is thrown away:

  search(query)     -> hybrid retrieval: semantic top-10 + BM25 over the WHOLE
                       corpus, fused with Lab 1's reciprocal_rank_fusion()   (TODO 2)
                       or the full Lab 1 MQR + RRF pipeline (AGENT_SEARCH_MODE=mqr_rrf)
  entity(name)      -> Graph RAG lite: every chunk that mentions an entity  (provided)
  calculate(expr)   -> safe arithmetic, so the LLM never does maths in its head (TODO 1)

Why not MQR inside the agent by default? The planner already writes focused
sub-questions (it does MQR's job), so a zero-LLM-call hybrid search is enough.
"""
from __future__ import annotations

import ast
import operator

from langchain_core.documents import Document # type: ignore

from ..basic_rag import basic_retrieve, with_meta
from ..config import RagConfig
from ..rerank import bm25_rank, mqr_rrf_retrieve, reciprocal_rank_fusion
from ..vector_store import InMemoryVectorStore
from .graph_rag import EntityGraph


class CalcError(ValueError):
    pass


_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"round": round, "min": min, "max": max, "abs": abs}


def format_number(value: float) -> str:
    """10.0 -> '10', 10.5 -> '10.5', 2/3 -> '0.67', 12000 -> '12000'."""
    if isinstance(value, bool):
        raise CalcError("booleans are not numbers")
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# TODO 1 - safe_calculate()
# ---------------------------------------------------------------------------
def safe_calculate(expr: str) -> str:
    """
    Evaluate an arithmetic expression SAFELY and return it formatted with format_number().

        safe_calculate("1.5 * 7")          -> "10.5"
        safe_calculate("3 * (2000 + 7500)") -> "28500"
        safe_calculate("round(50000/12)")   -> "4167"

    NEVER use eval(): the expression comes from an LLM, i.e. from untrusted text
    ("__import__('os').system(...)"). Parse with ast.parse(expr, mode="eval") and
    walk the tree yourself. Allowed:
      * numbers (int / float constants, not bool, not strings)
      * + - * / // % **  (use _BIN), unary + - (use _UNARY), parentheses
      * calls to round / min / max / abs only (use _FUNCS), positional args only
    Raise CalcError for anything else, and also for:
      * empty input or a syntax error
      * an exponent bigger than 100 (2 ** 10**9 would freeze the server)
      * division by zero
      * expressions longer than 200 characters
    """
    # >>> SOLUTION
    if not expr or not expr.strip():
        raise CalcError("empty expression")
    if len(expr) > 200:
        raise CalcError("expression too long")
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        raise CalcError(f"not an arithmetic expression: {expr!r}") from None

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise CalcError("exponent too large")
            try:
                return _BIN[type(node.op)](left, right)
            except ZeroDivisionError:
                raise CalcError("division by zero") from None
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](ev(node.operand))
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS
            and not node.keywords
        ):
            return _FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise CalcError(f"not allowed: {type(node).__name__}")

    return format_number(ev(tree))
    # <<< SOLUTION
    # >>> STARTER
    # raise NotImplementedError("TODO 1: implement safe_calculate() in app/agent/tools.py")
    # <<< STARTER


# ---------------------------------------------------------------------------
# TODO 2 - hybrid_search()
# ---------------------------------------------------------------------------
def hybrid_search(store: InMemoryVectorStore, query: str, k_each: int = 10, final_k: int = 5, rrf_k: int = 60) -> list[Document]:
    """
    Hybrid retrieval with ZERO LLM calls, reusing Lab 1 functions.

      1. semantic = basic_retrieve(store, query, k_each)           (FAISS, cosine)
      2. bm25     = bm25_rank([query], ALL chunks in the store)    (store.docs.values())
                    keep only docs with bm25_score > 0, then the first k_each
      3. fused    = reciprocal_rank_fusion([semantic, bm25], k=rrf_k, top_n=final_k)

    Difference with Lab 1: BM25 runs over the WHOLE corpus, not only over the
    semantic pool, so an exact code like PAY-E4035 is found even when the
    embedding model ranks it nowhere.
    Blank query or empty store -> [].
    """
    # >>> SOLUTION
    if not query or not query.strip() or store.size == 0:
        return []
    semantic = basic_retrieve(store, query, k_each)
    bm25 = [d for d in bm25_rank([query], list(store.docs.values())) if d.metadata["bm25_score"] > 0][:k_each]
    return reciprocal_rank_fusion([semantic, bm25], k=rrf_k, top_n=final_k)
    # <<< SOLUTION
    # >>> STARTER
    # raise NotImplementedError("TODO 2: implement hybrid_search() in app/agent/tools.py")
    # <<< STARTER


def search_tool(store: InMemoryVectorStore, query: str, cfg: RagConfig, mode: str = "hybrid") -> list[Document]:
    """PROVIDED. The 'search' tool: hybrid (default) or the full Lab 1 MQR + RRF pipeline."""
    if mode == "mqr_rrf":
        return mqr_rrf_retrieve(store, query, cfg).fused
    return hybrid_search(store, query, final_k=cfg.final_k, rrf_k=cfg.rrf_k)


def entity_tool(graph: EntityGraph, name: str, limit: int = 8) -> tuple[list[Document], dict | None]:
    """PROVIDED. The 'entity' tool (Graph RAG lite). Returns (chunks, info) or ([], None)."""
    found = graph.lookup(name, limit=limit)
    if not found:
        return [], None
    docs = [with_meta(d, score=1.0) for d in found["chunks"]]
    info = {k: found[k] for k in ("entity", "mentions", "documents", "neighbours")}
    return docs, info
