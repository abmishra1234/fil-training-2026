"""Lab 2 · A01-A07: tools (calculator, hybrid search) and Graph RAG lite."""
import pytest # type: ignore

from app.agent.graph_rag import EntityGraph, extract_entities
from app.agent.tools import CalcError, entity_tool, hybrid_search, safe_calculate
from app.basic_rag import basic_retrieve

from .conftest import ids, make_store
from .test_rerank import CODES


# ------------------------------------------------------------------ TODO 1
def test_A01_calculator_computes_and_formats():
    assert safe_calculate("1.5 * 7") == "10.5"
    assert safe_calculate("3 * (2000 + 7500)") == "28500"
    assert safe_calculate("round(50000/12)") == "4167"
    assert safe_calculate("-2 + 10 // 3") == "1"
    assert safe_calculate("max(3, 7) - min(1, 2)") == "6"
    assert safe_calculate("2/3") == "0.67"
    assert safe_calculate(" 2 ** 10 ") == "1024"
    assert safe_calculate("abs(-12000) % 7") == "2"


UNSAFE = [
    "__import__('os').system('ls')", "a + 1", "(1).real", "'a' * 3", "True + 1", "2 ** 1000",
    "1 / 0", "5 % 0", "", "   ", "1 +", "1" * 201, "round(2.5, ndigits=1)", "open('x')", "[1, 2]", "lambda: 1",
]


def test_A02_calculator_rejects_anything_unsafe():
    for expr in UNSAFE:
        with pytest.raises(CalcError):
            safe_calculate(expr)


# ------------------------------------------------------------------ TODO 2
def test_A03_hybrid_search_finds_exact_code_that_semantic_search_misses(fake):
    store = make_store(CODES)
    q = "PAY-E4035 settlement batch problem"
    assert "pay#7" not in ids(basic_retrieve(store, q, 3)), "precondition: embeddings miss the code"
    calls_before = fake.chat.completions.calls[:]
    out = hybrid_search(store, q, k_each=3, final_k=5)
    rescued = [d for d in out if d.metadata["chunk_id"] == "pay#7"]
    assert rescued and rescued[0].metadata["rrf_ranks"] == [None, 1]  # found ONLY by BM25 over the whole corpus
    assert fake.chat.completions.calls == calls_before  # zero LLM calls


def test_A04_hybrid_search_edge_cases(fake, handbook_store):
    assert hybrid_search(handbook_store, "   ") == []
    assert hybrid_search(make_store({}), "anything") == []
    out = hybrid_search(handbook_store, "hotel cap per night metro", final_k=4)
    assert 1 <= len(out) <= 4 and len(set(ids(out))) == len(out)
    assert all(d.metadata.get("rrf_score") is not None for d in out)


# ------------------------------------------------------------------ Graph RAG lite (provided, but test it)
def test_A05_entity_lookup_aggregates_across_documents(handbook_store):
    g = EntityGraph.build(list(handbook_store.docs.values()))
    found = g.lookup("graduate trainees")
    assert found["entity"] == "graduate trainee"
    assert {"01_leave_policy.md", "02_hybrid_working.md", "07_oncall_incidents.md", "10_learning_budget.md"} <= set(found["documents"])
    first = [d.metadata["source"] for d in found["chunks"][: len(found["documents"])]]
    assert len(set(first)) == len(first)  # one chunk per document first -> every document is covered


def test_A06_entity_resolution_aliases_and_unknowns(handbook_store):
    g = EntityGraph.build(list(handbook_store.docs.values()))
    assert g.resolve("PAY-E4035") == "PAY-E4035"
    assert g.resolve("pay-e4035") == "PAY-E4035"
    assert g.resolve("Hardware Security Module") == "HSM"
    assert g.resolve("grad trainees") == "graduate trainee"
    assert g.resolve("") is None and g.resolve("quantum physics") is None
    assert g.lookup("quantum physics") is None
    assert entity_tool(g, "quantum physics") == ([], None)


def test_A07_entities_and_graph_edges():
    ents = extract_entities("PAY-E4035: re-sign with the HSM key at NovaPay, then page the on-call engineer via PagerNova.")
    assert {"PAY-E4035", "HSM", "on-call", "PagerNova"} <= ents
    assert "NovaPay" not in ents  # hub node ignored
    from langchain_core.documents import Document
    docs = [Document(page_content="PAY-E4035 re-sign with the HSM key", metadata={"chunk_id": "a#0", "source": "a"}),
            Document(page_content="HSM stores signing keys. PAY-E4035 again", metadata={"chunk_id": "b#0", "source": "b"})]
    g = EntityGraph.build(docs)
    assert dict(g.neighbours("PAY-E4035")) == {"HSM": 2}
