"""Regression tests for the refactored LLM provider base class."""

from __future__ import annotations

from typing import Any

import pytest
from litellm import ModelResponse

from pydantic import BaseModel

from ml_tooling.llm.llm_service import LLMService
from ml_tooling.llm.providers.anthropic_provider import AnthropicProvider
from ml_tooling.llm.providers.openai_provider import OpenAIProvider
from ml_tooling.llm.providers.openrouter_provider import OpenRouterProvider


class _TestResponseModel(BaseModel):
    field: str


class TestLlmProviderRefactor:
    """Regression tests for the refactored LLM provider base class."""

    def test_openai_supports_strict_json_schema_response(self) -> None:
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
    def test_non_openai_providers_do_not_support_structured_output(
        self, provider_class: type
    ) -> None:
        provider = provider_class()
        provider.initialize(api_key="test")

        assert (
            provider.format_structured_output(
                response_model=_TestResponseModel,
                model_config={"kwargs": {}},
            )
            is None
        )

    def test_llm_service_falls_back_when_structured_output_unsupported(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifies structured_completion omits response_format for non-OpenAI providers."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test")

        captured_kwargs: dict[str, Any] = {}

        def _fake_completion(**kwargs: Any) -> ModelResponse:
            captured_kwargs.clear()
            captured_kwargs.update(kwargs)
            return ModelResponse(choices=[{"message": {"content": '{"field":"ok"}'}}])

        import ml_tooling.llm.llm_service as llm_service_mod

        monkeypatch.setattr(llm_service_mod.litellm, "completion", _fake_completion)

        service = LLMService()
        result = service.structured_completion(
            messages=[{"role": "user", "content": "test"}],
            response_model=_TestResponseModel,
            model="claude-4.5-haiku",
        )

        assert result.field == "ok"
        assert "response_format" not in captured_kwargs
