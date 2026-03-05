import sys
from pathlib import Path

# Ensure `backend/` is on sys.path so tests can import `app.*`
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from lib.load_env_vars import settings


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

