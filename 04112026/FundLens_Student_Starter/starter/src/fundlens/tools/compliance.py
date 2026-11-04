"""FR-11 / FR-13 compliance_check(draft) -> ComplianceResult.  >>> YOU BUILD THIS (Day 5) <<<

Load corpus/rules/compliance_rules.yaml and run every rule:
- banned_regex: any pattern match = violation (respect allow_phrases)
- required_if: if the draft quotes performance (performance_triggers), required mandatory text must be present
- required_always: mandatory text must always be present (warn)
- pii_regex: unmasked PII patterns
- llm_judgement: optional LLM check, temperature 0
passed = no "block" rule fired. Measure yourself with evaluation/seeded_drafts_dev.jsonl
(target: catch >= 9 of 10 non-compliant drafts and pass the 4 compliant controls).
"""
from __future__ import annotations

from ..schemas import ComplianceResult


def compliance_check(draft: str, client_email: str | None = None) -> ComplianceResult:
    raise NotImplementedError
