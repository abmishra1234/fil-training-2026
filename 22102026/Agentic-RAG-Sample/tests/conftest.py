"""
Shared test setup. The tests NEVER call the real gateway: llm_client.get_client()
is replaced by a fake, so `pytest` runs anywhere, any time, for free.

FakeEmbeddings: a hashed bag-of-words vector. Like a real embedding model it is
fuzzy about rare identifiers: tokens that contain a digit (PAY-E4035 -> "e4035")
are IGNORED. That is exactly the weakness BM25 + RRF must fix.

FakeChat: answers the MQR prompt with canned rewrites (set fake.rewrites[question])
and answers the grounded prompt with fake.answer.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from types import SimpleNamespace

# Must be set BEFORE app modules are imported. load_dotenv() never overrides
# these, so your personal .env does not change test behaviour.
os.environ["LLM_MODE"] = "direct"
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["CHAT_MODEL"] = "azure/gpt-6-luna"
os.environ["EMBED_MODEL"] = "azure/text-embedding-ada-002"
os.environ["RAG_DOCS_DIR"] = "data/docs"

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from langchain_core.documents import Document  # noqa: E402

import llm_client  # noqa: E402
from app.config import RagConfig  # noqa: E402
from app.llm import GatewayEmbeddings  # noqa: E402
from app.vector_store import InMemoryVectorStore  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIM = 512
FAKE_STOPWORDS = set("a an the is are am was were be to of and or in on for with at by from do does did i my me we "
                     "our you your it this that what how can should if any there get now who next".split())


def fake_vector(text: str) -> list[float]:
    v = np.zeros(DIM)
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if any(ch.isdigit() for ch in tok) or tok in FAKE_STOPWORDS:
            continue  # "embedding model" is blind to codes / numbers and ignores filler words
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0
    v[0] += 0.01  # never a zero vector
    return v.tolist()


class FakeEmbeddingsAPI:
    def __init__(self):
        self.calls = 0
        self.inputs: list[list[str]] = []

    def create(self, model, input, **kw):
        self.calls += 1
        self.inputs.append(list(input))
        data = [SimpleNamespace(embedding=fake_vector(t), index=i) for i, t in enumerate(input)]
        return SimpleNamespace(data=list(reversed(data)))  # out of order on purpose


def _contextualize_default(system, user):
    return user.rsplit("Latest message:", 1)[-1].strip()


DEFAULT_AGENT_REPLIES = {
    "CONTEXTUALIZE": _contextualize_default,
    "ROUTE": '{"route": "simple", "reason": "one fact"}',
    "PLAN": '{"sub_questions": []}',
    "ASSESS": lambda system, user: '{"relevant": [%s], "sufficient": true, "missing": []}'
    % ", ".join(str(i) for i in range(1, user.count("\n[") + 2)),
    "ANSWER": "Here is the answer [1].",
    "CHECK": '{"grounded": true, "complete": true, "problem": ""}',
}


class FakeChatAPI:
    """
    Lab 1 prompts: MQR rewrites (self.rewrites) and grounded answers (self.answer).
    Lab 2 prompts start with "TASK: NAME": answered by self.handlers[NAME], which may be
    a string, a list of strings (used one per call, last one repeats) or a
    callable(system, user) -> str.
    """

    def __init__(self):
        self.handlers: dict = {}
        self.tasks: list[str] = []
        self.calls: list[dict] = []
        self.rewrites: dict[str, str] = {}
        self.default_rewrites = "alpha query\nbeta query\ngamma query"
        self.answer = "Use the rollover command [1]. Inform treasury [2][9]."
        self.raise_exc: Exception | None = None

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise self.raise_exc
        content = kwargs["messages"][-1]["content"]
        system = kwargs["messages"][0]["content"] if kwargs["messages"][0]["role"] == "system" else ""
        m = re.match(r"TASK: (\w+)", system)
        if m:
            task = m.group(1)
            self.tasks.append(task)
            h = self.handlers.get(task, DEFAULT_AGENT_REPLIES.get(task, ""))
            if isinstance(h, list):
                h = h.pop(0) if len(h) > 1 else h[0]
            text = h(system, content) if callable(h) else h
            msg = SimpleNamespace(content=text)
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)], model=kwargs.get("model"))
        if "different search queries" in content:
            q = content.rsplit("User question:", 1)[-1].strip()
            text = self.rewrites.get(q, self.default_rewrites)
        else:
            text = self.answer
        msg = SimpleNamespace(content=text)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], model=kwargs.get("model"))


class FakeClient:
    def __init__(self):
        self.embeddings = FakeEmbeddingsAPI()
        self.chat = SimpleNamespace(completions=FakeChatAPI())


@pytest.fixture
def fake(monkeypatch):
    """The fake gateway. fake.chat.completions.rewrites[...] / .answer / .raise_exc control it."""
    client = FakeClient()
    monkeypatch.setattr(llm_client, "get_client", lambda: client)
    return client


def make_cfg(**over) -> RagConfig:
    base = dict(
        docs_dir=ROOT / "data" / "docs", chunk_size=500, chunk_overlap=60, basic_k=5,
        mqr_num_queries=3, mqr_k=5, mqr_include_original=True, rrf_k=60, final_k=5,
        max_context_chars=6000,
    )
    base.update(over)
    return RagConfig(**base)


@pytest.fixture
def cfg():
    return make_cfg()


def doc(cid: str, text: str, **md) -> Document:
    return Document(page_content=text, metadata={"chunk_id": cid, "source": cid.split("#")[0], **md})


def make_store(texts: dict[str, str]) -> InMemoryVectorStore:
    """Small store from {chunk_id: text}. Needs the `fake` fixture active."""
    store = InMemoryVectorStore(GatewayEmbeddings())
    store.build([doc(cid, t) for cid, t in texts.items()])
    return store


@pytest.fixture
def handbook_store(fake, cfg):
    """The real NovaPay handbook (data/docs) indexed with fake embeddings."""
    from app.ingest import load_folder

    store = InMemoryVectorStore(GatewayEmbeddings())
    store.build(load_folder(cfg.docs_dir, cfg.chunk_size, cfg.chunk_overlap))
    return store


def ids(docs) -> list[str]:
    return [d.metadata["chunk_id"] for d in docs]


def contains(docs, needle: str) -> bool:
    return any(needle.lower() in d.page_content.lower() for d in docs)


# --------------------------------------------------------------------------- #
# Lab 2 (agent) fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def agent_cfg():
    from app.agent.config import AgentConfig

    return AgentConfig(search_mode="hybrid", max_subquestions=3, max_rounds=2, max_regenerations=1,
                       check_answer=True, max_context_chunks=8, history_messages=6, recursion_limit=40)


@pytest.fixture
def rag_service(fake):
    from app.pipeline import RagService

    svc = RagService(cfg=make_cfg())
    svc.reindex()
    return svc


@pytest.fixture
def agent(rag_service, agent_cfg):
    from app.agent.service import AgentService

    return AgentService(rag_service, agent_cfg)


@pytest.fixture
def nodes(rag_service, agent_cfg):
    from app.agent.graph_rag import EntityGraph
    from app.agent.nodes import AgentNodes

    graph = EntityGraph.build(list(rag_service.store.docs.values()))
    return AgentNodes(rag_service.store, graph, rag_service.cfg, agent_cfg)


def sub(i="r1-q1", q="hotel cap per night", tool="search", entity="", rnd=1):
    return {"id": i, "question": q, "tool": tool, "entity": entity, "round": rnd}


def ev(cid, text="some text", source=None, sub_id="r1-q1"):
    return {"chunk_id": cid, "source": source or cid.split("#")[0], "section": "", "text": text,
            "sub_id": sub_id, "tool": "search", "score": 0.0}
