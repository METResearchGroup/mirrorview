import sys
from pathlib import Path

import pytest

# Ensure the repo root and `backend/` are on sys.path so tests can import `backend.*` and `app.*`
BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from lib.load_env_vars import settings  # noqa: E402


@pytest.fixture(autouse=True)
def _default_test_env(monkeypatch: pytest.MonkeyPatch):
    """Force hermetic defaults for tests.

    The repo-root `.env` may set RUN_MODE=local; tests must override this to avoid
    accidentally requiring external services (DB, LLMs).
    """
    monkeypatch.setenv("RUN_MODE", "test")
    monkeypatch.setenv("PERSISTENCE_ENABLED", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings.cache_clear()
    yield
    settings.cache_clear()

