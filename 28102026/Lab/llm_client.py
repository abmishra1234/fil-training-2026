"""
llm_client.py - ONE place that decides how we talk to the LLM *and* how we observe it.

Every sample script does:

    from llm_client import get_client, settings
    client = get_client()

and then uses the standard OpenAI SDK (client.chat..., client.embeddings..., ...).
Nothing else in the samples knows or cares whether we are inside FIL or not.

Two switches in .env control everything:

    LLM_MODE=enterprise   -> FIL AI Gateway, Azure AD token via MSAL (students)
    LLM_MODE=direct       -> OpenAI (or any OpenAI-compatible endpoint) with an API key

    OBS_MODE=fil          -> OpenTelemetry via the fil-aiobs SDK -> FIL AI Observability -> LangSmith
    OBS_MODE=otlp         -> plain OpenTelemetry straight to LangSmith's OTLP endpoint (home use)
    OBS_MODE=off          -> no telemetry (default when unset; tests run like this)

What you get for free once OBS_MODE is on
-----------------------------------------
* every client.chat.completions.create(...) becomes an LLM span with model, messages,
  answer, token usage and latency (LangSmith shows it as an "llm" run with cost);
* every client.embeddings.create(...) becomes an embedding span;
* the W3C `traceparent` header is sent to the gateway, so gateway-side spans join your trace;
* spans are flushed when the process exits (scripts don't lose the last trace);
* LangChain / LangGraph runs (graph nodes, tools, ChatOpenAI) join the same trace through the
  LangSmith SDK's OpenTelemetry-only mode (OBS_TRACE_LANGCHAIN=true, the default).

Datasets, experiments, prompts and feedback use the LangSmith SDK against the FIL LangSmith
REST API (<observability host>/api/v1):  client = get_langsmith_client()

For your own pipeline steps (retrieve, rerank, build_prompt, tools ...):

    from llm_client import traced, obs_context

    @traced("retrieve_docs", kind="retriever")
    def retrieve(question): ...

    with obs_context(session_id=thread_id, user_id="trainee-42"):
        answer(question)          # every span inside carries this metadata -> LangSmith Threads

Observability must never break the app: if telemetry cannot start, a warning is
printed and the app keeps working with OBS_MODE effectively 'off'.
"""

from __future__ import annotations

import atexit
import contextlib
import contextvars
import dataclasses
import functools
import inspect
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

import httpx
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from the folder this file lives in (works from scripts AND notebooks).
load_dotenv(Path(__file__).with_name(".env"))

log = logging.getLogger("llm_client")


def _env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if value is not None:
        value = value.strip()
    if required and not value:
        raise RuntimeError(
            f"Missing setting {name!r}. Copy .env.example to .env and fill it in "
            f"(LLM_MODE is currently {os.getenv('LLM_MODE', 'not set')!r})."
        )
    return value or None


def _env_bool(name: str, default: bool) -> bool:
    raw = (_env(name) or "").lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _model(kind: str, mode: str, default: str) -> str:
    """ENTERPRISE_CHAT_MODEL / DIRECT_CHAT_MODEL win; legacy CHAT_MODEL is the fallback."""
    prefix = "ENTERPRISE" if mode == "enterprise" else "DIRECT"
    return _env(f"{prefix}_{kind}_MODEL") or _env(f"{kind}_MODEL") or default


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Settings:
    mode: str
    # model names - the gateway routes by model name, so keep them in config
    chat_model: str
    embed_model: str
    tts_model: str
    stt_model: str
    image_model: str
    # networking
    timeout: float
    max_retries: int
    ca_bundle: str | None


_MODE = (_env("LLM_MODE", "direct") or "direct").lower()

settings = Settings(
    mode=_MODE,
    chat_model=_model("CHAT", _MODE, "azure/gpt-6-luna" if _MODE == "enterprise" else "gpt-4o-mini"),
    embed_model=_model("EMBED", _MODE, "azure/text-embedding-ada-002" if _MODE == "enterprise" else "text-embedding-3-small"),
    tts_model=_env("TTS_MODEL", "gpt-4o-mini-tts"),
    stt_model=_env("STT_MODEL", "gpt-4o-transcribe"),
    image_model=_env("IMAGE_MODEL", "gpt-image-1"),
    timeout=float(_env("LLM_TIMEOUT_SECONDS", "60")),
    max_retries=int(_env("LLM_MAX_RETRIES", "2")),
    ca_bundle=_env("CA_BUNDLE"),
)


