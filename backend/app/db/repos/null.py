"""Null repos used when persistence is disabled via `PERSISTENCE_ENABLED=false`."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.db.repos.interfaces import EditFeedbackRepo, GenerationRepo, SubmissionRepo, ThumbFeedbackRepo
from app.schemas import FlipResponse, SubmissionContext

NULL_UUID = uuid.UUID(int=0)


class NullSubmissionRepo(SubmissionRepo):
    async def upsert(self, submission: SubmissionContext) -> None:  # noqa: ARG002
        return


class NullGenerationRepo(GenerationRepo):
    async def add(  # noqa: PLR0913
        self,
        *,
        submission_id: uuid.UUID,  # noqa: ARG002
        flip: FlipResponse,  # noqa: ARG002
        provider: str | None = None,  # noqa: ARG002
        model_id: str | None = None,  # noqa: ARG002
        model_name: str | None = None,  # noqa: ARG002
        prompt_name: str | None = None,  # noqa: ARG002
        prompt_version: str | None = None,  # noqa: ARG002
        latency_ms: int | None = None,  # noqa: ARG002
        usage: dict | None = None,  # noqa: ARG002
    ) -> uuid.UUID:
        return NULL_UUID


class NullThumbFeedbackRepo(ThumbFeedbackRepo):
    async def add(  # noqa: ARG002
        self,
        *,
        submission_id: uuid.UUID,
        vote: str,
        voted_at: datetime,
        generation_id: uuid.UUID | None = None,
    ) -> None:
        return


class NullEditFeedbackRepo(EditFeedbackRepo):
    async def add(  # noqa: ARG002
        self,
        *,
        submission_id: uuid.UUID,
        edited_text: str,
        edited_at: datetime,
        generation_id: uuid.UUID | None = None,
    ) -> None:
        return

