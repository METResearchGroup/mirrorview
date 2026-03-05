from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas import ExampleResponse

_CATALOG_PATH = Path(__file__).parent / "catalog.json"


@lru_cache(maxsize=1)
def load_examples() -> tuple[ExampleResponse, ...]:
    if not _CATALOG_PATH.exists():
        raise FileNotFoundError(f"Examples catalog missing at {_CATALOG_PATH}")

    with _CATALOG_PATH.open("r", encoding="utf-8") as cursor:
        raw = json.load(cursor)

    examples: list[ExampleResponse] = []
    for entry in raw:
        examples.append(ExampleResponse(**entry))
    return tuple(examples)
