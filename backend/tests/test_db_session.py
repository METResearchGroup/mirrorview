import pytest

from app.db.session import is_persistence_enabled


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, False),
        ("", False),
        ("0", False),
        ("false", False),
        ("FALSE", False),
        ("no", False),
        ("off", False),
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("t", True),
    ],
)
def test_is_persistence_enabled_parses_truthy_values(monkeypatch: pytest.MonkeyPatch, raw, expected):
    monkeypatch.setenv("RUN_MODE", "test")

    if raw is None:
        monkeypatch.delenv("PERSISTENCE_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PERSISTENCE_ENABLED", raw)

    # Reset EnvVarsContainer singleton so env overrides are respected.
    from lib.load_env_vars import EnvVarsContainer

    EnvVarsContainer._instance = None  # noqa: SLF001 (test-only reset)
    assert is_persistence_enabled() is expected

