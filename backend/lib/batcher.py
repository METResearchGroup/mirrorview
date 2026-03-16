from collections.abc import Iterator
from typing import Generic, Protocol, TypeVar


BatchT = TypeVar("BatchT")
BatchT_co = TypeVar("BatchT_co", covariant=True)


class SupportsLenAndSlice(Protocol[BatchT_co]):
    def __len__(self) -> int: ...

    def __getitem__(self, key: slice) -> BatchT_co: ...


def generate_batches(
    *,
    data: SupportsLenAndSlice[BatchT],
    batch_size: int,
    max_batches: int | None = None,
) -> list[BatchT]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    batches: list[BatchT] = [data[i : i + batch_size] for i in range(0, len(data), batch_size)]
    if max_batches is not None:
        if max_batches <= 0:
            raise ValueError("max_batches must be > 0 when provided")
        batches = batches[:max_batches]
    return batches


class BatchLoader(Generic[BatchT], Iterator[BatchT]):
    def __init__(
        self,
        data: SupportsLenAndSlice[BatchT],
        batch_size: int,
        max_batches: int | None = None,
    ) -> None:
        self.data = data
        self.batch_size = batch_size
        self.max_batches = max_batches
        self.total_records = len(data)
        self.batches: list[BatchT] = generate_batches(
            data=self.data, batch_size=self.batch_size, max_batches=self.max_batches
        )
        self.batch_iter: Iterator[BatchT] = iter(self.batches)

    def __iter__(self) -> "BatchLoader[BatchT]":
        return self

    def __next__(self) -> BatchT:
        return next(self.batch_iter)

    def __len__(self) -> int:
        return len(self.batches)

    def __getitem__(self, index: int) -> BatchT:
        return self.batches[index]

    def __setitem__(self, index: int, value: BatchT) -> None:
        self.batches[index] = value
