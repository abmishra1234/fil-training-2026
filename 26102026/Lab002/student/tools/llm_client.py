"""
llm_client.py - ONE place that decides how we talk to the LLM.
(FIL reference client, as used in the earlier cohort labs, with three lab fixes - see CHANGES.)

Every script does:

    from llm_client import get_client, settings
    client = get_client()
    client.chat.completions.create(model=settings.chat_model, messages=[...])

and then uses the standard OpenAI SDK. Nothing else knows or cares whether we are
inside FIL or not. The mode is ONE line in .env:

    LLM_MODE=enterprise   -> FIL AI Gateway, Azure AD (Entra ID) token via MSAL   (students in FIL)
    LLM_MODE=direct       -> OpenAI or any OpenAI-compatible API with an API key  (trainer / home)
    LLM_MODE=mock         -> no network at all; handled by llm_adapter.py (dry runs)

CHANGES compared with the cohort reference client
  1. Model names are resolved PER MODE: ENTERPRISE_CHAT_MODEL / DIRECT_CHAT_MODEL, falling
     back to the legacy CHAT_MODEL. (The reference .env.example used the mode-specific names
     but the client only read CHAT_MODEL, so both modes silently got the default model,
     which the FIL gateway rejects.)
  2. .env is searched in the current folder and up to three parents of this file, so one
     .env at the lab root serves tools/ scripts and notebooks alike. Real environment
     variables always win over .env.
  3. 'mock' is accepted as a mode name; get_client() refuses it with a clear message.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


def _load_env_files() -> str | None:
    """Load the first .env found: cwd, then this folder and its parents. Returns its path."""
    if load_dotenv is None:
        return None
    here = Path(__file__).resolve().parent
    for folder in [Path.cwd(), here, *list(here.parents)[:3]]:
        candidate = folder / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)  # real env vars win
            return str(candidate)
    return None


ENV_FILE = _load_env_files()
MODES = ("enterprise", "direct", "mock")


def _env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if value is not None:
        value = value.strip()
    if required and not value:
        raise RuntimeError(
            f"Missing setting {name!r}. Copy tools/.env.example to .env and fill it in "
            f"(LLM_MODE is currently {os.getenv('LLM_MODE', 'not set')!r})."
        )
    return value or None


def _model(kind: str, mode: str, default: str) -> str:
    """ENTERPRISE_CHAT_MODEL / DIRECT_CHAT_MODEL first, then legacy CHAT_MODEL, then default."""
    prefix = "ENTERPRISE" if mode == "enterprise" else "DIRECT"
    return _env(f"{prefix}_{kind}_MODEL") or _env(f"{kind}_MODEL") or default


@dataclass(frozen=True)
class Settings:
    mode: str
    chat_model: str
    embed_model: str
    timeout: float
    max_retries: int
    ca_bundle: str | None


_mode = (_env("LLM_MODE", "direct") or "direct").lower()
settings = Settings(
    mode=_mode,
    chat_model=_model("CHAT", _mode, "azure/gpt-6-luna" if _mode == "enterprise" else "gpt-4o-mini"),
    embed_model=_model("EMBED", _mode,
                       "azure/text-embedding-ada-002" if _mode == "enterprise" else "text-embedding-3-small"),
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


def _bearer_auth():
    import httpx

    class _BearerTokenAuth(httpx.Auth):
        """Puts a fresh FIL token on every request (tokens last ~1 hour; MSAL caches them)."""

        def auth_flow(self, request):
            request.headers["Authorization"] = f"Bearer {get_access_token()}"
            yield request

    return _BearerTokenAuth()


# --------------------------------------------------------------------------- #
# The one function scripts call
# --------------------------------------------------------------------------- #
def get_client():
    import httpx
    from openai import OpenAI

    verify = settings.ca_bundle or True  # corporate CA bundle if the gateway uses an internal cert

    if settings.mode == "enterprise":
        return OpenAI(
            api_key="set-per-request-by-msal",  # placeholder; real token injected per request
            base_url=_env("FIL_BASE_URL", required=True),
            http_client=httpx.Client(auth=_bearer_auth(), verify=verify, timeout=settings.timeout),
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
    if settings.mode == "mock":
        raise RuntimeError("LLM_MODE=mock has no real client. Lab tools handle mock mode in llm_adapter.py.")
    raise RuntimeError(f"LLM_MODE must be one of {MODES}, got {settings.mode!r}")


def describe() -> str:
    """One-line summary of where calls will go (never prints secrets)."""
    src = f"  .env={ENV_FILE}" if ENV_FILE else "  .env=(none found, using environment variables)"
    if settings.mode == "enterprise":
        return (f"mode=enterprise  gateway={_env('FIL_BASE_URL')}  scope={_fil_scope()}  "
                f"chat_model={settings.chat_model}{src}")
    if settings.mode == "direct":
        return (f"mode=direct  base_url={_env('OPENAI_BASE_URL') or 'https://api.openai.com/v1'}  "
                f"chat_model={settings.chat_model}{src}")
    return f"mode={settings.mode}  (offline, no LLM calls){src}"
