"""
Shared test setup. The tests NEVER call the real gateway: get_client() is
replaced by a fake, so you can run `pytest` anywhere, any time, for free.
"""
import base64
import dataclasses
import io
import os
from types import SimpleNamespace

# Must be set BEFORE the app is imported. load_dotenv() never overrides these,
# so your personal .env does not change test behaviour.
os.environ["LLM_MODE"] = "direct"
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["AD_DRY_RUN"] = "false"
os.environ["IMAGE_INPUT_FIDELITY"] = ""

import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from app import config as config_module  # noqa: E402
from app import image_service, quote_service, routes, text_overlay  # noqa: E402

MODULES_WITH_CONFIG = (config_module, image_service, quote_service, routes, text_overlay)


def make_image_bytes(size=(320, 400), color=(200, 120, 90), fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


def png_b64(size=(256, 256), color=(30, 60, 90)) -> str:
    return base64.b64encode(make_image_bytes(size, color, "PNG")).decode()


class FakeImages:
    def __init__(self):
        self.calls = []
        self.raise_exc = None
        self.return_b64 = True

    def edit(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise self.raise_exc
        n = kwargs.get("n", 1)
        w, h = (int(v) // 4 for v in kwargs.get("size", "1024x1024").split("x"))
        data = [SimpleNamespace(b64_json=png_b64((w, h)) if self.return_b64 else None) for _ in range(n)]
        return SimpleNamespace(data=data)


class FakeCompletions:
    def __init__(self):
        self.calls = []
        self.content = '{"suggestions": ["Glow all day", "Your skin, upgraded", "Glow all day"]}'
        self.raise_exc = None

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise self.raise_exc
        msg = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class FakeClient:
    def __init__(self):
        self.images = FakeImages()
        self.chat = SimpleNamespace(completions=FakeCompletions())
        self.options = None

    def with_options(self, **kwargs):
        self.options = kwargs
        return self


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(image_service, "get_client", lambda: client)
    monkeypatch.setattr(quote_service, "get_client", lambda: client)
    return client


@pytest.fixture
def app_config(monkeypatch, tmp_path):
    """Point output/ at a temp folder. Call set_config(dry_run=True, ...) to change more."""
    base = dataclasses.replace(config_module.config, output_dir=tmp_path)

    def set_config(**changes):
        cfg = dataclasses.replace(base, **changes)
        for mod in MODULES_WITH_CONFIG:
            monkeypatch.setattr(mod, "config", cfg)
        return cfg

    set_config()
    return set_config


@pytest.fixture
def api(fake_client, app_config):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, raise_server_exceptions=False)
