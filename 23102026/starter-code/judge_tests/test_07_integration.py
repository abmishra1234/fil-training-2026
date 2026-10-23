"""
Group G - End to end in the RAG app: Basic RAG, MQR, MQR + RRF, Agentic RAG and the HTTP API.
The LLM is an offline recorder (fakes.py): the tests see EVERY prompt that would have
been sent to the model.                                                            JT29 - JT30
"""
from __future__ import annotations

import json

import adapter
import pytest
from conftest import (
    ALL_SECRET_DOCS, CLEAN_DOCS, CLEAN_PASSAGE_MARKERS, CONTEXT_BLOCKED_REPLY, QUERY_BLOCKED_REPLY, SECRET_DOC,
    SECRET_PASSAGE_MARKERS,
)
from samples import AKIA_KEY, ALL_SECRET_STRINGS

SECRET_QUERY = f"Why is the parking barrier rejecting {AKIA_KEY}?"
FAKE_ANSWER = "FAKE-ANSWER"


def dump(obj) -> str:
    return json.dumps(obj, default=str)


def assert_no_secret(where: str, text: str):
    leaked = [s for s in ALL_SECRET_STRINGS + [AKIA_KEY] if s in text]
    assert not leaked, f"secret text in {where}: {leaked}"


def run(kind: str, svc, question: str) -> dict:
    if kind == "agent":
        return adapter.make_agent_service(svc).ask(question)
    return svc.run(kind, question)


# =============================================================================== JT29
@pytest.mark.parametrize("kind", ["basic", "mqr", "mqr_rrf", "agent", "http-chat", "http-agent"])
def test_JT29_secret_query_never_reaches_any_llm_call(kind, rag_factory, fake_llm):
    """
    Secret in the query -> exact restricted reply, ZERO chat calls (MQR rewrite, router,
    contextualize all count), and the response never echoes the secret back.
    """
    if kind.startswith("http"):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            fake_llm.reset()
            if kind == "http-chat":
                resp = client.post("/api/chat", json={"question": SECRET_QUERY, "mode": "mqr_rrf"})
            else:
                resp = client.post("/api/agent/chat", json={"question": SECRET_QUERY})
        assert QUERY_BLOCKED_REPLY in resp.text, f"HTTP {resp.status_code}: {resp.text[:300]}"
        assert_no_secret("HTTP response body", resp.text)
    else:
        svc = rag_factory({**CLEAN_DOCS, **SECRET_DOC})
        out = run(kind, svc, SECRET_QUERY)
        assert out["answer"] == QUERY_BLOCKED_REPLY
        assert_no_secret("API response", dump(out))
    assert fake_llm.chat_calls == [], f"{len(fake_llm.chat_calls)} LLM call(s) were made for a blocked query"
    assert_no_secret("LLM prompts", fake_llm.all_prompt_text())


# =============================================================================== JT30
SCENARIOS = [(m, s) for s in ("partial", "all-secret") for m in ("basic", "mqr", "mqr_rrf", "agent")] + \
            [("basic", "gateway-error"), ("mqr_rrf", "gateway-error")]


@pytest.mark.parametrize("kind, scenario", SCENARIOS, ids=[f"{s}-{m}" for m, s in SCENARIOS])
def test_JT30_secret_passages_are_dropped_before_every_llm_call(kind, scenario, rag_factory, fake_llm):
    """
    partial      : the LLM answers from the clean passages; no prompt (answer, assess, check...) holds a secret.
    all-secret   : the approved-sources reply, and no passage text is ever sent to the LLM.
    gateway-error: a crashing detector -> fail closed: no passage text sent, no normal answer.
    In every case the API response (sources, inspector pool, trace) contains no secret.
    """
    question = "What is the parking policy?"
    gateway = None
    if scenario == "partial":
        docs = {**CLEAN_DOCS, **SECRET_DOC}
    elif scenario == "all-secret":
        docs = ALL_SECRET_DOCS
    else:
        docs = CLEAN_DOCS

        def crash_on_passages(text: str) -> int:
            if "Parking policy >" in text or "bay B" in text:  # chunk text, never the question
                raise RuntimeError("detector crashed")
            return 0

        gateway = adapter.make_gateway(extra_detectors=[adapter.make_custom_detector("CRASH", crash_on_passages)])

    svc = rag_factory(docs, gateway=gateway)
    out = run(kind, svc, question)
    prompts = fake_llm.all_prompt_text()
    assert_no_secret("LLM prompts", prompts)
    assert_no_secret("API response", dump(out))

    if scenario == "partial":
        assert FAKE_ANSWER in out["answer"], f"expected a normal answer, got {out['answer']!r}"
        assert all(m in prompts for m in CLEAN_PASSAGE_MARKERS), "the clean passages must still reach the LLM"
        assert not any(m in prompts for m in SECRET_PASSAGE_MARKERS), "the dropped passage reached the LLM"
    elif scenario == "all-secret":
        assert out["answer"] == CONTEXT_BLOCKED_REPLY
        assert not any(m in prompts for m in SECRET_PASSAGE_MARKERS), "a blocked passage reached the LLM"
        assert FAKE_ANSWER not in out["answer"]
    else:
        assert FAKE_ANSWER not in out["answer"], "gateway error must not produce a normal LLM answer"
        assert not any(m in prompts for m in CLEAN_PASSAGE_MARKERS), "fail closed: passages were sent after a gateway error"
        assert out["answer"] not in ("", None)
