"""
Observability tests - run fully offline.

A real OpenAI SDK client talks to an httpx.MockTransport (no network), and spans go
to an InMemorySpanExporter instead of LangSmith. We check that llm_client:
  * turns chat / embedding calls into spans with LangSmith-friendly attributes,
  * nests them under @traced pipeline steps, with obs_context metadata,
  * sends a W3C traceparent header to the gateway (same trace id as the span),
  * marks failures as error spans,
  * respects OBS_CAPTURE_CONTENT=false (metadata only).
"""
from __future__ import annotations

import dataclasses
import json

import httpx
import pytest
from openai import OpenAI

import llm_client

otel_sdk = pytest.importorskip("opentelemetry.sdk.trace")
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

SEEN_HEADERS: list[dict] = []


def _handler(request: httpx.Request) -> httpx.Response:
    SEEN_HEADERS.append(dict(request.headers))
    body = json.loads(request.content or b"{}")
    if request.url.path.endswith("/chat/completions"):
        if body.get("model") == "broken-model":
            return httpx.Response(404, json={"error": {"message": "model not found"}})
        return httpx.Response(200, json={
            "id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": body["model"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "pong"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 1, "total_tokens": 13},
        })
    if request.url.path.endswith("/embeddings"):
        n = len(body["input"]) if isinstance(body["input"], list) else 1
        return httpx.Response(200, json={
            "object": "list", "model": body["model"],
            "data": [{"object": "embedding", "index": i, "embedding": [0.1, 0.2, 0.3]} for i in range(n)],
            "usage": {"prompt_tokens": 4, "total_tokens": 4},
        })
    return httpx.Response(404)


