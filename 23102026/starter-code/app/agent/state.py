"""
app/agent/state.py - PROVIDED. The agent's STATE: the one dict every node reads
and updates. LangGraph merges each node's returned dict into it.

Two kinds of fields:

  * plain fields  (route, answer, ...)       -> the node's value REPLACES the old one
  * reducer fields (Annotated[..., reducer]) -> the node's value is MERGED

Why reducers?
  * `messages` uses LangGraph's add_messages: the chat history grows turn by turn
    and is saved by the checkpointer per thread_id (= conversation memory).
  * `evidence`, `tried_queries`, `steps` use `accumulate`: several `retrieve`
    nodes run IN PARALLEL (Send fan-out) and each returns its own chunks. Without
    a reducer, LangGraph would raise "can receive only one value per step".

The state of a thread survives between turns (checkpointer!), so `start_turn`
resets the per-question fields. `accumulate(old, None)` means "reset to []".
"""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage # type: ignore
from langgraph.graph.message import add_messages # type: ignore

Route = Literal["direct", "clarify", "simple", "complex"]
Tool = Literal["search", "entity"]


def accumulate(left: list | None, right: list | None) -> list:
    """Reducer: append lists. Returning None from a node resets the field to []."""
    if right is None:
        return []
    return (left or []) + list(right)


class SubQuery(TypedDict):
    id: str          # "r1-q1" = round 1, query 1
    question: str    # what to search for
    tool: Tool       # which tool to use
    entity: str      # only for tool == "entity"
    round: int


class Evidence(TypedDict):
    chunk_id: str
    source: str
    section: str
    text: str
    sub_id: str      # which sub-query found it
    tool: str        # search | entity
    score: float


class Step(TypedDict, total=False):
    node: str
    detail: str
    data: dict
    ms: int


class AgentState(TypedDict, total=False):
    # ---- conversation (persisted per thread by the checkpointer) ----
    messages: Annotated[list[AnyMessage], add_messages]
    # ---- this turn ----
    question: str                 # what the user typed
    standalone: str               # question rewritten without pronouns ("and for interns?" -> full question)
    route: Route
    route_reason: str
    direct_reply: str             # router's reply for small talk / out-of-scope
    clarify_question: str
    clarifications: int           # how many times we already asked the user
    plan: list[SubQuery]          # sub-questions of round 1
    pending: list[SubQuery]       # sub-queries to run in the next retrieval round
    rounds: int                   # retrieval rounds done
    evidence: Annotated[list[Evidence], accumulate]       # all chunks found (parallel-safe)
    tried_queries: Annotated[list[str], accumulate]       # never search the same thing twice
    relevant_ids: list[str]       # chunk_ids the assess node kept
    sufficient: bool
    answer: str
    citations: list[int]
    calculations: list[dict]      # [{"expr": "1.5*7", "value": "10.5"}]
    used_ids: list[str]           # chunk_ids given to the generator, in [n] order
    check: dict                   # {"grounded": bool, "complete": bool, "problem": str}
    regenerations: int
    feedback: str                 # self-check feedback for a regeneration
    steps: Annotated[list[Step], accumulate]              # trace for the UI
