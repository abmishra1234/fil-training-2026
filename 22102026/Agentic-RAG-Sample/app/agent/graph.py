"""
app/agent/graph.py - wire the nodes into a LangGraph StateGraph.        TODO 12

    START → start_turn → contextualize → route
    route    ──after_route──►  direct_answer | clarify | plan
    clarify  → route                         (after the human answered)
    direct_answer → finalize
    plan     ──fan_out──────►  retrieve (×N, parallel via Send) | generate
    retrieve → assess
    assess   ──after_assess─►  retrieve (×M, follow-up round)  | generate
    generate → check
    check    ──after_check──►  generate (one rewrite)          | finalize
    finalize → END
"""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver # type: ignore
from langgraph.graph import END, START, StateGraph # type: ignore

from .nodes import AgentNodes
from .state import AgentState


def build_graph(nodes: AgentNodes, checkpointer=None):
    """
    1. g = StateGraph(AgentState)
    2. add_node() for: start_turn, contextualize, route, clarify, direct_answer,
       plan, retrieve, assess, generate, check, finalize   (use the AgentNodes methods)
    3. plain edges (add_edge) and conditional edges (add_conditional_edges) exactly as
       in the diagram above. Give every conditional edge its list of possible targets,
       e.g. g.add_conditional_edges("plan", nodes.fan_out, ["retrieve", "generate"]),
       so LangGraph can draw the graph and validate it.
    4. return g.compile(checkpointer=checkpointer or InMemorySaver())
       The checkpointer saves the state after every step, per thread_id. That gives
       conversation memory AND makes interrupt() (human-in-the-loop) possible.
    """
    # >>> SOLUTION
    g = StateGraph(AgentState)
    for name in ("start_turn", "contextualize", "route", "clarify", "direct_answer",
                 "plan", "retrieve", "assess", "generate", "check", "finalize"):
        g.add_node(name, getattr(nodes, name))
    g.add_edge(START, "start_turn")
    g.add_edge("start_turn", "contextualize")
    g.add_edge("contextualize", "route")
    g.add_conditional_edges("route", nodes.after_route, ["direct_answer", "clarify", "plan"])
    g.add_edge("clarify", "route")
    g.add_edge("direct_answer", "finalize")
    g.add_conditional_edges("plan", nodes.fan_out, ["retrieve", "generate"])
    g.add_edge("retrieve", "assess")
    g.add_conditional_edges("assess", nodes.after_assess, ["retrieve", "generate"])
    g.add_edge("generate", "check")
    g.add_conditional_edges("check", nodes.after_check, ["generate", "finalize"])
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
    # <<< SOLUTION
    # >>> STARTER
    # raise NotImplementedError("TODO 12: implement build_graph() in app/agent/graph.py")
    # <<< STARTER
