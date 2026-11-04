"""FR-11 policy_search(query, policy_type=None) -> top clauses with clause ids.  >>> YOU BUILD THIS <<<

Must return ACTIVE versions by default (POL-01-v2.1 is SUPERSEDED). Each hit: doc_id, section ("§4.2"), text, status.
"""
from __future__ import annotations


def policy_search(query: str, policy_type: str | None = None, k: int = 4) -> list[dict]:
    raise NotImplementedError
