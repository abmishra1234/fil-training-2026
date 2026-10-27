# Trainer notes: Lab 2 · Agentic RAG with LangGraph · TRAINER ZIP ONLY

## Before class

1. Unzip the trainer zip, `pip install -r requirements.txt` (adds `langgraph`), fill `.env` (enterprise).
2. `python 00_check_setup.py` → All good. `pytest` → **50 passed**.
3. Run the app and click all 8 scenarios in the **Agentic RAG** tab with the real gateway. For each,
   also press **Compare with MQR + RRF**. Screenshot the best 3 pairs for the debrief.
4. Check that `azure/gpt-6-luna` returns usable JSON for ROUTE / PLAN / ASSESS / CHECK. In the trace,
   "could not parse router reply" or "grader unavailable" means it did not. JSON wrapped in prose
   or ```json fences is fine: `parse_json` handles it.
5. Unzip the student zip: the app starts, the Agentic tab answers 501 "TODO 12", the Lab 1 tabs work,
   `pytest` → **22 failed, 28 passed**.

## What was and was not verified

The code ran end to end through `llm_client.py` against an OpenAI-compatible stand-in server with
scripted replies, and against a fake client in the tests. It was **not** run against the FIL gateway.
How the router and the assess node behave depends on gpt-6-luna; tune `app/agent/prompts.py` if a
scenario routes differently than `data/agent_scenarios.json` expects.

## Suggested timing (3.5 h)

| Time | Block |
|---|---|
| 0:00–0:30 | Concept deck, part 1: what Lab 1 still gets wrong. Live: run S1, S4, S5 in the Lab 1 chat tab. |
| 0:30–0:50 | Concept deck, part 2: Graph RAG (what chunk retrieval cannot see). |
| 0:50–1:20 | Concept deck, part 3: LangGraph features. Live: open `/api/agent/graph` (Mermaid). |
| 1:20–1:40 | Build deck steps 1–3, TODO 1–2 (tools). Checkpoint A: A01–A04 green. |
| 1:40–2:00 | TODO 12 (wiring). The graph compiles; nodes still raise. |
| 2:00–2:45 | TODO 3–8. Checkpoint B: A08–A17 green; S4 shows two retrieval rounds in the trace. |
| 2:45–3:10 | TODO 9–11. Checkpoint C: 50 passed; clarify and follow-up scenarios work. |
| 3:10–3:30 | Teams run all scenarios + Compare; discuss cost (LLM calls per question). |

## Typical mistakes

| TODO | Mistake | Caught by |
|---|---|---|
| 1 | `eval()`; allowing `True`, names, attributes or huge powers | A02 |
| 2 | BM25 only over the semantic pool (Lab 1 habit) instead of the whole corpus | A03 |
| 3 | trusting the router: no fallback for broken JSON; clarifying forever | A08, A09 |
| 5 | not validating planner output; unknown entity reaches the entity tool | A12 |
| 6 | returning `[]` instead of `"generate"` when nothing is new | A13 |
| 7 | forgetting `tried_queries`; losing the `sub_id` from the Send payload | A14 |
| 8 | 0-based passage numbers; no fail-open; loop without the round limit | A15–A17, A22 |
| 9 | sending irrelevant evidence; letting the model do the maths | A18 |
| 10 | retrying forever; trying to update state inside the routing function | A19, A22 |
| 11 | side effects before `interrupt()` (the node re-runs from the top on resume) | A23 |
| 12 | no checkpointer (interrupt and memory break); conditional edges without target lists | A20–A25 |

## Discussion answers

* **Is agentic always better?** No. It costs 2–3× the LLM calls and the latency of MQR + RRF. The
  router keeps simple questions cheap; switch the self-check off for low-risk use.
* **Why JSON prompts instead of native tool calling?** They work with any chat model behind any
  gateway, and every decision is an explicit, testable node. Native tool calling (`bind_tools`,
  `ToolNode`, `create_react_agent`) is a stretch goal: more flexible, less predictable.
* **Why does `retrieve` receive only `{"sub": ...}`?** `Send` gives each parallel branch its own
  payload. Results flow back into the shared state through reducers.
* **Why reset state in `start_turn`?** The checkpointer keeps the whole state of a thread between
  turns. Only `messages` should carry over.
* **Graph RAG lite vs real GraphRAG?** Ours links entities that co-occur in a chunk (regex + a
  dictionary): free, instant, shallow. GraphRAG has an LLM extract typed relations and
  pre-summarises communities: far better for global questions, but it costs LLM calls over the whole
  corpus and must be rebuilt when documents change.

## Stretch goals

1. Replace the JSON router with native tool calling: `llm.bind_tools([...])` + `ToolNode`.
2. Swap `InMemorySaver` for `SqliteSaver` so conversations survive a restart.
3. Extract (entity, relation, entity) triples with the LLM for Graph RAG; compare S5 quality and cost.
4. Add an `interrupt()` before answering sensitive topics (salary, health) for human review.
5. Turn `data/agent_scenarios.json` into automatic checks (expected route, must-contain text).

## Regenerating the student starter

```bash
python tools/make_variants.py . ../student-out
```

---

# Lab 3 · Vectorless RAG · TRAINER ZIP ONLY

## Before class

1. `pytest` → **64 passed** (50 from Labs 1–2 + 14 vectorless tests V01–V14).
2. Run the app, open **Tree index**, press **LLM summaries**. That costs 12 `gpt-6-luna` calls once
   and writes `data/.cache/tree_summaries.json`. Read the signposts: if most are tagged `extractive`,
   the model did not return JSON for `TREE_SUMMARY`. Tune `app/vectorless/prompts.py` and bump
   `SUMMARY_PROMPT_VERSION`.
3. Run the five questions of Part B1 (exercise sheet) in Vectorless mode and check the navigation
   paths. "Reply unusable" or many `↩` in Evaluate means the `TREE_NAVIGATE` reply is not usable JSON.
4. Run **Evaluate** once with the real gateway and keep the numbers for the debrief (one run is about
   60 chat + 135 embedding calls; well inside 200 req/min and the $50 budget).
5. Build the student zip: `python tools/make_variants.py . ../lab3-student --labs lab3`.
   Check that the app starts, Lab 1 and Agentic tabs work, Vectorless answers `501 · TODO V1`, and
   `pytest` → **14 failed, 50 passed**. (Without `--labs` the script makes the old all-labs starter.)

## What was and was not verified

All of Lab 3 ran end to end against fakes: the tests' fake client, and the full app (API + React UI,
all four modes in Chat, Compare and Evaluate, the Tree index tab) with a keyword-matching stand-in
for the navigator. It was **not** run against the FIL gateway. The stand-in's Evaluate numbers mean
nothing about quality; get the real ones in step 4. How well vectorless does depends on how good
`gpt-6-luna`'s signposts and navigation choices are.

## Suggested timing (3 h)

| Time | Block |
|---|---|
| 0:00–0:20 | Concept: why "similar" is not "relevant"; how an expert reads a manual. Live: Q05 and Q14 in MQR + RRF. |
| 0:20–0:35 | Tour: Tree index tab, a vectorless answer with its navigation path (trainer build). |
| 0:35–1:05 | V1 + V2. Checkpoints A and B. |
| 1:05–1:35 | V3 + V4. Checkpoint D: 64 passed. |
| 1:35–2:20 | Part B: chat, compare, evaluate. Teams fill in the results table. |
| 2:20–2:45 | Part C: two experiments per team (split them so all five are covered). |
| 2:45–3:00 | Part D debrief: "is it always better?" with the teams' own numbers. |

## Typical mistakes

| TODO | Mistake | Caught by |
|---|---|---|
| V1 | Treating `### ` as a new section; dropping the intro; numbering by file name instead of position | V01, V03 |
| V1 | `line.startswith("#")` also matches `##`: every section becomes a title | V01 |
| V1 | Losing the last section (not flushing it at end of file) | V02 |
| V2 | Crashing on non-JSON or a gateway error; one bad section summary discards all the others | V05 |
| V3 | `"4"` ≠ `"04"`; keeping invented ids; `True` treated as id 1 | V07 |
| V4 | No step limit; recursing into leaves; not counting failed calls; no fallback → empty evidence | V08–V11 |
| V4 | Calling the embedding model "just to rank": then it is not vectorless | V08, V12 |

