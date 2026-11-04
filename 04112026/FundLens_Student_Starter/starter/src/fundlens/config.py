"""Settings read from environment / .env. Secrets live only in .env (never in code, logs or prompts)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llm_mode: str = os.getenv("FUNDLENS_LLM_MODE", "gateway")          # gateway | mock
    gateway_base_url: str = os.getenv("LLM_GATEWAY_BASE_URL", "")
    gateway_api_key: str = os.getenv("LLM_GATEWAY_API_KEY", "")
    chat_model: str = os.getenv("LLM_CHAT_MODEL", "azure/gpt-6-luna")
    embed_model: str = os.getenv("LLM_EMBED_MODEL", "azure/text-embedding-ada-002")
    llm_cache: bool = _flag("FUNDLENS_LLM_CACHE")
    kit_dir: Path = Path(os.getenv("FUNDLENS_KIT_DIR") or ("kit" if Path("kit/MANIFEST.sha256").exists() else "..")).resolve()  # holds corpus/, data/, evaluation/
    index_dir: Path = Path(os.getenv("FUNDLENS_INDEX_DIR", ".index")).resolve()
    db_path: Path = Path(os.getenv("FUNDLENS_DB_PATH", ".data/fundlens.sqlite")).resolve()
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "fundlens-capstone")
    api_url: str = os.getenv("FUNDLENS_API_URL", "http://localhost:8000")

    @property
    def corpus_dir(self) -> Path:
        return self.kit_dir / "corpus"

    @property
    def fund_master_csv(self) -> Path:
        return self.kit_dir / "data" / "fund_master.csv"

    @property
    def rules_yaml(self) -> Path:
        return self.corpus_dir / "rules" / "compliance_rules.yaml"


settings = Settings()
