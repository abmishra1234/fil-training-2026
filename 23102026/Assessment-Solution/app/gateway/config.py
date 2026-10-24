"""
app/gateway/config.py - gateway settings live in a file, not in code.

    config/gateway.json           (override the path with GATEWAY_CONFIG=...)
    {
      "codenames":              ["Project Falcon", "Project Monsoon"],
      "credential_prefixes":    [regex, ...]     optional, defaults in detectors.py
      "credential_keywords":    ["password", "secret", "api_key"]   optional
    }

A broken config raises at START-UP (fail fast) instead of letting secrets through.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .detectors import DEFAULT_KEY_PREFIX_PATTERNS, DEFAULT_SECRET_KEYWORDS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "gateway.json"


class GatewayConfigError(ValueError):
    pass


@dataclass(frozen=True)
class GatewayConfig:
    codenames: list[str] = field(default_factory=list)
    credential_prefixes: list[str] = field(default_factory=lambda: list(DEFAULT_KEY_PREFIX_PATTERNS))
    credential_keywords: list[str] = field(default_factory=lambda: list(DEFAULT_SECRET_KEYWORDS))


def config_path() -> Path:
    raw = (os.getenv("GATEWAY_CONFIG") or "").strip()
    if not raw:
        return DEFAULT_CONFIG_PATH
    p = Path(raw)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _str_list(data: dict, key: str, default: list[str]) -> list[str]:
    value = data.get(key, default)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise GatewayConfigError(f"'{key}' must be a list of strings")
    return value


def load_config(path: str | Path | None = None) -> GatewayConfig:
    path = Path(path) if path else config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise GatewayConfigError(f"gateway config not found: {path}") from None
    except json.JSONDecodeError as err:
        raise GatewayConfigError(f"gateway config is not valid JSON ({path}, line {err.lineno})") from None
    if not isinstance(data, dict):
        raise GatewayConfigError("gateway config must be a JSON object")
    cfg = GatewayConfig(
        codenames=_str_list(data, "codenames", []),
        credential_prefixes=_str_list(data, "credential_prefixes", list(DEFAULT_KEY_PREFIX_PATTERNS)),
        credential_keywords=_str_list(data, "credential_keywords", list(DEFAULT_SECRET_KEYWORDS)),
    )
    for rx in cfg.credential_prefixes:
        try:
            re.compile(rx)
        except re.error as err:
            raise GatewayConfigError(f"bad regex in credential_prefixes: {err}") from None
    return cfg
