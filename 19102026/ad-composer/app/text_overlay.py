"""
app/text_overlay.py - TEXT composition with Pillow (text_mode = "overlay").

Why do this at all if the image model can draw text?
  * Image models still misspell words, especially long quotes or Hindi/Hinglish.
  * Marketing teams need the headline pixel-perfect and on-brand.
So in "overlay" mode the prompt asks for a clean empty band, and WE draw the
quote on top - exact spelling, exact colour, exact font, every time.
"""
from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .config import config
from .schemas import AdSettings

# PROVIDED: font files shipped in app/fonts (DejaVu, free licence) so Windows,
# Mac and Linux all render the same.
FONT_FILES = {
    "modern-sans": "DejaVuSans-Bold.ttf",
    "elegant-serif": "DejaVuSerif-Bold.ttf",
    "bold-display": "DejaVuSansCondensed-Bold.ttf",
}


@lru_cache(maxsize=64)
def load_font(font_style: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """PROVIDED: bundled font -> common system fonts -> Pillow default."""
    candidates = [str(config.fonts_dir / FONT_FILES.get(font_style, "DejaVuSans-Bold.ttf")),
                  "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    """PROVIDED: pixel width of `text` in `font`."""
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def hex_to_rgb(c: str) -> tuple[int, int, int]:
    """PROVIDED: '#E4572E' -> (228, 87, 46)"""
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


# ---------------------------------------------------------------------------
# TODO 4a - wrap_text()
# ---------------------------------------------------------------------------
def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """
    Greedy word wrap by PIXEL width (not characters - fonts are proportional).

    Walk the words; keep adding a word to the current line while
    text_width(draw, candidate, font) <= max_width; otherwise start a new line.
    A single word wider than max_width goes on its own line (do not split words).
    Empty text -> [].
    """
    raise NotImplementedError("TODO 4a: implement wrap_text() in app/text_overlay.py")


# ---------------------------------------------------------------------------
# TODO 4b - overlay_quote()
# ---------------------------------------------------------------------------
def overlay_quote(png: bytes, quote: str, s: AdSettings) -> bytes:
    """
    Draw the quote (and the brand name, if any) onto the image. Return PNG bytes.

    Suggested recipe (W, H = image size):
      1. img = Image.open(...).convert("RGBA"); make a transparent layer the same size
      2. Band: height ~ 24% of H, full width, at s.quote_position
         (top -> y=0, center -> middle, bottom -> y=H-band)
      3. Fit the text: start with font size ~ 7% of H and shrink (step 2px, min 18px)
         until wrap_text(..., max_width = 88% of W) gives lines whose total height
         (line height = 1.2 x font size) fits in ~75% of the band.
      4. Draw a rounded rectangle behind the text block in s.accent_color with
         alpha ~200 (so the photo shows through a little).
      5. Draw each line centred horizontally in s.text_color; a 2px dark shadow
         first makes it readable on any background.
      6. If s.brand_name: draw it in small caps-ish (upper case, ~40% of the font
         size) under the quote, inside the same panel.
      7. Image.alpha_composite(img, layer) -> convert("RGB") -> save PNG -> bytes.
    Blank quote -> return the input unchanged.
    """
    raise NotImplementedError("TODO 4b: implement overlay_quote() in app/text_overlay.py")
