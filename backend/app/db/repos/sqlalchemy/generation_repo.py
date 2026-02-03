from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Generation
from app.schemas import FlipResponse


class SqlAlchemyGenerationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        submission_id: uuid.UUID,
        flip: FlipResponse,
        provider: str | None = None,
        model_name: str | None = None,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
        latency_ms: int | None = None,
        usage: dict | None = None,
    ) -> uuid.UUID:
        row = Generation(
            submission_id=submission_id,
            flipped_text=flip.flipped_text,
            explanation=flip.explanation,
            provider=provider,
            model_name=model_name,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            latency_ms=latency_ms,
            usage=usage,
        )
        self._session.add(row)
        await self._session.flush()
        return row.id

