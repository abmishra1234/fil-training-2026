"""Tests 13-22: BM25, semantic re-rank, Reciprocal Rank Fusion (TODO 5-8)."""
import pytest

from app.basic_rag import basic_retrieve
from app.rerank import bm25_rank, mqr_rrf_retrieve, reciprocal_rank_fusion, semantic_rank

from .conftest import contains, doc, ids, make_cfg, make_store

# Sibling error codes: many chunks talk about "payment settlement batch",
# the one we want (PAY-E4035) uses different words. The fake embedding model
# cannot see codes, so semantic search alone ranks it low.
CODES = {
    "pay#1": "PAY-E4031 payment settlement batch rejected after cut-off. Payment batch moved to next day.",
    "pay#2": "PAY-E4032 payment settlement batch has duplicate UTR. Payment held.",
    "pay#3": "PAY-E4033 payment settlement batch beneficiary frozen. Payment reversed.",
    "pay#4": "PAY-E4034 payment settlement batch limit exceeded. Payment split.",
    "pay#5": "PAY-E4036 payment settlement batch currency mismatch. Payment converted.",
    "pay#6": "PAY-E4037 payment settlement batch partner timeout. Payment retried.",
    "pay#7": "PAY-E4035 signature mismatch on outbound bank file: re-sign with the HSM key.",
    "hr#1": "Earned leave is 24 days per year and can be carried forward.",
}
CODE_Q = "What does PAY-E4035 mean for my payment settlement batch?"


# ------------------------------------------------------------------ TODO 5
def test_13_bm25_ranks_exact_code_first_ignoring_case_and_punctuation():
    docs = [doc(cid, t) for cid, t in CODES.items()]
    out = bm25_rank(["pay-e4035??"], docs)
    assert out[0].metadata["chunk_id"] == "pay#7"
    assert out[0].metadata["bm25_score"] > out[1].metadata["bm25_score"]
    out2 = bm25_rank(["what is PAY-E4035", "PAY-E4035 bank file"], docs)  # several queries = expansion
    assert out2[0].metadata["chunk_id"] == "pay#7"


def test_14_bm25_keeps_every_doc_and_survives_edge_cases():
    docs = [doc(cid, t) for cid, t in CODES.items()]
    out = bm25_rank(["earned leave"], docs)
    assert sorted(ids(out)) == sorted(CODES)  # never drops a doc
    assert out[0].metadata["chunk_id"] == "hr#1"
    assert bm25_rank(["anything"], []) == []
    stop = bm25_rank(["what is the", "  "], docs)  # no usable tokens
    assert ids(stop) == list(CODES) and all(d.metadata["bm25_score"] == 0.0 for d in stop)
    assert "bm25_score" not in docs[0].metadata  # input not mutated


# ------------------------------------------------------------------ TODO 6
def test_15_semantic_rank_uses_max_over_queries_and_cached_query_vectors(fake):
    store = make_store({
        "a#0": "hybrid working anchor days tuesday thursday",
        "b#0": "expense per diem hotel claims",
        "c#0": "laptop stolen remote wipe",
    })
    store.search("laptop stolen", 2)  # MQR would have searched these queries already
    store.search("hybrid working", 2)
    calls_before = fake.embeddings.calls
    out = semantic_rank(store, ["laptop stolen", "hybrid working"], [store.docs[c] for c in ("b#0", "a#0", "c#0")])
    assert fake.embeddings.calls == calls_before, "query vectors must come from the cache"
    assert ids(out)[2] == "b#0"  # matches neither query -> last
    assert set(ids(out)[:2]) == {"a#0", "c#0"}  # each matches ONE query -> max() lifts both
    scores = [d.metadata["semantic_score"] for d in out]
    assert scores == sorted(scores, reverse=True) and -1.0 <= scores[-1] <= scores[0] <= 1.0001


def test_16_semantic_rank_empty_inputs(fake):
    store = make_store({"a#0": "alpha"})
    assert semantic_rank(store, ["alpha"], []) == []
    d = [store.docs["a#0"]]
    assert ids(semantic_rank(store, [], d)) == ["a#0"]


