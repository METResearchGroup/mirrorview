from __future__ import annotations

import importlib
import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from litellm import ModelResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from docker.errors import DockerException

from lib.load_env_vars import settings


def _run_migrations(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    alembic_ini = backend_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    # env.py reads DATABASE_URL from env; set it for the upgrade.
    command.upgrade(cfg, "head")


async def _fetch_one(
    database_url: str, sql: str, params: dict[str, Any] | None = None
) -> tuple[Any, ...] | None:
    engine = create_async_engine(
        database_url,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            row = result.fetchone()
            return None if row is None else tuple(row)
    finally:
        await engine.dispose()


def _patch_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    import ml_tooling.llm.llm_service as llm_service_mod

    def _fake_completion(**kwargs: Any) -> ModelResponse:
        content = json.dumps({"flipped_text": "hello (flipped)", "explanation": "because"})
        return ModelResponse(choices=[{"message": {"content": content}}])

    monkeypatch.setattr(llm_service_mod.litellm, "completion", _fake_completion)


class TestPersistenceIntegration:
    """Integration tests for DB persistence using a hermetic Postgres container."""

    def test_generate_and_feedback_persist_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """POST endpoints persist expected rows to Postgres."""
        # Arrange
        _patch_litellm(monkeypatch)
        try:
            with PostgresContainer("postgres:16-alpine") as pg:
                sync_url = pg.get_connection_url()
                database_url = (
                    sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
                    .replace("postgresql://", "postgresql+asyncpg://")
                    .replace("postgres://", "postgresql+asyncpg://")
                )

                monkeypatch.setenv("RUN_MODE", "test")
                monkeypatch.setenv("PERSISTENCE_ENABLED", "true")
                monkeypatch.setenv("DATABASE_URL", database_url)

                settings.cache_clear()

                _run_migrations(database_url)

                import app.di.providers as providers
                import app.main as main

                importlib.reload(providers)
                importlib.reload(main)

                class _FakeLLM:
                    def structured_completion(
                        self,
                        messages: list[dict[str, Any]],
                        response_model: type[BaseModel],
                        model: str | None = None,  # noqa: ARG002
                        **kwargs: Any,  # noqa: ARG002
                    ) -> BaseModel:
                        return response_model(flipped_text="hello (flipped)", explanation="because")

                main.app.dependency_overrides[providers.get_llm_client] = lambda: _FakeLLM()

                submission_id = str(uuid.uuid4())
                payload = {
                    "text": "hello",
                    "submission": {
                        "id": submission_id,
                        "created_at": "2026-02-03T00:00:00.000Z",
                        "input_text": "hello",
                        "model_id": "gpt-5-nano",
                    },
                }

                # Act
                with TestClient(main.app) as client:
                    res = client.post("/generate_response", json=payload)
                    assert res.status_code == 200

                    res2 = client.post(
                        "/feedback/thumb",
                        json={
                            "submission": payload["submission"],
                            "vote": "up",
                            "voted_at": "2026-02-03T00:00:01.000Z",
                        },
                    )
                    assert res2.status_code == 200

                # Assert
                submissions_row = asyncio.run(
                    _fetch_one(
                        database_url,
                        "select count(*), max(selected_model_id) from submissions where id = :id",
                        {"id": submission_id},
                    )
                )
                assert submissions_row is not None
                expected_submissions = 1
                assert submissions_row[0] == expected_submissions
                assert submissions_row[1] == "gpt-5-nano"

                generations_row = asyncio.run(
                    _fetch_one(
                        database_url,
                        "select count(*), max(model_id), max(model_name) from generations where submission_id = :id",
                        {"id": submission_id},
                    )
                )
                assert generations_row is not None
                expected_generations = 1
                assert generations_row[0] == expected_generations
                assert generations_row[1] == "gpt-5-nano"
                assert generations_row[2] == "gpt-5-nano"

                thumbs_row = asyncio.run(
                    _fetch_one(
                        database_url,
                        "select count(*) from thumb_feedback_events where submission_id = :id",
                        {"id": submission_id},
                    )
                )
                assert thumbs_row is not None
                expected_thumbs = 1
                assert thumbs_row[0] == expected_thumbs
                main.app.dependency_overrides.clear()
        except (DockerException, FileNotFoundError) as e:
            pytest.skip(f"Docker not available for integration test: {e}")

    def test_generate_persists_rows_without_manual_migrations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """App startup applies migrations so a fresh DB can serve requests."""
        _patch_litellm(monkeypatch)
        try:
            with PostgresContainer("postgres:16-alpine") as pg:
                sync_url = pg.get_connection_url()
                database_url = (
                    sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
                    .replace("postgresql://", "postgresql+asyncpg://")
                    .replace("postgres://", "postgresql+asyncpg://")
                )

                monkeypatch.setenv("RUN_MODE", "test")
                monkeypatch.setenv("PERSISTENCE_ENABLED", "true")
                monkeypatch.setenv("DATABASE_URL", database_url)

                settings.cache_clear()

                import app.di.providers as providers
                import app.main as main

                importlib.reload(providers)
                importlib.reload(main)

                class _FakeLLM:
                    def structured_completion(
                        self,
                        messages: list[dict[str, Any]],
                        response_model: type[BaseModel],
                        model: str | None = None,  # noqa: ARG002
                        **kwargs: Any,  # noqa: ARG002
                    ) -> BaseModel:
                        return response_model(flipped_text="hello (flipped)", explanation="because")

                main.app.dependency_overrides[providers.get_llm_client] = lambda: _FakeLLM()

                submission_id = str(uuid.uuid4())
                payload = {
                    "text": "hello",
                    "submission": {
                        "id": submission_id,
                        "created_at": "2026-02-03T00:00:00.000Z",
                        "input_text": "hello",
                        "model_id": "gpt-5-nano",
                    },
                }

                with TestClient(main.app) as client:
                    res = client.post("/generate_response", json=payload)
                    assert res.status_code == 200

                submissions_row = asyncio.run(
                    _fetch_one(
                        database_url,
                        "select count(*), max(selected_model_id) from submissions where id = :id",
                        {"id": submission_id},
                    )
                )
                assert submissions_row is not None
                assert submissions_row[0] == 1
                assert submissions_row[1] == "gpt-5-nano"

                main.app.dependency_overrides.clear()
        except (DockerException, FileNotFoundError) as e:
            pytest.skip(f"Docker not available for integration test: {e}")
