"""LLM + embeddings client for FundLens.

Two modes, chosen by FUNDLENS_LLM_MODE in .env:

* gateway (default) - calls the FIL AI Gateway through its OpenAI-compatible endpoint
  (models azure/gpt-6-luna and azure/text-embedding-ada-002).
  If your batch uses the shared `llm_client.py` from earlier labs, you may replace the body of
  `_gateway_chat` / `_gateway_embed` with calls to it. Keep the public functions below unchanged
  so the rest of the starter (and the evaluation scripts) keep working.
* mock - fully offline and deterministic. Chat returns a canned string; embeddings are a hashed
  bag-of-words vector, so retrieval still works roughly. Use it for unit tests, CI and when the
  gateway is down. Do NOT report evaluation numbers produced in mock mode.

Optional disk cache (FUNDLENS_LLM_CACHE=1) stores responses under .cache/llm to save gateway calls
while developing. Never commit the cache.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

from .config import settings

_CACHE_DIR = Path(".cache/llm")
CALL_COUNTER = {"chat": 0, "embed": 0}   # read this to log LLM calls per request (NFR: <= 6 per fact question)


# ----------------------------------------------------------------------------- public API
def chat(messages: list[dict[str, str]], *, temperature: float = 0.0, json_mode: bool = False,
         max_tokens: int = 1200, model: str | None = None) -> str:
    """Return the assistant message text. messages = [{"role": "system"|"user"|"assistant", "content": "..."}]."""
    CALL_COUNTER["chat"] += 1
    model = model or settings.chat_model
    key = _key("chat", model, messages, temperature, json_mode)
    if (hit := _cache_get(key)) is not None:
        return hit
    if settings.llm_mode == "mock":
        out = _mock_chat(messages, json_mode)
    else:
        out = _retry(lambda: _gateway_chat(messages, temperature, json_mode, max_tokens, model))
    _cache_put(key, out)
    return out


def embed(texts: list[str], *, model: str | None = None) -> list[list[float]]:
    """Return one embedding vector per input text."""
    CALL_COUNTER["embed"] += 1
    model = model or settings.embed_model
    if settings.llm_mode == "mock":
        return [_mock_embed(t) for t in texts]
    out: list[list[float]] = []
    for i in range(0, len(texts), 64):          # batch to stay under gateway limits
        batch = texts[i:i + 64]
        key = _key("embed", model, batch)
        hit = _cache_get(key)
        if hit is None:
            hit = _retry(lambda b=batch: _gateway_embed(b, model))
            _cache_put(key, hit)
        out.extend(hit)
    return out


# ----------------------------------------------------------------------------- gateway backend
def _client():
    from openai import OpenAI  # imported lazily so mock mode needs no network packages
    return OpenAI(base_url=settings.gateway_base_url, api_key=settings.gateway_api_key, timeout=60)


def _gateway_chat(messages, temperature, json_mode, max_tokens, model) -> str:
    kwargs: dict[str, Any] = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def _gateway_embed(texts, model) -> list[list[float]]:
    resp = _client().embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def _retry(fn, tries: int = 2, backoff: float = 2.0):
    """NFR reliability: retry once with backoff, then raise a clean error."""
    for attempt in range(tries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if attempt == tries - 1:
                raise LLMUnavailable(f"LLM gateway call failed: {type(exc).__name__}") from exc
            time.sleep(backoff * (attempt + 1))


class LLMUnavailable(RuntimeError):
    """Raised when the gateway fails twice. Catch it in the API layer and return a friendly message."""


# ----------------------------------------------------------------------------- mock backend
def _mock_chat(messages, json_mode) -> str:
    last = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if json_mode:
        return json.dumps({"mock": True, "echo": last[:120]})
    return f"MOCK_RESPONSE: {last[:120]}"


_DIM = 1536


def _mock_embed(text: str) -> list[float]:
    vec = [0.0] * _DIM
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % _DIM] += 1.0 if (h >> 11) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# ----------------------------------------------------------------------------- cache helpers
def _key(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _cache_get(key: str):
    if not settings.llm_cache:
        return None
    p = _CACHE_DIR / f"{key}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _cache_put(key: str, value) -> None:
    if not settings.llm_cache:
        return
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_CACHE_DIR / f"{key}.json").write_text(json.dumps(value))