# ------------------------------------------------------------------ TODO 7
def test_17_rrf_matches_hand_computed_scores():
    A, B, C, D = (doc(x + "#0", x) for x in "ABCD")
    out = reciprocal_rank_fusion([[A, B, C], [C, A, D]], k=60)
    expected = {
        "A#0": 1 / 61 + 1 / 62,
        "C#0": 1 / 63 + 1 / 61,
        "B#0": 1 / 62,
        "D#0": 1 / 63,
    }
    assert ids(out) == ["A#0", "C#0", "B#0", "D#0"]
    for d in out:
        assert d.metadata["rrf_score"] == pytest.approx(expected[d.metadata["chunk_id"]])
    assert out[0].metadata["rrf_ranks"] == [1, 2]
    assert out[2].metadata["rrf_ranks"] == [2, None]  # B is only in list 0


def test_18_rrf_single_list_docs_and_duplicates_inside_one_list():
    A, B, C = (doc(x + "#0", x) for x in "ABC")
    A_dup = doc("A#0", "A", note="dup")
    out = reciprocal_rank_fusion([[A, A_dup, B], [C]], k=0)
    scores = {d.metadata["chunk_id"]: d.metadata["rrf_score"] for d in out}
    assert scores["A#0"] == pytest.approx(1.0)        # duplicate in the same list counted once
    assert scores["B#0"] == pytest.approx(1 / 3)      # B keeps its real position (3)
    assert scores["C#0"] == pytest.approx(1.0)        # only in list 1, still included
    assert "note" not in out[0].metadata              # first-seen document is the base


def test_19_rrf_tie_break_is_first_seen_and_top_n_is_respected():
    A, B, C, D = (doc(x + "#0", x, semantic_score=0.5) for x in "ABCD")
    out = reciprocal_rank_fusion([[A, B], [C, D]], k=60)
    assert ids(out) == ["A#0", "C#0", "B#0", "D#0"]  # A ties C, B ties D: list 0 first
    assert out[0].metadata["semantic_score"] == 0.5    # metadata of the base doc kept
    assert ids(reciprocal_rank_fusion([[A, B], [C, D]], top_n=2)) == ["A#0", "C#0"]
    assert len(reciprocal_rank_fusion([[A, B], [C, D]], top_n=50)) == 4
    assert reciprocal_rank_fusion([[A, B]], top_n=0) == []


def test_20_rrf_rejects_negative_k_and_handles_empty_lists():
    A = doc("A#0", "A")
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([[A]], k=-1)
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


# ------------------------------------------------------------------ TODO 8
def test_21_mqr_rrf_sends_at_most_final_k_chunks_from_the_pool(fake, handbook_store):
    q = "Prod payments are broken at 2am and nobody picks up. Who next?"
    fake.chat.completions.rewrites[q] = (
        "Sev-1 escalation matrix secondary on-call engineer\n"
        "PagerNova page acknowledgement escalates Engineering Manager\n"
        "payments on-call incident response times"
    )
    cfg = make_cfg(final_k=5)
    res = mqr_rrf_retrieve(handbook_store, q, cfg)
    pool = set(ids(res.mqr.docs))
    assert len(pool) > 5
    assert len(res.fused) == 5 and set(ids(res.fused)) <= pool
    assert sorted(ids(res.semantic)) == sorted(pool) == sorted(ids(res.bm25))
    rrf = [d.metadata["rrf_score"] for d in res.fused]
    assert rrf == sorted(rrf, reverse=True)
    assert contains(res.fused, "escalates to the secondary")


def test_22_mqr_rrf_rescues_exact_error_code_that_basic_rag_ranks_low(fake):
    store = make_store(CODES)
    fake.chat.completions.rewrites[CODE_Q] = (
        "PAY-E4035 error meaning\nPAY-E4035 first response runbook\nPAY-E4035 bank file"
    )
    cfg = make_cfg(basic_k=3, mqr_k=5, final_k=3)
    basic = basic_retrieve(store, CODE_Q, cfg.basic_k)
    assert "pay#7" not in ids(basic), "precondition: semantic search alone misses the code"
    res = mqr_rrf_retrieve(store, CODE_Q, cfg)
    assert "pay#7" in ids(res.mqr.docs)
    assert len(res.fused) == 3
    assert "pay#7" in ids(res.fused)  # rescued into the top-k sent to the LLM
    rescued = next(d for d in res.fused if d.metadata["chunk_id"] == "pay#7")
    sem_rank, bm25_rank_ = rescued.metadata["rrf_ranks"]
    assert bm25_rank_ == 1 and sem_rank > cfg.final_k  # BM25 alone pulled it up
