from __future__ import annotations

import importlib
import time
import types
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import jwt
import pytest


def _reload_app(monkeypatch: pytest.MonkeyPatch, **env: str) -> types.ModuleType:
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from lib.load_env_vars import settings

    settings.cache_clear()

    import app.main as main

    importlib.reload(main)
    return main


def _install_fake_llm(
    main: types.ModuleType,
    *,
    response_builder: Callable[[Any], Any] | None = None,
) -> None:
    class _FakeLLM:
        def structured_completion(
            self,
            messages: Any,
            response_model: Any,
            model: str | None = None,
        ) -> Any:
            if response_builder is not None:
                return response_builder(response_model)
            return response_model(flipped_text="ok", explanation="ok")

    import app.di.providers as providers

    main.app.dependency_overrides[providers.get_llm_client] = _FakeLLM


def _payload(text: str) -> dict[str, Any]:
    return {
        "text": text,
        "submission": {
            "id": str(uuid4()),
            "created_at": "2026-02-03T00:00:00.000Z",
            "input_text": text,
            "model_id": "gpt-5-nano",
        },
    }


def _make_token(*, secret: str, supabase_url: str, aud: str = "authenticated") -> str:
    now = int(time.time())
    issuer = f"{supabase_url.rstrip('/')}/auth/v1"
    claims = {
        "sub": str(uuid4()),
        "role": "authenticated",
        "aud": aud,
        "iss": issuer,
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(claims, secret, algorithm="HS256")  # pyright: ignore[reportUnknownMemberType]


def test_docs_disabled_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _reload_app(
        monkeypatch,
        RUN_MODE="prod",
        AUTH_REQUIRED="false",
        CORS_ORIGINS="http://localhost:3000",
    )

    from fastapi.testclient import TestClient

    try:
        with TestClient(main.app) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/docs").status_code == 404
            assert client.get("/openapi.json").status_code == 404
    finally:
        main.app.dependency_overrides.clear()


def test_write_endpoints_require_auth_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "test_secret_32_bytes_minimum_length!"
    supabase_url = "https://example.supabase.co"
    token = _make_token(secret=secret, supabase_url=supabase_url)

    main = _reload_app(
        monkeypatch,
        RUN_MODE="local",
        AUTH_REQUIRED="true",
        SUPABASE_URL=supabase_url,
        SUPABASE_JWT_SECRET=secret,
        SUPABASE_JWT_AUDIENCE="authenticated",
        CORS_ORIGINS="http://localhost:3000",
    )
    _install_fake_llm(main)

    from fastapi.testclient import TestClient

    try:
        with TestClient(main.app) as client:
            no_auth = client.post("/generate_response", json=_payload("hello"))
            assert no_auth.status_code == 401

            ok = client.post(
                "/generate_response",
                json=_payload("hello"),
                headers={"Authorization": f"Bearer {token}"},
            )
            assert ok.status_code == 200

            thumb_no_auth = client.post(
                "/feedback/thumb",
                json={
                    "submission": _payload("hello")["submission"],
                    "vote": "up",
                    "voted_at": "2026-02-03T00:00:00.000Z",
                },
            )
            assert thumb_no_auth.status_code == 401

            thumb_ok = client.post(
                "/feedback/thumb",
                json={
                    "submission": _payload("hello")["submission"],
                    "vote": "up",
                    "voted_at": "2026-02-03T00:00:00.000Z",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert thumb_ok.status_code == 200
    finally:
        main.app.dependency_overrides.clear()
