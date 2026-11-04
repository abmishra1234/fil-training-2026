# 01 - Problem brief (one page)

## The situation

Client-servicing analysts at Lumen Crest Investments (a fictional fund house) answer the same fund questions many times a week by searching factsheets, KIDs, policies and spreadsheets by hand. Answers are slow, inconsistent and sometimes quote the wrong share class or an out-of-date figure. A plain chatbot is not acceptable: it invents numbers, cannot compare funds, ignores servicing rules and might give investment advice to a client.

## What you build

**FundLens**, a copilot for two internal users:

- **Servicing analyst** - asks questions and asks for draft replies to client emails.
- **Reviewer** (compliance or team lead) - approves, edits or rejects drafts in a review queue.

No client ever talks to FundLens directly.

For each request FundLens must:

1. Work out the intent and route it: `fact`, `compare`, `policy`, `draft` or `out_of_scope`.
2. Retrieve the right passages (hybrid BM25 + FAISS, Multi-Query rewrites, RRF fusion) and answer only from them, citing every claim as `[doc_id §section]`.
3. Get numbers from tools (`fund_lookup`, `compare_funds`, `calculator`), never from free-text model arithmetic.
4. For drafts: write the reply, run `compliance_check`, revise until it passes (max 3 rounds) or escalate.
5. Pause every draft for human approval (LangGraph interrupt) and log every step for audit.

## The seven use cases

| ID | Use case | Example | Route |
| --- | --- | --- | --- |
| UC1 | Fact lookup | What is the ongoing charge of the Global Tech Fund, A-Acc share class? | fact |
| UC2 | Fund comparison | Compare the risk indicator, top 3 holdings and 3-year return of two funds | compare |
| UC3 | Policy question | Can we waive the switching fee for a client who switched twice this month? | policy |
| UC4 | Draft client reply | Draft a reply to EML-001 asking why the fund fell last quarter | draft |
| UC5 | Multi-hop | Which of our ESG funds has the lowest charge, and what does its KID say about risk? | compare (+ fact) |
| UC6 | Refusal | Should my client move all savings into the India Equity Fund? | out_of_scope |
| UC7 | Unanswerable / forecast | What will the fund return next year? | out_of_scope |

## Must-haves (you need all of these to pass)

FR-01 ingestion with metadata · FR-03 hybrid search + RRF · FR-04 MQR · FR-07 citation per claim · FR-08 "not found" fallback · FR-09 Pydantic JSON output · FR-10 router · FR-11 tools · FR-12 groundedness self-check (max 2 retries) · FR-13 draft-compliance-revise loop · FR-14 human-in-the-loop · FR-16 PII and secret guard · FR-17 refusals · FR-18 UI · FR-19 API · FR-20 tracing + audit log · FR-21 one-command evaluation.

Should-haves for higher scores: FR-02 idempotent re-ingest, FR-05 metadata filters, FR-06 reranking, FR-15 short conversation memory.

## Pass thresholds (on the hidden set, demo day)

| Metric | Pass | Distinction |
| --- | --- | --- |
| Route accuracy | 85% | 95% |
| Retrieval hit rate@5 | 80% | 90% |
| Faithfulness (LLM judge) | 0.85 | 0.92 |
| Answer correctness | 80% | 90% |
| Citation precision | 85% | 95% |
| Refusal accuracy | 100% | 100% |
| Compliance catch rate (seeded drafts) | 9 of 10 | 10 of 10 |
| Injection resistance | 5 of 5 | 5 of 5 |
| HITL integrity | always | always |

Non-functional targets: fact/policy answer p95 under 8 s, draft p95 under 25 s, 6 or fewer LLM calls per fact question, temperature 0 for routing, grading and compliance.

## Fixed technology

Python 3.11+, LangChain + LangGraph, FAISS (in-memory, saved to disk), rank_bm25, FastAPI, Streamlit, SQLite, LangSmith, the FIL AI Gateway (`azure/gpt-6-luna`, `azure/text-embedding-ada-002`). Text models only.

## Deliverables (end of Day 6)

Git repo with one-command setup, architecture note (max 2 pages), evaluation report (baseline vs final, 3 failure analyses), 5-minute demo recording. Day 7 is the live demo. See `10_submission_checklist.md`.
