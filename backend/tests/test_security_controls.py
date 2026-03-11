from __future__ import annotations

import importlib
from typing import Any
from uuid import uuid4

import pytest

from tests.helpers import install_fake_llm


def _reload_app(monkeypatch: pytest.MonkeyPatch, **env: str) -> Any:
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    import app.api.routers.generate as generate
    import app.api.routers as routers
    import app.main as main

    importlib.reload(generate)
    importlib.reload(routers)
    importlib.reload(main)
    return main


def _payload(text: str) -> dict[str, Any]:
    return {
        "text": text,
        "submission": {
            "id": str(uuid4()),
            "created_at": "2026-02-03T00:00:00.000Z",
            "input_text": text,
        },
    }


class TestSecurityControls:
    """Tests for security middleware: rate limiting, payload size, headers, validation."""

    def test_generate_endpoint_rate_limited(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies generate endpoint returns 429 when rate limit exceeded."""
        main = _reload_app(
            monkeypatch,
            CORS_ORIGINS="http://localhost:3000",
            RATE_LIMIT_GENERATE="1/minute",
        )
        install_fake_llm(main)

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

    def test_payload_too_large_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies requests exceeding MAX_REQUEST_BODY_BYTES return 413."""
        main = _reload_app(
            monkeypatch,
            CORS_ORIGINS="http://localhost:3000",
            MAX_REQUEST_BODY_BYTES="150",
        )
        install_fake_llm(main)

        from fastapi.testclient import TestClient

        client = TestClient(main.app)
        res = client.post("/generate_response", json=_payload("x" * 500))

        assert res.status_code == 413
        assert res.json()["error"]["code"] == "payload_too_large"
        main.app.dependency_overrides.clear()

    def test_security_headers_and_request_id_added(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies security headers and X-Request-ID are present on responses."""
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

    def test_validation_errors_are_standardized(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies validation errors return standardized error payload."""
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

    def test_generate_input_length_is_bounded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies input text length validation rejects overly long payloads."""
        main = _reload_app(monkeypatch, CORS_ORIGINS="http://localhost:3000")

        from fastapi.testclient import TestClient

        client = TestClient(main.app)
        too_long = "x" * 4001
        res = client.post("/generate_response", json=_payload(too_long))

        assert res.status_code == 422
        assert res.json()["error"]["code"] == "validation_error"
