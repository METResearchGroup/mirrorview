from __future__ import annotations

import uuid

from app.db.uow import UnitOfWork
from app.db.repos.interfaces import EditFeedbackRepo, SubmissionRepo, ThumbFeedbackRepo
from app.schemas import EditFeedbackRequest, ThumbFeedbackRequest


class FeedbackService:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        submissions: SubmissionRepo,
        thumbs: ThumbFeedbackRepo,
        edits: EditFeedbackRepo,
    ) -> None:
        self._uow = uow
        self._submissions = submissions
        self._thumbs = thumbs
        self._edits = edits

    async def submit_thumb(self, *, req: ThumbFeedbackRequest, generation_id: uuid.UUID | None = None) -> None:
        async with self._uow.transaction():
            await self._submissions.upsert(req.submission)
            await self._thumbs.add(
                submission_id=req.submission.id,
                generation_id=generation_id,
                vote=req.vote,
                voted_at=req.voted_at,
            )

    async def submit_edit(self, *, req: EditFeedbackRequest, generation_id: uuid.UUID | None = None) -> None:
        async with self._uow.transaction():
            await self._submissions.upsert(req.submission)
            await self._edits.add(
                submission_id=req.submission.id,
                generation_id=generation_id,
                edited_text=req.edited_text,
                edited_at=req.edited_at,
            )

