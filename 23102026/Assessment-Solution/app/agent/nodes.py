"""
app/agent/nodes.py - the NODES of the agent graph.          TODO 3, 4, 5, 6, 7, 8, 9, 10, 11

A node is a function  state -> dict of updates.  A routing function (used by a
conditional edge) is a function  state -> name of the next node (or Send list).

    START → start_turn → contextualize → route ─┬─ direct ─► direct_answer ───────────────┐
                                                ├─ clarify ─► clarify (interrupt) ─► route │
                                                └─ simple / complex ─► plan                │
                                                                        │ fan_out (Send)   │
                                       ┌──────────── retrieve ×N (parallel) ◄──┘           │
                                       ▼                                                   │
                                     assess ── not sufficient & rounds left ─► retrieve ×M │
                                       │ sufficient / out of rounds                        │
                                       ▼                                                   │
                                    generate ◄── check failed & retries left ── check      │
                                       └──────────────────────────────────────► check      │
                                                                                 │ ok      │
                                                                             finalize ◄────┘ → END

Every LLM call goes through chat_complete() -> llm_client.get_client(), as in Lab 1.
"""
from __future__ import annotations

import re
import time

from langchain_core.documents import Document # type: ignore
from langchain_core.messages import AIMessage # type: ignore
from langgraph.types import Send, interrupt # type: ignore

from ..config import RagConfig
from ..gateway import CONTEXT_BLOCKED_REPLY, Guard, documents_to_passages, get_default_gateway, keep_safe
from ..generation import NOT_FOUND, build_context_block, extract_citations
from ..llm import RagError, chat_complete
from ..vector_store import InMemoryVectorStore
from . import prompts
from .config import AgentConfig
from .graph_rag import EntityGraph
from .parsing import as_bool, parse_json
from .state import AgentState, Evidence, SubQuery
from .tools import CalcError, entity_tool, safe_calculate, search_tool

ROUTES = ("direct", "clarify", "simple", "complex")
DEFAULT_DIRECT_REPLY = "Hi! I answer questions about the NovaPay employee handbook: leave, travel, hybrid work, IT, error codes, releases and on-call."
_CALC = re.compile(r"<calc>(.*?)</calc>", re.IGNORECASE | re.DOTALL)


def apply_calculations(text: str) -> tuple[str, list[dict]]:
    """PROVIDED. Replace every <calc>expr</calc> with its exact value (tool call)."""
    calcs: list[dict] = []

    def repl(m: re.Match) -> str:
        expr = m.group(1).strip()
        try:
            value = safe_calculate(expr)
            calcs.append({"expr": expr, "value": value})
            return value
        except CalcError as err:
            calcs.append({"expr": expr, "value": None, "error": str(err)})
            return f"{expr} (could not compute)"

    return _CALC.sub(repl, text or ""), calcs


def evidence_from(doc: Document, sub: SubQuery) -> Evidence:
    md = doc.metadata
    return Evidence(
        chunk_id=md["chunk_id"], source=md.get("source", ""), section=md.get("section", ""),
        text=doc.page_content, sub_id=sub["id"], tool=sub["tool"],
        score=float(md.get("rrf_score") or md.get("score") or 0.0),
    )


def unique_evidence(items: list[Evidence]) -> list[Evidence]:
    seen, out = set(), []
    for e in items or []:
        if e["chunk_id"] not in seen:
            seen.add(e["chunk_id"])
            out.append(e)
    return out


def query_key(sub: SubQuery) -> str:
    """How we remember what was already searched."""
    if sub["tool"] == "entity":
        return "entity:" + sub["entity"].lower()
    return " ".join(sub["question"].lower().split())


def passages_block(items: list[Evidence], max_chars_each: int = 500) -> str:
    return "\n\n".join(
        f"[{i}] (source: {e['source']})\n{e['text'][:max_chars_each]}" for i, e in enumerate(items, start=1)
    )


