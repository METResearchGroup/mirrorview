import importlib
from uuid import uuid4


def _reload_app(monkeypatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import app.main as main

    importlib.reload(main)
    return main


def _payload(text: str) -> dict:
    return {
        "text": text,
        "submission": {
            "id": str(uuid4()),
            "created_at": "2026-02-03T00:00:00.000Z",
            "input_text": text,
        },
    }


def _install_fake_llm(main):
    class _FakeLLM:
        def structured_completion(self, messages, response_model, model=None):
            return response_model(flipped_text="ok", explanation="ok")

    import app.di.providers as providers

    main.app.dependency_overrides[providers.get_llm_client] = lambda: _FakeLLM()


def test_generate_endpoint_rate_limited(monkeypatch):
    main = _reload_app(
        monkeypatch,
        CORS_ORIGINS="http://localhost:3000",
        RATE_LIMIT_GENERATE="1/minute",
    )
    _install_fake_llm(main)

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    first = client.post("/generate_response", json=_payload("hello"))
    second = client.post("/generate_response", json=_payload("hello again"))

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
    assert second.json()["error"]["request_id"]
    assert second.headers.get("Retry-After")
    main.app.dependency_overrides.clear()


def test_payload_too_large_rejected(monkeypatch):
    main = _reload_app(
        monkeypatch,
        CORS_ORIGINS="http://localhost:3000",
        MAX_REQUEST_BODY_BYTES="150",
    )
    _install_fake_llm(main)

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.post("/generate_response", json=_payload("x" * 500))

    assert res.status_code == 413
    assert res.json()["error"]["code"] == "payload_too_large"
    main.app.dependency_overrides.clear()


def test_security_headers_and_request_id_added(monkeypatch):
    main = _reload_app(monkeypatch, CORS_ORIGINS="http://localhost:3000")

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.get("/health")

    assert res.status_code == 200
    assert res.headers.get("X-Request-ID")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "no-referrer"
    assert res.headers.get("Content-Security-Policy-Report-Only")


def test_validation_errors_are_standardized(monkeypatch):
    main = _reload_app(monkeypatch, CORS_ORIGINS="http://localhost:3000")

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    res = client.post(
        "/feedback/thumb",
        json={
            "submission": {
                "id": str(uuid4()),
                "created_at": "2026-02-03T00:00:00.000Z",
                "input_text": "hello",
            },
            "vote": "maybe",
            "voted_at": "2026-02-03T00:00:00.000Z",
        },
    )

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


def test_generate_input_length_is_bounded(monkeypatch):
    main = _reload_app(monkeypatch, CORS_ORIGINS="http://localhost:3000")

    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    too_long = "x" * 4001
    res = client.post("/generate_response", json=_payload(too_long))

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


