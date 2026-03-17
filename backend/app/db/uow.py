from __future__ import annotations

from collections.abc import AsyncIterator
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork(ABC):
    @abstractmethod
    async def _transaction(self) -> AsyncIterator[None]:
        """Implementation for the transaction boundary (as an async generator)."""
        raise NotImplementedError
        yield  # pragma: no cover

    def transaction(self) -> AsyncContextManager[None]:
        """Provide a transaction boundary for a service operation."""
        return asynccontextmanager(self._transaction)()


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _transaction(self) -> AsyncIterator[None]:
        async with self._session.begin():
            yield


class NullUnitOfWork(UnitOfWork):
    async def _transaction(self) -> AsyncIterator[None]:
        yield
