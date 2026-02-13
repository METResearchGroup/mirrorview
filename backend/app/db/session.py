from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from lib.load_env_vars import EnvVarsContainer


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def is_persistence_enabled() -> bool:
    """Return whether DB persistence is enabled via env config.

    Accepts common truthy values (case-insensitive): 1, true, t, yes, y, on.
    All other values (including empty / unset) are treated as false.
    """
    raw = str(EnvVarsContainer.get_env_var("PERSISTENCE_ENABLED") or "").strip().lower()
    return raw in {"1", "true", "t", "yes", "y", "on"}


def init_engine(database_url: str) -> None:
    """Initialize the async SQLAlchemy engine and session factory.

    Call once at app startup.
    """
    global _engine, _sessionmaker

    if _engine is not None or _sessionmaker is not None:
        return

    # If using Supabase pooler / transaction mode, prepared statements can break.
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

    _engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        connect_args=connect_args,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        raise RuntimeError("DB sessionmaker is not initialized. Did you call init_engine()?")
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an AsyncSession."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None

