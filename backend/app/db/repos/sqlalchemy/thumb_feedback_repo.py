from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ThumbFeedbackEvent
from app.db.repos.interfaces import ThumbFeedbackRepo


class SqlAlchemyThumbFeedbackRepo(ThumbFeedbackRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        submission_id: uuid.UUID,
        vote: str,
        voted_at: datetime,
        generation_id: uuid.UUID | None = None,
    ) -> None:
        row = ThumbFeedbackEvent(
            submission_id=submission_id,
            generation_id=generation_id,
            vote=vote,
            voted_at=voted_at,
        )
        self._session.add(row)
        await self._session.flush()