@dataclass(frozen=True)
class ObsSettings:
    mode: str                 # fil | otlp | off
    project: str              # LangSmith project that receives the traces
    endpoint: str | None      # FIL AI Observability URL (fil) or LangSmith OTLP base URL (otlp)
    api_key: str | None       # LangSmith API key (lsv2_...)
    service_name: str         # OpenTelemetry service.name
    environment: str          # deployment.environment + langsmith metadata
    console_export: bool      # also print spans to the console (debugging)
    capture_content: bool     # send prompts / answers? False = metadata only
    max_content_chars: int    # truncate long prompts / answers
    propagate: bool           # send traceparent to the LLM gateway
    sample_rate: float        # otlp mode only: fraction of traces kept
    trace_langchain: bool     # LangChain / LangGraph runs -> the same OTel route (OTel-only mode)
    metadata: dict            # standard keys stamped on every span (team, app, use_case ...)
    api_url: str | None       # LangSmith REST API for the SDK Client: datasets, prompts, feedback


OBS_DEFAULT_ENDPOINTS = {
    "fil": "https://fil-ai-observability-uat.k8s.npiek8sinfra1np1.npaws.ukfilcld/api/v1/otel",
    "otlp": "https://api.smith.langchain.com/otel",
}


def _parse_metadata(raw: str | None) -> dict:
    """OBS_METADATA=team=ai-batch,app=rag-lab,use_case=hr-helpdesk -> dict"""
    out = {}
    for pair in (raw or "").split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            if k.strip():
                out[k.strip()] = v.strip()
    return out


def _default_api_url(mode: str, endpoint: str | None) -> str | None:
    """FIL: the OTLP endpoint is <base>/api/v1/otel and the LangSmith REST API is <base>/api/v1."""
    if endpoint and endpoint.rstrip("/").endswith("/otel"):
        return endpoint.rstrip("/")[: -len("/otel")]
    return None


def _load_obs_settings() -> ObsSettings:
    mode = (_env("OBS_MODE", "off") or "off").lower()
    endpoint = _env("OBS_ENDPOINT") or OBS_DEFAULT_ENDPOINTS.get(mode)
    return ObsSettings(
        mode=mode,
        project=_env("LANGSMITH_PROJECT") or "FilCopilot-Observability",
        endpoint=endpoint,
        api_key=_env("LANGSMITH_API_KEY"),
        service_name=_env("OBS_SERVICE_NAME") or "llm-app",
        environment=_env("OBS_ENVIRONMENT") or (_env("FIL_ENV") or "dev"),
        console_export=_env_bool("OBS_CONSOLE_EXPORT", False),
        capture_content=_env_bool("OBS_CAPTURE_CONTENT", True),
        max_content_chars=int(_env("OBS_MAX_CONTENT_CHARS", "4000")),
        propagate=_env_bool("OBS_PROPAGATE_CONTEXT", True),
        sample_rate=float(_env("OBS_SAMPLE_RATE", "1.0")),
        trace_langchain=_env_bool("OBS_TRACE_LANGCHAIN", True),
        metadata=_parse_metadata(_env("OBS_METADATA")),
        api_url=_env("LANGSMITH_ENDPOINT") or _default_api_url(mode, endpoint),
    )


obs_settings = _load_obs_settings()


# --------------------------------------------------------------------------- #
# Enterprise mode: Azure AD (Entra ID) client-credentials token via MSAL
# --------------------------------------------------------------------------- #
FIL_SCOPES = {
    "uat": "https://uat.filxgptnp.fil.com/.default",
    "dev": "https://dev.filxgptnp.fil.com/.default",
}

_msal_app = None  # created once, so MSAL's in-memory token cache is reused
_msal_lock = threading.Lock()


def _fil_scope() -> str:
    # An explicit FIL_SCOPE wins; otherwise pick it from FIL_ENV (uat | dev).
    explicit = _env("FIL_SCOPE")
    if explicit:
        return explicit
    env = (_env("FIL_ENV", "uat") or "uat").lower()
    if env not in FIL_SCOPES:
        raise RuntimeError(f"FIL_ENV must be one of {list(FIL_SCOPES)}, got {env!r}")
    return FIL_SCOPES[env]


