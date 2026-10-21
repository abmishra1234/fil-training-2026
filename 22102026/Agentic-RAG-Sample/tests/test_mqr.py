"""Tests 01-12: Multi-Query Retriever (TODO 1-4)."""
import httpx
from openai import APIConnectionError, APIStatusError

from app.basic_rag import basic_retrieve
from app.mqr import generate_queries, mqr_retrieve, parse_queries, unique_union

from .conftest import contains, doc, ids, make_cfg, make_store

Q = "Can I WFH on Fridays?"


# ------------------------------------------------------------------ TODO 1
def test_01_parse_strips_numbering_and_bullets():
    raw = "1. hybrid working policy\n2) remote days per week\n- anchor days\n* office presence\n• home location rules\nQuery 6: friday remote"
    assert parse_queries(raw, Q, 10) == [
        "hybrid working policy", "remote days per week", "anchor days",
        "office presence", "home location rules", "friday remote",
    ]


def test_02_parse_removes_quotes_preamble_and_blank_lines():
    raw = 'Here are 3 search queries:\n\n  "hybrid working policy"  \n\n`remote work days`\n\'anchor days office\'\n'
    assert parse_queries(raw, Q, 3) == ["hybrid working policy", "remote work days", "anchor days office"]


def test_03_parse_dedupes_and_drops_the_original_question():
    raw = "can i wfh on fridays\nHybrid  Working policy\nhybrid working policy?\nREMOTE days\nremote days."
    assert parse_queries(raw, Q, 5) == ["Hybrid  Working policy", "REMOTE days"]


def test_04_parse_caps_at_n_and_handles_empty_input():
    raw = "a one\nb two\nc three\nd four\ne five"
    assert parse_queries(raw, Q, 3) == ["a one", "b two", "c three"]
    assert parse_queries("", Q, 3) == []
    assert parse_queries(None, Q, 3) == []
    assert parse_queries("\n \n:\n", Q, 3) == []


# ------------------------------------------------------------------ TODO 2
def test_05_generate_queries_calls_chat_model_once_with_question_and_n(fake):
    fake.chat.completions.rewrites[Q] = "1. hybrid working policy\n2. remote days\n3. anchor days"
    out = generate_queries(Q, 3)
    assert out == ["hybrid working policy", "remote days", "anchor days"]
    calls = fake.chat.completions.calls
    assert len(calls) == 1
    assert calls[0]["model"] == "azure/gpt-6-luna"
    prompt = calls[0]["messages"][-1]["content"]
    assert Q in prompt and "3" in prompt
    assert fake.embeddings.calls == 0  # generating queries must not embed anything


def test_06_generate_queries_skips_llm_for_blank_question_or_zero_n(fake):
    assert generate_queries("   ", 3) == []
    assert generate_queries("", 3) == []
    assert generate_queries(Q, 0) == []
    assert fake.chat.completions.calls == []


def test_07_generate_queries_returns_empty_list_when_llm_fails(fake):
    req = httpx.Request("POST", "http://gateway/chat/completions")
    fake.chat.completions.raise_exc = APIConnectionError(request=req)
    assert generate_queries(Q, 3) == []
    fake.chat.completions.raise_exc = APIStatusError(
        "rate limited", response=httpx.Response(429, request=req), body=None
    )
    assert generate_queries(Q, 3) == []


# ------------------------------------------------------------------ TODO 3
def test_08_unique_union_keeps_first_occurrence_in_first_seen_order():
    a1, b1, c1 = doc("a#0", "A", query="q1"), doc("b#0", "B", query="q1"), doc("c#0", "C", query="q2")
    a2, d2 = doc("a#0", "A", query="q2"), doc("d#0", "D", query="q3")
    out = unique_union([[a1, b1], [a2, c1], [d2, b1]])
    assert ids(out) == ["a#0", "b#0", "c#0", "d#0"]
    assert out[0].metadata["query"] == "q1"  # first occurrence wins


def test_09_unique_union_handles_empty_inputs():
    assert unique_union([]) == []
    assert unique_union([[], [], []]) == []
    only = doc("x#0", "X")
    assert ids(unique_union([[], [only], []])) == ["x#0"]


# ------------------------------------------------------------------ TODO 4
def test_10_mqr_searches_original_plus_each_rewrite_with_mqr_k(fake):
    store = make_store({f"d#{i}": f"topic{chr(97 + i)} words here" for i in range(12)})
    seen = []
    real_search = store.search
    store.search = lambda q, k: seen.append((q, k)) or real_search(q, k)
    fake.chat.completions.rewrites[Q] = "hybrid working\nremote days\nanchor days"

    res = mqr_retrieve(store, Q, make_cfg(mqr_k=4))
    assert res.queries == [Q, "hybrid working", "remote days", "anchor days"]
    assert res.generated == ["hybrid working", "remote days", "anchor days"]
    assert seen == [(Q, 4), ("hybrid working", 4), ("remote days", 4), ("anchor days", 4)]
    assert set(res.per_query) == set(res.queries)
    for q, docs in res.per_query.items():
        assert len(docs) == 4 and all(d.metadata["query"] == q and "score" in d.metadata for d in docs)
    assert len(set(ids(res.docs))) == len(res.docs)  # union has no duplicates
    assert not res.llm_failed


def test_11_mqr_falls_back_to_original_question_when_llm_fails(fake):
    store = make_store({"a#0": "hybrid working anchor days", "b#0": "expense claims per diem"})
    fake.chat.completions.raise_exc = APIConnectionError(request=httpx.Request("POST", "http://x"))
    res = mqr_retrieve(store, Q, make_cfg(mqr_include_original=False, mqr_k=2))
    assert res.queries == [Q]
    assert res.llm_failed is True
    assert len(res.docs) == 2

    res2 = mqr_retrieve(store, Q, make_cfg(mqr_include_original=True, mqr_k=2), generated=[])
    assert res2.queries == [Q] and res2.llm_failed is True


def test_12_mqr_recovers_chunk_that_basic_rag_misses(fake, handbook_store, cfg):
    """Vocabulary mismatch: the user says 'WFH', the handbook says 'hybrid', 'anchor days'."""
    fake.chat.completions.rewrites[Q] = (
        "hybrid working arrangement office presence days per week\n"
        "team anchor days Tuesday Thursday remote day Friday\n"
        "work from a home location manager approval"
    )
    basic = basic_retrieve(handbook_store, Q, cfg.basic_k)
    assert not contains(basic, "anchor days"), "precondition: Basic RAG misses the answer"
    res = mqr_retrieve(handbook_store, Q, cfg)
    assert contains(res.docs, "anchor days")
    assert len(res.docs) > cfg.basic_k  # the price of recall: more chunks
