"""TODO 4a + 4b - text_overlay.py"""
import io

from PIL import Image, ImageChops, ImageDraw

from app.schemas import AdSettings
from app.text_overlay import load_font, overlay_quote, text_width, wrap_text

from .conftest import make_image_bytes


def _draw():
    return ImageDraw.Draw(Image.new("RGB", (10, 10)))


# --------------------------------------------------------------- TODO 4a
def test_wrap_respects_width_and_keeps_words():
    d, f = _draw(), load_font("modern-sans", 32)
    text = "Glow that lasts from sunrise to sunset, every single day of the week"
    lines = wrap_text(d, text, f, 300)
    assert len(lines) > 1
    assert " ".join(lines) == text
    assert all(text_width(d, ln, f) <= 300 for ln in lines)


def test_wrap_long_single_word_gets_own_line():
    d, f = _draw(), load_font("modern-sans", 32)
    lines = wrap_text(d, "Hi Supercalifragilisticexpialidocious yes", f, 120)
    assert "Supercalifragilisticexpialidocious" in lines


def test_wrap_empty():
    assert wrap_text(_draw(), "   ", load_font("modern-sans", 20), 100) == []


# --------------------------------------------------------------- TODO 4b
def _png(size=(600, 600)):
    return make_image_bytes(size, (40, 90, 140), "PNG")


def _diff_rows(before: bytes, after: bytes):
    a = Image.open(io.BytesIO(before)).convert("RGB")
    b = Image.open(io.BytesIO(after)).convert("RGB")
    assert a.size == b.size
    box = ImageChops.difference(a, b).getbbox()
    assert box is not None, "overlay_quote did not change the image"
    return box


def test_overlay_keeps_size_and_returns_png():
    src = _png((640, 480))
    out = overlay_quote(src, "Glow all day", AdSettings())
    img = Image.open(io.BytesIO(out))
    assert img.format == "PNG" and img.size == (640, 480)


def test_overlay_blank_quote_returns_input():
    src = _png()
    assert overlay_quote(src, "  ", AdSettings()) == src


def test_overlay_respects_position():
    src = _png()
    top = _diff_rows(src, overlay_quote(src, "Glow all day", AdSettings(quote_position="top")))
    bottom = _diff_rows(src, overlay_quote(src, "Glow all day", AdSettings(quote_position="bottom")))
    assert top[3] <= 300      # all changes in the upper half
    assert bottom[1] >= 300   # all changes in the lower half


def test_overlay_long_quote_still_fits():
    src = _png((1024, 1024))
    long_q = "Glow that lasts from sunrise to sunset with the lightest touch of natural goodness"
    box = _diff_rows(src, overlay_quote(src, long_q, AdSettings(brand_name="Lumina")))
    assert box[0] > 0 and box[2] < 1024   # did not run off the left/right edge