class AgentNodes:
    """All nodes, with their dependencies (vector store, entity graph, configs) as attributes."""

    def __init__(self, store: InMemoryVectorStore, graph: EntityGraph, rag_cfg: RagConfig, cfg: AgentConfig,
                 gateway: Guard | None = None):
        self.store, self.graph, self.rag_cfg, self.cfg = store, graph, rag_cfg, cfg
        self.gateway: Guard = gateway or get_default_gateway()

    @staticmethod
    def _step(node: str, detail: str, t0: float, **data) -> dict:
        return {"node": node, "detail": detail, "data": data, "ms": round((time.perf_counter() - t0) * 1000)}

    # =================================================================== PROVIDED
    def start_turn(self, state: AgentState) -> dict:
        """Reset the per-question fields (the thread's state survives between turns)."""
        return {
            "standalone": state.get("question", ""), "route": "simple", "route_reason": "", "direct_reply": "",
            "clarify_question": "", "clarifications": 0, "plan": [], "pending": [], "rounds": 0,
            "evidence": None, "tried_queries": None, "steps": None, "relevant_ids": [], "sufficient": False,
            "answer": "", "citations": [], "calculations": [], "used_ids": [], "check": {},
            "regenerations": 0, "feedback": "", "gateway_dropped": None,
        }

    def contextualize(self, state: AgentState) -> dict:
        """Memory in action: rewrite a follow-up ("and for interns?") into a standalone question."""
        t0 = time.perf_counter()
        question = state["question"]
        history = state.get("messages", [])[:-1][-self.cfg.history_messages:]
        if not history:
            return {"standalone": question, "steps": [self._step("contextualize", "first message: nothing to rewrite", t0)]}
        convo = "\n".join(f"{'User' if m.type == 'human' else 'Assistant'}: {m.content[:600]}" for m in history)
        try:
            out = chat_complete([
                {"role": "system", "content": prompts.CONTEXTUALIZE},
                {"role": "user", "content": f"Conversation:\n{convo}\n\nLatest message: {question}"},
            ]).strip().strip('"').strip()
        except RagError:
            out = ""
        standalone = out or question
        return {"standalone": standalone,
                "steps": [self._step("contextualize", f"→ {standalone}", t0, llm=1, history=len(history))]}

    def direct_answer(self, state: AgentState) -> dict:
        t0 = time.perf_counter()
        return {"answer": state.get("direct_reply") or DEFAULT_DIRECT_REPLY,
                "steps": [self._step("direct_answer", "answered without retrieval", t0)]}

    def finalize(self, state: AgentState) -> dict:
        t0 = time.perf_counter()
        answer = state.get("answer") or NOT_FOUND
        return {"answer": answer, "messages": [AIMessage(content=answer)],
                "steps": [self._step("finalize", "answer saved to conversation memory", t0)]}

    # =================================================================== TODO 3
    def route(self, state: AgentState) -> dict:
        """
        Decide HOW to handle the question (Adaptive RAG). One LLM call.

        * messages: system = prompts.ROUTER, user =
              f"ALREADY_CLARIFIED: {'yes' if state.get('clarifications') else 'no'}\\nQuestion: {state['standalone']}"
        * parse the reply with parse_json(). Then validate:
            - route not in ROUTES (or unparsable reply)      -> "simple"   (when unsure, retrieve)
            - route == "clarify" but clarifications >= 1      -> "simple"   (ask at most once)
            - route == "clarify" but no clarify_question      -> "simple"
            - route == "direct" with no reply                 -> reply = DEFAULT_DIRECT_REPLY
        * chat_complete raises RagError -> route "simple", reason "router unavailable".
        * return {"route", "route_reason", "direct_reply", "clarify_question",
                  "steps": [self._step("route", f"{route}: {reason}", t0, llm=1)]}
        """
        # >>> SOLUTION
        t0 = time.perf_counter()
        user = f"ALREADY_CLARIFIED: {'yes' if state.get('clarifications') else 'no'}\nQuestion: {state['standalone']}"
        try:
            data = parse_json(chat_complete([
                {"role": "system", "content": prompts.ROUTER}, {"role": "user", "content": user},
            ])) or {}
            reason = str(data.get("reason", "")).strip()
        except RagError:
            data, reason = {}, "router unavailable"
        route = str(data.get("route", "")).strip().lower()
        reply = str(data.get("reply") or "").strip()
        clarify_q = str(data.get("clarify_question") or "").strip()
        if route not in ROUTES:
            route, reason = "simple", reason or "could not parse router reply"
        if route == "clarify" and (state.get("clarifications", 0) >= 1 or not clarify_q):
            route = "simple"
        if route == "direct" and not reply:
            reply = DEFAULT_DIRECT_REPLY
        return {
            "route": route, "route_reason": reason, "direct_reply": reply if route == "direct" else "",
            "clarify_question": clarify_q if route == "clarify" else "",
            "steps": [self._step("route", f"{route}: {reason}", t0, llm=1)],
        }
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 3: implement AgentNodes.route() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 4
    def after_route(self, state: AgentState) -> str:
        """
        Conditional edge after `route`:  "direct" -> "direct_answer",
        "clarify" -> "clarify", "simple" / "complex" (or anything else) -> "plan".
        """
        # >>> SOLUTION
        return {"direct": "direct_answer", "clarify": "clarify"}.get(state.get("route"), "plan")
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 4: implement AgentNodes.after_route() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 11
    def clarify(self, state: AgentState) -> dict:
        """
        Human-in-the-loop. Pause the graph and ask the user.

        * answer = interrupt({"question": state["clarify_question"], "original": state["standalone"]})
          The graph STOPS here and is saved by the checkpointer. The API returns the
          question to the browser. When the user replies, the API calls
          graph.invoke(Command(resume="<their answer>"), config) and interrupt()
          RETURNS that answer. (The node re-runs from its first line on resume,
          so do nothing with side effects before interrupt().)
        * return {"standalone": f"{state['standalone']} ({answer})",   # stripped answer
                  "clarifications": state.get("clarifications", 0) + 1,
                  "steps": [self._step("clarify", f"user said: {answer}", t0)]}
          The graph then goes back to `route` with the clarified question.
        """
        # >>> SOLUTION
        t0 = time.perf_counter()
        answer = str(interrupt({"question": state.get("clarify_question", ""), "original": state.get("standalone", "")}) or "").strip()
        return {
            "standalone": f"{state['standalone']} ({answer})" if answer else state["standalone"],
            "clarifications": state.get("clarifications", 0) + 1,
            "steps": [self._step("clarify", f"user said: {answer}", t0)],
        }
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 11: implement AgentNodes.clarify() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 5
    def plan(self, state: AgentState) -> dict:
        """
        Break the question into sub-queries (query planning / decomposition).

        * route == "simple": NO LLM call. One SubQuery: id "r1-q1", the standalone
          question, tool "search", entity "", round 1.
        * route == "complex": one LLM call with
              system = prompts.PLANNER.format(max_sub=self.cfg.max_subquestions,
                                              entities=", ".join(self.graph.entities[:40]))
              user   = state["standalone"]
          From data["sub_questions"] build SubQuery dicts, validating each item:
            - skip items that are not dicts or have an empty "question"
            - tool must be "search" or "entity", otherwise "search"
            - tool "entity": entity = self.graph.resolve(item["entity"]); if None -> tool "search", entity ""
            - skip duplicates (same query_key())
            - keep at most self.cfg.max_subquestions; ids "r1-q1", "r1-q2", ...
          Nothing valid (or RagError) -> fall back to the simple single sub-query.
        * return {"plan": subs, "pending": subs, "rounds": 0,
                  "steps": [self._step("plan", f"{len(subs)} sub-question(s)", t0, llm=0 or 1, plan=subs)]}
        """
        # >>> SOLUTION
        t0 = time.perf_counter()
        q = state["standalone"]
        simple = [SubQuery(id="r1-q1", question=q, tool="search", entity="", round=1)]
        if state.get("route") != "complex":
            return {"plan": simple, "pending": simple, "rounds": 0,
                    "steps": [self._step("plan", "simple question: 1 search, no planning call", t0, llm=0, plan=simple)]}
        system = prompts.PLANNER.format(max_sub=self.cfg.max_subquestions, entities=", ".join(self.graph.entities[:40]))
        try:
            data = parse_json(chat_complete([{"role": "system", "content": system}, {"role": "user", "content": q}])) or {}
        except RagError:
            data = {}
        subs: list[SubQuery] = []
        seen: set[str] = set()
        for item in data.get("sub_questions") or []:
            if not isinstance(item, dict) or not str(item.get("question") or "").strip():
                continue
            tool = item.get("tool") if item.get("tool") in ("search", "entity") else "search"
            entity = ""
            if tool == "entity":
                entity = self.graph.resolve(str(item.get("entity") or "")) or ""
                if not entity:
                    tool = "search"
            sub = SubQuery(id=f"r1-q{len(subs) + 1}", question=str(item["question"]).strip(), tool=tool, entity=entity, round=1)
            if query_key(sub) in seen:
                continue
            seen.add(query_key(sub))
            subs.append(sub)
            if len(subs) >= self.cfg.max_subquestions:
                break
        if not subs:
            subs = simple
        return {"plan": subs, "pending": subs, "rounds": 0,
                "steps": [self._step("plan", f"{len(subs)} sub-question(s)", t0, llm=1, plan=subs)]}
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 5: implement AgentNodes.plan() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 6
    def fan_out(self, state: AgentState):
        """
        Conditional edge after `plan` (and reused by after_assess): map-reduce with Send.

        For every SubQuery in state["pending"] whose query_key() is NOT already in
        state["tried_queries"], create  Send("retrieve", {"sub": sub}).
        LangGraph runs all those `retrieve` nodes IN PARALLEL in one step, then
        continues to `assess` once.
        Return the list of Send objects, or "generate" if there is nothing new to search.
        """
        # >>> SOLUTION
        tried = set(state.get("tried_queries") or [])
        sends = [Send("retrieve", {"sub": s}) for s in state.get("pending") or [] if query_key(s) not in tried]
        return sends or "generate"
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 6: implement AgentNodes.fan_out() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 7
    def retrieve(self, payload: dict) -> dict:
        """
        Run ONE sub-query with the tool the planner chose. Receives the Send
        payload {"sub": SubQuery}, NOT the whole state.

        * tool "entity": docs, info = entity_tool(self.graph, sub["entity"])
          if no docs -> fall back to the search tool
        * tool "search": docs = search_tool(self.store, sub["question"], self.rag_cfg, self.cfg.search_mode)
        * return {"evidence": [evidence_from(d, sub) for d in docs],
                  "tried_queries": [query_key(sub)],
                  "steps": [self._step("retrieve", f"{tool}: {what} -> {len(docs)} chunks", t0,
                                       sub_id=sub["id"], tool=tool_used, chunks=[chunk_ids])]}
          Because `evidence` has a reducer, parallel retrieve nodes do not overwrite each other.
        """
        # >>> SOLUTION
        t0 = time.perf_counter()
        sub: SubQuery = payload["sub"]
        docs, tool_used, what, extra = [], sub["tool"], sub["question"], {}
        if sub["tool"] == "entity":
            docs, info = entity_tool(self.graph, sub["entity"])
            what = sub["entity"]
            if info:
                extra = {"documents": info["documents"], "neighbours": info["neighbours"]}
        if not docs:
            tool_used, what = "search", sub["question"]
            docs = search_tool(self.store, sub["question"], self.rag_cfg, self.cfg.search_mode)
        # Mini AI Gateway: evidence enters the state ONLY after the check, so assess /
        # generate / check (all LLM calls) never see a secret. Fail closed: drop all.
        try:
            verdict = self.gateway.check(sub["question"], documents_to_passages(docs))
            safe = keep_safe(docs, verdict)
        except Exception:  # noqa: BLE001
            safe = []
        safe_ids = {d.metadata["chunk_id"] for d in safe}
        dropped = [d.metadata["chunk_id"] for d in docs if d.metadata["chunk_id"] not in safe_ids]
        docs = safe
        return {
            "evidence": [evidence_from(d, sub) for d in docs],
            "tried_queries": [query_key(sub)],
            "gateway_dropped": dropped,
            "steps": [self._step("retrieve", f"{tool_used}: {what} → {len(docs)} chunks"
                                 + (f" · gateway dropped {len(dropped)}" if dropped else ""), t0,
                                 sub_id=sub["id"], tool=tool_used, chunks=[d.metadata["chunk_id"] for d in docs],
                                 gateway_dropped=dropped, **extra)],
        }
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 7: implement AgentNodes.retrieve() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 8
    def assess(self, state: AgentState) -> dict:
        """
        Corrective RAG: grade what we found, decide if it is enough, plan follow-ups.

        * rounds = state.get("rounds", 0) + 1
        * items = unique_evidence(state["evidence"])[:16]
        * no items -> relevant_ids [], sufficient False, pending [] (no LLM call)
        * otherwise one LLM call: system = prompts.ASSESS,
              user = f"Question: {state['standalone']}\\n\\nPassages:\\n{passages_block(items)}"
          - "relevant": passage NUMBERS (1-based); ignore numbers out of range or not ints
          - "sufficient": as_bool(...)
          - "missing": up to 2 non-empty strings -> new SubQuery(id f"r{rounds+1}-q{i}",
             tool "search", entity "", round rounds+1), skipping ones already in tried_queries
        * FAIL OPEN: unparsable reply or RagError -> all items relevant, sufficient True.
        * return {"rounds", "relevant_ids", "sufficient", "pending",
                  "steps": [self._step("assess", "...", t0, llm=1, relevant=..., missing=[...])]}
        """
        # >>> SOLUTION
        t0 = time.perf_counter()
        rounds = state.get("rounds", 0) + 1
        items = unique_evidence(state.get("evidence"))[:16]
        if not items:
            return {"rounds": rounds, "relevant_ids": [], "sufficient": False, "pending": [],
                    "steps": [self._step("assess", "nothing retrieved", t0, llm=0)]}
        try:
            data = parse_json(chat_complete([
                {"role": "system", "content": prompts.ASSESS},
                {"role": "user", "content": f"Question: {state['standalone']}\n\nPassages:\n{passages_block(items)}"},
            ]))
        except RagError:
            data = None
        if not data:
            ids = [e["chunk_id"] for e in items]
            return {"rounds": rounds, "relevant_ids": ids, "sufficient": True, "pending": [],
                    "steps": [self._step("assess", "grader unavailable: keeping everything", t0, llm=1)]}
        nums = []
        for n in data.get("relevant") or []:
            if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(items) and n not in nums:
                nums.append(n)
        relevant = [items[n - 1]["chunk_id"] for n in nums]
        sufficient = as_bool(data.get("sufficient"))
        tried = set(state.get("tried_queries") or [])
        pending: list[SubQuery] = []
        for m in data.get("missing") or []:
            if not isinstance(m, str) or not m.strip():
                continue
            sub = SubQuery(id=f"r{rounds + 1}-q{len(pending) + 1}", question=m.strip(), tool="search", entity="", round=rounds + 1)
            if query_key(sub) not in tried and all(query_key(p) != query_key(sub) for p in pending):
                pending.append(sub)
            if len(pending) >= 2:
                break
        detail = f"{len(relevant)}/{len(items)} relevant · " + ("sufficient" if sufficient else f"missing: {len(pending)} follow-up(s)")
        return {"rounds": rounds, "relevant_ids": relevant, "sufficient": sufficient, "pending": pending,
                "steps": [self._step("assess", detail, t0, llm=1, relevant=relevant, missing=[p["question"] for p in pending])]}
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 8: implement AgentNodes.assess() in app/agent/nodes.py")
        # <<< STARTER

    def after_assess(self, state: AgentState):
        """
        TODO 8 (part 2). Conditional edge after `assess`:
          sufficient, or rounds >= self.cfg.max_rounds, or no pending -> "generate"
          otherwise -> self.fan_out(state)   (Send list for the follow-up queries)
        This is the LOOP that gives multi-hop retrieval, bounded by max_rounds.
        """
        # >>> SOLUTION
        if state.get("sufficient") or state.get("rounds", 0) >= self.cfg.max_rounds or not state.get("pending"):
            return "generate"
        return self.fan_out(state)
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 8: implement AgentNodes.after_assess() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 9
    def generate(self, state: AgentState) -> dict:
        """
        Write the answer from the RELEVANT evidence, with the calculator tool.

        * items = [e for e in unique_evidence(state["evidence"]) if e["chunk_id"] in relevant_ids]
          (keep evidence order), at most self.cfg.max_context_chunks
        * no items -> answer NOT_FOUND, citations [], calculations [], used_ids [] (NO LLM call)
        * docs = [Document(page_content=e["text"], metadata={"chunk_id":..., "source":...})]
          context, used = build_context_block(docs, self.rag_cfg.max_context_chars)   (Lab 1!)
        * user = f"Context passages:\\n{context}\\n\\nQuestion: {state['standalone']}"
          if state.get("feedback"): append
              f"\\n\\nA reviewer found a problem in your previous answer. Fix it: {feedback}"
          raw = chat_complete([system = prompts.ANSWER, user])
        * answer, calcs = apply_calculations(raw); empty answer -> NOT_FOUND
        * citations = extract_citations(answer, len(used))                          (Lab 1!)
        * return {"answer", "citations", "calculations": calcs,
                  "used_ids": [d.metadata["chunk_id"] for d in used],
                  "steps": [self._step("generate", "...", t0, llm=1, calculations=calcs)]}
        """
        # >>> SOLUTION
        t0 = time.perf_counter()
        relevant = set(state.get("relevant_ids") or [])
        items = [e for e in unique_evidence(state.get("evidence")) if e["chunk_id"] in relevant][: self.cfg.max_context_chunks]
        if not items:
            blocked = bool(state.get("gateway_dropped"))  # everything found was withheld by the gateway
            return {"answer": CONTEXT_BLOCKED_REPLY if blocked else NOT_FOUND, "citations": [], "calculations": [], "used_ids": [],
                    "steps": [self._step("generate", "all passages withheld by gateway" if blocked
                                         else "no relevant evidence: not found", t0, llm=0)]}
        docs = [Document(page_content=e["text"], metadata={"chunk_id": e["chunk_id"], "source": e["source"]}) for e in items]
        context, used = build_context_block(docs, self.rag_cfg.max_context_chars)
        user = f"Context passages:\n{context}\n\nQuestion: {state['standalone']}"
        if state.get("feedback"):
            user += f"\n\nA reviewer found a problem in your previous answer. Fix it: {state['feedback']}"
        raw = chat_complete([{"role": "system", "content": prompts.ANSWER}, {"role": "user", "content": user}])
        answer, calcs = apply_calculations(raw)
        answer = answer.strip() or NOT_FOUND
        detail = f"{len(used)} passages" + (f" · {len(calcs)} calculation(s)" if calcs else "")
        if state.get("feedback"):
            detail = "rewrite after self-check · " + detail
        return {"answer": answer, "citations": extract_citations(answer, len(used)), "calculations": calcs,
                "used_ids": [d.metadata["chunk_id"] for d in used],
                "steps": [self._step("generate", detail, t0, llm=1, calculations=calcs)]}
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 9: implement AgentNodes.generate() in app/agent/nodes.py")
        # <<< STARTER

    # =================================================================== TODO 10
    def check(self, state: AgentState) -> dict:
        """
        Self-RAG style self-check: is the answer grounded and complete?

        * Skip (no LLM call) when self.cfg.check_answer is False, when used_ids is
          empty, or when the answer is NOT_FOUND:
              check = {"grounded": True, "complete": True, "retry": False, "skipped": True}
        * Otherwise one LLM call: system = prompts.CHECK, user =
              f"Passages:\\n{passages_block(used items, 800)}\\n\\nQuestion: {standalone}\\n\\nAnswer:\\n{answer}"
          (used items = the evidence whose chunk_id is in used_ids, in used_ids order)
          unparsable / RagError -> treat as passed.
        * retry = (not grounded or not complete) and regenerations < self.cfg.max_regenerations
        * return {"check": {"grounded", "complete", "problem", "retry"},
                  "regenerations": regenerations + (1 if retry else 0),
                  "feedback": problem if retry else "",
                  "steps": [...]}
        """
        # >>> SOLUTION
        t0 = time.perf_counter()
        used_ids = state.get("used_ids") or []
        if not self.cfg.check_answer or not used_ids or state.get("answer") == NOT_FOUND:
            return {"check": {"grounded": True, "complete": True, "retry": False, "skipped": True}, "feedback": "",
                    "steps": [self._step("check", "skipped", t0, llm=0)]}
        by_id = {e["chunk_id"]: e for e in unique_evidence(state.get("evidence"))}
        used = [by_id[c] for c in used_ids if c in by_id]
        user = f"Passages:\n{passages_block(used, 800)}\n\nQuestion: {state['standalone']}\n\nAnswer:\n{state['answer']}"
        try:
            data = parse_json(chat_complete([{"role": "system", "content": prompts.CHECK}, {"role": "user", "content": user}])) or {}
        except RagError:
            data = {}
        grounded = as_bool(data.get("grounded"), True)
        complete = as_bool(data.get("complete"), True)
        problem = str(data.get("problem") or "").strip()
        regen = state.get("regenerations", 0)
        retry = (not grounded or not complete) and regen < self.cfg.max_regenerations
        verdict = "passed" if grounded and complete else ("retry: " + problem if retry else "failed, no retries left")
        return {"check": {"grounded": grounded, "complete": complete, "problem": problem, "retry": retry},
                "regenerations": regen + (1 if retry else 0), "feedback": problem if retry else "",
                "steps": [self._step("check", verdict, t0, llm=1, grounded=grounded, complete=complete)]}
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 10: implement AgentNodes.check() in app/agent/nodes.py")
        # <<< STARTER

    def after_check(self, state: AgentState) -> str:
        """TODO 10 (part 2). "generate" if state["check"]["retry"] else "finalize"."""
        # >>> SOLUTION
        return "generate" if (state.get("check") or {}).get("retry") else "finalize"
        # <<< SOLUTION
        # >>> STARTER
        # raise NotImplementedError("TODO 10: implement AgentNodes.after_check() in app/agent/nodes.py")
        # <<< STARTER
