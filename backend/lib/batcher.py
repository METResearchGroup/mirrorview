from typing import Iterable, TypeVar


T = TypeVar('T')

def generate_batches(
    *,
    data: Iterable[T],
    batch_size: int,
    max_batches: int | None = None,
) -> Iterable[list[T]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    batches = [
        data[i : i + batch_size]
        for i in range(0, len(data), batch_size)
    ]
    if max_batches is not None:
        if max_batches <= 0:
            raise ValueError("max_batches must be > 0 when provided")
        batches = batches[:max_batches]
    return batches


class BatchLoader:
    def __init__(self, data: Iterable[T], batch_size: int, max_batches: int | None = None):
        self.data = data
        self.batch_size = batch_size
        self.max_batches = max_batches
        self.total_records = len(data)
        self.batches = generate_batches(
            data=self.data,
            batch_size=self.batch_size,
            max_batches=self.max_batches
        )
        self.batch_iter = iter(self.batches)

    def __iter__(self) -> Iterable[list[T]]:
        return next(self.batch_iter)

    def __next__(self) -> list[T]:
        return next(self.batch_iter)

    def __len__(self) -> int:
        return len(self.batches)

    def __getitem__(self, index: int) -> list[T]:
        return self.batches[index]

    def __setitem__(self, index: int, value: list[T]) -> None:
        self.batches[index] = value
