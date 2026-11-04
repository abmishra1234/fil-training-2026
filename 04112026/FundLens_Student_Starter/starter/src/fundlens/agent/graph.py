"""The FundLens LangGraph agent.  >>> YOU BUILD THIS (Day 4-5) <<<

Nodes (see the agent graph in the requirements doc):
  input_guard -> router --out_of_scope--> refuse_safely -> audit
                       --fact/compare/policy--> retrieve_and_tools -> answer -> grounded? --no (retry<2)--> rewrite_query -> retrieve_and_tools
                                                                                          --yes--> output_guard -> audit
                       --draft--> retrieve_and_tools -> draft -> compliant? --no (rev<3)--> revise -> compliant?
                                                                            --no (rev=3)--> escalate -> human_review
                                                                            --yes--> human_review (interrupt) -> audit
Use a SQLite checkpointer so a paused draft survives an API restart, and set a recursion_limit.
"""
from __future__ import annotations


def build_graph():
    raise NotImplementedError("TODO Day 4: StateGraph(AgentState), add nodes and conditional edges, compile(checkpointer=..., interrupt_before=['human_review'])")
