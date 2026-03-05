"""Regression tests for the refactored LLM provider base class."""

from __future__ import annotations

import pytest

from pydantic import BaseModel

from ml_tooling.llm.llm_service import LLMService
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


@pytest.mark.parametrize(
    "provider_class",
    [AnthropicProvider, OpenRouterProvider],
)
def test_non_openai_providers_do_not_support_structured_output(provider_class: type) -> None:
    provider = provider_class()
    provider.initialize(api_key="test")

    assert (
        provider.format_structured_output(
            response_model=_TestResponseModel,
            model_config={"kwargs": {}},
        )
        is None
    )


def test_llm_service_raises_for_unsupported_structured_output() -> None:
    service = LLMService()
    provider = AnthropicProvider()
    provider.initialize(api_key="test")

    with pytest.raises(ValueError, match="does not support structured outputs"):
        service._prepare_completion_kwargs(
            model="test-model",
            provider=provider,
            response_format=_TestResponseModel,
        )
