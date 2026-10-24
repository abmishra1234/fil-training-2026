"""app/schemas.py - PROVIDED. Request bodies (FastAPI validates them for you)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Mode = Literal["basic", "mqr", "mqr_rrf"]


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, examples=["Can I WFH on Fridays?"])
    mode: Mode = "mqr_rrf"

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()


class CompareRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()


class EvaluateRequest(BaseModel):
    modes: list[Mode] = ["basic", "mqr", "mqr_rrf"]
