from __future__ import annotations

from litellm import ModelResponse

from app.schemas import FlipResponse
from ml_tooling.llm.llm_service import LLMService


def test_structured_completion_falls_back_to_json_in_text_for_openrouter(monkeypatch):
    # Ensure provider can initialize
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")

    def _fake_completion(**kwargs):
        # For non-OpenAI providers we should NOT pass response_format.
        assert "response_format" not in kwargs
        # Must use the configured route for the model.
        assert kwargs["model"] == "openrouter/anthropic/claude-haiku-4.5"
        # Return content containing extra prose + JSON to test extraction.
        content = 'Here you go:\\n{\"flipped_text\":\"hello (flipped)\",\"explanation\":\"because\"}\\nThanks!'
        return ModelResponse(choices=[{"message": {"content": content}}])

    import ml_tooling.llm.llm_service as llm_service_mod

    monkeypatch.setattr(llm_service_mod.litellm, "completion", _fake_completion)

    svc = LLMService()
    result = svc.structured_completion(
        messages=[{"role": "system", "content": "flip it"}, {"role": "user", "content": "hello"}],
        response_model=FlipResponse,
        model="claude-4.5-haiku",
    )

    assert isinstance(result, FlipResponse)
    assert result.flipped_text == "hello (flipped)"
    assert result.explanation == "because"

