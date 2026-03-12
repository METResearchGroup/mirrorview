from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class GenerationRunStats:
    processed: int
    succeeded: int
    remaining: int
