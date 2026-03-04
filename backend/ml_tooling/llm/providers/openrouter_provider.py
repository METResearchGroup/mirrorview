"""OpenRouter provider implementation."""

from ml_tooling.llm.providers.base import LLMProviderProtocol
from ml_tooling.llm.providers.provider_mixins import (
    EnvApiKeyMixin,
    SupportsModelMixin,
    StrictSchemaCompletionMixin,
)


class OpenRouterProvider(
    EnvApiKeyMixin,
    StrictSchemaCompletionMixin,
    SupportsModelMixin,
    LLMProviderProtocol,
):
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