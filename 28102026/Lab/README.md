# RAG Lab · Lab 3: Vectorless RAG (on top of Lab 2: Agentic RAG and Lab 1: Basic RAG → MQR → RRF)

> **Observability (new).** Every LLM call, pipeline step and API request is traced with
> OpenTelemetry and lands in **LangSmith** - inside FIL via the `fil-aiobs` SDK and the
> FIL AI Observability endpoint. Configure the `OBS_*` block in `.env`, then run
> `python 01_check_observability.py`. Details: **[OBSERVABILITY.md](OBSERVABILITY.md)**.

> **New in Lab 3.** A fourth retrieval mode, **Vectorless**, that uses no embeddings and no
> vector database. The handbook's own outline becomes a tree index; `azure/gpt-6-luna` reads the
> document titles and one-line summaries, opens the right documents, picks the right sections, and
> reads them in full. The Compare and Evaluate tabs now put all four modes side by side, with
> **cost per mode** (LLM calls, embedding calls, latency, context size) next to quality.
> Exercise sheet: **[LAB3_VECTORLESS.md](LAB3_VECTORLESS.md)**.
>
> | TODO | File | What |
> |---|---|---|
> | V1 | `app/vectorless/tree.py` | `build_tree()`: Markdown headings → tree (no LLM) |
> | V2 | `app/vectorless/tree.py` | `summarize_document()`: one LLM call writes every signpost of a document |
> | V3 | `app/vectorless/navigator.py` | `parse_selection()`: validate the ids the LLM picked |
> | V4 | `app/vectorless/navigator.py` | `tree_search()`: the navigation loop, with a BM25 safety net |
>
> Lab 3 starter: `pytest` → **14 failed, 50 passed**. Done = **64 passed**.
> New endpoints: `GET /api/tree`, `POST /api/tree/summarize {mode: llm|extractive|none}`;
> `/api/chat` and `/api/compare` accept `mode: "vectorless"`.

---

## Lab 2 · Agentic RAG with LangGraph (on top of Lab 1: Basic RAG → MQR → RRF)

FIL Graduate AI Cohort · full-stack GenAI lab (FastAPI + LangChain + **LangGraph** + FAISS + React).

Lab 1 made retrieval better (MQR for recall, RRF for precision). But the pipeline
is still a **fixed, one-shot chain**: it always retrieves, never checks whether it
found the right thing, cannot do a second hop, cannot calculate, forgets the last
question, and cannot ask back. In Lab 2 you turn it into an **agent**: a
LangGraph state machine where the LLM decides *whether*, *what*, *how* and
*how much* to retrieve, and checks its own work.

Everything from Lab 1 stays and is **reused as tools** (FAISS store, BM25, RRF,
grounded prompt, citations). The Lab 1 tabs still work, so you can compare.

### What the agent does

```
 START → start_turn → contextualize → route ─┬─ direct ──► direct_answer ──────────────────┐
         (reset turn)  (memory: rewrite      ├─ clarify ─► clarify ⏸ interrupt ─► route     │
                        follow-ups)          └─ simple / complex ─► plan                    │
                                                                     │ fan_out (Send)       │
                                  ┌──────── retrieve ×N (parallel: search | entity) ◄┘      │
                                  ▼                                                         │
                                assess ── not enough & rounds left ─► retrieve ×M (next hop)│
                                  │ enough / out of rounds                                  │
                                  ▼                                                         │
                               generate (+ calculator) ◄── self-check failed (1 retry) ─ check
                                  └────────────────────────────────────────────────► check │
                                                                                      │ ok  │
                                                                                  finalize ◄┘ → END
```

| Lab 1 weakness | Agent feature | LangGraph feature used |
|---|---|---|
| Always retrieves (even "hi", or a Python question) | `route` → direct answer | conditional edges |
| Vague questions get a guess | `clarify` asks once, then resumes | `interrupt()` + `Command(resume=…)` + checkpointer |
| One shot: no second hop | `assess` grades chunks and asks for follow-up searches | cycles (bounded loop) |
| Multi-part questions share one top-5 | `plan` splits; sub-queries run in parallel | `Send` (map-reduce) + reducers |
| Top-k cannot "list every rule for X" | `entity` tool = Graph RAG lite | tool choice inside a node |
| LLM does arithmetic in its head | `<calc>` calculator tool | — |
| Never checks the answer | `check` (grounded? complete?) → one rewrite | cycles |
| Forgets the previous question | `contextualize` + chat history per thread | `add_messages` + checkpointer + `thread_id` |
| Black box | live node-by-node trace in the UI | `stream(stream_mode="updates")` |

