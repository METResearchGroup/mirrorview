import uuid
from contextlib import asynccontextmanager

import pytest

from app.schemas import FlipResponse, GenerateResponseRequest, SubmissionContext
from app.services.generation_service import GenerationService


class TestGenerationServiceGenerate:
    """Tests for GenerationService.generate method."""

    @pytest.mark.asyncio
    async def test_persists_and_returns_flip(self, mocker):
        """Service persists submission+generation and returns FlipResponse."""
        # Arrange
        submission = SubmissionContext(
            id=uuid.uuid4(),
            created_at="2026-02-03T00:00:00.000Z",
            input_text="hello",
        )
        req = GenerateResponseRequest(text="hello", submission=submission)
        messages = [{"role": "user", "content": "hello"}]

        expected = FlipResponse(flipped_text="hello (flipped)", explanation="because")

        class _FakeLLM:
            def structured_completion(self, messages, response_model, model=None):
                return response_model(**expected.model_dump())

        submissions_repo = mocker.AsyncMock()
        generations_repo = mocker.AsyncMock()

        entered_tx = {"value": False}

        class _UoW:
            @asynccontextmanager
            async def transaction(self):
                entered_tx["value"] = True
                yield

        svc = GenerationService(
            uow=_UoW(),
            llm=_FakeLLM(),
            submissions=submissions_repo,
            generations=generations_repo,
        )

        # Act
        result = await svc.generate(req=req, messages=messages)

        # Assert
        assert result == expected
        assert entered_tx["value"] is True
        submissions_repo.upsert.assert_awaited_once()
        generations_repo.add.assert_awaited_once()

