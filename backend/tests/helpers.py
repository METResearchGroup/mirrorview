"""Shared test helpers for LLM mocking and dependency overrides."""

from typing import Any


def create_fake_llm(
    flipped_text: str = "ok",
    explanation: str = "ok",
) -> type:
    """Return a fake LLM class parameterized by flipped_text and explanation."""

    class _FakeLLM:
        def structured_completion(
            self,
            messages: Any,
            response_model: type,
            model: str | None = None,
        ) -> Any:
            return response_model(flipped_text=flipped_text, explanation=explanation)

    return _FakeLLM


def override_llm_dependency(app: Any, fake_llm_cls: type) -> None:
    """Walk FastAPI dependants and override get_llm_client with fake_llm_cls."""

    def _walk(dependant: Any) -> None:
        for dep in dependant.dependencies:
            if getattr(dep.call, "__name__", "") == "get_llm_client":
                app.dependency_overrides[dep.call] = lambda: fake_llm_cls()
            _walk(dep)

    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is not None:
            _walk(dependant)


def install_fake_llm(
    main: Any,
    flipped_text: str = "ok",
    explanation: str = "ok",
) -> None:
    """Install a fake LLM into main.app and override all get_llm_client dependencies."""
    import app.di.providers as providers

    fake_llm_cls = create_fake_llm(flipped_text=flipped_text, explanation=explanation)
    main.app.dependency_overrides[providers.get_llm_client] = lambda: fake_llm_cls()
    override_llm_dependency(main.app, fake_llm_cls)