@pytest.fixture()
def obs(monkeypatch):
    """In-memory OpenTelemetry + an instrumented OpenAI client on a mock transport."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(llm_client, "obs_settings", dataclasses.replace(
        llm_client.obs_settings, mode="otlp", project="pytest", capture_content=True, propagate=True))
    # Inject the test provider directly (init_observability(force=True) would re-read .env).
    with llm_client._obs_lock:
        llm_client._obs_state.update(started=True, active=True, backend="custom", provider=provider)
        monkeypatch.setattr(llm_client, "_tracer", provider.get_tracer("test"))
    client = OpenAI(api_key="test", base_url="https://gateway.test/v1",
                    http_client=llm_client._http_client(transport=httpx.MockTransport(_handler)), max_retries=0)
    llm_client.instrument_client(client)
    SEEN_HEADERS.clear()
    yield client, exporter
    llm_client._obs_state.update(started=False, active=False, backend="off", provider=None)


def _by_name(exporter, prefix):
    return [s for s in exporter.get_finished_spans() if s.name.startswith(prefix)]


def test_chat_call_becomes_llm_span(obs):
    client, exporter = obs
    reply = client.chat.completions.create(model="azure/gpt-6-luna",
                                           messages=[{"role": "user", "content": "ping"}])
    assert reply.choices[0].message.content == "pong"
    [sp] = _by_name(exporter, "chat")
    a = sp.attributes
    assert a["langsmith.span.kind"] == "llm"
    assert a["gen_ai.request.model"] == "azure/gpt-6-luna"
    assert a["gen_ai.prompt.0.content"] == "ping"
    assert a["gen_ai.completion.0.content"] == "pong"
    assert a["gen_ai.usage.input_tokens"] == 12 and a["gen_ai.usage.total_tokens"] == 13


def test_traceparent_sent_to_gateway_matches_span(obs):
    client, exporter = obs
    client.chat.completions.create(model="m", messages=[{"role": "user", "content": "x"}])
    [sp] = _by_name(exporter, "chat")
    tp = SEEN_HEADERS[-1].get("traceparent")
    assert tp, "traceparent header missing"
    assert tp.split("-")[1] == format(sp.context.trace_id, "032x")


def test_nesting_metadata_and_embeddings(obs):
    client, exporter = obs

    @llm_client.traced("retrieve_docs", kind="retriever")
    def retrieve(q):
        client.embeddings.create(model="azure/text-embedding-ada-002", input=[q])
        return [{"page_content": "Passwords expire after 90 days."}]

    @llm_client.traced("rag_answer")
    def answer(q):
        docs = retrieve(q)
        r = client.chat.completions.create(model="m", messages=[{"role": "user", "content": docs[0]["page_content"]}])
        return r.choices[0].message.content

    with llm_client.obs_context(session_id="thread-1", user_id="u-42", tags=["pytest"]):
        assert answer("When do passwords expire?") == "pong"

    root = _by_name(exporter, "rag_answer")[0]
    ret = _by_name(exporter, "retrieve_docs")[0]
    emb = _by_name(exporter, "embeddings")[0]
    chat = _by_name(exporter, "chat")[0]
    assert ret.parent.span_id == root.context.span_id
    assert emb.parent.span_id == ret.context.span_id
    assert chat.parent.span_id == root.context.span_id
    assert len({s.context.trace_id for s in (root, ret, emb, chat)}) == 1
    assert ret.attributes["langsmith.span.kind"] == "retriever"
    assert emb.attributes["langsmith.span.kind"] == "embedding"
    for s in (root, ret, emb, chat):
        assert s.attributes["langsmith.metadata.session_id"] == "thread-1"
        assert "pytest" in s.attributes["langsmith.span.tags"]
    assert "When do passwords expire?" in root.attributes["input.value"]
    assert root.attributes["output.value"] == "pong"


def test_errors_are_recorded(obs):
    client, exporter = obs
    with pytest.raises(Exception):
        client.chat.completions.create(model="broken-model", messages=[{"role": "user", "content": "x"}])
    [sp] = _by_name(exporter, "chat")
    assert sp.status.status_code.name == "ERROR"
    assert any(e.name == "exception" for e in sp.events)


def test_metadata_only_mode(obs, monkeypatch):
    client, exporter = obs
    monkeypatch.setattr(llm_client, "obs_settings",
                        dataclasses.replace(llm_client.obs_settings, capture_content=False))
    client.chat.completions.create(model="m", messages=[{"role": "user", "content": "secret customer data"}])
    [sp] = _by_name(exporter, "chat")
    assert "gen_ai.prompt.0.content" not in sp.attributes
    assert "gen_ai.completion.0.content" not in sp.attributes
    assert sp.attributes["gen_ai.usage.total_tokens"] == 13  # usage and model are still there


def test_off_mode_adds_no_spans_and_no_header(obs):
    client, exporter = obs
    llm_client._obs_state["active"] = False
    client.chat.completions.create(model="m", messages=[{"role": "user", "content": "x"}])
    assert exporter.get_finished_spans() == ()
    assert "traceparent" not in SEEN_HEADERS[-1]


def test_status_never_leaks_secrets(monkeypatch):
    monkeypatch.setattr(llm_client, "obs_settings",
                        dataclasses.replace(llm_client.obs_settings, api_key="lsv2_sk_SECRET"))
    text = json.dumps(llm_client.observability_status()) + llm_client.describe_observability()
    assert "SECRET" not in text


def test_langgraph_runs_join_the_trace_via_otel(monkeypatch):
    """OTel-only LangSmith mode: graph nodes, tools and chat models become child spans of our span."""
    from opentelemetry import trace
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from langchain_core.tools import tool
    from langchain_core.tracers.langchain import wait_for_all_tracers
    from langgraph.graph import END, START, StateGraph
    from typing_extensions import TypedDict

    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):  # first test to need the global provider
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    for k in ("LANGSMITH_TRACING", "LANGSMITH_OTEL_ENABLED", "LANGSMITH_OTEL_ONLY", "LANGSMITH_PROJECT",
              "LANGSMITH_API_KEY", "LANGSMITH_TRACING_MODE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_test")
    llm_client._enable_langchain_otel(dataclasses.replace(llm_client.obs_settings, project="pytest"))
    monkeypatch.setattr(llm_client, "_tracer", provider.get_tracer("test"))
    monkeypatch.setitem(llm_client._obs_state, "active", True)

    chat = FakeListChatModel(responses=["sunny"])

    @tool
    def get_weather(city: str) -> str:
        """Weather for a city."""
        return "sunny"

    class S(TypedDict):
        q: str
        a: str

    g = StateGraph(S)
    g.add_node("model", lambda s: {"a": chat.invoke(s["q"]).content})
    g.add_node("tools", lambda s: {"a": get_weather.invoke({"city": "SF"})})
    g.add_edge(START, "model")
    g.add_edge("model", "tools")
    g.add_edge("tools", END)
    with llm_client.span("POST /api/agent/chat"):
        g.compile().invoke({"q": "weather in SF?"})
    wait_for_all_tracers()
    provider.force_flush()

    spans = {s.name: s for s in exporter.get_finished_spans()}
    names = {s.context.span_id: s.name for s in spans.values()}
    assert names[spans["LangGraph"].parent.span_id] == "POST /api/agent/chat"
    assert names[spans["get_weather"].parent.span_id] == "tools"
    assert spans["get_weather"].attributes["langsmith.span.kind"] == "tool"
    assert spans["FakeListChatModel"].attributes["langsmith.span.kind"] == "llm"
    for k in ("LANGSMITH_TRACING", "LANGSMITH_OTEL_ENABLED", "LANGSMITH_OTEL_ONLY"):
        monkeypatch.setenv(k, "false")  # leave the process clean for other tests


def test_fil_api_url_derived_from_otel_endpoint():
    url = "https://fil-ai-observability-uat.k8s.npiek8sinfra1np1.npaws.ukfilcld/api/v1/otel"
    assert llm_client._default_api_url("fil", url) == url[: -len("/otel")]
    assert llm_client._parse_metadata("team=ai-batch, app=rag-lab,bad") == {"team": "ai-batch", "app": "rag-lab"}


def test_trace_headers_for_custom_http_calls(obs):
    _, exporter = obs
    with llm_client.span("filcopilot.ask", kind="llm") as sp:
        h = llm_client.trace_headers()
    assert h["traceparent"].split("-")[1] == format(sp.get_span_context().trace_id, "032x")