def get_access_token() -> str:
    """Return a valid FIL gateway token. MSAL returns the cached one until it is near expiry."""
    global _msal_app
    from msal import ConfidentialClientApplication  # only needed in enterprise mode

    with _msal_lock:
        if _msal_app is None:
            tenant_id = _env("FIL_TENANT_ID", required=True)
            _msal_app = ConfidentialClientApplication(
                client_id=_env("FIL_CLIENT_ID", required=True),
                client_credential=_env("FIL_CLIENT_SECRET", required=True),
                authority="https://login.microsoftonline.com/" + tenant_id,
            )

    result = _msal_app.acquire_token_for_client(scopes=[_fil_scope()])
    if "access_token" not in result:
        raise RuntimeError(
            "Could not get a token from Azure AD: "
            f"{result.get('error')}: {result.get('error_description')}"
        )
    return result["access_token"]


class _BearerTokenAuth(httpx.Auth):
    """
    Puts a *fresh* FIL token on every request.

    Tokens last ~1 hour. If we passed the token once as api_key, a long job
    would start failing with 401 halfway. MSAL serves the token from cache,
    so it only really goes to Azure AD when the token is expiring.
    """

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {get_access_token()}"
        yield request


# =========================================================================== #
#  OBSERVABILITY  (OpenTelemetry -> LangSmith)
# =========================================================================== #
# LangSmith reads standard OpenTelemetry GenAI attributes plus a few
# langsmith.* attributes. These are the ones we write:
#   langsmith.span.kind        llm | chain | retriever | tool | embedding | prompt | parser
#   langsmith.metadata.<key>   searchable metadata (session_id -> Threads tab)
#   langsmith.span.tags        comma-separated tags
#   gen_ai.*                   model, messages, completion, token usage
#   input.value / output.value inputs / outputs of non-LLM steps
_obs_lock = threading.Lock()
_obs_state: dict[str, Any] = {"started": False, "active": False, "backend": "off", "provider": None, "reason": ""}
_tracer = None
_fil_build_headers: Callable[..., Any] | None = None
_metadata_var: contextvars.ContextVar[dict] = contextvars.ContextVar("obs_metadata", default={})
_tags_var: contextvars.ContextVar[tuple] = contextvars.ContextVar("obs_tags", default=())


def _get_tracer():
    """The real tracer once observability is on, or OpenTelemetry's no-op tracer."""
    if _tracer is not None:
        return _tracer
    try:
        from opentelemetry import trace
        return trace.get_tracer("llm_client")  # no-op until a provider is installed
    except ImportError:
        return None


def _resource_attributes() -> dict:
    return {
        "service.name": obs_settings.service_name,
        "deployment.environment": obs_settings.environment,
        "llm.mode": settings.mode,
    }


def _start_fil(o: ObsSettings):
    """Exactly the FIL snippet: fil_aiobs.telemetry.init_otel(...) -> FIL AI Observability -> LangSmith."""
    global _fil_build_headers
    from fil_aiobs.telemetry import init_otel  # FIL internal package (FIL PyPI mirror)

    if not o.api_key:
        raise RuntimeError("LANGSMITH_API_KEY is empty (needed by the FIL observability endpoint).")
    provider = init_otel(
        endpoint=o.endpoint,
        x_api_key=o.api_key,
        project_name=o.project,
        console_export=o.console_export,
    )
    try:  # optional helper from the same SDK; used for gateway header propagation
        from fil_aiobs.decorators import build_otel_headers
        _fil_build_headers = build_otel_headers
    except ImportError:
        _fil_build_headers = None
    return provider


