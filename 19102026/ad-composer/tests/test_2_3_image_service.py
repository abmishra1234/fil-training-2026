"""TODO 2 (normalize_upload) + TODO 3 (compose_with_llm) - image_service.py"""
import io

import httpx
import pytest
from openai import APITimeoutError, AuthenticationError, BadRequestError
from PIL import Image

from app.image_service import AdComposeError, compose_with_llm, normalize_upload
from app.schemas import AdSettings

from .conftest import make_image_bytes

REQ = httpx.Request("POST", "https://example.test/v1/images/edits")


# --------------------------------------------------------------- TODO 2
def test_normalize_returns_png(app_config):
    out = normalize_upload(make_image_bytes(), "image/jpeg", "model image")
    img = Image.open(io.BytesIO(out))
    assert img.format == "PNG"
    assert img.size == (320, 400)


@pytest.mark.parametrize(
    "data, ctype, status",
    [
        (b"", "image/png", 400),
        (b"not an image at all", "image/png", 400),
        (make_image_bytes(), "application/pdf", 415),
        (make_image_bytes(), None, 415),
        (make_image_bytes((40, 40)), "image/jpeg", 400),
    ],
)
def test_normalize_rejects_bad_input(app_config, data, ctype, status):
    with pytest.raises(AdComposeError) as e:
        normalize_upload(data, ctype, "product image")
    assert e.value.status_code == status
    assert "product image" in e.value.message


def test_normalize_rejects_too_large(app_config):
    app_config(max_upload_bytes=1000)
    with pytest.raises(AdComposeError) as e:
        normalize_upload(make_image_bytes(), "image/jpeg", "model image")
    assert e.value.status_code == 413


def test_normalize_downscales_huge_images(app_config):
    out = normalize_upload(make_image_bytes((3000, 1500)), "image/jpeg", "model image")
    assert max(Image.open(io.BytesIO(out)).size) <= 2048


def test_normalize_keeps_transparency(app_config):
    buf = io.BytesIO()
    Image.new("RGBA", (200, 200), (255, 0, 0, 0)).save(buf, "PNG")
    out = normalize_upload(buf.getvalue(), "image/png", "product image")
    assert Image.open(io.BytesIO(out)).mode == "RGBA"


# --------------------------------------------------------------- TODO 3
def test_compose_calls_images_edit_correctly(fake_client, app_config):
    s = AdSettings(aspect_ratio="portrait", quality="high", variations=2)
    out = compose_with_llm(b"MODEL", b"PRODUCT", "the prompt", s)

    assert len(out) == 2 and all(isinstance(b, bytes) for b in out)
    assert fake_client.options["max_retries"] == 0
    assert fake_client.options["timeout"] > 0
    call = fake_client.images.calls[0]
    assert call["prompt"] == "the prompt"
    assert call["size"] == "1024x1536"
    assert call["quality"] == "high"
    assert call["n"] == 2
    assert call["image"][0][1] == b"MODEL"      # image 1 = model
    assert call["image"][1][1] == b"PRODUCT"    # image 2 = product
    assert "input_fidelity" not in call


def test_compose_sends_input_fidelity_only_when_configured(fake_client, app_config):
    app_config(input_fidelity="high")
    compose_with_llm(b"M", b"P", "p", AdSettings())
    assert fake_client.images.calls[0]["input_fidelity"] == "high"


def test_compose_timeout_maps_to_504(fake_client, app_config):
    fake_client.images.raise_exc = APITimeoutError(request=REQ)
    with pytest.raises(AdComposeError) as e:
        compose_with_llm(b"M", b"P", "p", AdSettings())
    assert e.value.status_code == 504


def test_compose_bad_request_maps_to_400_with_message(fake_client, app_config):
    resp = httpx.Response(400, request=REQ)
    fake_client.images.raise_exc = BadRequestError(
        "bad", response=resp, body={"error": {"message": "Your request was rejected by the safety system."}}
    )
    with pytest.raises(AdComposeError) as e:
        compose_with_llm(b"M", b"P", "p", AdSettings())
    assert e.value.status_code == 400
    assert "safety system" in e.value.message


def test_compose_auth_error_maps_to_502(fake_client, app_config):
    fake_client.images.raise_exc = AuthenticationError("no", response=httpx.Response(401, request=REQ), body=None)
    with pytest.raises(AdComposeError) as e:
        compose_with_llm(b"M", b"P", "p", AdSettings())
    assert e.value.status_code == 502
    assert "00_check_setup" in (e.value.hint or "")


def test_compose_missing_b64_maps_to_502(fake_client, app_config):
    fake_client.images.return_b64 = False
    with pytest.raises(AdComposeError) as e:
        compose_with_llm(b"M", b"P", "p", AdSettings())
    assert e.value.status_code == 502
