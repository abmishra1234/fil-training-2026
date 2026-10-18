"""
app/routes.py - the HTTP API the frontend calls.

  GET  /api/health              PROVIDED  is the server up, which mode/model?
  GET  /api/options             PROVIDED  dropdown values for the frontend
  GET  /api/ads                 PROVIDED  recent ads (history panel)
  GET  /api/ads/files/{name}    PROVIDED  download one generated image
  POST /api/prompt/preview      TODO 7    show the prompt WITHOUT calling the model
  POST /api/quote/refine        TODO 8    3 polished versions of the quote (chat model)
  POST /api/ads/compose         TODO 6    THE main endpoint: images + quote + settings -> ad

Endpoints are plain `def` (not `async def`) on purpose: the OpenAI SDK call
is blocking, and FastAPI runs `def` endpoints in a worker thread, so one slow
image call does not freeze the whole server.
"""
from __future__ import annotations

import json
import logging
import time
from typing import get_args

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from llm_client import describe, settings as llm_settings

from . import schemas
from .config import config
from .image_service import (
    AdComposeError,
    compose_dry_run,
    compose_with_llm,
    new_ad_id,
    normalize_upload,
    save_images,
)
from .prompt_builder import build_ad_prompt, clean_quote
from .quote_service import refine_quote
from .schemas import (
    AdImage,
    AdResponse,
    AdSettings,
    PromptPreviewRequest,
    PromptPreviewResponse,
    QuoteRefineRequest,
    QuoteRefineResponse,
)
from .text_overlay import overlay_quote

log = logging.getLogger("ad_composer")
router = APIRouter(prefix="/api")


# --------------------------------------------------------------------------- #
# PROVIDED
# --------------------------------------------------------------------------- #
@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm": describe(),
        "image_model": llm_settings.image_model,
        "chat_model": llm_settings.chat_model,
        "dry_run": config.dry_run,
    }


@router.get("/options")
def options() -> dict:
    """Every Literal in schemas.py, so the frontend never hard-codes a value the API rejects."""
    return {
        "style": list(get_args(schemas.Style)),
        "scene": list(get_args(schemas.Scene)),
        "mood": list(get_args(schemas.Mood)),
        "aspect_ratio": list(get_args(schemas.AspectRatio)),
        "quality": list(get_args(schemas.Quality)),
        "text_mode": list(get_args(schemas.TextMode)),
        "quote_position": list(get_args(schemas.Position)),
        "font_style": list(get_args(schemas.FontStyle)),
        "defaults": AdSettings().model_dump(),
        "max_quote_chars": schemas.MAX_QUOTE_CHARS,
        "max_upload_mb": config.max_upload_bytes / (1024 * 1024),
    }


@router.get("/ads")
def list_ads(limit: int = 12) -> list[dict]:
    files = sorted(config.output_dir.glob("ad_*.json"), reverse=True)[: max(1, min(limit, 50))]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


@router.get("/ads/files/{name}")
def get_ad_file(name: str):
    # only plain file names that we generated - no "../" path tricks
    if not (name.startswith("ad_") and name.endswith(".png")) or "/" in name or "\\" in name or ".." in name:
        raise HTTPException(404, "Not found")
    path = config.output_dir / name
    if not path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="image/png", filename=name)


def parse_settings(raw: str) -> AdSettings:
    """PROVIDED: the frontend sends settings as a JSON string inside the multipart form."""
    try:
        return AdSettings.model_validate_json(raw or "{}")
    except ValidationError as err:
        first = err.errors()[0]
        where = ".".join(str(p) for p in first.get("loc", ())) or "settings"
        raise AdComposeError(422, f"Invalid setting '{where}': {first.get('msg')}", None) from None


def save_metadata(resp: AdResponse) -> None:
    """PROVIDED: write ad_<id>.json next to the images (feeds GET /api/ads)."""
    path = config.output_dir / f"ad_{resp.id}.json"
    path.write_text(resp.model_dump_json(indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# TODO 7 - prompt preview
# --------------------------------------------------------------------------- #
@router.post("/prompt/preview", response_model=PromptPreviewResponse)
def preview_prompt(req: PromptPreviewRequest) -> PromptPreviewResponse:
    """
    Return the exact prompt build_ad_prompt() would send, plus size and text_mode.
    No model call - this is free, use it to debug your prompt.
    """
    raise NotImplementedError("TODO 7: implement POST /api/prompt/preview in app/routes.py")


# --------------------------------------------------------------------------- #
# TODO 8 - quote refine
# --------------------------------------------------------------------------- #
@router.post("/quote/refine", response_model=QuoteRefineResponse)
def refine(req: QuoteRefineRequest) -> QuoteRefineResponse:
    """Call quote_service.refine_quote() and wrap the result in QuoteRefineResponse."""
    raise NotImplementedError("TODO 8: implement POST /api/quote/refine in app/routes.py")


# --------------------------------------------------------------------------- #
# TODO 6 - THE main endpoint
# --------------------------------------------------------------------------- #
@router.post("/ads/compose", response_model=AdResponse)
def compose_ad(
    model_image: UploadFile = File(..., description="Photo of the model / person"),
    product_image: UploadFile = File(..., description="Photo of the product"),
    quote: str = Form("", description="Marketing quote / headline"),
    settings: str = Form("{}", description="AdSettings as a JSON string"),
) -> AdResponse:
    """
    Wire everything together:

      1. s = parse_settings(settings);  q = clean_quote(quote)
      2. If s.text_mode != "none" and q is empty
             -> AdComposeError(400, "Please enter a marketing quote ...")
      3. model_png   = normalize_upload(model_image.file.read(),   model_image.content_type,   "model image")
         product_png = normalize_upload(product_image.file.read(), product_image.content_type, "product image")
      4. prompt = build_ad_prompt(q, s)
      5. t0 = time.perf_counter()
         images = compose_dry_run(...) if config.dry_run else compose_with_llm(...)
      6. TEXT composition: if s.text_mode == "overlay"
             (or dry-run with text_mode "ai" - the collage cannot paint text)
             -> images = [overlay_quote(img, q, s) for img in images]
      7. ad_id = new_ad_id();  names = save_images(ad_id, images)
      8. Build AdResponse (url = f"/api/ads/files/{name}"), mode "dry-run" or "llm",
         model = llm_settings.image_model (or "pillow-collage" in dry-run),
         elapsed_seconds rounded to 1 decimal.
      9. save_metadata(resp); log one INFO line; return resp
    """
    raise NotImplementedError("TODO 6: implement POST /api/ads/compose in app/routes.py")