def _start_otlp(o: ObsSettings, extra_processors: list | None = None):
    """Plain OpenTelemetry SDK -> LangSmith OTLP endpoint (outside FIL / at home)."""
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    provider = TracerProvider(
        resource=Resource.create(_resource_attributes()),
        sampler=ParentBased(TraceIdRatioBased(max(0.0, min(1.0, o.sample_rate)))),
    )
    if o.endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        if not o.api_key:
            raise RuntimeError("LANGSMITH_API_KEY is empty (needed to send traces to LangSmith).")
        exporter = OTLPSpanExporter(
            endpoint=o.endpoint.rstrip("/") + "/v1/traces",
            headers={"x-api-key": o.api_key, "Langsmith-Project": o.project},
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    if o.console_export:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    for proc in extra_processors or []:
        provider.add_span_processor(proc)
    return provider


def init_observability(force: bool = False, provider=None) -> bool:
    """
    Start OpenTelemetry once per process. Safe to call many times.
    Returns True when spans are being exported.

    `provider` lets tests (or an app that already owns a TracerProvider) inject one.
    """
    global _tracer, obs_settings
    with _obs_lock:
        if _obs_state["started"] and not force:
            return _obs_state["active"]
        if force:
            obs_settings = _load_obs_settings()
        _obs_state.update(started=True, active=False, backend="off", reason="")
        o = obs_settings

        try:
            from opentelemetry import trace
        except ImportError:
            _obs_state["reason"] = "opentelemetry-api not installed (pip install -r requirements.txt)"
            return False

        try:
            if provider is not None:
                backend = "custom"
            elif o.mode == "off":
                _obs_state["reason"] = "OBS_MODE=off"
                return False
            elif o.mode == "fil":
                provider = _start_fil(o)
                backend = "fil-aiobs"
            elif o.mode == "otlp":
                provider = _start_otlp(o)
                backend = "otlp"
            else:
                raise RuntimeError(f"OBS_MODE must be 'fil', 'otlp' or 'off', got {o.mode!r}")
        except Exception as err:  # noqa: BLE001 - telemetry must never break the app
            _obs_state["reason"] = f"{type(err).__name__}: {err}"
            log.warning("Observability disabled: %s", _obs_state["reason"])
            print(f"[observability] DISABLED - {_obs_state['reason']}")
            return False

        # init_otel normally installs the global provider itself; make sure of it.
        if provider is not None and isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
            trace.set_tracer_provider(provider)
        _tracer = (provider.get_tracer("llm_client") if provider is not None and hasattr(provider, "get_tracer")
                   else trace.get_tracer("llm_client"))
        _obs_state.update(active=True, backend=backend, provider=provider)
        if o.trace_langchain and backend != "custom":
            _enable_langchain_otel(o)
        if not getattr(init_observability, "_atexit", False):
            atexit.register(shutdown_observability)
            init_observability._atexit = True  # type: ignore[attr-defined]
        return True


def _enable_langchain_otel(o: ObsSettings) -> None:
    """
    LangChain / LangGraph runs (chains, graph nodes, tools, ChatOpenAI ...) are traced by the
    LangSmith SDK. In OTel-only mode the SDK does NOT call the LangSmith API: it reuses the
    OpenTelemetry provider that is already installed (fil-aiobs's), so those runs travel the
    same FIL route and nest under our spans. Must run AFTER the provider is installed.
    """
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
    os.environ["LANGSMITH_OTEL_ONLY"] = "true"          # never send directly to a LangSmith API
    if os.environ.get("LANGSMITH_TRACING_MODE"):         # newer SDKs: this one takes precedence
        os.environ["LANGSMITH_TRACING_MODE"] = "otel"
    os.environ["LANGSMITH_PROJECT"] = o.project
    try:  # the SDK caches env lookups; make it see the values we just set
        from langsmith import utils as ls_utils
        ls_utils.get_env_var.cache_clear()
    except Exception:  # noqa: BLE001 - langsmith not installed or older SDK
        pass


def get_langsmith_client():
    """
    LangSmith SDK client for datasets, experiments, prompts and feedback.
    Inside FIL it talks to the FIL LangSmith REST API (<observability host>/api/v1),
    as in the FIL 'Dataset generation using Python' example. Traces still go via OpenTelemetry.
    """
    from langsmith import Client

    o = obs_settings
    if not o.api_key:
        raise RuntimeError("LANGSMITH_API_KEY is empty.")
    kwargs = {"api_key": o.api_key}
    if o.api_url:
        kwargs["api_url"] = o.api_url
    try:  # newer SDKs: runs created by evaluate() go to the API, not to OpenTelemetry
        return Client(tracing_mode="langsmith", **kwargs)
    except TypeError:
        return Client(**kwargs)


def flush_observability(timeout_millis: int = 10_000) -> bool:
    """Push buffered spans now. Call at the end of short scripts and notebooks."""
    if obs_settings.trace_langchain:
        try:  # LangChain hands runs to its tracer on a background thread
            from langchain_core.tracers.langchain import wait_for_all_tracers
            wait_for_all_tracers()
        except Exception:  # noqa: BLE001
            pass
    provider = _obs_state.get("provider")
    if provider is not None and hasattr(provider, "force_flush"):
        try:
            return bool(provider.force_flush(timeout_millis))
        except Exception:  # noqa: BLE001
            return False
    return True


def shutdown_observability() -> None:
    flush_observability()
    provider = _obs_state.get("provider")
    if provider is not None and hasattr(provider, "shutdown"):
        with contextlib.suppress(Exception):
            provider.shutdown()
    _obs_state.update(active=False, provider=None)


def observability_status() -> dict:
    """What is configured and whether it is running (never contains secrets)."""
    o = obs_settings
    return {
        "mode": o.mode,
        "active": _obs_state["active"],
        "backend": _obs_state["backend"],
        "project": o.project,
        "endpoint": o.endpoint,
        "api_key_set": bool(o.api_key),
        "capture_content": o.capture_content,
        "trace_langchain": o.trace_langchain,
        "api_url": o.api_url,
        "metadata": o.metadata,
        "reason": _obs_state["reason"],
    }


# ---- helpers that write LangSmith-friendly attributes ---------------------- #
def _clip(text: Any) -> str:
    s = text if isinstance(text, str) else _to_json(text)
    limit = obs_settings.max_content_chars
    return s if len(s) <= limit else s[:limit] + f"... [truncated {len(s) - limit} chars]"


def _jsonable(o: Any) -> Any:
    """json.dumps fallback: pydantic / LangChain Documents become dicts, anything else a short tag
    (never dump big objects such as vector stores or numpy matrices into a span)."""
    if hasattr(o, "model_dump"):
        with contextlib.suppress(Exception):
            return o.model_dump()
    if hasattr(o, "page_content"):
        return {"page_content": o.page_content, "metadata": getattr(o, "metadata", {})}
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        with contextlib.suppress(Exception):
            return {f.name: getattr(o, f.name) for f in dataclasses.fields(o)}
    if isinstance(o, (set, tuple)):
        return list(o)
    return f"<{type(o).__name__}>"


def _to_json(value: Any) -> str:
    try:
        return json.dumps(value, default=_jsonable, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return repr(value)[:500]


def _set(span, key: str, value: Any) -> None:
    if value is None or span is None:
        return
    if not isinstance(value, (str, bool, int, float)):
        value = _to_json(value)
    span.set_attribute(key, value)


def _apply_context(span, kind: str, metadata: dict | None = None, tags: list | tuple | None = None) -> None:
    _set(span, "langsmith.span.kind", kind)
    meta = {"environment": obs_settings.environment, **obs_settings.metadata, **_metadata_var.get(), **(metadata or {})}
    for k, v in meta.items():
        _set(span, f"langsmith.metadata.{k}", v)
    all_tags = list(dict.fromkeys([*_tags_var.get(), *(tags or [])]))
    if all_tags:
        _set(span, "langsmith.span.tags", ",".join(map(str, all_tags)))


def _record_error(span, err: BaseException) -> None:
    from opentelemetry.trace import Status, StatusCode
    span.record_exception(err)
    span.set_status(Status(StatusCode.ERROR, f"{type(err).__name__}: {err}"))


@contextlib.contextmanager
def obs_context(tags: list[str] | None = None, **metadata: Any) -> Iterator[None]:
    """
    Attach metadata / tags to every span started inside the block.

        with obs_context(session_id=thread_id, user_id="u-42", tags=["beta"]):
            answer(q)

    session_id (or thread_id / conversation_id) groups traces in LangSmith's Threads tab.
    """
    t1 = _metadata_var.set({**_metadata_var.get(), **metadata})
    t2 = _tags_var.set(tuple(dict.fromkeys([*_tags_var.get(), *(tags or [])])))
    try:
        yield
    finally:
        _tags_var.reset(t2)
        _metadata_var.reset(t1)


@contextlib.contextmanager
def span(name: str, kind: str = "chain", inputs: Any = None, metadata: dict | None = None,
         tags: list[str] | None = None) -> Iterator[Any]:
    """
    A manual span. Use .set_attribute(...) on the yielded object, or set_output(sp, value).

        with span("build_prompt", kind="prompt", inputs={"question": q}) as sp:
            prompt = ...
            set_output(sp, prompt)
    """
    tracer = _get_tracer()
    if tracer is None:  # opentelemetry not installed at all
        yield None
        return
    with tracer.start_as_current_span(name, record_exception=False, set_status_on_exception=False) as sp:
        _apply_context(sp, kind, metadata, tags)
        if inputs is not None and obs_settings.capture_content:
            _set(sp, "input.value", _clip(inputs))
            _set(sp, "input.mime_type", "application/json")
        try:
            yield sp
        except BaseException as err:
            _record_error(sp, err)
            raise


def set_output(sp, value: Any) -> None:
    if sp is not None and obs_settings.capture_content:
        _set(sp, "output.value", _clip(value))
        _set(sp, "output.mime_type", "application/json")


def current_trace_id() -> str | None:
    """Hex trace id of the active span (print it, then search for it in LangSmith)."""
    try:
        from opentelemetry import trace
        ctx = trace.get_current_span().get_span_context()
        return format(ctx.trace_id, "032x") if ctx.is_valid else None
    except ImportError:
        return None


def traced(name: str | None = None, kind: str = "chain", capture_args: bool = True,
           metadata: dict | None = None, tags: list[str] | None = None):
    """
    Decorator: turn any function (sync or async) into a span - the OTel twin of @traceable.

        @traced("retrieve_docs", kind="retriever")
        def retrieve(question: str) -> list[dict]: ...
    """
    def decorator(fn):
        span_name = name or fn.__name__
        sig = inspect.signature(fn)

        def _inputs(args, kwargs):
            if not capture_args:
                return None
            try:
                bound = sig.bind_partial(*args, **kwargs)
                return {k: v for k, v in bound.arguments.items() if k not in ("self", "cls")}
            except TypeError:
                return {"args": args, "kwargs": kwargs}

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                with span(span_name, kind, _inputs(args, kwargs), metadata, tags) as sp:
                    result = await fn(*args, **kwargs)
                    set_output(sp, result)
                    return result
            return async_wrapper

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with span(span_name, kind, _inputs(args, kwargs), metadata, tags) as sp:
                result = fn(*args, **kwargs)
                set_output(sp, result)
                return result
        return wrapper

    return decorator


# ---- trace-context propagation to the gateway ------------------------------ #
def trace_headers() -> dict[str, str]:
    """
    W3C trace headers (traceparent, ...) for the active span. Add them to any HTTP call you make
    yourself - e.g. a FilCopilot API request - so spans on the other side join your trace.
    get_client() already does this for OpenAI-SDK calls.
    """
    headers: dict[str, str] = {}
    if _obs_state["active"] and obs_settings.propagate:
        try:
            from opentelemetry import propagate
            propagate.inject(headers)
        except Exception:  # noqa: BLE001
            pass
    return headers


def _inject_trace_headers(request: httpx.Request) -> None:
    """httpx event hook: add traceparent (+ any FIL headers) so gateway spans join our trace."""
    global _fil_build_headers
    if not (_obs_state["active"] and obs_settings.propagate):
        return
    headers: dict[str, str] = {}
    try:
        from opentelemetry import propagate
        propagate.inject(headers)
    except Exception:  # noqa: BLE001
        pass
    if _fil_build_headers is not None:
        try:
            extra = _fil_build_headers()
            if isinstance(extra, dict):
                headers.update({str(k): str(v) for k, v in extra.items()})
        except TypeError:
            _fil_build_headers = None  # signature differs in this SDK version; W3C inject is enough
        except Exception:  # noqa: BLE001
            pass
    for k, v in headers.items():
        if k.lower() != "authorization":  # never let a helper overwrite the gateway token
            request.headers[k] = v


# ---- automatic spans around the OpenAI SDK --------------------------------- #
def _usage_attrs(sp, usage) -> None:
    if usage is None:
        return
    inp = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None)
    out = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None)
    tot = getattr(usage, "total_tokens", None)
    _set(sp, "gen_ai.usage.input_tokens", inp)
    _set(sp, "gen_ai.usage.output_tokens", out)
    _set(sp, "gen_ai.usage.total_tokens", tot if tot is not None else ((inp or 0) + (out or 0) or None))


