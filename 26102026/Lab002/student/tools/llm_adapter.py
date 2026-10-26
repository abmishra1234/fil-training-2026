"""
llm_adapter.py - the ONE function every lab tool uses to talk to an LLM.

    chat(system: str, user: str) -> str

Connection details live in llm_client.py and your .env. Pick the mode with ONE line:

  LLM_MODE=enterprise   FIL AI Gateway, Azure AD token via MSAL          (in FIL)
  LLM_MODE=direct       OpenAI or any OpenAI-compatible API, API key     (home / trainer)
  LLM_MODE=mock         fully offline and deterministic, for dry runs

Lab code never changes between modes: only .env does. Run `python tools/check_setup.py`
first; it tells you which step is broken.

Mock mode: the mock "router" scores skill descriptions by word overlap, so a better
description still gives a better score. The mock never writes a real answer for
run_cases.py.
"""
import os
import re


def _mode() -> str:
    # read after llm_client has loaded .env, so LLM_MODE in .env is honoured
    import llm_client  # noqa: F401
    return os.getenv("LLM_MODE", "direct").strip().lower()


def chat(system: str, user: str, temperature: float = 0.0) -> str:
    if _mode() == "mock":
        return _mock(system, user)
    from llm_client import get_client, settings
    resp = get_client().chat.completions.create(
        model=settings.chat_model,
        temperature=temperature,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------- mock
_STOP = set("""a an the to of for and or in on at by with from into is are be this that it its as
user users asks ask when use used do not any about my our your me we you i please can could would
should will want need help make get give some more one all""".split())


def _words(text):
    words = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in _STOP:
            continue
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        words.add(w)
    return words


def _mock(system, user):
    if "SKILL ROUTER" in system:
        return _mock_route(system, user)
    return ("MOCK MODE: no model was called. Set LLM_MODE=enterprise (in FIL) or "
            "LLM_MODE=direct in .env to get a real answer.")


def _mock_route(system, user):
    """Parse '- name: description' lines from the router prompt and pick by overlap."""
    req = _words(user)
    best, best_score = "NONE", 0.0
    for line in system.splitlines():
        m = re.match(r"^- ([a-z0-9-]+): (.*)$", line.strip())
        if not m:
            continue
        name, desc = m.group(1), m.group(2)
        parts = re.split(r"(?i)do not use", desc, maxsplit=1)
        pos = _words(parts[0])
        neg = _words(parts[1]) if len(parts) > 1 else set()
        score = len(req & pos) - 1.5 * len(req & (neg - pos))
        if score > best_score:
            best, best_score = name, score
    return best if best_score >= 2 else "NONE"
