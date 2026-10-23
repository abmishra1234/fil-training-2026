"""
app/agent/service.py - PROVIDED. Runs the graph for the API: one call per user
message, resume after a clarification, or stream node-by-node updates.
"""
from __future__ import annotations

import uuid
from typing import Iterator

from langchain_core.messages import HumanMessage # type: ignore
from langgraph.errors import GraphRecursionError # type: ignore
from langgraph.types import Command # type: ignore

from ..generation import NOT_FOUND
from ..llm import RagError
from ..pipeline import RagService
from .config import AgentConfig, load_agent_config
from .graph import build_graph
from .graph_rag import EntityGraph
from .nodes import AgentNodes, unique_evidence


class AgentService:
    def __init__(self, rag: RagService, cfg: AgentConfig | None = None):
        self.rag = rag
        self.cfg = cfg or load_agent_config()
        self._built_for: str | None = None
        self.graph = None
        self.entity_graph: EntityGraph | None = None
        self._ensure()

    def _ensure(self):
        """(Re)build the entity graph + LangGraph app when the index changed."""
        stamp = f"{self.rag.indexed_at}|{self.rag.store.size}"
        if stamp == self._built_for and self.graph is not None:
            return
        self.entity_graph = EntityGraph.build(list(self.rag.store.docs.values()))
        nodes = AgentNodes(self.rag.store, self.entity_graph, self.rag.cfg, self.cfg)
        try:
            self.graph = build_graph(nodes)  # new InMemorySaver: conversations reset after re-index
            self.not_ready = ""
        except NotImplementedError as err:  # student starter: TODO 12 not done yet
            self.graph, self.not_ready = None, str(err)
        self._built_for = stamp

    def _require_graph(self):
        self._ensure()
        if self.graph is None:
            raise RagError(501, f"Agent not ready yet: {self.not_ready}", "Implement the Lab 2 TODOs (suggested order: TODO 1-2, 12, then 3-11) and run pytest.")

    def _config(self, thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": self.cfg.recursion_limit}

    # ------------------------------------------------------------------ run
    def ask(self, question: str, thread_id: str | None = None) -> dict:
        self.rag._require_index()
        self._require_graph()
        thread_id = thread_id or uuid.uuid4().hex
        return self._run({"question": question, "messages": [HumanMessage(content=question)]}, thread_id)

    def resume(self, thread_id: str, answer: str) -> dict:
        self._require_graph()
        if not self._pending_interrupt(thread_id):
            raise RagError(409, "This conversation is not waiting for a clarification.", "Send a normal question instead.")
        return self._run(Command(resume=answer), thread_id)

    def _run(self, graph_input, thread_id: str) -> dict:
        emb0 = getattr(self.rag.embeddings, "calls", 0)
        try:
            self.graph.invoke(graph_input, self._config(thread_id))
        except GraphRecursionError:
            raise RagError(500, "The agent took too many steps.", "Raise AGENT_RECURSION_LIMIT or lower AGENT_MAX_ROUNDS.") from None
        except NotImplementedError as err:
            raise RagError(501, f"Agent not ready yet: {err}", "Implement the Lab 2 TODOs and run pytest.") from None
        out = self.result(thread_id)
        out["embedding_calls"] = getattr(self.rag.embeddings, "calls", 0) - emb0
        return out

    def stream(self, question: str | None, thread_id: str | None, resume: str | None = None) -> Iterator[dict]:
        """Yields {"type": "step", ...} per node update, then {"type": "final", ...}."""
        self.rag._require_index()
        self._require_graph()
        thread_id = thread_id or uuid.uuid4().hex
        graph_input = Command(resume=resume) if resume is not None else {"question": question, "messages": [HumanMessage(content=question)]}
        emb0 = getattr(self.rag.embeddings, "calls", 0)
        yield {"type": "start", "thread_id": thread_id}
        try:
            for update in self.graph.stream(graph_input, self._config(thread_id), stream_mode="updates"):
                for node, delta in update.items():
                    if node == "__interrupt__":
                        continue
                    for step in (delta or {}).get("steps") or []:
                        yield {"type": "step", **step}
        except NotImplementedError as err:
            yield {"type": "error", "status": 501, "detail": f"Agent not ready yet: {err}", "hint": "Implement the Lab 2 TODOs."}
            return
        except GraphRecursionError:
            yield {"type": "error", "status": 500, "detail": "The agent took too many steps.", "hint": "Raise AGENT_RECURSION_LIMIT."}
            return
        except RagError as err:
            yield {"type": "error", "status": err.status, "detail": err.message, "hint": err.hint}
            return
        yield {"type": "final", **self.result(thread_id), "embedding_calls": getattr(self.rag.embeddings, "calls", 0) - emb0}

    # --------------------------------------------------------------- results
    def _pending_interrupt(self, thread_id: str):
        snap = self.graph.get_state(self._config(thread_id))
        for task in snap.tasks or ():
            for intr in getattr(task, "interrupts", ()) or ():
                return intr.value
        return None

    def result(self, thread_id: str) -> dict:
        snap = self.graph.get_state(self._config(thread_id))
        s = snap.values or {}
        pending = self._pending_interrupt(thread_id)
        evidence = unique_evidence(s.get("evidence"))
        by_id = {e["chunk_id"]: e for e in evidence}
        used = [by_id[c] for c in s.get("used_ids") or [] if c in by_id]
        cited = set(s.get("citations") or [])
        steps = s.get("steps") or []
        return {
            "thread_id": thread_id,
            "status": "needs_clarification" if pending else "done",
            "clarify_question": (pending or {}).get("question", "") if pending else "",
            "question": s.get("question", ""),
            "standalone": s.get("standalone", ""),
            "route": s.get("route", ""),
            "route_reason": s.get("route_reason", ""),
            "answer": "" if pending else (s.get("answer") or NOT_FOUND),
            "plan": s.get("plan") or [],
            "rounds": s.get("rounds", 0),
            "evidence_count": len(evidence),
            "relevant_count": len(s.get("relevant_ids") or []),
            "sources": [
                {"n": i, "chunk_id": e["chunk_id"], "source": e["source"], "section": e["section"],
                 "text": e["text"], "tool": e["tool"], "sub_id": e["sub_id"], "cited": i in cited}
                for i, e in enumerate(used, start=1)
            ],
            "citations": sorted(cited),
            "calculations": s.get("calculations") or [],
            "check": s.get("check") or {},
            "regenerations": s.get("regenerations", 0),
            "steps": steps,
            "llm_calls": sum(int((st.get("data") or {}).get("llm", 0)) for st in steps),
            "turns": sum(1 for m in s.get("messages") or [] if m.type == "human"),
        }

    def mermaid(self) -> str:
        self._require_graph()
        return self.graph.get_graph().draw_mermaid()