def _msg_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # multimodal parts
        return " ".join(p.get("text", f"<{p.get('type', 'part')}>") if isinstance(p, dict) else str(p) for p in content)
    return "" if content is None else str(content)


def _request_attrs(sp, kwargs: dict, operation: str) -> None:
    _set(sp, "gen_ai.system", "fil-ai-gateway" if settings.mode == "enterprise" else "openai")
    _set(sp, "gen_ai.operation.name", operation)
    _set(sp, "gen_ai.request.model", kwargs.get("model"))
    for key in ("temperature", "top_p", "max_tokens", "max_completion_tokens", "seed"):
        _set(sp, f"gen_ai.request.{key}", kwargs.get(key))
    _set(sp, "langsmith.metadata.ls_model_name", kwargs.get("model"))
    _set(sp, "langsmith.metadata.ls_provider", "openai")
    if obs_settings.capture_content and operation == "chat":
        for i, m in enumerate(kwargs.get("messages") or []):
            m = m if isinstance(m, dict) else getattr(m, "__dict__", {})
            _set(sp, f"gen_ai.prompt.{i}.role", m.get("role"))
            _set(sp, f"gen_ai.prompt.{i}.content", _clip(_msg_text(m.get("content"))))
        if kwargs.get("tools"):
            _set(sp, "gen_ai.request.tools", _clip(kwargs["tools"]))


