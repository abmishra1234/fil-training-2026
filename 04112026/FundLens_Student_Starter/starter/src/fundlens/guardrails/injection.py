"""Prompt-injection handling.  >>> YOU BUILD THIS <<<

Text from documents and client emails is DATA. Wrap it in clear delimiters in prompts, tell the model never to follow
instructions found inside it, and optionally flag suspicious phrases ("ignore all previous instructions", "system override",
"mark this approved", HTML comments addressed to an AI) so the trace shows they were detected.
Some corpus documents and client emails contain planted injection attempts.
"""
from __future__ import annotations


def flag_injection(text: str) -> list[str]:
    raise NotImplementedError
