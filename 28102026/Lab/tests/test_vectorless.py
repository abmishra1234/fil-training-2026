"""
Tests V01-V14: Lab 3 · Vectorless RAG (tree index + LLM navigation).

Same rules as Lab 1 and 2: the gateway is faked, so this runs offline and free.
The fake LLM answers "TASK: TREE_SUMMARY" and "TASK: TREE_NAVIGATE" prompts with
whatever a test puts in fake.chat.completions.handlers[...].
"""
import json
import re

import pytest # type: ignore

from app.rerank import tokenize
from app.vectorless.navigator import parse_selection, skeleton, tree_search
from app.vectorless.tree import (
    ROOT_TITLE, build_tree, extractive_summary, node_document, summarize_document, summarize_tree,
)

from .conftest import ROOT, make_cfg

DOCS = ROOT / "data" / "docs"


# --------------------------------------------------------------------------- #
# Fake LLM helpers
# --------------------------------------------------------------------------- #
def fake_summarizer(system, user):
    """TREE_SUMMARY: 'About <title>' for the document and for every [id] section."""
    first = user.splitlines()[0]
    sections = {m.group(1): f"About {m.group(2)}" for m in re.finditer(r"^\[([\d.]+)\] (.+)$", user, re.M)}
    return "```json\n" + json.dumps({"document": "About " + first.split("] ", 1)[-1], "sections": sections}) + "\n```"


def smart_navigator(system, user):
    """TREE_NAVIGATE: pick the ids whose line shares the most words with the question."""
    k = int(re.search(r"at most (\d+) ids", system).group(1))
    question = set(tokenize(user.split("Question:", 1)[1].split("\n\n", 1)[0]))
    scored = []
    for m in re.finditer(r"^\[([\d.]+)\] (.+)$", user, re.M):
        scored.append((len(question & set(tokenize(m.group(2)))), m.group(1)))
    picks = [i for s, i in sorted(scored, key=lambda x: -x[0]) if s > 0][:k]
    return json.dumps({"thinking": "keyword overlap", "node_ids": picks})


def nav(*replies):
    """Scripted navigator: one reply per navigation call (the last one repeats)."""
    return [json.dumps(r) if isinstance(r, dict) else r for r in replies]


def chat_tasks(fake):
    return fake.chat.completions.tasks


# =================================================================== TODO V1
def test_V01_build_tree_mirrors_the_handbook_outline():
    tree = build_tree(DOCS)
    assert tree.root.node_id == "root" and tree.root.kind == "root" and tree.root.title == ROOT_TITLE
    docs = tree.documents
    assert [d.node_id for d in docs] == [f"{i:02d}" for i in range(1, 13)]
    assert all(d.kind == "document" for d in docs)

    pay = tree.find("04")
    assert pay.title == "Payments Platform Error Codes (ENG-RUN-PAY)" and pay.source == "04_payment_error_codes.md"
    assert [c.node_id for c in pay.children] == ["04.0", "04.1", "04.2", "04.3", "04.4", "04.5"]
    assert pay.children[0].title == "Overview" and "Ledgerline" in pay.children[0].text
    sig = tree.find("04.4")
    assert sig.title == "PAY-E4035 - Signature mismatch on bank file" and sig.kind == "section"
    assert sig.text.startswith("The PGP signature") and "##" not in sig.text
    assert sig.doc_title == pay.title and sig.source == pay.source and sig.is_leaf

    hybrid = tree.find("02")
    assert hybrid.children[0].node_id == "02.1"          # no intro -> no Overview
    glossary = tree.find("11")
    assert glossary.is_leaf and "UTR: Unique Transaction Reference" in glossary.text
    assert tree.by_id["04.4"] is sig


def test_V02_build_tree_loses_no_text():
    tree = build_tree(DOCS)
    for path in sorted(DOCS.glob("*.md")):
        doc = next(d for d in tree.documents if d.source == path.name)
        body = "\n".join(leaf.text for leaf in doc.leaves())
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith(("# ", "## ")):
                assert line.strip() in body, f"{path.name}: lost {line[:50]!r}"


