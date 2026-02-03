import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from app.schemas import EditFeedbackRequest, SubmissionContext, ThumbFeedbackRequest
from app.services.feedback_service import FeedbackService


class TestFeedbackServiceSubmitThumb:
    """Tests for FeedbackService.submit_thumb method."""

    @pytest.mark.asyncio
    async def test_persists_thumb_event(self, mocker):
        """Service upserts submission and inserts a thumb feedback event."""
        # Arrange
        submission = SubmissionContext(
            id=uuid.uuid4(),
            created_at="2026-02-03T00:00:00.000Z",
            input_text="hello",
        )
        req = ThumbFeedbackRequest(
            submission=submission,
            vote="up",
            voted_at=datetime.now(timezone.utc),
        )

        submissions_repo = mocker.AsyncMock()
        thumbs_repo = mocker.AsyncMock()
        edits_repo = mocker.AsyncMock()

        class _UoW:
            @asynccontextmanager
            async def transaction(self):
                yield

        svc = FeedbackService(
            uow=_UoW(),
            submissions=submissions_repo,
            thumbs=thumbs_repo,
            edits=edits_repo,
        )

        # Act
        await svc.submit_thumb(req=req)

        # Assert
        submissions_repo.upsert.assert_awaited_once_with(submission)
        thumbs_repo.add.assert_awaited_once()


class TestFeedbackServiceSubmitEdit:
    """Tests for FeedbackService.submit_edit method."""

    @pytest.mark.asyncio
    async def test_persists_edit_event(self, mocker):
        """Service upserts submission and inserts an edit feedback event."""
        # Arrange
        submission = SubmissionContext(
            id=uuid.uuid4(),
            created_at="2026-02-03T00:00:00.000Z",
            input_text="hello",
        )
        req = EditFeedbackRequest(
            submission=submission,
            edited_text="my preferred version",
            edited_at=datetime.now(timezone.utc),
        )

        submissions_repo = mocker.AsyncMock()
        thumbs_repo = mocker.AsyncMock()
        edits_repo = mocker.AsyncMock()

        class _UoW:
            @asynccontextmanager
            async def transaction(self):
                yield

        svc = FeedbackService(
            uow=_UoW(),
            submissions=submissions_repo,
            thumbs=thumbs_repo,
            edits=edits_repo,
        )

        # Act
        await svc.submit_edit(req=req)

        # Assert
        submissions_repo.upsert.assert_awaited_once_with(submission)
        edits_repo.add.assert_awaited_once()

