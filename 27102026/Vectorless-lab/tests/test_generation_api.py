"""Tests 23-25: grounded generation (TODO 9-10) and the full API in mqr_rrf mode."""
from fastapi.testclient import TestClient # type: ignore

from app.generation import build_context_block, extract_citations

from .conftest import doc


# ------------------------------------------------------------------ TODO 9
def test_23_context_block_numbers_sources_and_respects_the_budget():
    d1 = doc("a.md#0", "x" * 50)
    d2 = doc("b.md#0", "y" * 400)   # too big for the budget -> skipped
    d3 = doc("c.md#0", "z" * 30)    # still fits -> used as [2]
    block, used = build_context_block([d1, d2, d3], max_chars=200)
    p1 = "[1] (source: a.md)\n" + "x" * 50
    p2 = "[2] (source: c.md)\n" + "z" * 30
    assert block == p1 + "\n\n" + p2
    assert [u.metadata["chunk_id"] for u in used] == ["a.md#0", "c.md#0"]
    assert len(block) <= 200

    big = doc("big.md#0", "w" * 1000)
    block2, used2 = build_context_block([big, d1], max_chars=120)
    assert len(block2) == 120 and block2.startswith("[1] (source: big.md)\n")
    assert [u.metadata["chunk_id"] for u in used2] == ["big.md#0"]
    assert build_context_block([], 500) == ("", [])


# ------------------------------------------------------------------ TODO 10
def test_24_extract_citations_handles_every_format_and_bad_numbers():
    text = "Move it to next day [1][3]. See [3], [7], [0] and [1, 2]. Also [see 4] and [a]."
    assert extract_citations(text, 4) == [1, 2, 3]
    assert extract_citations("compact [2,4] form", 4) == [2, 4]
    assert extract_citations("no citations here", 4) == []
    assert extract_citations("", 4) == []
    assert extract_citations(None, 4) == []
    assert extract_citations("[1]", 0) == []


# ------------------------------------------------------------------ API
def test_25_chat_api_mqr_rrf_end_to_end(fake):
    from app.main import app

    q = "Can I WFH on Fridays?"
    fake.chat.completions.rewrites[q] = (
        "hybrid working arrangement office presence days per week\n"
        "team anchor days Tuesday Thursday remote day Friday\n"
        "work from a home location manager approval"
    )
    fake.chat.completions.answer = "Friday is the most common remote day [1]; anchor days are Tue/Thu [2][9]."
    with TestClient(app) as client:
        assert client.get("/api/health").json()["chunks"] > 20

        r = client.post("/api/chat", json={"question": q, "mode": "mqr_rrf"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["queries"][0] == q and len(body["queries"]) == 4
        assert 1 <= body["chunks_sent"] <= 5 < body["chunks_retrieved"]
        assert body["citations"] == [1, 2]                       # [9] ignored
        assert [s["cited"] for s in body["sources"]][:2] == [True, True]
        assert any("anchor days" in s["text"].lower() for s in body["sources"])
        assert all(s["rrf_score"] is not None for s in body["sources"])

        basic = client.post("/api/chat", json={"question": q, "mode": "basic"})
        assert basic.status_code == 200 and basic.json()["chunks_sent"] == 5
        assert client.post("/api/chat", json={"question": "   ", "mode": "mqr_rrf"}).status_code == 422
        assert client.post("/api/chat", json={"question": q, "mode": "magic"}).status_code == 422