def test_V03_build_tree_edge_cases(tmp_path):
    (tmp_path / "1_policy.md").write_text(
        "Intro without a title.\n\n## First\nalpha\n### Detail\nbeta\n\n## Empty\n\n## Last\ngamma\n", encoding="utf-8")
    (tmp_path / "2_notes.txt").write_text("plain notes\nline two\n", encoding="utf-8")
    (tmp_path / "3_data.json").write_text("{}", encoding="utf-8")
    (tmp_path / "4_upper.MD").write_text("# Upper\nonly an intro here\n", encoding="utf-8")
    t = build_tree(tmp_path)
    assert [d.node_id for d in t.documents] == ["01", "02", "03"]       # .json skipped, .MD kept
    pol = t.find("01")
    assert pol.title == "1_policy"                                      # no "# " line -> stem
    assert [c.node_id for c in pol.children] == ["01.0", "01.1", "01.3"]  # Overview first, empty "## Empty" skipped
    assert t.find("01.1").text == "alpha\n### Detail\nbeta"             # ### stays inside the section
    assert t.find("01.0").text == "Intro without a title."
    notes = t.find("02")
    assert notes.is_leaf and notes.title == "2_notes" and notes.text == "plain notes\nline two"
    upper = t.find("03")
    assert upper.is_leaf and upper.title == "Upper" and upper.text == "only an intro here"


# =================================================================== TODO V2
def test_V04_summarize_document_one_llm_call_fills_every_signpost(fake):
    tree = build_tree(DOCS)
    fake.chat.completions.handlers["TREE_SUMMARY"] = fake_summarizer
    pay = tree.find("04")
    assert summarize_document(pay) == 1
    call = fake.chat.completions.calls[0]
    assert len(fake.chat.completions.calls) == 1
    assert call["messages"][0]["content"].startswith("TASK: TREE_SUMMARY")
    assert "[04.4] PAY-E4035" in call["messages"][1]["content"]
    assert pay.summary == "About Payments Platform Error Codes (ENG-RUN-PAY)" and pay.summary_source == "llm"
    assert tree.find("04.4").summary == "About PAY-E4035 - Signature mismatch on bank file"
    assert all(c.summary_source == "llm" for c in pay.children)
    assert fake.embeddings.calls == 0


def test_V05_summarize_document_falls_back_per_node_and_never_crashes(fake):
    tree = build_tree(DOCS)
    pay = tree.find("04")
    fake.chat.completions.handlers["TREE_SUMMARY"] = "Sorry, I cannot help with that."
    assert summarize_document(pay) == 1
    assert pay.summary.startswith("Covers: Overview; PAY-E4031") and pay.summary_source == "extractive"
    assert tree.find("04.1").summary_source == "extractive" and tree.find("04.1").summary.startswith("The clearing partner")

    fake.chat.completions.handlers["TREE_SUMMARY"] = json.dumps(
        {"document": "Payment error runbook.", "sections": {"04.1": "Cut-off rejection.", "04.2": "  ", "04.3": 7}})
    summarize_document(pay)
    assert (pay.summary, pay.summary_source) == ("Payment error runbook.", "llm")
    assert (tree.find("04.1").summary, tree.find("04.1").summary_source) == ("Cut-off rejection.", "llm")
    assert {tree.find(i).summary_source for i in ("04.2", "04.3", "04.4")} == {"extractive"}

    fake.chat.completions.handlers["TREE_SUMMARY"] = json.dumps({"document": "Doc.", "sections": ["not", "a dict"]})
    summarize_document(pay)
    assert tree.find("04.4").summary_source == "extractive"

    fake.chat.completions.raise_exc = RuntimeError("gateway down")
    assert summarize_document(pay) == 1                              # RagError -> fallback, no crash
    assert pay.summary_source == "extractive"


