from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_api_key: str | None
    ark_api_key: str | None
    ark_base_url: str
    llm_model: str


def load_settings(env_path: Path | None = None) -> Settings:
    resolved_env_path = _resolve_env_path(env_path)
    _load_dotenv_optional(resolved_env_path)
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ark_api_key=os.getenv("ARK_API_KEY"),
        ark_base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )


def _load_dotenv_optional(env_path: Path | None = None) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(dotenv_path=env_path)


def _resolve_env_path(env_path: Path | None) -> Path | None:
    if env_path is not None:
        return env_path

    local_default = Path.cwd() / ".env"
    if local_default.exists():
        return local_default

    demo_default = Path(__file__).resolve().parents[1] / ".env"
    if demo_default.exists():
        return demo_default

    return None
