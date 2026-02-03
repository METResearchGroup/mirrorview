from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repos.noop import (
    NoopEditFeedbackRepo,
    NoopGenerationRepo,
    NoopSubmissionRepo,
    NoopThumbFeedbackRepo,
)
from app.db.repos.sqlalchemy import (
    SqlAlchemyEditFeedbackRepo,
    SqlAlchemyGenerationRepo,
    SqlAlchemySubmissionRepo,
    SqlAlchemyThumbFeedbackRepo,
)
from app.db.session import get_sessionmaker, is_persistence_enabled
from app.db.uow import NoopUnitOfWork, SqlAlchemyUnitOfWork, UnitOfWork
from app.services.feedback_service import FeedbackService
from app.services.generation_service import GenerationService, LLMClient


def get_llm_client() -> LLMClient:
    # Lazy import so unit tests (and feedback-only usage) don't require LLM deps.
    from ml_tooling.llm.llm_service import get_llm_service as _get_llm_service

    return _get_llm_service()


async def get_maybe_session() -> AsyncIterator[AsyncSession | None]:
    if not is_persistence_enabled():
        yield None
        return

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session


def get_unit_of_work(session: AsyncSession | None = Depends(get_maybe_session)) -> UnitOfWork:
    if session is None:
        return NoopUnitOfWork()
    return SqlAlchemyUnitOfWork(session)


def get_submission_repo(session: AsyncSession | None = Depends(get_maybe_session)) -> Any:
    if session is None:
        return NoopSubmissionRepo()
    return SqlAlchemySubmissionRepo(session)


def get_generation_repo(session: AsyncSession | None = Depends(get_maybe_session)) -> Any:
    if session is None:
        return NoopGenerationRepo()
    return SqlAlchemyGenerationRepo(session)


def get_thumb_feedback_repo(session: AsyncSession | None = Depends(get_maybe_session)) -> Any:
    if session is None:
        return NoopThumbFeedbackRepo()
    return SqlAlchemyThumbFeedbackRepo(session)


def get_edit_feedback_repo(session: AsyncSession | None = Depends(get_maybe_session)) -> Any:
    if session is None:
        return NoopEditFeedbackRepo()
    return SqlAlchemyEditFeedbackRepo(session)


def get_generation_service(
    uow: UnitOfWork = Depends(get_unit_of_work),
    llm: LLMClient = Depends(get_llm_client),
    submissions=Depends(get_submission_repo),
    generations=Depends(get_generation_repo),
) -> GenerationService:
    return GenerationService(uow=uow, llm=llm, submissions=submissions, generations=generations)


def get_feedback_service(
    uow: UnitOfWork = Depends(get_unit_of_work),
    submissions=Depends(get_submission_repo),
    thumbs=Depends(get_thumb_feedback_repo),
    edits=Depends(get_edit_feedback_repo),
) -> FeedbackService:
    return FeedbackService(uow=uow, submissions=submissions, thumbs=thumbs, edits=edits)

