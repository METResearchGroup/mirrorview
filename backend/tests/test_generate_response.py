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

    monkeypatch.setattr(main, "get_llm_service", lambda: _FakeLLM())

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.post("/generate_response", json={"text": "hello"})
    assert res.status_code == 200
    assert res.json()["flipped_text"] == "hello (flipped)"


def test_generate_response_accepts_submission_context_and_logs_id(monkeypatch, caplog):
    main = _reload_app_with_env(monkeypatch, cors_origins="http://localhost:3000")

    class _FakeLLM:
        def structured_completion(self, messages, response_model, model=None):
            return response_model(flipped_text="hello (flipped)", explanation="because")

    monkeypatch.setattr(main, "get_llm_service", lambda: _FakeLLM())

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

