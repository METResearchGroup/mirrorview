"""OpenRouter provider implementation."""

import copy
from typing import Any

from pydantic import BaseModel

from lib.load_env_vars import EnvVarsContainer
from ml_tooling.llm.providers.base import LLMProviderProtocol


class OpenRouterProvider(LLMProviderProtocol):
    def __init__(self):
        self._initialized = False
        self._api_key: str | None = None

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

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            raise RuntimeError(
                "OpenRouterProvider has not been initialized with an API key. "
                "Call initialize() before making LiteLLM requests."
            )
        return self._api_key

    def initialize(self, api_key: str | None = None) -> None:
        if api_key is None:
            api_key = EnvVarsContainer.get_env_var("OPENROUTER_API_KEY", required=True)
        if not self._initialized:
            self._api_key = api_key
            self._initialized = True

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.supported_models

    def format_structured_output(
        self,
        response_model: type[BaseModel],
        model_config: dict[str, Any],
    ) -> dict[str, Any]:
        schema = response_model.model_json_schema()
        fixed_schema = self._fix_schema_for_provider(schema)
        return {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__.lower(),
                "strict": True,
                "schema": fixed_schema,
            },
        }

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        if not self._initialized:
            self.initialize()

        merged_kwargs = {**model_config.get("kwargs", {}), **kwargs}
        completion_kwargs = {
            "model": model_config.get("litellm_route", model),
            "messages": messages,
            **merged_kwargs,
        }
        if response_format is not None:
            completion_kwargs["response_format"] = response_format
        return completion_kwargs

    def _fix_schema_for_provider(self, schema: dict) -> dict:
        schema_copy = copy.deepcopy(schema)
        self._patch_recursive(schema_copy)
        return schema_copy

    def _patch_recursive(self, obj) -> None:
        if isinstance(obj, dict):
            if obj.get("type") == "object":
                obj["additionalProperties"] = False
            for value in obj.values():
                self._patch_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                self._patch_recursive(item)