## Discussion answers

* **What does vectorless pay instead of embeddings?** LLM calls. Indexing: 1 per document, once
  (cached by content hash). Every question: 1 per tree level (2 here), so it is seconds slower than
  FAISS (milliseconds) and costs more per question. Expect retrieval latency of about 2× one
  `gpt-6-luna` call, against about 0 for Basic RAG.
* **Where it should win.** Exact identifiers that are section titles (PAY-/AUTH- codes), vocabulary
  gaps the LLM can bridge ("WFH" → Hybrid working, "deploy on 30th" → Change freeze), and questions
  whose parts live in different documents (Q14), because it picks per part instead of taking the
  top 5 lookalikes. Evidence is whole sections, never cut mid-table or mid-list.
* **Where it should lose.** A wrong turn at level 1 is never recovered (no second chance without a
  sufficiency loop). Weak signposts mean weak navigation (Experiment 1 shows this). Latency and cost
  per question are higher. It needs structure: a flat chat log or 100,000 tickets has no outline.
* **The honest point about this corpus.** The whole handbook is about 14,000 characters (≈3,500
  tokens). It fits in one prompt, so "send everything" (long context, with prompt caching) is a real
  competitor here. Vectorless pays off when documents are long (hundreds of pages, a real table of
  contents) and the full text does not fit or is too expensive to send on every question.
* **50 questions/s, under 1 s.** Basic or MQR + RRF with caching; not vectorless (two sequential
  LLM calls). **400-page regulation with audit:** vectorless (the path is the audit trail) plus BM25
  for exact clause numbers, a sufficiency check, and logged paths.
* **Always better?** No. Better for long, structured, precision-critical documents; worse for huge
  flat corpora, vague exploratory questions and tight latency budgets. In production, hybrids win:
  a cheap shortlist (BM25 / vectors), then reasoning inside the shortlist.

## Stretch goals (answers not provided)

See section 8 of `LAB3_VECTORLESS.md`. Stretch 1 (hybrid router) and 2 (follow cross-references)
make the best demos: Q5 of Part B1 is designed to need stretch 2.
