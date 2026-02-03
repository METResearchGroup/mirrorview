from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.schemas import FlipResponse, SubmissionContext


class SubmissionRepo(Protocol):
    async def upsert(self, submission: SubmissionContext) -> None:
        """Insert or update a submission row (idempotent by submission.id)."""


class GenerationRepo(Protocol):
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
        """Insert a generation row and return its ID."""


class ThumbFeedbackRepo(Protocol):
    async def add(
        self,
        *,
        submission_id: uuid.UUID,
        vote: str,
        voted_at: datetime,
        generation_id: uuid.UUID | None = None,
    ) -> None:
        """Insert a thumb feedback event row."""


class EditFeedbackRepo(Protocol):
    async def add(
        self,
        *,
        submission_id: uuid.UUID,
        edited_text: str,
        edited_at: datetime,
        generation_id: uuid.UUID | None = None,
    ) -> None:
        """Insert an edit feedback event row."""

