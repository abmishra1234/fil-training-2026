"""FR-16 input guard: mask PII before any LLM call and in the audit log.  >>> YOU BUILD THIS (Day 5-6) <<<

Mask at least: person names in email signatures/headers, email addresses, phone numbers (+91 ...), account numbers
(LCI-XXXXXXXX -> ****XXXX), dates of birth, bank account numbers / IFSC codes.
Also block FIL-sensitive secrets (API keys, passwords, internal URLs) - extend your Mini AI Gateway from the earlier lab.
Keep a reversible mapping per request if you want to re-insert the client's own first name into the final draft.
"""
from __future__ import annotations


def mask_pii(text: str) -> tuple[str, dict[str, str]]:
    raise NotImplementedError


def contains_secret(text: str) -> bool:
    raise NotImplementedError
