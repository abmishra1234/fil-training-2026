"""FR-11 calculator - all arithmetic goes through here, never free-text maths by the LLM.  >>> YOU BUILD THIS <<<

Safe evaluation only: parse with `ast` and allow numbers, + - * / ( ) and round(). Never use eval() on model output.
"""
from __future__ import annotations


def calculate(expression: str) -> float:
    raise NotImplementedError
