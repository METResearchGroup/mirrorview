"""Shared mixins for LLM providers."""

from __future__ import annotations

import copy
from typing import Any, ClassVar

from pydantic import BaseModel

from lib.load_env_vars import settings


class ProviderStateMixin:
    """Tracks common initialization state for providers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._initialized: bool = False
        self._api_key: str | None = None


class EnvApiKeyMixin(ProviderStateMixin):
    """Handles env-var backed API keys."""

    API_KEY_ENV_VAR: ClassVar[str]

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            raise RuntimeError(
                f"{self.__class__.__name__} has not been initialized with an API key. "
                "Call initialize() before making LiteLLM requests."
            )
        return self._api_key

    def initialize(self, api_key: str | None = None) -> None:
        if api_key is None:
            api_key = settings().require_api_key(self.API_KEY_ENV_VAR)
        if not self._initialized:
            self._api_key = api_key
            self._initialized = True


class SupportsModelMixin:
    """Shared `supports_model` implementation."""

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.supported_models


class StrictJsonSchemaMixin:
    """Provides OpenAI-style strict JSON schema formatting."""

    def format_structured_output(
        self,
        response_model: type[BaseModel],
        model_config: dict[str, Any],
    ) -> dict[str, Any]:
        schema = response_model.model_json_schema()
        fixed_schema = self._strict_schema(schema)
        return {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__.lower(),
                "strict": True,
                "schema": fixed_schema,
            },
        }

    def _strict_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        schema_copy = copy.deepcopy(schema)
        self._patch_recursive(schema_copy)
        return schema_copy

    def _patch_recursive(self, obj: Any) -> None:
        if isinstance(obj, dict):
            if obj.get("type") == "object":
                obj["additionalProperties"] = False
            for value in obj.values():
                self._patch_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                self._patch_recursive(item)


class StandardCompletionKwargsMixin:
    """Shares the common completion kwargs builder."""

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not getattr(self, "_initialized", False):
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


class StrictSchemaCompletionMixin(StrictJsonSchemaMixin, StandardCompletionKwargsMixin):
    """Convenience mixin combining schema + kwargs helpers."""

