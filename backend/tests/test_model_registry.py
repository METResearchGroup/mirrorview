from ml_tooling.llm.config.model_registry import ModelConfigRegistry


def test_default_model_is_available():
    assert ModelConfigRegistry.get_default_model() == "gpt-5-nano"
    assert ModelConfigRegistry.is_model_available("gpt-5-nano")


def test_available_models_filtered_for_ui():
    available_models = ModelConfigRegistry.list_available_models()
    model_ids = {model["model_id"] for model in available_models}

    assert "gpt-5-nano" in model_ids
    assert "openai-gpt-4o-mini" in model_ids
    assert "claude-4.5-sonnet" in model_ids
    assert "claude-4.5-haiku" in model_ids
    assert "openrouter-llama-3.3-70b" in model_ids
    assert "openrouter-qwen3-32b" in model_ids
    assert "gpt-4" not in model_ids


def test_route_resolution_uses_public_model_id_mapping():
    assert ModelConfigRegistry.resolve_litellm_route("openai-gpt-4o-mini") == "gpt-4o-mini"
    assert (
        ModelConfigRegistry.resolve_litellm_route("claude-4.5-haiku")
        == "openrouter/anthropic/claude-haiku-4.5"
    )


def test_model_exists_and_availability():
    assert ModelConfigRegistry.model_exists("gpt-4")
    assert not ModelConfigRegistry.is_model_available("gpt-4")
    assert not ModelConfigRegistry.model_exists("not-a-real-model")
