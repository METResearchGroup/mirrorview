from __future__ import annotations

import time
from typing import Any, Protocol

import anyio

from app.db.uow import UnitOfWork
from app.db.repos.interfaces import GenerationRepo, SubmissionRepo
from app.schemas import FlipResponse, GenerateResponseRequest


class LLMClient(Protocol):
    def structured_completion(self, messages: list[dict[str, Any]], response_model: Any, model: str | None = None):
        """Synchronous LLM call returning an instance of response_model."""


class GenerationService:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        llm: LLMClient,
        submissions: SubmissionRepo,
        generations: GenerationRepo,
    ) -> None:
        self._uow = uow
        self._llm = llm
        self._submissions = submissions
        self._generations = generations

    async def generate(
        self,
        *,
        req: GenerateResponseRequest,
        messages: list[dict[str, Any]],
    ) -> FlipResponse:
        submission = req.submission

        start = time.monotonic()
        flip: FlipResponse = await anyio.to_thread.run_sync(
            lambda: self._llm.structured_completion(
                messages=messages,
                response_model=FlipResponse,
                model=None,
            )
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        async with self._uow.transaction():
            await self._submissions.upsert(submission)
            await self._generations.add(
                submission_id=submission.id,
                flip=flip,
                provider=None,
                model_name=None,
                prompt_name=None,
                prompt_version=None,
                latency_ms=latency_ms,
                usage=None,
            )

        return flip

