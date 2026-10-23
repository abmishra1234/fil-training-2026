"""
judge_tests/fakes.py - an OFFLINE stand-in for the OpenAI client.

`llm_client.get_client()` is monkeypatched to return FakeClient, so the whole
app (Basic RAG, MQR, MQR + RRF, Agentic RAG, FastAPI routes) runs with no
network, no credentials and no cost. Every chat / embedding request is
RECORDED so a test can assert exactly what would have been sent to the model.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from types import SimpleNamespace

DIM = 64
_WORD = re.compile(r"[a-z0-9]+")


def fake_vector(text: str) -> list[float]:
    """Deterministic bag-of-words hashing embedding (unit length)."""
    v = [0.0] * DIM
    for tok in _WORD.findall((text or "").lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0 if (h >> 8) % 2 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _text_of(messages) -> str:
    return "\n".join(str(m.get("content", "")) for m in messages)


def default_chat_reply(messages) -> str:
    system = str(messages[0].get("content", "")) if messages else ""
    allt = _text_of(messages)
    if "TASK: ROUTE" in system:
        return json.dumps({"route": "simple", "reason": "one fact", "reply": "", "clarify_question": ""})
    if "TASK: PLAN" in system:
        q = str(messages[-1].get("content", ""))
        return json.dumps({"sub_questions": [{"question": q, "tool": "search", "entity": ""}]})
    if "TASK: ASSESS" in system:
        n = len(re.findall(r"^\[\d+\] \(source:", allt, flags=re.M))
        return json.dumps({"relevant": list(range(1, n + 1)), "sufficient": True, "missing": []})
    if "TASK: CHECK" in system:
        return json.dumps({"grounded": True, "complete": True, "problem": ""})
    if "TASK: CONTEXTUALIZE" in system:
        return str(messages[-1].get("content", "")).split("Latest message:")[-1].strip()
    if "Write" in allt and "search queries" in allt:  # MQR rewrite prompt
        return "parking policy rules\nvisitor parking allowance\nparking permit process"
    return "FAKE-ANSWER: according to the handbook [1]."


class _Chat:
    def __init__(self, owner):
        self.owner = owner
        self.completions = self

    def create(self, model=None, messages=None, **kw):
        self.owner.chat_calls.append([dict(m) for m in (messages or [])])
        content = self.owner.chat_fn(messages or [])
        return SimpleNamespace(
            model=model,
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(total_tokens=1),
        )


class _Emb:
    def __init__(self, owner):
        self.owner = owner

    def create(self, model=None, input=None, **kw):
        items = input if isinstance(input, list) else [input]
        self.owner.embed_calls.append(list(items))
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=fake_vector(t)) for i, t in enumerate(items)])


class FakeLLM:
    """Records every request. `chat_fn(messages) -> str` decides the reply."""

    def __init__(self, chat_fn=None):
        self.chat_calls: list[list[dict]] = []
        self.embed_calls: list[list[str]] = []
        self.chat_fn = chat_fn or default_chat_reply

    def client(self):
        return SimpleNamespace(chat=_Chat(self), embeddings=_Emb(self))

    # ---- helpers for assertions
    def all_prompt_text(self) -> str:
        return "\n".join(_text_of(call) for call in self.chat_calls)

    def all_embedded_text(self) -> str:
        return "\n".join("\n".join(map(str, c)) for c in self.embed_calls)

    def reset(self):
        self.chat_calls.clear()
        self.embed_calls.clear()


def install(monkeypatch, fake: FakeLLM | None = None) -> FakeLLM:
    """Route every model call of the app through `fake`."""
    import llm_client

    fake = fake or FakeLLM()
    monkeypatch.setattr(llm_client, "get_client", fake.client)
    return fake
