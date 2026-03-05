"""Anthropic provider implementation."""

from typing import Any

from pydantic import BaseModel

from ml_tooling.llm.providers.openai_structured_output import (
    format_openai_strict_json_schema,
)
from ml_tooling.llm.providers.provider_base import BaseLLMProvider

SUPPORTED_STRUCTURED_ROUTES = frozenset(
    {
        "anthropic/claude-sonnet-4-5-20250929",
        "anthropic/claude-opus-4-1-20250805",
        "anthropic/claude-opus-4-5-20251101",
    }
)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider implementation with shared helpers."""

    API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def supported_models(self) -> list[str]:
        return [
            "claude-4.5-sonnet",
        ]

    def format_structured_output(
        self, response_model: type[BaseModel], model_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        route = model_config.get("litellm_route") or ""
        if route in SUPPORTED_STRUCTURED_ROUTES:
            return format_openai_strict_json_schema(response_model)
        return None

    def supports_json_mode(self) -> bool:
        return True

