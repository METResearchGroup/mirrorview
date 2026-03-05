import importlib
import logging
from uuid import uuid4


def _reload_app_with_env(monkeypatch, cors_origins: str | None = None):
    if cors_origins is None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGINS", cors_origins)

    # `app` is created at import time, so reload to apply env changes.
    import app.main as main

    importlib.reload(main)
    return main


def test_generate_response_returns_flipped_text(monkeypatch):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    class _FakeLLM:
        def structured_completion(self, messages, response_model, model=None):
            return response_model(flipped_text="hello (flipped)", explanation="because")

    import app.di.providers as providers

    main.app.dependency_overrides[providers.get_llm_client] = lambda: _FakeLLM()

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    submission_id = str(uuid4())
    res = client.post(
        "/generate_response",
        json={
            "text": "hello",
            "submission": {
                "id": submission_id,
                "created_at": "2026-02-03T00:00:00.000Z",
                "input_text": "hello",
            },
        },
    )
    assert res.status_code == 200
    assert res.json()["flipped_text"] == "hello (flipped)"
    main.app.dependency_overrides.clear()


def test_generate_response_accepts_submission_context_and_logs_id(monkeypatch, caplog):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    class _FakeLLM:
        def structured_completion(self, messages, response_model, model=None):
            return response_model(flipped_text="hello (flipped)", explanation="because")

    import app.di.providers as providers

    main.app.dependency_overrides[providers.get_llm_client] = lambda: _FakeLLM()

    submission_id = str(uuid4())
    payload = {
        "text": "hello",
        "submission": {
            "id": submission_id,
            "created_at": "2026-02-03T00:00:00.000Z",
            "input_text": "hello",
        },
    }

    from fastapi.testclient import TestClient

    caplog.set_level(logging.INFO)
    client = TestClient(main.app)
    res = client.post("/generate_response", json=payload)

    assert res.status_code == 200
    expected_result = "hello (flipped)"
    assert res.json()["flipped_text"] == expected_result
    assert submission_id in caplog.text
    main.app.dependency_overrides.clear()


def test_cors_allows_configured_origin(monkeypatch):
    main = _reload_app_with_env(monkeypatch, cors_origins="https://example.com")

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.options(
        "/generate_response",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "https://example.com"


def test_models_endpoint_returns_default_and_options(monkeypatch):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.get("/models")
    assert res.status_code == 200
    payload = res.json()
    assert payload["default_model_id"] == "gpt-5-nano"
    model_ids = {model["model_id"] for model in payload["models"]}
    assert "gpt-5-nano" in model_ids
    assert "openai-gpt-4o-mini" in model_ids
    assert "gpt-4" not in model_ids


def test_generate_response_rejects_unknown_model_id(monkeypatch):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    submission_id = str(uuid4())
    res = client.post(
        "/generate_response",
        json={
            "text": "hello",
            "submission": {
                "id": submission_id,
                "created_at": "2026-02-03T00:00:00.000Z",
                "input_text": "hello",
                "model_id": "does-not-exist",
            },
        },
    )
    assert res.status_code == 400
    assert "Unknown model_id" in res.json()["error"]["message"]


def test_generate_response_rejects_unavailable_model_id(monkeypatch):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    submission_id = str(uuid4())
    res = client.post(
        "/generate_response",
        json={
            "text": "hello",
            "submission": {
                "id": submission_id,
                "created_at": "2026-02-03T00:00:00.000Z",
                "input_text": "hello",
                "model_id": "gpt-4",
            },
        },
    )
    assert res.status_code == 400
    assert "Model is not available" in res.json()["error"]["message"]

