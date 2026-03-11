from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LogExperiment:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def write_hyperparameters(self, config: dict[str, Any]) -> Path:
        path = self.run_dir / "hyperparameters.json"
        path.write_text(json.dumps(config, indent=2, sort_keys=True, default=str))
        return path

    def write_results(
        self,
        *,
        metrics: dict[str, Any],
        runtime_seconds: float,
        total_epochs: int,
    ) -> Path:
        payload = {
            "final_metrics": metrics,
            "total_epochs": total_epochs,
            "total_runtime_seconds": runtime_seconds,
        }
        path = self.run_dir / "run_results.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return path

    def append_epoch_metrics(self, metrics: dict[str, Any]) -> Path:
        path = self.run_dir / "metrics.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(metrics))
            f.write("\n")
        return path
