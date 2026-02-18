import importlib
import asyncio
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from docker.errors import DockerException


def _run_migrations(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    alembic_ini = backend_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    # env.py reads DATABASE_URL from env; set it for the upgrade.
    command.upgrade(cfg, "head")


async def _fetch_one(database_url: str, sql: str, params: dict | None = None):
    engine = create_async_engine(
        database_url,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            return result.fetchone()
    finally:
        await engine.dispose()


class TestPersistenceIntegration:
    """Integration tests for DB persistence using a hermetic Postgres container."""

    def test_generate_and_feedback_persist_rows(self, monkeypatch):
        """POST endpoints persist expected rows to Postgres."""
        # Arrange
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

                from lib.load_env_vars import EnvVarsContainer

                EnvVarsContainer._instance = None  # noqa: SLF001 (test-only reset)

                _run_migrations(database_url)

                import app.di.providers as providers
                import app.main as main

                importlib.reload(providers)
                importlib.reload(main)

                class _FakeLLM:
                    def structured_completion(self, messages, response_model, model=None):
                        return response_model(flipped_text="hello (flipped)", explanation="because")

                monkeypatch.setattr(providers, "get_llm_client", lambda: _FakeLLM())

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
                expected_thumbs = 1
                assert thumbs_row[0] == expected_thumbs
        except (DockerException, FileNotFoundError) as e:
            pytest.skip(f"Docker not available for integration test: {e}")

