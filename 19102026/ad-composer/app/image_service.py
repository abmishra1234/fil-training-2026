"""
app/image_service.py - everything that touches image BYTES.

  normalize_upload()   validate one uploaded file and return clean PNG bytes   (TODO 2)
  compose_with_llm()   call the image model through llm_client.get_client()    (TODO 3)
  compose_dry_run()    local Pillow collage, no LLM - for offline testing     (PROVIDED)
  save_images()        write results to output/ and return file names         (PROVIDED)

Same pattern as 07_image_edit_compose.py:
    client = get_client().with_options(timeout=..., max_retries=0)
    result = client.images.edit(model=settings.image_model, image=[a, b], prompt=prompt)
    png    = base64.b64decode(result.data[0].b64_json)
"""
from __future__ import annotations

import base64
import io
import uuid
from datetime import datetime

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from llm_client import get_client, settings as llm_settings

from .config import config
from .schemas import AdSettings

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIDE = 2048   # bigger inputs are downscaled - the model does not need more
MIN_SIDE = 64     # smaller than this is not a usable photo


class AdComposeError(Exception):
    """Raised by the service layer; main.py turns it into a JSON HTTP error. (PROVIDED)"""

    def __init__(self, status_code: int, message: str, hint: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.hint = hint


# ---------------------------------------------------------------------------
# TODO 2 - normalize_upload()
# ---------------------------------------------------------------------------
def normalize_upload(data: bytes, content_type: str | None, label: str) -> bytes:
    """
    Validate ONE uploaded image and return it as PNG bytes.

    `label` is "model image" or "product image" - use it in error messages so
    the user knows WHICH upload was wrong.

    Raise AdComposeError with:
      400  file is empty
      413  file is bigger than config.max_upload_bytes
      415  content_type not in ALLOWED_TYPES
      400  Pillow cannot open it (UnidentifiedImageError / OSError)
      400  smaller than MIN_SIDE pixels on either side

    Then:
      * ImageOps.exif_transpose()  - phone photos are often stored sideways
      * convert to "RGB" (or keep "RGBA" if the image has transparency)
      * if the longest side > MAX_SIDE, shrink with img.thumbnail((MAX_SIDE, MAX_SIDE))
      * save to an io.BytesIO() as PNG and return the bytes
    """
    raise NotImplementedError("TODO 2: implement normalize_upload() in app/image_service.py")


# ---------------------------------------------------------------------------
# TODO 3 - compose_with_llm()
# ---------------------------------------------------------------------------
def compose_with_llm(model_png: bytes, product_png: bytes, prompt: str, s: AdSettings) -> list[bytes]:
    """
    Call the image model and return a list of PNG bytes (one per variation).

    1. client = get_client().with_options(timeout=config.image_timeout, max_retries=0)
       (image calls are slow and expensive - do not silently retry them)
    2. Build the kwargs for client.images.edit:
         model   = llm_settings.image_model
         image   = [("model.png", model_png, "image/png"), ("product.png", product_png, "image/png")]
                   ORDER MATTERS: the prompt says image 1 = model, image 2 = product
         prompt  = prompt
         size    = s.size            ("1024x1024" | "1536x1024" | "1024x1536")
         quality = s.quality
         n       = s.variations
       and ONLY if config.input_fidelity is set: input_fidelity = config.input_fidelity
       (some gateways reject parameters they do not know)
    3. Decode every item in result.data: base64.b64decode(item.b64_json)
       If an item has no b64_json -> AdComposeError(502, ...)

    Map SDK errors to AdComposeError (status, message, hint):
       APITimeoutError                          -> 504  hint: raise IMAGE_TIMEOUT_SECONDS
       BadRequestError (incl. safety rejection) -> 400  message: the error text
       AuthenticationError / PermissionDenied   -> 502  hint: run python 00_check_setup.py
       RateLimitError                           -> 429  hint: wait and retry
       APIConnectionError                       -> 502  hint: VPN / CA_BUNDLE
       any other APIStatusError                 -> 502
    """
    raise NotImplementedError("TODO 3: implement compose_with_llm() in app/image_service.py")


def _err_text(err: APIStatusError) -> str:
    """Pull the human message out of an OpenAI SDK error. (PROVIDED)"""
    body = getattr(err, "body", None)
    if isinstance(body, dict):
        inner = body.get("error", body)
        if isinstance(inner, dict) and inner.get("message"):
            return str(inner["message"])
    return str(getattr(err, "message", err))


# ---------------------------------------------------------------------------
# PROVIDED - dry-run collage (AD_DRY_RUN=true). No network, no cost.
# ---------------------------------------------------------------------------
def compose_dry_run(model_png: bytes, product_png: bytes, s: AdSettings) -> list[bytes]:
    """A plain side-by-side collage so the whole app can be tested without the gateway."""
    w, h = (int(v) for v in s.size.split("x"))
    w, h = w // 2, h // 2  # half size keeps dry runs fast
    out: list[bytes] = []
    for i in range(s.variations):
        canvas = Image.new("RGB", (w, h), _shade(s.accent_color, 0.25 + 0.1 * i))
        draw = ImageDraw.Draw(canvas)
        for y in range(h):  # simple vertical gradient
            t = y / h
            draw.line([(0, y), (w, y)], fill=_mix(_shade(s.accent_color, 0.15), _shade(s.accent_color, 0.55), t))

        band = int(h * 0.22)  # keep the quote band empty, like the real prompt asks
        top = band if s.quote_position == "top" else int(h * 0.05)
        bottom = h - band if s.quote_position == "bottom" else int(h * 0.95)
        box_h = bottom - top
        for idx, png in enumerate((model_png, product_png)):
            img = Image.open(io.BytesIO(png)).convert("RGBA")
            img.thumbnail((int(w * 0.44), box_h))
            x = int(w * 0.04) if idx == 0 else w - img.width - int(w * 0.04)
            y = top + (box_h - img.height) // 2
            canvas.paste(img, (x, y), img)

        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        out.append(buf.getvalue())
    return out


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _shade(c: str, k: float) -> tuple[int, int, int]:
    r, g, b = _hex(c)
    return int(r * k), int(g * k), int(b * k)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# PROVIDED - save results
# ---------------------------------------------------------------------------
def new_ad_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def save_images(ad_id: str, images: list[bytes]) -> list[str]:
    names: list[str] = []
    for i, data in enumerate(images, start=1):
        name = f"ad_{ad_id}_{i}.png"
        (config.output_dir / name).write_bytes(data)
        names.append(name)
    return names
