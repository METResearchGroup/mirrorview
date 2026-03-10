from __future__ import annotations

from litellm import ModelResponse
from litellm.exceptions import BadRequestError

from app.schemas import FlipResponse
from ml_tooling.llm.llm_service import LLMService


def test_openai_model_can_fall_back_when_response_format_rejected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    calls = {"n": 0}

    def _fake_completion(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # First attempt uses response_format and the provider rejects it.
            assert "response_format" in kwargs
            raise BadRequestError(
                message="response_format is not supported for this model",
                model=kwargs.get("model"),
                llm_provider="openai",
            )
        # Second attempt should omit response_format.
        assert "response_format" not in kwargs
        # And should include a JSON-only system instruction to avoid prose.
        assert isinstance(kwargs.get("messages"), list)
        assert kwargs["messages"][0]["role"] == "system"
        assert "Return ONLY valid JSON" in kwargs["messages"][0]["content"]
        content = "{\"flipped_text\":\"ok\",\"explanation\":\"ok\"}"
        return ModelResponse(choices=[{"message": {"content": content}}])

    import ml_tooling.llm.llm_service as llm_service_mod

    monkeypatch.setattr(llm_service_mod.litellm, "completion", _fake_completion)

    svc = LLMService()
    result = svc.structured_completion(
        messages=[{"role": "system", "content": "flip"}, {"role": "user", "content": "hello"}],
        response_model=FlipResponse,
        model="gpt-5-nano",
    )

    assert result.flipped_text == "ok"
    assert result.explanation == "ok"
    assert calls["n"] == 2