def test_V06_summarize_tree_modes_and_disk_cache(fake, tmp_path):     # PROVIDED code, uses V1 + V2
    fake.chat.completions.handlers["TREE_SUMMARY"] = fake_summarizer
    cache = tmp_path / "cache.json"
    t1 = build_tree(DOCS)
    assert summarize_tree(t1, "llm", cache) == 12 and t1.summaries == "llm"
    assert cache.exists()
    t2 = build_tree(DOCS)
    assert summarize_tree(t2, "llm", cache) == 0                      # unchanged docs: free
    assert t2.find("04.4").summary == t1.find("04.4").summary and t2.find("04").summary_source == "cache"
    shifted = tmp_path / "docs"                                       # a new file that sorts FIRST shifts every id
    shifted.mkdir()
    (shifted / "00_new.md").write_text("# New policy\n\n## Rule\nBe kind.\n", encoding="utf-8")
    for f in DOCS.glob("*.md"):
        (shifted / f.name).write_bytes(f.read_bytes())
    t4 = build_tree(shifted)
    assert t4.find("05").title == t1.find("04").title
    assert summarize_tree(t4, "llm", cache) == 1                      # only the new document costs a call
    assert t4.find("05.4").summary == t1.find("04.4").summary
    assert len(fake.chat.completions.calls) == 13
    t3 = build_tree(DOCS)
    assert summarize_tree(t3, "extractive") == 0 and t3.find("07.3").summary.startswith("Sev-1 must be acknowledged")
    assert summarize_tree(t3, "none") == 0 and t3.find("07.3").summary == ""
    assert len(fake.chat.completions.calls) == 13
    assert extractive_summary("One. Two. " + "x" * 300, 20) == "One. Two."


# =================================================================== TODO V3
def test_V07_parse_selection_accepts_any_id_format_and_drops_inventions():
    allowed = ["01", "02", "04", "10", "11"]
    ids, thinking, ok = parse_selection(
        '```json\n{"thinking": " payments runbook ", "node_ids": ["04", 4, "[10]", " 11 ", "99", "04"]}\n```', allowed, 3)
    assert (ids, thinking, ok) == (["04", "10", "11"], "payments runbook", True)
    assert parse_selection('Sure! {"node_ids": [2]} hope that helps', allowed, 3) == (["02"], "", True)
    assert parse_selection('{"node_ids": ["4.2", "04.10"]}', ["04.2", "04.10", "04.1"], 4)[0] == ["04.2", "04.10"]
    assert parse_selection('{"node_ids": ["99", "x"]}', allowed, 3) == ([], "", False)
    assert parse_selection('{"node_ids": "04"}', allowed, 3) == ([], "", False)
    assert parse_selection("no json at all", allowed, 3) == ([], "", False)
    assert parse_selection(None, allowed, 3) == ([], "", False)
    assert parse_selection('{"node_ids": ["04"]}', allowed, 0) == ([], "", False)
    assert parse_selection('{"node_ids": [true, "01"]}', allowed, 3)[0] == ["01"]


# =================================================================== TODO V4
def test_V08_tree_search_walks_document_then_section(fake):
    tree = build_tree(DOCS)
    fake.chat.completions.handlers["TREE_NAVIGATE"] = nav(
        {"thinking": "error codes live in the payments runbook", "node_ids": ["04"]},
        {"thinking": "the section titled with the exact code", "node_ids": ["04.4"]},
    )
    res = tree_search("What does PAY-E4035 mean?", tree, max_docs=3, max_sections=4, max_steps=3)
    assert [n.node_id for n in res.nodes] == ["04.4"]
    assert res.llm_calls == 2 and res.fallback == ""
    s1, s2 = res.steps
    assert (s1.level, s1.picked, s1.ok) == (1, ["04"], True) and s1.thinking.startswith("error codes")
    assert s1.shown == [f"{i:02d}" for i in range(1, 13)]
    assert s2.shown == ["04.0", "04.1", "04.2", "04.3", "04.4", "04.5"] and s2.picked == ["04.4"]
    calls = fake.chat.completions.calls
    assert "at most 3 ids" in calls[0]["messages"][0]["content"] and "at most 4 ids" in calls[1]["messages"][0]["content"]
    assert "Question: What does PAY-E4035 mean?" in calls[0]["messages"][1]["content"]
    assert skeleton(tree.documents) in calls[0]["messages"][1]["content"]
    assert fake.embeddings.calls == 0                                 # vectorless: no embedding call at all


