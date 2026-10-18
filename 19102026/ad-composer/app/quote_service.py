"""
app/quote_service.py - TEXT generation: polish the user's marketing quote.

Uses the CHAT model (settings.chat_model) through the same get_client(),
exactly like 01_first_call.py. The user keeps control: we return 3
suggestions and the frontend lets them pick one (or keep their own).
"""
from __future__ import annotations

import json
import re

from openai import APIConnectionError, APIStatusError, APITimeoutError

from llm_client import get_client, settings as llm_settings

from .config import config
from .image_service import AdComposeError
from .prompt_builder import clean_quote
from .schemas import QuoteRefineRequest

SYSTEM_PROMPT = (
    "You are a senior advertising copywriter for the Indian market. "
    "Rewrite the user's product line into short ad headlines. "
    "Rules: max 12 words each, no hashtags, no emojis, no medical or financial claims, "
    "no competitor names, keep the brand name exactly as given. "
    'Reply ONLY with JSON: {"suggestions": ["...", "...", "..."]}'
)


def parse_suggestions(raw: str) -> list[str]:
    """
    PROVIDED: models do not always return clean JSON. Accept:
      * {"suggestions": [...]}           (what we asked for)
      * the same JSON wrapped in ```json fences
      * a plain numbered / bulleted list  (fallback)
    Returns up to 3 cleaned, non-empty, de-duplicated suggestions.
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    items: list[str] = []
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            items = [str(x) for x in data.get("suggestions", [])]
        elif isinstance(data, list):
            items = [str(x) for x in data]
    except json.JSONDecodeError:
        items = [re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", ln) for ln in text.splitlines()]
    seen, out = set(), []
    for it in items:
        q = clean_quote(it.strip().strip("'\""))
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:3]


# ---------------------------------------------------------------------------
# TODO 5 - refine_quote()
# ---------------------------------------------------------------------------
def refine_quote(req: QuoteRefineRequest) -> list[str]:
    """
    Return up to 3 polished versions of req.quote in the requested mood.

    * If config.dry_run: do NOT call the LLM - return
        [req.quote, req.quote + "!", "<Brand>: " + req.quote]   (cleaned; brand only if given)
      so the UI can be tested offline.
    * Otherwise:
        client = get_client()
        reply  = client.chat.completions.create(
                    model=llm_settings.chat_model,
                    messages=[{"role": "developer", "content": SYSTEM_PROMPT},
                              {"role": "user", "content": <quote + mood + brand>}],
                    timeout=llm_settings.timeout)
        suggestions = parse_suggestions(reply.choices[0].message.content or "")
    * No suggestions parsed -> AdComposeError(502, "...")
    * APITimeoutError -> 504, APIConnectionError -> 502, APIStatusError -> 502
    """
    raise NotImplementedError("TODO 5: implement refine_quote() in app/quote_service.py")
