"""
app/gateway/detectors.py - one class per secret type (Strategy pattern).

The gateway only knows the SecretDetector interface:

    secret_type : str                      e.g. "CREDENTIAL"
    find(text)  -> list[(start, end)]      where the secrets are (positions, never the text)
    count(text) -> int                     how many

Adding a secret type = write one new SecretDetector subclass (or a RegexDetector
instance) and register it in factory.py. The gateway core is never edited (OCP).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Iterable, Sequence

Span = tuple[int, int]


class SecretDetector(ABC):
    """Interface every detector implements (small on purpose: ISP)."""

    secret_type: str = ""

    @abstractmethod
    def find(self, text: str) -> list[Span]:
        """Positions of every secret of this type in `text` (non-overlapping, sorted)."""

    def count(self, text: str) -> int:
        return len(self.find(text))


def merge_spans(spans: Iterable[Span]) -> list[Span]:
    """Overlapping matches of different patterns are ONE secret ("api_key=sk-test-..." counts once)."""
    out: list[Span] = []
    for start, end in sorted(spans):
        if out and start < out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


class RegexDetector(SecretDetector):
    """Generic detector: any number of regexes, overlapping hits merged. Reusable for new types."""

    def __init__(self, secret_type: str, patterns: Sequence[str | re.Pattern], flags: int = 0):
        if not secret_type:
            raise ValueError("secret_type must not be empty")
        self.secret_type = secret_type
        self._patterns = [p if isinstance(p, re.Pattern) else re.compile(p, flags) for p in patterns]

    def find(self, text: str) -> list[Span]:
        return merge_spans(m.span() for rx in self._patterns for m in rx.finditer(text))


# --------------------------------------------------------------------------- credentials
DEFAULT_KEY_PREFIX_PATTERNS = [
    r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{15,}",             # OpenAI-style: sk-test-..., sk-live-..., sk-proj-...
    r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",                  # AWS access key id
    r"\bgh[pousr]_[A-Za-z0-9]{36}\b",                  # GitHub tokens
    r"\bxox[abprs]-[A-Za-z0-9-]{10,}",                 # Slack tokens
    r"\bAIza[0-9A-Za-z_-]{35}\b",                      # Google API key
    r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",        # PEM private key header
]
DEFAULT_SECRET_KEYWORDS = ["password", "secret", "api_key"]


def keyword_assignment_pattern(keywords: Sequence[str]) -> str:
    """
    password / secret / api_key FOLLOWED BY = or :  and a value.
      matches  password=Winter2026!   client_secret: Qx7abc   DB_PASSWORD = x   API-KEY:abc
      ignores  "passwords and tokens must never be committed"   "the secrets manager"
    An optional prefix ending in _ or - is allowed (client_secret, DB_PASSWORD).
    """
    alts = []
    for kw in keywords:
        # api_key also accepts api-key / apikey
        alts.append(re.escape(kw).replace("_", "[_-]?") if "_" in kw else re.escape(kw))
    words = "|".join(sorted(alts, key=len, reverse=True))
    return rf"(?<![A-Za-z0-9])(?:[A-Za-z0-9]+[_-])?(?:{words})[ \t]*[:=][ \t]*[^\s,;]+"


class CredentialDetector(RegexDetector):
    def __init__(self, prefix_patterns: Sequence[str] | None = None, keywords: Sequence[str] | None = None):
        prefix = list(DEFAULT_KEY_PREFIX_PATTERNS if prefix_patterns is None else prefix_patterns)
        kw = list(DEFAULT_SECRET_KEYWORDS if keywords is None else keywords)
        patterns: list[re.Pattern] = [re.compile(p) for p in prefix]
        if kw:
            patterns.append(re.compile(keyword_assignment_pattern(kw), re.IGNORECASE))
        super().__init__("CREDENTIAL", patterns)


# --------------------------------------------------------------------------- payment cards
# 13-19 digits, a single space or dash allowed between digits. The look-arounds make
# the match a WHOLE run of digits: a 20-digit number or a phone number is not cut into a
# 16-digit "card". Linear time (no nested quantifiers), safe on 2,000-char digit runs.
_CARD_CANDIDATE = re.compile(r"(?<!\d)(?<!\d[ -])\d(?:[ -]?\d){12,18}(?![ -]?\d)")


def luhn_valid(digits: str) -> bool:
    """Luhn (mod 10) checksum. `digits` contains only 0-9."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


class PaymentCardDetector(SecretDetector):
    secret_type = "PAYMENT_CARD"

    def find(self, text: str) -> list[Span]:
        spans = []
        for m in _CARD_CANDIDATE.finditer(text):
            digits = re.sub(r"[ -]", "", m.group())
            if 13 <= len(digits) <= 19 and luhn_valid(digits):
                spans.append(m.span())
        return spans


# --------------------------------------------------------------------------- codenames
class CodenameDetector(SecretDetector):
    """Case-insensitive, whole-phrase match against a list from the config file."""

    secret_type = "CODENAME"

    def __init__(self, codenames: Iterable[str]):
        names = sorted({" ".join(n.split()) for n in codenames if n and n.strip()}, key=len, reverse=True)
        self.codenames = names
        if names:
            # each name: words escaped literally, any whitespace (incl. a line break) between words
            alts = "|".join(r"\s+".join(re.escape(w) for w in n.split()) for n in names)
            self._rx: re.Pattern | None = re.compile(rf"(?<!\w)(?:{alts})(?!\w)", re.IGNORECASE)
        else:
            self._rx = None

    def find(self, text: str) -> list[Span]:
        return [m.span() for m in self._rx.finditer(text)] if self._rx else []
