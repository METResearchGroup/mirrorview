from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SingleBatchGenerationStats:
    processed: int = field(default=0)
    succeeded: int = field(default=0)
    remaining: int = field(default=0)

@dataclass(frozen=True)
class GenerationRunStats:
    total_attempted: int = field(default=0)
    succeeded: int = field(default=0)
    failed: int = field(default=0)


@dataclass(frozen=True)
class GenerationRunMetadata:
    completed_at: str
    model: str
    git_hash: str
    input_csv: str
    output_csv_dir: str
    total_attempted: int
    succeeded: int
    failed: int
