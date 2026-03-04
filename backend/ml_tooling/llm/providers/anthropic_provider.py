"""Anthropic provider implementation."""

from ml_tooling.llm.providers.base import LLMProviderProtocol
from ml_tooling.llm.providers.provider_mixins import (
    EnvApiKeyMixin,
    SupportsModelMixin,
    StrictSchemaCompletionMixin,
)


class AnthropicProvider(
    EnvApiKeyMixin,
    StrictSchemaCompletionMixin,
    SupportsModelMixin,
    LLMProviderProtocol,
):
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