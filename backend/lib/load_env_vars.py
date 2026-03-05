"""Centralized environment configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

from backend.lib.constants import ROOT_DIR
from dotenv import load_dotenv


_VALID_RUN_MODES = {"local", "test", "prod"}
_TRUTHY_VALUES = {"1", "true", "t", "yes", "y", "on"}


class Settings(BaseModel):
    run_mode: str
    persistence_enabled: bool
    database_url: str | None
    api_keys: dict[str, str | None]

    model_config = ConfigDict(frozen=True)

    @field_validator("run_mode", mode="before")
    def _validate_run_mode(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in _VALID_RUN_MODES:
            raise ValueError("RUN_MODE must be set to either 'local', 'test', or 'prod'")
        return normalized

    def require_database_url(self) -> str:
        url = (self.database_url or "").strip()
        if not url:
            raise ValueError("DATABASE_URL is required when persistence is enabled.")
        return url

    def require_api_key(self, env_var: str) -> str:
        value = (self.api_keys.get(env_var) or "").strip()
        if not value:
            raise ValueError(f"{env_var} is required but not set in the environment.")
        return value


@lru_cache(maxsize=1)
def settings() -> Settings:
    return _build_settings()

def _build_settings() -> Settings:
    _load_dotenv()

    run_mode: str = _load_run_mode()
    persistence_enabled: bool = _load_persistence_enabled(run_mode)
    database_url: str | None = _load_database_url()
    api_keys: dict[str, str | None] = _load_api_keys()

    return Settings(
        run_mode=run_mode,
        persistence_enabled=persistence_enabled,
        database_url=database_url,
        api_keys=api_keys,
    )

def _repo_env_path() -> Path:
    return ROOT_DIR / ".env"

def _load_dotenv() -> None:
    load_dotenv(_repo_env_path())

def _load_run_mode() -> str:
    run_mode = os.getenv("RUN_MODE", "test").strip().lower()
    if run_mode not in _VALID_RUN_MODES:
        raise ValueError("RUN_MODE must be set to either 'local', 'test', or 'prod'")
    return run_mode

def _load_persistence_enabled(run_mode: str) -> bool:
    persistence_default = "false" if run_mode == "test" else "true"
    persistence_enabled = _is_truthy(os.getenv("PERSISTENCE_ENABLED", persistence_default))
    return persistence_enabled

def _load_database_url() -> str | None:
    return os.getenv("DATABASE_URL")

def _load_api_keys() -> dict[str, str | None]:
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    }

def _is_truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() in _TRUTHY_VALUES)
