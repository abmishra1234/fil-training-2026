"""
app/schemas.py - the contract between the frontend and the API.

AdSettings is what the user picks in the "Output settings" panel.
The frontend sends it as ONE JSON string in the multipart form field
`settings`, next to the two image files and the quote.
(PROVIDED - read it, you will use every field in prompt_builder.py)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Style = Literal["studio", "luxury", "minimal", "vibrant", "festive", "lifestyle"]
Scene = Literal["auto", "plain-studio", "nature-outdoor", "urban-street", "beach", "festive-lights", "home-interior"]
Mood = Literal["premium", "playful", "bold", "calm", "warm"]
AspectRatio = Literal["square", "landscape", "portrait"]
Quality = Literal["low", "medium", "high"]
TextMode = Literal["ai", "overlay", "none"]
Position = Literal["top", "center", "bottom"]
FontStyle = Literal["modern-sans", "elegant-serif", "bold-display"]

# aspect ratio -> the three sizes gpt-image-1 supports
SIZE_FOR_ASPECT: dict[str, str] = {
    "square": "1024x1024",
    "landscape": "1536x1024",
    "portrait": "1024x1536",
}

MAX_QUOTE_CHARS = 120


class AdSettings(BaseModel):
    style: Style = "studio"
    scene: Scene = "auto"
    mood: Mood = "premium"
    aspect_ratio: AspectRatio = "square"
    quality: Quality = "medium"
    # ai      -> the image model paints the quote into the picture
    # overlay -> the model leaves clean space, Pillow writes the quote (pixel-perfect spelling)
    # none    -> no text at all (image only)
    text_mode: TextMode = "ai"
    quote_position: Position = "bottom"
    font_style: FontStyle = "modern-sans"
    text_color: str = Field("#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str = Field("#E4572E", pattern=r"^#[0-9A-Fa-f]{6}$")
    brand_name: str | None = Field(None, max_length=40)
    variations: int = Field(1, ge=1, le=3)
    extra_instructions: str | None = Field(None, max_length=300)

    @field_validator("brand_name", "extra_instructions")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())
        return v or None

    @property
    def size(self) -> str:
        return SIZE_FOR_ASPECT[self.aspect_ratio]


class QuoteRefineRequest(BaseModel):
    quote: str = Field(..., min_length=1, max_length=300)
    mood: Mood = "premium"
    brand_name: str | None = Field(None, max_length=40)


class QuoteRefineResponse(BaseModel):
    original: str
    suggestions: list[str]


class PromptPreviewRequest(BaseModel):
    quote: str = Field("", max_length=300)
    settings: AdSettings = AdSettings()


class PromptPreviewResponse(BaseModel):
    prompt: str
    size: str
    text_mode: TextMode


class AdImage(BaseModel):
    url: str
    filename: str


class AdResponse(BaseModel):
    id: str
    images: list[AdImage]
    prompt: str
    quote: str
    settings: AdSettings
    mode: Literal["llm", "dry-run"]
    model: str
    elapsed_seconds: float
