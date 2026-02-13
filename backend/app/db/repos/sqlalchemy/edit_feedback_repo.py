from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EditFeedbackEvent
from app.db.repos.interfaces import EditFeedbackRepo


class SqlAlchemyEditFeedbackRepo(EditFeedbackRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        submission_id: uuid.UUID,
        edited_text: str,
        edited_at: datetime,
        generation_id: uuid.UUID | None = None,
    ) -> None:
        row = EditFeedbackEvent(
            submission_id=submission_id,
            generation_id=generation_id,
            edited_text=edited_text,
            edited_at=edited_at,
        )
        self._session.add(row)
        await self._session.flush()

