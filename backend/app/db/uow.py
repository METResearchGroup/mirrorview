from __future__ import annotations

from collections.abc import AsyncIterator
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork(ABC):
    @asynccontextmanager
    @abstractmethod
    async def transaction(self) -> AsyncIterator[None]:
        """Provide a transaction boundary for a service operation."""


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        async with self._session.begin():
            yield


class NoopUnitOfWork(UnitOfWork):
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        yield

