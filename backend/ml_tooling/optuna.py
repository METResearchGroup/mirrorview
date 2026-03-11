from __future__ import annotations

# optuna has incomplete typing; suppress unknown-member/parameter diagnostics
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class SearchSpace:
    learning_rate: list[float]
    batch_size: list[int]
    epochs: list[int]
    max_length: list[int]
    weight_decay: list[float]


DEFAULT_SEARCH_SPACE = SearchSpace(
    learning_rate=[1e-5, 2e-5, 5e-5],
    batch_size=[8, 16],
    epochs=[3, 5],
    max_length=[128, 256],
    weight_decay=[0.0, 0.01],
)


class OptunaOptimizer:
    def __init__(
        self,
        *,
        study_name: str,
        direction: str = "maximize",
        search_space: SearchSpace = DEFAULT_SEARCH_SPACE,
    ) -> None:
        self.study_name = study_name
        self.direction = direction
        self.search_space = search_space

    def suggest_hyperparameters(self, trial: Any) -> dict[str, Any]:
        return {
            "learning_rate": trial.suggest_float(
                "learning_rate",
                min(self.search_space.learning_rate),
                max(self.search_space.learning_rate),
                log=True,
            ),
            "batch_size": trial.suggest_categorical("batch_size", self.search_space.batch_size),
            "epochs": trial.suggest_categorical("epochs", self.search_space.epochs),
            "max_length": trial.suggest_categorical("max_length", self.search_space.max_length),
            "weight_decay": trial.suggest_categorical(
                "weight_decay", self.search_space.weight_decay
            ),
        }

    def optimize(
        self,
        *,
        objective: Callable[[dict[str, Any]], float],
        n_trials: int,
    ):
        try:
            import optuna  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "optuna is not installed. Install the ml dependency group."
            ) from exc

        def _objective(trial: optuna.Trial) -> float:
            hparams = self.suggest_hyperparameters(trial)
            return float(objective(hparams))

        study = optuna.create_study(direction=self.direction, study_name=self.study_name)
        study.optimize(_objective, n_trials=n_trials)
        return study
