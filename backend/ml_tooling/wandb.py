from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.lib.load_env_vars import settings


class WandbTelemetry:
    def __init__(self, *, project: str, enabled: bool, config: dict[str, object]) -> None:
        self.project = project
        self.enabled = enabled
        self.config = config
        self._run = None

    def start(self) -> None:
        if not self.enabled:
            return
        api_key = settings().require_api_key("WANDB_API_KEY")
        try:
            import wandb  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "wandb is not installed. Install the ml dependency group."
            ) from exc
        wandb.login(key=api_key)
        self._run = wandb.init(project=self.project, config=self.config)

    def log_metrics(self, metrics: dict[str, float | int], step: int) -> None:
        if not self.enabled or self._run is None:
            return
        self._run.log(metrics, step=step)

    def log_artifact_path(self, name: str, path: Path) -> None:
        if not self.enabled or self._run is None:
            return
        import wandb  # type: ignore[import-not-found]

        artifact = wandb.Artifact(name, type="file")
        artifact.add_file(str(path))
        self._run.log_artifact(artifact)

    def finish(self, summary: dict[str, object]) -> None:
        if not self.enabled or self._run is None:
            return
        for key, value in summary.items():
            self._run.summary[key] = value
        self._run.finish()
