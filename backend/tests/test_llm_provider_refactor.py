"""Regression tests for the refactored LLM provider base class."""

from __future__ import annotations

import pytest

from pydantic import BaseModel

from ml_tooling.llm.llm_service import LLMService, ResponseMode
from ml_tooling.llm.providers.anthropic_provider import AnthropicProvider
from ml_tooling.llm.providers.openai_provider import OpenAIProvider
from ml_tooling.llm.providers.openrouter_provider import OpenRouterProvider


class _TestResponseModel(BaseModel):
    field: str


def test_openai_supports_strict_json_schema_response() -> None:
    provider = OpenAIProvider()
    provider.initialize(api_key="test")

    response_format = provider.format_structured_output(
        response_model=_TestResponseModel,
        model_config={"kwargs": {}},
    )

    assert response_format is not None
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"].get("additionalProperties") is False


def test_anthropic_supports_structured_output_for_sonnet_route() -> None:
    provider = AnthropicProvider()
    provider.initialize(api_key="test")

    response_format = provider.format_structured_output(
        response_model=_TestResponseModel,
        model_config={
            "kwargs": {},
            "litellm_route": "anthropic/claude-sonnet-4-5-20250929",
        },
    )

    assert response_format is not None
    assert response_format["type"] == "json_schema"


def test_openrouter_supports_structured_output_for_llama_route() -> None:
    provider = OpenRouterProvider()
    provider.initialize(api_key="test")

    response_format = provider.format_structured_output(
        response_model=_TestResponseModel,
        model_config={"kwargs": {}, "litellm_route": "openrouter/meta-llama/llama-3.3-70b-instruct"},
    )

    assert response_format is not None
    assert response_format["type"] == "json_schema"


def test_openrouter_haiku_requires_fallback() -> None:
    provider = OpenRouterProvider()
    provider.initialize(api_key="test")

    assert (
        provider.format_structured_output(
            response_model=_TestResponseModel,
            model_config={"kwargs": {}, "litellm_route": "openrouter/anthropic/claude-haiku-4.5"},
        )
        is None
    )


def test_llm_service_uses_json_object_fallback_for_unsupported_structured_output() -> None:
    service = LLMService()
    provider = OpenRouterProvider()
    provider.initialize(api_key="test")

    completion_kwargs, response_format_dict, response_mode = service._prepare_completion_kwargs(
        model="claude-4.5-haiku",
        provider=provider,
        response_format=_TestResponseModel,
    )

    assert response_format_dict == {"type": "json_object"}
    assert response_mode == ResponseMode.JSON_OBJECT
