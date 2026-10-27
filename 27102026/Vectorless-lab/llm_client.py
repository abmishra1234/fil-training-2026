"""
llm_client.py - ONE place that decides how we talk to the LLM.

Every sample script does:

    from llm_client import get_client, settings
    client = get_client()

and then uses the standard OpenAI SDK (client.chat..., client.embeddings..., ...).
Nothing else in the samples knows or cares whether we are inside FIL or not.

Which mode is used is controlled by ONE line in .env:

    LLM_MODE=enterprise   -> FIL AI Gateway, Azure AD token via MSAL (students)
    LLM_MODE=direct       -> OpenAI (or any OpenAI-compatible endpoint) with an API key (trainer / home use)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from the folder this file lives in (works from scripts AND notebooks).
load_dotenv(Path(__file__).with_name(".env"))


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


settings = Settings(
    mode=(_env("LLM_MODE", "direct") or "direct").lower(),
    chat_model=_env("CHAT_MODEL", "gpt-5.1"),
    embed_model=_env("EMBED_MODEL", "text-embedding-ada-002"),
    tts_model=_env("TTS_MODEL", "gpt-4o-mini-tts"),
    stt_model=_env("STT_MODEL", "gpt-4o-transcribe"),
    image_model=_env("IMAGE_MODEL", "gpt-image-1"),
    timeout=float(_env("LLM_TIMEOUT_SECONDS", "60")),
    max_retries=int(_env("LLM_MAX_RETRIES", "2")),
    ca_bundle=_env("CA_BUNDLE"),
)


# --------------------------------------------------------------------------- #
# Enterprise mode: Azure AD (Entra ID) client-credentials token via MSAL
# --------------------------------------------------------------------------- #
FIL_SCOPES = {
    "uat": "https://uat.filxgptnp.fil.com/.default",
    "dev": "https://dev.filxgptnp.fil.com/.default",
}

_msal_app = None  # created once, so MSAL's in-memory token cache is reused


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
    (e.g. transcribing a big folder) would start failing with 401 halfway.
    This hook asks MSAL for the token before each request; MSAL serves it
    from cache, so it only really goes to Azure AD when the token is expiring.
    """

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {get_access_token()}"
        yield request


# --------------------------------------------------------------------------- #
# The one function the samples call
# --------------------------------------------------------------------------- #
def get_client() -> OpenAI:
    verify = settings.ca_bundle or True  # corporate CA bundle if the gateway uses an internal cert

    if settings.mode == "enterprise":
        http_client = httpx.Client(auth=_BearerTokenAuth(), verify=verify, timeout=settings.timeout)
        return OpenAI(
            api_key="set-per-request-by-msal",  # placeholder; real token injected by _BearerTokenAuth
            base_url=_env("FIL_BASE_URL", required=True),
            http_client=http_client,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
        )

    if settings.mode == "direct":
        return OpenAI(
            api_key=_env("OPENAI_API_KEY", required=True),
            base_url=_env("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            http_client=httpx.Client(verify=verify, timeout=settings.timeout),
            timeout=settings.timeout,
            max_retries=settings.max_retries,
        )

    raise RuntimeError(f"LLM_MODE must be 'enterprise' or 'direct', got {settings.mode!r}")


def describe() -> str:
    """One-line summary of where calls will go (never prints secrets)."""
    if settings.mode == "enterprise":
        return f"mode=enterprise  gateway={_env('FIL_BASE_URL')}  scope={_fil_scope()}"
    return f"mode=direct  base_url={_env('OPENAI_BASE_URL') or 'https://api.openai.com/v1'}"


