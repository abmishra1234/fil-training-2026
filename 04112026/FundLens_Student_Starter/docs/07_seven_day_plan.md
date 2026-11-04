# 07 - Seven-day plan

Three gates keep you on track. A team that misses a gate cuts should-have items (FR-02, 05, 06, 15), never the evaluation.

| Day | Focus | Done when | FRs |
| --- | --- | --- | --- |
| 1 | Setup, corpus, ingestion | `make check` ALL GOOD; repo + LangSmith project created; all 59 docs chunked with full metadata; FAISS + BM25 built and saved | FR-01, FR-02 |
| 2 | Baseline RAG | `/ask` answers with citations and "not found" fallback; Pydantic output; first `make eval` | FR-07, 08, 09, 19 |
| | **Gate 1 (end of Day 2)** | Baseline eval report committed in `reports/baseline/` | |
| 3 | Better retrieval + tools | MQR + RRF + metadata filters (+ rerank); fund_lookup, compare_funds, calculator, policy_search with unit tests; second eval report | FR-03 to 06, 11 |
| 4 | LangGraph agent | Router, tool nodes, groundedness self-check with max 2 retries, refusals | FR-10, 12, 17 |
| | **Gate 2 (end of Day 4)** | UC1, UC2, UC3, UC5, UC6, UC7 work end to end through the graph with traces in LangSmith | |
| 5 | Drafting, compliance, HITL | Draft node, compliance_check over the YAML rules, revise loop (max 3) + escalation, interrupt before human review, SQLite review queue, `/review` endpoints | FR-13, 14 |
| 6 | Guardrails, UI, hardening, evaluation | PII masking + secret filter, injection handling, audit log, Streamlit (chat, sources/trace, review queue), error handling, full eval with `--judge`, 3 failure analyses | FR-15, 16, 18, 20, 21 |
| | **Gate 3 (end of Day 6)** | Feature freeze; dev report meets every pass threshold; submission checklist complete | |
| 7 | Demo day | 20-minute demo, live hidden-set run, code walkthrough, Q&A | |

## Daily rhythm

- 09:30 stand-up (10 minutes): yesterday, today, blockers, today's eval numbers.
- Merge to `main` at least twice a day; keep `make test` green.
- 17:30 run `make eval`, commit the report, note the worst three failures for tomorrow.

## Suggested split

| Team of 3 | Owns |
| --- | --- |
| Member A - Retrieval + evaluation | Ingestion, chunking, hybrid search, MQR, RRF, rerank, eval runs and report |
| Member B - Agent + tools | LangGraph graph, router, state, tools, self-check and revise loops, interrupt |
| Member C - Safety + platform | PII/secret guard, injection handling, compliance_check, FastAPI, Streamlit, review store, audit log |

With 2 members: A takes retrieval, evaluation, API and UI; B takes the agent, tools, compliance and guardrails. Everyone writes tests and everyone must be able to explain every part on demo day.

## Day-by-day tips

- **Day 1.** Do not over-engineer chunking. Headings and policy clauses already give you clean sections. Print 10 random chunks and read them.
- **Day 2.** Write the system prompt for grounded answers first: answer only from context, cite every sentence, say "not found in the provided documents" otherwise.
- **Day 3.** Measure each change with `make eval`. Keep what moves hit@5 or correctness; drop what does not.
- **Day 4.** Start with a router prompt that returns JSON `{"route": ..., "fund_ids": [...], "share_class": ...}` at temperature 0. Test it alone on the 40 questions before wiring the graph.
- **Day 5.** Make the compliance check deterministic first (regex rules from the YAML), then add an LLM check on top if you want.
- **Day 6.** Rehearse the demo twice. Record the 5-minute backup video before 17:00.
