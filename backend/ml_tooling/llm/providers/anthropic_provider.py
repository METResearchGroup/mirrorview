"""Anthropic provider implementation."""

from ml_tooling.llm.providers.provider_base import BaseLLMProvider


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