def _completion_attrs(sp, resp) -> None:
    _set(sp, "gen_ai.response.model", getattr(resp, "model", None))
    _set(sp, "gen_ai.response.id", getattr(resp, "id", None))
    _usage_attrs(sp, getattr(resp, "usage", None))
    for i, choice in enumerate(getattr(resp, "choices", None) or []):
        msg = getattr(choice, "message", None)
        _set(sp, f"gen_ai.completion.{i}.role", getattr(msg, "role", "assistant"))
        _set(sp, f"gen_ai.completion.{i}.finish_reason", getattr(choice, "finish_reason", None))
        if obs_settings.capture_content:
            _set(sp, f"gen_ai.completion.{i}.content", _clip(getattr(msg, "content", "") or ""))
            calls = getattr(msg, "tool_calls", None)
            if calls:
                _set(sp, f"gen_ai.completion.{i}.tool_calls", _clip([c.model_dump() if hasattr(c, "model_dump") else c for c in calls]))


class _TracedStream:
    """Wraps a streaming response: the span ends when the stream is consumed or closed."""

    def __init__(self, stream, sp):
        self._stream, self._sp = stream, sp
        self._parts: list[str] = []
        self._done = False

    def __iter__(self):
        try:
            for chunk in self._stream:
                for choice in getattr(chunk, "choices", None) or []:
                    delta = getattr(choice, "delta", None)
                    if delta is not None and getattr(delta, "content", None):
                        self._parts.append(delta.content)
                if getattr(chunk, "usage", None):
                    _usage_attrs(self._sp, chunk.usage)
                yield chunk
        except BaseException as err:
            _record_error(self._sp, err)
            self._finish()
            raise
        self._finish()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        with contextlib.suppress(Exception):
            self._stream.close()
        self._finish()

    def _finish(self):
        if self._done:
            return
        self._done = True
        if obs_settings.capture_content:
            _set(self._sp, "gen_ai.completion.0.role", "assistant")
            _set(self._sp, "gen_ai.completion.0.content", _clip("".join(self._parts)))
        self._sp.end()

    def __getattr__(self, item):
        return getattr(self._stream, item)


