"""
app/gateway/factory.py - the ONE place that decides which detectors exist.

To add a secret type (say EMAIL or IBAN):
    1. write a SecretDetector (or use RegexDetector("EMAIL", [r"..."]))
    2. add it to default_detectors() below
The gateway core (core.py) and the pipeline stay untouched.
"""
from __future__ import annotations

import threading
from pathlib import Path

from .config import GatewayConfig, load_config
from .core import MiniAIGateway
from .detectors import CodenameDetector, CredentialDetector, PaymentCardDetector, SecretDetector
from .models import Decision, GatewayResult, Passage


def default_detectors(cfg: GatewayConfig) -> list[SecretDetector]:
    return [
        CredentialDetector(cfg.credential_prefixes, cfg.credential_keywords),
        PaymentCardDetector(),
        CodenameDetector(cfg.codenames),
    ]


def build_gateway(config_path: str | Path | None = None, extra_detectors: list[SecretDetector] | None = None) -> MiniAIGateway:
    cfg = load_config(config_path)
    return MiniAIGateway([*default_detectors(cfg), *(extra_detectors or [])])


_default: MiniAIGateway | None = None
_lock = threading.Lock()


def get_default_gateway() -> MiniAIGateway:
    """Built once from config/gateway.json (or $GATEWAY_CONFIG). Raises on a broken config."""
    global _default
    if _default is None:
        with _lock:
            if _default is None:
                _default = build_gateway()
    return _default


def reset_default_gateway() -> None:
    """Forget the cached gateway (after editing the config file, and in tests)."""
    global _default
    with _lock:
        _default = None


def check(query: str, passages: list[Passage]) -> GatewayResult:
    """The minimum interface from the brief. Fails closed even if the config cannot be loaded."""
    try:
        gw = get_default_gateway()
    except Exception as err:  # noqa: BLE001
        return GatewayResult(Decision.BLOCK_ERROR, [], [], {}, 0.0, type(err).__name__)
    return gw.check(query, passages)
