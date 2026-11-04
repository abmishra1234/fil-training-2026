# 04 - API contract (FR-19)

The shapes come from `starter/src/fundlens/schemas.py`. The UI, `scripts/make_predictions.py` and the scorer depend on them. You may add optional fields; do not rename or remove any.

Base URL: `http://localhost:8000`. Interactive docs at `/docs` once the API runs.

## GET /health

```json
{"status": "ok", "llm_mode": "gateway", "kit_dir": "/path/to/kit", "corpus_found": true}
```

## POST /ask - fact, compare, policy and out-of-scope questions

Request:

```json
{"question": "What is the ongoing charge of the Global Tech Fund, A-Acc share class?", "session_id": "analyst-1"}
```

Response (`AnswerOutput`):

```json
{
  "answer": "The ongoing charge (OCF) of the LCI Global Technology Fund A-Acc-USD share class is 1.89% a year, as of 30 September 2026 [DATA-FUND-MASTER §F01/A-Acc-USD].",
  "citations": [
    {"doc_id": "DATA-FUND-MASTER", "section": "F01/A-Acc-USD", "as_of_date": "2026-09-30",
     "text": "F01 | A-Acc-USD | ocf_pct 1.89 | as_of 2026-09-30"}
  ],
  "confidence": 0.93,
  "route": "fact",
  "refused": false,
  "freshness_warning": null,
  "tools_called": ["fund_lookup"],
  "retrieved_doc_ids": ["DATA-FUND-MASTER", "FS-F01", "KID-F01", "FS-F03", "COM-F01-2026Q3"],
  "review_id": null,
  "review_status": "n/a",
  "llm_calls": 3,
  "latency_ms": 2140
}
```

Rules:
- `retrieved_doc_ids` is the ordered list after fusion/rerank (duplicates allowed; the scorer de-duplicates). It drives hit@5.
- Each citation's `text` is the chunk (or tool output) that supports the claim. The LLM judge reads it.
- For refusals: `route = "out_of_scope"`, `refused = true`, and a helpful answer saying what you can do instead.
- If nothing supports an answer: answer contains "not found in the provided documents", `refused = false`.

## POST /draft - draft a client reply

Request (give `email_ref` for a kit email, or paste `email_text`):

```json
{"instruction": "Draft a reply to this client email.", "email_ref": "EML-001", "session_id": "analyst-1"}
```

Response: `AnswerOutput` with `route = "draft"`, `answer` = the draft text, `review_id` set and `review_status = "pending_review"` (or `"escalated"` if compliance still fails after 3 revisions). The draft is now paused in the LangGraph graph waiting for a reviewer.

## GET /review?status=pending_review

Returns a list of `ReviewItem`:

```json
[{
  "review_id": "rv_0007", "email_ref": "EML-001", "question": "Draft a reply to this client email.",
  "draft": "Dear Priya, ...", "citations": [...],
  "compliance": {"passed": true, "violated_rule_ids": [], "findings": []},
  "revision_count": 1, "status": "pending_review", "reviewer": null, "reviewer_reason": null,
  "final_text": null, "created_at": "2026-11-05T10:02:11Z", "decided_at": null
}]
```

## POST /review/{review_id}

```json
{"action": "approve", "reviewer": "team.lead.1", "reason": null, "edited_text": null}
{"action": "edit", "reviewer": "team.lead.1", "reason": "softened tone", "edited_text": "Dear Priya, ..."}
{"action": "reject", "reviewer": "compliance.2", "reason": "quotes internal policy"}
```

Resumes the paused graph. Returns the updated `ReviewItem` (`approved`, `edited_and_approved` or `rejected`). An edited text must pass `compliance_check` again before it is stored as approved. Nothing is ever sent to a client; "approved" just means ready to send.

## POST /ingest

Rebuilds chunks and indexes from `FUNDLENS_KIT_DIR`. Idempotent (FR-02). Response example:

```json
{"documents": 59, "chunks": 412, "superseded_docs": ["POL-01-v2.1"], "seconds": 38.4}
```

## Errors

Never return a stack trace. If the gateway fails twice (`LLMUnavailable`), return HTTP 503 with `{"detail": "The language model is temporarily unavailable. Please try again in a minute."}`.