def test_V09_tree_search_covers_multi_part_questions_and_direct_leaves(fake):
    tree = build_tree(DOCS)
    fake.chat.completions.handlers["TREE_NAVIGATE"] = nav(
        {"thinking": "budget + pager", "node_ids": ["10", "07", "11"]},   # 11 (glossary) is a leaf: read directly
        {"thinking": "one section per part", "node_ids": ["10.1", "07.4", "01.1"]},  # 01.1 not shown -> dropped
    )
    res = tree_search("As a grad trainee, how much learning budget do I get and do I carry the on-call pager?", tree)
    assert [n.node_id for n in res.nodes] == ["11", "10.1", "07.4"]
    assert {n.source for n in res.nodes} == {"11_glossary.md", "10_learning_budget.md", "07_oncall_incidents.md"}
    assert res.steps[1].shown == [c.node_id for c in tree.find("10").children + tree.find("07").children]

    fake.chat.completions.handlers["TREE_NAVIGATE"] = nav({"node_ids": ["11"]})
    res = tree_search("What does UTR stand for?", tree)
    assert [n.node_id for n in res.nodes] == ["11"] and res.llm_calls == 1


def test_V10_tree_search_respects_max_steps_and_reads_whole_document(fake):
    tree = build_tree(DOCS)
    fake.chat.completions.handlers["TREE_NAVIGATE"] = nav({"node_ids": ["04", "05"]})
    res = tree_search("Payment and login error codes?", tree, max_docs=1, max_steps=1)
    assert [n.node_id for n in res.nodes] == ["04"] and res.llm_calls == 1     # max_docs=1 caps the pick
    d = node_document(res.nodes[0])
    assert d.metadata["chunk_id"] == "04_payment_error_codes.md::04"
    assert "PAY-E4031" in d.page_content and "PAY-E5000" in d.page_content


def test_V11_tree_search_falls_back_to_bm25_never_returns_nothing(fake):
    tree = build_tree(DOCS)
    fake.chat.completions.handlers["TREE_NAVIGATE"] = "I think the answer is in the payments section."
    res = tree_search("PAY-E4035 keeps coming in prod", tree)
    assert res.fallback == "bm25" and res.llm_calls == 1 and res.steps[0].ok is False
    assert res.nodes[0].node_id == "04.4"

    fake.chat.completions.handlers["TREE_NAVIGATE"] = nav({"node_ids": ["07"]}, {"node_ids": ["99"]})
    res = tree_search("who gets the page if there is no acknowledgement", tree)
    assert res.fallback == "bm25" and res.llm_calls == 2
    assert res.nodes and all(n.source == "07_oncall_incidents.md" for n in res.nodes)   # stays inside doc 07

    fake.chat.completions.raise_exc = RuntimeError("gateway down")
    res = tree_search("PAY-E4035", tree)
    assert res.fallback == "bm25" and res.llm_calls == 1 and res.nodes[0].node_id == "04.4"
    fake.chat.completions.raise_exc = None

    n_calls = len(fake.chat.completions.calls)
    assert tree_search("   ", tree).nodes == [] and len(fake.chat.completions.calls) == n_calls


# =================================================================== end to end
@pytest.fixture
def vectorless_app(fake, monkeypatch):
    from app import pipeline

    monkeypatch.setattr(pipeline.config, "vectorless_cache", None)      # never write into the repo in tests
    monkeypatch.setattr(pipeline.config, "vectorless_summaries", "llm")
    monkeypatch.setattr(pipeline.config, "vectorless_max_docs", 3)
    monkeypatch.setattr(pipeline.config, "vectorless_max_sections", 4)
    monkeypatch.setattr(pipeline.config, "vectorless_max_steps", 3)
    fake.chat.completions.handlers["TREE_SUMMARY"] = fake_summarizer
    fake.chat.completions.handlers["TREE_NAVIGATE"] = smart_navigator
    from app.main import app

    return app


