from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork(Protocol):
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Provide a transaction boundary for a service operation."""


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        async with self._session.begin():
            yield


class NoopUnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        yield

