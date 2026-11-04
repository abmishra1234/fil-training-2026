"""FR-14 / FR-20 review queue + audit log in SQLite.  >>> YOU BUILD THIS (Day 5) <<<

Tables (suggested): reviews(review_id, email_ref, question, draft, citations_json, compliance_json, revision_count,
status, reviewer, reviewer_reason, final_text, created_at, decided_at) and audit(event_id, ts, session_id, kind, payload_json).
Rule: status can move to approved / edited_and_approved / rejected ONLY through POST /review/{id} with a reviewer name.
"""