def _wrap_chat_create(original: Callable) -> Callable:
    @functools.wraps(original)
    def create(*args, **kwargs):
        tracer = _get_tracer()
        if tracer is None or not _obs_state["active"]:
            return original(*args, **kwargs)
        from opentelemetry import trace
        sp = tracer.start_span(f"chat {kwargs.get('model', '')}".strip())
        _apply_context(sp, "llm")
        _request_attrs(sp, kwargs, "chat")
        t0 = time.perf_counter()
        try:
            with trace.use_span(sp, end_on_exit=False, record_exception=False, set_status_on_exception=False):
                resp = original(*args, **kwargs)  # traceparent header is injected inside this call
        except BaseException as err:
            _record_error(sp, err)
            sp.end()
            raise
        if kwargs.get("stream"):
            return _TracedStream(resp, sp)
        try:
            _completion_attrs(sp, resp)
            _set(sp, "llm.latency_ms", round((time.perf_counter() - t0) * 1000, 1))
        finally:
            sp.end()
        return resp
    create.__wrapped_by_llm_client__ = True  # type: ignore[attr-defined]
    return create


def _wrap_embeddings_create(original: Callable) -> Callable:
    @functools.wraps(original)
    def create(*args, **kwargs):
        if not _obs_state["active"]:
            return original(*args, **kwargs)
        inputs = kwargs.get("input")
        n = len(inputs) if isinstance(inputs, list) else 1
        with span(f"embeddings {kwargs.get('model', '')}".strip(), kind="embedding") as sp:
            _request_attrs(sp, kwargs, "embeddings")
            _set(sp, "gen_ai.request.input_count", n)
            if obs_settings.capture_content:
                preview = inputs[:5] if isinstance(inputs, list) else [inputs]
                _set(sp, "input.value", _clip({"input": preview, "count": n}))
            resp = original(*args, **kwargs)
            _set(sp, "gen_ai.response.model", getattr(resp, "model", None))
            _usage_attrs(sp, getattr(resp, "usage", None))
            data = getattr(resp, "data", None) or []
            if data:
                _set(sp, "output.value", _to_json({"vectors": len(data), "dimensions": len(data[0].embedding)}))
            return resp
    create.__wrapped_by_llm_client__ = True  # type: ignore[attr-defined]
    return create


