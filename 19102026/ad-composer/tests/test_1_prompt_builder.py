"""TODO 1a + 1b - prompt_builder.py"""
from app.prompt_builder import (
    FONT_PRESETS,
    MOOD_PRESETS,
    SAFETY_RULES,
    SCENE_PRESETS,
    STYLE_PRESETS,
    build_ad_prompt,
    clean_quote,
)
from app.schemas import MAX_QUOTE_CHARS, AdSettings


# ----------------------------------------------------------------- clean_quote
def test_clean_quote_blank():
    assert clean_quote(None) == ""
    assert clean_quote("   \n\t ") == ""


def test_clean_quote_collapses_whitespace():
    assert clean_quote("  Glow   all\n day  ") == "Glow all day"


def test_clean_quote_replaces_double_quotes():
    out = clean_quote('Say "hello" to “summer”')
    assert '"' not in out and "“" not in out and "”" not in out
    assert out == "Say 'hello' to 'summer'"


def test_clean_quote_truncates_with_ellipsis():
    out = clean_quote("word " * 60)
    assert len(out) <= MAX_QUOTE_CHARS
    assert out.endswith("…")


def test_clean_quote_keeps_short_text():
    assert clean_quote("Pure. Simple. You.") == "Pure. Simple. You."


# ------------------------------------------------------------- build_ad_prompt
def test_prompt_names_image_order():
    p = build_ad_prompt("Glow all day", AdSettings())
    assert "Image 1" in p and "MODEL" in p
    assert "Image 2" in p and "PRODUCT" in p
    assert p.index("Image 1") < p.index("Image 2")


def test_prompt_uses_presets():
    s = AdSettings(style="luxury", scene="beach", mood="bold")
    p = build_ad_prompt("Glow all day", s)
    assert STYLE_PRESETS["luxury"] in p
    assert SCENE_PRESETS["beach"] in p
    assert MOOD_PRESETS["bold"] in p


def test_prompt_ai_mode_has_exact_quote_font_colour_position():
    s = AdSettings(text_mode="ai", quote_position="top", font_style="elegant-serif", text_color="#ffcc00")
    p = build_ad_prompt('  Glow  all "day"  ', s)
    assert "\"Glow all 'day'\"" in p
    assert FONT_PRESETS["elegant-serif"] in p
    assert "#FFCC00" in p
    assert "top" in p


def test_prompt_overlay_mode_asks_for_no_text_and_hides_quote():
    s = AdSettings(text_mode="overlay", quote_position="center")
    p = build_ad_prompt("Glow all day", s)
    assert "Glow all day" not in p
    assert "NOT" in p and "text" in p.lower()
    assert "center" in p


def test_prompt_none_mode_and_empty_quote():
    for s, q in ((AdSettings(text_mode="none"), "Glow all day"), (AdSettings(text_mode="ai"), "   ")):
        p = build_ad_prompt(q, s)
        assert "Glow all day" not in p
        assert "NOT add any text" in p


def test_prompt_brand_and_accent():
    p = build_ad_prompt("Glow", AdSettings(brand_name="Lumina", accent_color="#12ab34"))
    assert "Lumina" in p and "#12AB34" in p
    p2 = build_ad_prompt("Glow", AdSettings(accent_color="#12ab34"))
    assert "#12AB34" in p2


def test_prompt_has_all_safety_rules():
    p = build_ad_prompt("Glow", AdSettings())
    for rule in SAFETY_RULES:
        assert rule in p


def test_prompt_extra_instructions_last():
    p = build_ad_prompt("Glow", AdSettings(extra_instructions="model smiling, soft pink tones"))
    assert p.rstrip().endswith("model smiling, soft pink tones")
    assert "must not override" in p
    assert "Additional art direction" not in build_ad_prompt("Glow", AdSettings())
