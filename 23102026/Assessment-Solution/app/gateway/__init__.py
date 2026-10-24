"""
app/gateway - Mini AI Gateway (Week 06 assessment, reference solution).

    from app.gateway import check, Passage
    result = check("What is our parking policy?", [Passage("doc#0", "...")])
    result.decision        # "ALLOW" | "BLOCK_QUERY" | "BLOCK_CONTEXT" | "BLOCK_ERROR"
    result.safe_passages   # passages allowed through
    result.dropped         # chunk_ids that were dropped
    result.findings        # {"CREDENTIAL": 1, "CODENAME": 2}

    models.py     Passage, Decision, GatewayResult, fixed replies
    detectors.py  SecretDetector interface + Credential / PaymentCard / Codename detectors
    core.py       MiniAIGateway: the decision logic (knows no concrete detector)
    config.py     config/gateway.json loader (codenames live there)
    factory.py    which detectors exist; default gateway; module-level check()
    adapters.py   Document / Evidence <-> Passage
"""
from .adapters import Guard, document_to_passage, documents_to_passages, guarded_check, keep_safe
from .config import GatewayConfig, GatewayConfigError, load_config
from .core import MiniAIGateway
from .detectors import (
    CodenameDetector,
    CredentialDetector,
    PaymentCardDetector,
    RegexDetector,
    SecretDetector,
    luhn_valid,
)
from .factory import build_gateway, check, default_detectors, get_default_gateway, reset_default_gateway
from .models import (
    CONTEXT_BLOCKED_REPLY,
    ERROR_REPLY,
    QUERY_BLOCKED_REPLY,
    REPLIES,
    WITHHELD_TEXT,
    Decision,
    GatewayResult,
    Passage,
)

__all__ = [
    "check", "Passage", "GatewayResult", "Decision", "MiniAIGateway", "SecretDetector", "RegexDetector",
    "CredentialDetector", "PaymentCardDetector", "CodenameDetector", "luhn_valid", "GatewayConfig",
    "GatewayConfigError", "load_config", "build_gateway", "default_detectors", "get_default_gateway",
    "reset_default_gateway", "Guard", "guarded_check", "document_to_passage", "documents_to_passages", "keep_safe",
    "QUERY_BLOCKED_REPLY", "CONTEXT_BLOCKED_REPLY", "ERROR_REPLY", "REPLIES", "WITHHELD_TEXT",
]
