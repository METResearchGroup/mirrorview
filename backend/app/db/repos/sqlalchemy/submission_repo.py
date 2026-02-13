from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Submission
from app.db.repos.interfaces import SubmissionRepo
from app.schemas import SubmissionContext


class SqlAlchemySubmissionRepo(SubmissionRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, submission: SubmissionContext) -> None:
        stmt = pg_insert(Submission).values(
            id=submission.id,
            client_created_at=submission.created_at,
            input_text=submission.input_text,
            client_metadata=None,
        )

        # Keep server_received_at as the first-seen time (server_default), but allow
        # client fields to be refreshed if re-sent.
        stmt = stmt.on_conflict_do_update(
            index_elements=[Submission.id],
            set_={
                "client_created_at": stmt.excluded.client_created_at,
                "input_text": stmt.excluded.input_text,
                "client_metadata": stmt.excluded.client_metadata,
            },
        )

        await self._session.execute(stmt)

