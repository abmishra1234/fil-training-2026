"""
app/config.py - settings that belong to the Ad Composer app.

LLM connection settings (mode, gateway, keys, model names) stay in
llm_client.py exactly as in the sample scripts. This file only adds the
few knobs the web app needs. Importing llm_client first makes sure .env
has been loaded before we read anything.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import llm_client  # noqa: F401  (side effect: load_dotenv from the project folder)

ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppConfig:
    image_timeout: float
    dry_run: bool
    max_upload_bytes: int
    input_fidelity: str | None
    output_dir: Path
    frontend_dir: Path
    fonts_dir: Path


def load_config() -> AppConfig:
    timeout = float(os.getenv("IMAGE_TIMEOUT_SECONDS", "600") or 600)
    if timeout <= 0:
        raise ValueError("IMAGE_TIMEOUT_SECONDS must be greater than zero")
    fidelity = (os.getenv("IMAGE_INPUT_FIDELITY") or "").strip().lower() or None
    if fidelity not in (None, "high", "low"):
        raise ValueError("IMAGE_INPUT_FIDELITY must be empty, 'high' or 'low'")
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    return AppConfig(
        image_timeout=timeout,
        dry_run=_bool("AD_DRY_RUN"),
        max_upload_bytes=int(float(os.getenv("MAX_UPLOAD_MB", "10") or 10) * 1024 * 1024),
        input_fidelity=fidelity,
        output_dir=out,
        frontend_dir=ROOT / "frontend",
        fonts_dir=ROOT / "app" / "fonts",
    )


config = load_config()
