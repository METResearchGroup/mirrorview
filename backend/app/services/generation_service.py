from __future__ import annotations

import time
from typing import Any, Protocol

import anyio

from app.db.uow import UnitOfWork
from app.db.repos.interfaces import GenerationRepo, SubmissionRepo
from app.schemas import FlipResponse, GenerateResponseRequest
from fastapi import HTTPException
from ml_tooling.llm.config.model_registry import ModelConfigRegistry


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
        selected_model_id = submission.model_id
        model_config = ModelConfigRegistry.get_model_config(selected_model_id)
        litellm_route = model_config.get_litellm_route()

        start = time.monotonic()
        timeout_s = 30
        try:
            with anyio.fail_after(timeout_s):
                flip: FlipResponse = await anyio.to_thread.run_sync(
                    lambda: self._llm.structured_completion(
                        messages=messages,
                        response_model=FlipResponse,
                        model=selected_model_id,
                    ),
                    abandon_on_cancel=True,
                )
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail="LLM request timed out") from e
        latency_ms = int((time.monotonic() - start) * 1000)

        async with self._uow.transaction():
            await self._submissions.upsert(submission)
            await self._generations.add(
                submission_id=submission.id,
                flip=flip,
                provider=model_config.provider_name,
                model_id=selected_model_id,
                model_name=litellm_route,
                prompt_name=None,
                prompt_version=None,
                latency_ms=latency_ms,
                usage=None,
            )

        return flip

