"""TODO 5 (refine_quote) + TODO 6/7/8 (routes) - end-to-end through FastAPI."""
import io
import json

from PIL import Image

from app.quote_service import parse_suggestions

from .conftest import make_image_bytes


def _files():
    return {
        "model_image": ("model.jpg", make_image_bytes((300, 380), (220, 180, 160)), "image/jpeg"),
        "product_image": ("product.jpg", make_image_bytes((300, 300), (60, 140, 200)), "image/jpeg"),
    }


# ----------------------------------------------------------- PROVIDED endpoints
def test_health_and_options(api):
    assert api.get("/api/health").json()["status"] == "ok"
    opts = api.get("/api/options").json()
    assert "overlay" in opts["text_mode"] and opts["defaults"]["aspect_ratio"] == "square"


def test_parse_suggestions_variants():
    assert parse_suggestions('```json\n{"suggestions": ["A", "B"]}\n```') == ["A", "B"]
    assert parse_suggestions("1. Glow on\n2. Shine bright\n- Be you") == ["Glow on", "Shine bright", "Be you"]


# ----------------------------------------------------------- TODO 7
def test_prompt_preview(api):
    r = api.post("/api/prompt/preview", json={"quote": "Glow all day", "settings": {"aspect_ratio": "landscape"}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "Glow all day" in body["prompt"]
    assert body["size"] == "1536x1024" and body["text_mode"] == "ai"


# ----------------------------------------------------------- TODO 5 + 8
def test_quote_refine_calls_chat_model(api, fake_client):
    r = api.post("/api/quote/refine", json={"quote": "our cream is good", "mood": "playful", "brand_name": "Lumina"})
    assert r.status_code == 200, r.text
    assert r.json()["suggestions"] == ["Glow all day", "Your skin, upgraded"]   # de-duplicated
    call = fake_client.chat.completions.calls[0]
    sent = json.dumps(call["messages"])
    assert "our cream is good" in sent and "playful" in sent and "Lumina" in sent


def test_quote_refine_dry_run_skips_llm(api, fake_client, app_config):
    app_config(dry_run=True)
    r = api.post("/api/quote/refine", json={"quote": "our cream is good", "brand_name": "Lumina"})
    assert r.status_code == 200, r.text
    assert len(r.json()["suggestions"]) >= 2
    assert fake_client.chat.completions.calls == []


def test_quote_refine_empty_model_answer_is_502(api, fake_client):
    fake_client.chat.completions.content = "   "
    assert api.post("/api/quote/refine", json={"quote": "x"}).status_code == 502


# ----------------------------------------------------------- TODO 6
def test_compose_happy_path(api, fake_client, app_config):
    settings = {"aspect_ratio": "landscape", "quality": "low", "variations": 2, "text_mode": "ai"}
    r = api.post("/api/ads/compose", files=_files(), data={"quote": "Glow all day", "settings": json.dumps(settings)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "llm" and len(body["images"]) == 2
    assert "Glow all day" in body["prompt"]
    call = fake_client.images.calls[0]
    assert call["size"] == "1536x1024" and call["n"] == 2 and call["quality"] == "low"
    # the generated file can be downloaded
    img = api.get(body["images"][0]["url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    # and it shows up in history
    assert api.get("/api/ads").json()[0]["id"] == body["id"]


def test_compose_overlay_mode_draws_text(api, fake_client):
    r = api.post("/api/ads/compose", files=_files(),
                 data={"quote": "Glow all day", "settings": json.dumps({"text_mode": "overlay"})})
    assert r.status_code == 200, r.text
    assert "Glow all day" not in r.json()["prompt"]          # model was told: no text
    png = api.get(r.json()["images"][0]["url"]).content
    colours = Image.open(io.BytesIO(png)).convert("RGB").getcolors(maxcolors=100000)
    assert colours is None or len(colours) > 1                # fake image was one flat colour


def test_compose_requires_quote_unless_none(api, fake_client):
    r = api.post("/api/ads/compose", files=_files(), data={"quote": " ", "settings": "{}"})
    assert r.status_code == 400 and "quote" in r.json()["error"].lower()
    r = api.post("/api/ads/compose", files=_files(), data={"quote": "", "settings": json.dumps({"text_mode": "none"})})
    assert r.status_code == 200, r.text


def test_compose_invalid_settings_is_422(api, fake_client):
    r = api.post("/api/ads/compose", files=_files(), data={"quote": "Hi", "settings": json.dumps({"variations": 9})})
    assert r.status_code == 422 and "variations" in r.json()["error"]


def test_compose_wrong_file_type_is_415(api, fake_client):
    files = _files()
    files["product_image"] = ("x.pdf", b"%PDF-1.4", "application/pdf")
    r = api.post("/api/ads/compose", files=files, data={"quote": "Hi", "settings": "{}"})
    assert r.status_code == 415 and "product image" in r.json()["error"]
    assert fake_client.images.calls == []                    # validated BEFORE spending money


def test_compose_dry_run_never_calls_llm(api, fake_client, app_config):
    app_config(dry_run=True)
    r = api.post("/api/ads/compose", files=_files(), data={"quote": "Glow all day", "settings": "{}"})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "dry-run"
    assert fake_client.images.calls == []
