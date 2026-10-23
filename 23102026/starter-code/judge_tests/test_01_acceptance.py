"""
Group A - Acceptance: the "Expected behaviour" table of the brief, row by row.     JT01 - JT07
"""
from __future__ import annotations

import adapter
import pytest
from conftest import capture_everything, log_text
from samples import AKIA_KEY, CLEAN_TEXT, CLIENT_SECRET, FALCON, SK_KEY, VISA_DASHES

P = adapter.make_passage
V = adapter.result_view
DECISIONS = {"ALLOW", "BLOCK_QUERY", "BLOCK_CONTEXT", "BLOCK_ERROR"}


def nonzero(findings: dict) -> dict:
    return {k: v for k, v in findings.items() if v}


def test_JT01_no_secret_is_allowed_unchanged():
    """No secret found -> ALLOW, every passage passes through in the original order."""
    ps = [P("doc#0", CLEAN_TEXT), P("doc#1", "Earned leave accrues at 1.5 days per month."), P("doc#2", "Sev-1 needs a 15 minute ack.")]
    r = V(adapter.check("How many anchor days do we have?", ps))
    assert r["decision"] == "ALLOW"
    assert r["safe_ids"] == ["doc#0", "doc#1", "doc#2"]
    assert r["dropped"] == []
    assert nonzero(r["findings"]) == {}


def test_JT02_secret_in_one_passage_drops_only_that_passage():
    """Secret in one passage -> that passage is dropped, the LLM still gets the rest (in order)."""
    ps = [P("a#0", CLEAN_TEXT), P("b#1", f"Service account config: {CLIENT_SECRET} (rotate monthly)."), P("c#2", "Anchor days are Tue and Thu.")]
    r = V(adapter.check("What are the anchor days?", ps))
    assert r["decision"] in ("ALLOW", "BLOCK_CONTEXT"), "a passage secret must never block the whole query"
    assert r["safe_ids"] == ["a#0", "c#2"]
    assert r["dropped"] == ["b#1"]
    assert nonzero(r["findings"]) == {adapter.TYPE_CREDENTIAL: 1}


def test_JT03_secret_in_every_passage_blocks_context_with_exact_counts():
    """Secret in every passage -> BLOCK_CONTEXT, nothing passes, findings counted per type."""
    ps = [
        P("k#0", f"Gateway key {SK_KEY} rotates monthly."),
        P("c#1", f"Refund to card {VISA_DASHES} failed twice."),
        P("d#2", f"{FALCON} and project monsoon merge next quarter."),
    ]
    r = V(adapter.check("Summarise the finance updates", ps))
    assert r["decision"] == "BLOCK_CONTEXT"
    assert r["safe"] == [] and r["safe_ids"] == []
    assert r["dropped"] == ["k#0", "c#1", "d#2"]
    assert nonzero(r["findings"]) == {adapter.TYPE_CREDENTIAL: 1, adapter.TYPE_CARD: 1, adapter.TYPE_CODENAME: 2}


@pytest.mark.parametrize("query, kind", [
    (f"why does {AKIA_KEY} fail in prod?", "CREDENTIAL"),
    (f"refund the customer on {VISA_DASHES} please", "CARD"),
    ("what is the status of PROJECT FALCON?", "CODENAME"),
], ids=["credential", "card", "codename"])
def test_JT04_secret_in_query_blocks_request(query, kind):
    """Secret in the query -> BLOCK_QUERY, no passage is released (even though all are clean)."""
    expected_type = {"CREDENTIAL": adapter.TYPE_CREDENTIAL, "CARD": adapter.TYPE_CARD, "CODENAME": adapter.TYPE_CODENAME}[kind]
    ps = [P("x#0", CLEAN_TEXT), P("x#1", "Per diem is INR 2,500.")]
    r = V(adapter.check(query, ps))
    assert r["decision"] == "BLOCK_QUERY"
    assert r["safe"] == []
    assert r["findings"].get(expected_type, 0) >= 1


def test_JT05_query_block_takes_precedence_over_context():
    """Secret in the query AND in passages -> BLOCK_QUERY (the request itself is restricted)."""
    ps = [P("y#0", f"key {SK_KEY}"), P("y#1", CLEAN_TEXT)]
    r = V(adapter.check(f"Is {FALCON} still on track?", ps))
    assert r["decision"] == "BLOCK_QUERY"
    assert r["safe"] == []


def test_JT06_gateway_error_fails_closed_even_mid_scan():
    """Any error inside the gateway -> BLOCK_ERROR and NOTHING is released (not even passages scanned before the error)."""
    def boom_on_third(text: str) -> int:
        if "THIRD" in text:
            raise RuntimeError("detector crashed")
        return 0

    gw = adapter.make_gateway(extra_detectors=[adapter.make_custom_detector("FLAKY", boom_on_third)])
    ps = [P("e#0", CLEAN_TEXT), P("e#1", "second clean passage"), P("e#2", "THIRD passage"), P("e#3", "fourth")]
    r = V(gw.check("anchor days?", ps))  # must not raise
    assert r["decision"] == "BLOCK_ERROR"
    assert r["safe"] == [], "fail closed: an error must not release the passages scanned before it"

    def always_boom(text: str) -> int:
        raise MemoryError("simulated")

    gw2 = adapter.make_gateway(extra_detectors=[adapter.make_custom_detector("BROKEN", always_boom)])
    r2 = V(gw2.check("hello", [P("f#0", CLEAN_TEXT)]))
    assert r2["decision"] == "BLOCK_ERROR" and r2["safe"] == []


def test_JT07_error_path_never_leaks_the_text_it_failed_on():
    """The exception message contains the secret; result, logs and console must not."""
    marker = "ZETA-PRIVATE-778899"

    def leaky_crash(text: str) -> int:
        if marker in text:
            raise ValueError(f"cannot parse passage: {text}")
        return 0

    gw = adapter.make_gateway(extra_detectors=[adapter.make_custom_detector("LEAKY", leaky_crash)])
    with capture_everything() as (handler, out, err):
        result = gw.check("what is the vault rule?", [P("z#0", f"vault seed {marker} do not share")])
    v = V(result)
    assert v["decision"] == "BLOCK_ERROR"
    everything = " ".join([repr(result), str(result), repr(v), log_text(handler), out.getvalue(), err.getvalue()])
    assert marker not in everything, "secret text leaked through the error path (log / result / console)"
    assert v["decision"] in DECISIONS