def instrument_client(client: OpenAI) -> OpenAI:
    """Add LLM/embedding spans to an OpenAI client (idempotent). get_client() does this for you."""
    chat = client.chat.completions
    if not getattr(chat.create, "__wrapped_by_llm_client__", False):
        chat.create = _wrap_chat_create(chat.create)
    emb = client.embeddings
    if not getattr(emb.create, "__wrapped_by_llm_client__", False):
        emb.create = _wrap_embeddings_create(emb.create)
    return client


# --------------------------------------------------------------------------- #
# The one function the samples call
# --------------------------------------------------------------------------- #
_client_cache: OpenAI | None = None
_client_lock = threading.Lock()


def _http_client(auth: httpx.Auth | None = None, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    verify = settings.ca_bundle or True  # corporate CA bundle if the gateway uses an internal cert
    return httpx.Client(
        auth=auth, verify=verify, timeout=settings.timeout, transport=transport,
        event_hooks={"request": [_inject_trace_headers]},
    )


def _build_client() -> OpenAI:
    if settings.mode == "enterprise":
        return OpenAI(
            api_key="set-per-request-by-msal",  # placeholder; real token injected by _BearerTokenAuth
            base_url=_env("FIL_BASE_URL", required=True),
            http_client=_http_client(auth=_BearerTokenAuth()),
            timeout=settings.timeout,
            max_retries=settings.max_retries,
        )
    if settings.mode == "direct":
        return OpenAI(
            api_key=_env("OPENAI_API_KEY", required=True),
            base_url=_env("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            http_client=_http_client(),
            timeout=settings.timeout,
            max_retries=settings.max_retries,
        )
    raise RuntimeError(f"LLM_MODE must be 'enterprise' or 'direct', got {settings.mode!r}")


def get_client(fresh: bool = False) -> OpenAI:
    """
    The OpenAI client every script uses. Shared per process (one connection pool),
    observability started on first use, LLM + embedding calls traced automatically.
    """
    global _client_cache
    init_observability()
    if fresh:
        return instrument_client(_build_client())
    with _client_lock:
        if _client_cache is None:
            _client_cache = instrument_client(_build_client())
        return _client_cache


def describe() -> str:
    """One-line summary of where calls and traces go (never prints secrets)."""
    if settings.mode == "enterprise":
        llm = f"mode=enterprise  gateway={_env('FIL_BASE_URL')}  scope={_fil_scope()}"
    else:
        llm = f"mode=direct  base_url={_env('OPENAI_BASE_URL') or 'https://api.openai.com/v1'}"
    return f"{llm}  chat={settings.chat_model}  embed={settings.embed_model}"


def describe_observability() -> str:
    s = observability_status()
    if s["mode"] == "off":
        return "observability=off (set OBS_MODE=fil inside FIL, otlp outside)"
    state = f"ACTIVE via {s['backend']}" if s["active"] else (
        "not started yet" if not _obs_state["started"] else f"FAILED - {s['reason']}")
    return (f"observability={s['mode']}  {state}  project={s['project']}  endpoint={s['endpoint']}  "
            f"content={'on' if s['capture_content'] else 'metadata-only'}  "
            f"langchain={'otel' if s['trace_langchain'] else 'off'}")
