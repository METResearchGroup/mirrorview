"""Ensure DI returns Null repos when persistence is disabled."""

from __future__ import annotations

import pytest

from app.db.repos.null import (
    NullEditFeedbackRepo,
    NullGenerationRepo,
    NullSubmissionRepo,
    NullThumbFeedbackRepo,
)
from app.db.uow import NullUnitOfWork
from lib.load_env_vars import settings


def _disable_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_MODE", "test")
    monkeypatch.setenv("PERSISTENCE_ENABLED", "false")
    settings.cache_clear()


@pytest.mark.parametrize(
    "repo_getter, expected_type",
    [
        ("get_submission_repo", NullSubmissionRepo),
        ("get_generation_repo", NullGenerationRepo),
        ("get_thumb_feedback_repo", NullThumbFeedbackRepo),
        ("get_edit_feedback_repo", NullEditFeedbackRepo),
    ],
)
def test_null_repos_returned_when_persistence_disabled(
    monkeypatch: pytest.MonkeyPatch,
    repo_getter: str,
    expected_type: type,
) -> None:
    _disable_persistence(monkeypatch)

    from app.di import providers

    getter = getattr(providers, repo_getter)
    repo = getter(session=None)  # type: ignore[call-arg]

    assert isinstance(repo, expected_type)


def test_null_unit_of_work_returned_when_persistence_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_persistence(monkeypatch)

    from app.di import providers

    uow = providers.get_unit_of_work(session=None)  # type: ignore[call-arg]

    assert isinstance(uow, NullUnitOfWork)
