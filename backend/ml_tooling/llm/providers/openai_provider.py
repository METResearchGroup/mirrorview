"""OpenAI provider implementation."""

from typing import Any

from pydantic import BaseModel

from ml_tooling.llm.providers.openai_structured_output import (
    format_openai_strict_json_schema,
)
from ml_tooling.llm.providers.provider_base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation with shared helpers."""

    API_KEY_ENV_VAR = "OPENAI_API_KEY"

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> list[str]:
        return [
            "openai-gpt-4o-mini",
            "gpt-5-nano",
            "gpt-4o-mini",
            "gpt-4o-mini-2024-07-18",
            "gpt-4",
        ]

    def format_structured_output(
        self,
        response_model: type[BaseModel],
        model_config: dict[str, Any],
    ) -> dict[str, Any]:
        return format_openai_strict_json_schema(response_model)
