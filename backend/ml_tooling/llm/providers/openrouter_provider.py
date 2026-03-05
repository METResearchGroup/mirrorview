"""OpenRouter provider implementation."""

from typing import Any

from pydantic import BaseModel

from ml_tooling.llm.providers.openai_structured_output import (
    format_openai_strict_json_schema,
)
from ml_tooling.llm.providers.provider_base import BaseLLMProvider

SUPPORTED_JSON_SCHEMA_ROUTES = frozenset(
    {
        "openrouter/meta-llama/llama-3.3-70b-instruct",
        "openrouter/qwen/qwen3-32b",
    }
)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider implementation with shared helpers."""

    API_KEY_ENV_VAR = "OPENROUTER_API_KEY"

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def supported_models(self) -> list[str]:
        return [
            "claude-4.5-haiku",
            "openrouter-llama-3.3-70b",
            "openrouter-qwen3-32b",
        ]

    def format_structured_output(
        self, response_model: type[BaseModel], model_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        route = model_config.get("litellm_route") or ""
        if route in SUPPORTED_JSON_SCHEMA_ROUTES:
            return format_openai_strict_json_schema(response_model)
        return None

    def supports_json_mode(self) -> bool:
        return True
