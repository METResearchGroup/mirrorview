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
            model_id="gpt-5-nano",
        )
        req = GenerateResponseRequest(text="hello", submission=submission)
        messages = [{"role": "user", "content": "hello"}]

        expected = FlipResponse(flipped_text="hello (flipped)", explanation="because")

        fake_llm = mocker.Mock()
        fake_llm.structured_completion.return_value = expected

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
            llm=fake_llm,
            submissions=submissions_repo,
            generations=generations_repo,
        )

        # Act
        result = await svc.generate(req=req, messages=messages)

        # Assert
        assert result == expected
        assert entered_tx["value"] is True
        submissions_repo.upsert.assert_awaited_once()
        fake_llm.structured_completion.assert_called_once_with(
            messages=messages,
            response_model=FlipResponse,
            model="gpt-5-nano",
        )
        generations_repo.add.assert_awaited_once()
        kwargs = generations_repo.add.await_args.kwargs
        assert kwargs["submission_id"] == submission.id
        assert kwargs["provider"] == "openai"
        assert kwargs["model_id"] == "gpt-5-nano"
        assert kwargs["model_name"] == "gpt-5-nano"

