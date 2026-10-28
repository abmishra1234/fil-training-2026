"""
app/llm.py - PROVIDED. The only file that talks to the model.

Every call goes through llm_client.get_client(), exactly like the sample
scripts, so the app works inside FIL (AI Gateway) and outside (OpenAI key)
with no code change.

  GatewayEmbeddings  - a LangChain `Embeddings` class, so FAISS/LangChain can
                       use our gateway for azure/text-embedding-ada-002.
  chat_complete()    - one chat call to CHAT_MODEL (azure/gpt-6-luna).
  RagError           - an error with an HTTP status + a hint for the UI.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings # type: ignore
from openai import APIConnectionError, APIStatusError, APITimeoutError # type: ignore

import llm_client
from llm_client import settings as llm_settings

EMBED_BATCH = 64  # inputs per embeddings request (ada-002 accepts many; keep requests small)


class RagError(Exception):
    def __init__(self, status: int, message: str, hint: str = ""):
        super().__init__(message)
        self.status = status
        self.message = message
        self.hint = hint


def _client():
    # Looked up at call time so tests can monkeypatch llm_client.get_client.
    return llm_client.get_client()


def _translate(err: Exception, what: str) -> RagError:
    if isinstance(err, APITimeoutError):
        return RagError(504, f"The {what} model timed out.", "Raise LLM_TIMEOUT_SECONDS in .env.")
    if isinstance(err, APIConnectionError):
        return RagError(502, "Could not reach the LLM gateway / API.", "Check VPN, FIL_BASE_URL and CA_BUNDLE.")
    if isinstance(err, APIStatusError):
        hint = "Run: python 00_check_setup.py"
        if err.status_code == 429:
            hint = "Rate limit (200 req/min) or $50 monthly budget reached. Wait a minute and retry."
        elif err.status_code in (401, 403):
            hint = "Token rejected. Check FIL_CLIENT_ID / FIL_CLIENT_SECRET / FIL_ENV."
        elif err.status_code == 404:
            hint = "Model not found. Check CHAT_MODEL / EMBED_MODEL in .env."
        return RagError(502, f"{what.capitalize()} model error {err.status_code}.", hint)
    return RagError(500, f"{what.capitalize()} call failed: {err}", "")


class GatewayEmbeddings(Embeddings):
    """LangChain Embeddings backed by llm_client.get_client().embeddings.create()."""

    def __init__(self, model: str | None = None):
        self.model = model or llm_settings.embed_model
        self.calls = 0  # how many HTTP requests we made (shown in the UI)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH):
            batch = [t.replace("\n", " ") for t in texts[i : i + EMBED_BATCH]]
            try:
                resp = _client().embeddings.create(model=self.model, input=batch)
            except Exception as err:  # noqa: BLE001
                raise _translate(err, "embedding") from None
            self.calls += 1
            # The API may return items in any order; sort by index to be safe.
            vectors.extend(item.embedding for item in sorted(resp.data, key=lambda d: d.index))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


USAGE = {"chat": 0}  # Lab 3: chat calls made by this process (Evaluate shows cost per mode)


def chat_complete(messages: list[dict]) -> str:
    """One chat completion. Returns the text ('' if the model sent nothing)."""
    USAGE["chat"] += 1
    try:
        reply = _client().chat.completions.create(
            model=llm_settings.chat_model,
            messages=messages,
            timeout=llm_settings.timeout,
        )
    except Exception as err:  # noqa: BLE001
        raise _translate(err, "chat") from None
    return (reply.choices[0].message.content or "").strip()