def test_V12_chat_api_vectorless_end_to_end(fake, vectorless_app):
    from fastapi.testclient import TestClient # type: ignore

    fake.chat.completions.answer = "Re-sign the bank file with the current HSM key [1]."
    with TestClient(vectorless_app) as client:
        health = client.get("/api/health").json()
        assert health["tree"]["status"] == "ok" and health["tree"]["documents"] == 12
        emb_after_index = fake.embeddings.calls

        r = client.post("/api/chat", json={"question": "What does PAY-E4035 mean?", "mode": "vectorless"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "vectorless" and body["embedding_calls"] == 0
        assert body["index_llm_calls"] == 12 and body["llm_calls"] == 3          # 2 navigation + 1 answer
        assert [p["picked"][0]["node_id"] for p in body["tree_path"]] == ["04", "04.4"]
        assert body["sources"][0]["chunk_id"] == "04_payment_error_codes.md::04.4"
        assert body["citations"] == [1] and body["sources"][0]["cited"]
        assert any(row["evidence"] and row["selected"] for row in body["pool"])
        assert fake.embeddings.calls == emb_after_index                          # still no embedding call

        again = client.post("/api/chat", json={"question": "What does PAY-E4035 mean?", "mode": "vectorless"}).json()
        assert again["index_llm_calls"] == 0                                     # summaries are written once

        cmp = client.post("/api/compare", json={"question": "Can I WFH on Fridays?"}).json()
        assert set(cmp) == {"basic", "mqr", "mqr_rrf", "vectorless"}

        tree = client.get("/api/tree").json()
        assert len(tree["tree"]["children"]) == 12 and tree["summaries"] == "llm"
        ext = client.post("/api/tree/summarize", json={"mode": "extractive"}).json()
        assert ext["llm_calls"] == 0 and ext["summaries"] == "extractive"
        assert client.post("/api/tree/summarize", json={"mode": "magic"}).status_code == 422


def test_V13_evaluate_reports_quality_and_cost_per_mode(fake, rag_service):
    from app.pipeline import evaluate, load_eval_set

    fake.chat.completions.handlers["TREE_SUMMARY"] = fake_summarizer
    fake.chat.completions.handlers["TREE_NAVIGATE"] = smart_navigator
    questions = [q for q in load_eval_set(ROOT / "data" / "eval_set.json") if q["id"] in ("Q01", "Q03", "Q04")]
    out = evaluate(rag_service, questions, modes=("basic", "mqr_rrf", "vectorless"))
    s = out["summary"]
    v, b, r = s["vectorless"], s["basic"], s["mqr_rrf"]
    assert v["status"] == "ok" and v["questions"] == 3 and v["index_llm_calls"] == 12
    assert v["embedding_calls_per_q"] == 0 and 1 <= v["llm_calls_per_q"] <= 2   # 1 if a leaf doc was picked at level 1
    assert b["llm_calls_per_q"] == 0 and b["embedding_calls_per_q"] == 1
    assert r["llm_calls_per_q"] == 1                     # cold cache: MQR+RRF pays for its own rewrites
    assert v["hit_rate"] == 1.0 and all(row["vectorless"]["hit"] for row in out["rows"])
    assert {"avg_ms", "avg_context_chars", "fallbacks"} <= set(v)


def test_V14_vectorless_works_even_when_the_embedding_model_is_down(fake, monkeypatch):
    """The tree needs no embeddings: vectorless keeps answering while FAISS cannot be built."""
    from app.pipeline import RagService

    fake.chat.completions.handlers["TREE_SUMMARY"] = fake_summarizer
    fake.chat.completions.handlers["TREE_NAVIGATE"] = smart_navigator

    def broken(*a, **kw):
        raise RuntimeError("embeddings deployment missing")

    monkeypatch.setattr(fake.embeddings, "create", broken)
    svc = RagService(cfg=make_cfg())
    with pytest.raises(Exception):
        svc.reindex()
    assert svc.store.size == 0 and svc.tree is not None
    out = svc.run("vectorless", "What does PAY-E4035 mean?")
    assert out["sources"] and "PAY-E4035" in out["sources"][0]["text"]