### Setup and run

Same as Lab 1:

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                         # now includes langgraph
cp .env.example .env                                    # fill the enterprise block
python 00_check_setup.py
python 01_check_observability.py                        # traces visible in LangSmith?
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000 → **Agentic RAG** tab. Try the 8 scenario buttons; under
each answer press **Compare with MQR + RRF** to see what Lab 1 does with the same question.

### Your tasks (Lab 2 student starter)

`pytest` starts at **22 failed, 28 passed** (the 25 Lab 1 regression tests and the 3
Graph RAG lite tests pass because that code is provided). Suggested order:

| TODO | File | What |
|---|---|---|
| 1 | `app/agent/tools.py` | `safe_calculate()`: an AST calculator, never `eval()` |
| 2 | `app/agent/tools.py` | `hybrid_search()`: semantic + BM25 over the whole corpus, fused with RRF |
| 12 | `app/agent/graph.py` | `build_graph()`: wire the StateGraph, compile with a checkpointer |
| 3–4 | `app/agent/nodes.py` | `route()` + `after_route()`: Adaptive RAG |
| 5–6 | `app/agent/nodes.py` | `plan()` + `fan_out()`: decomposition and parallel `Send` |
| 7 | `app/agent/nodes.py` | `retrieve()`: run one sub-query with the chosen tool |
| 8 | `app/agent/nodes.py` | `assess()` + `after_assess()`: Corrective RAG loop, multi-hop |
| 9 | `app/agent/nodes.py` | `generate()`: grounded answer + calculator |
| 10 | `app/agent/nodes.py` | `check()` + `after_check()`: self-check with one retry |
| 11 | `app/agent/nodes.py` | `clarify()`: human-in-the-loop with `interrupt()` |

Done = `pytest` shows **50 passed** and the 8 scenarios behave as described in
`data/agent_scenarios.json`.

### Project map (new in Lab 2)

| File | What it is | Edit? |
|---|---|---|
| `app/agent/state.py` | `AgentState` TypedDict, reducers (`add_messages`, `accumulate`) | no |
| `app/agent/prompts.py` | one prompt per decision, JSON replies | no (stretch: tune) |
| `app/agent/parsing.py` | defensive JSON parsing | no |
| `app/agent/graph_rag.py` | Graph RAG lite: entity graph over the chunks | no |
| `app/agent/tools.py` | search / entity / calculator tools | **TODO 1–2** |
| `app/agent/nodes.py` | every node and routing function | **TODO 3–11** |
| `app/agent/graph.py` | StateGraph wiring | **TODO 12** |
| `app/agent/service.py`, `routes.py` | run / resume / stream, HTTP API | no |
| `data/agent_scenarios.json` | 8 questions that each show one Lab 1 weakness | stretch |
| `tests/test_agent_*.py` | 25 agent tests (fake LLM, offline, free) | no |

### API

| Method | Path | Body / result |
|---|---|---|
| POST | `/api/agent/chat` | `{question, thread_id?}` → answer, or `status: needs_clarification` |
| POST | `/api/agent/resume` | `{thread_id, answer}` |
| POST | `/api/agent/stream` | `{question` or `resume, thread_id?}` → Server-Sent Events, one per node |
| GET | `/api/agent/graph` | Mermaid text of the compiled graph |
| GET | `/api/graph/entity/{name}` | Graph RAG lite lookup |

### Cost and safety rails (.env)

`AGENT_MAX_ROUNDS=2`, `AGENT_MAX_REGENERATIONS=1`, `AGENT_MAX_SUBQUESTIONS=3`,
`AGENT_RECURSION_LIMIT=40`. Typical LLM calls per question: direct 1, simple 4–5,
complex 5–7 (Lab 1 MQR + RRF: always 2). Same gateway limits as before: 200 requests
per minute per credential, $50 per month.

### Troubleshooting

| Symptom | Fix |
|---|---|
| "Agent not ready yet (501)" | Expected in the starter until TODO 12 and the nodes are implemented. |
| `InvalidUpdateError ... can receive only one value per step` | A field written by the parallel `retrieve` nodes has no reducer. |
| `GraphRecursionError` | A loop without an exit: `after_assess` / `after_check` must respect the limits. |
| Clarification never resumes | Graph compiled without a checkpointer, or a different `thread_id` was sent. |
| Router always says "simple" | Look at the trace: the model may not be returning JSON, so `parse_json` falls back. |
