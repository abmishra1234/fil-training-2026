"""app/agent/parsing.py - PROVIDED. Get a JSON object out of an LLM reply, defensively."""
from __future__ import annotations

import json
import re


def parse_json(text: str | None) -> dict | None:
    """
    Accepts plain JSON, ```json fenced``` JSON, or JSON with chatter around it.
    Returns the first JSON object found, or None. Never raises.
    """
    if not text:
        return None
    t = re.sub(r"```(?:json)?", "", text).strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            ch = t[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(t[start : i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
                    break
        start = t.find("{", start + 1)
    return None


def as_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    if isinstance(value, (int, float)):
        return bool(value)
    return default
