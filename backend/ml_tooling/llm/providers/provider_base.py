"""Shared base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel

from lib.load_env_vars import settings
from ml_tooling.llm.providers.base import LLMProviderProtocol


class BaseLLMProvider(LLMProviderProtocol, ABC):
    """Provides common initialization, API key storage, and kwargs helpers."""

    API_KEY_ENV_VAR: ClassVar[str]

    def __init__(self) -> None:
        self._initialized = False
        self._api_key: str | None = None

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

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.supported_models

    def format_structured_output(
        self, response_model: type[BaseModel], model_config: dict[str, Any]
    ) -> dict[str, Any] | None:
        return None

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs: Any,
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

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        ...
