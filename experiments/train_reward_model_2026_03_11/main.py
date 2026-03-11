from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import sys
from types import ModuleType

from .train import TrainingConfig, train_once


EXPERIMENT_DIR = Path(__file__).resolve().parent
CONSTANTS_PATH = EXPERIMENT_DIR.parents[1] / "backend" / "lib" / "constants.py"


def _load_module(name: str, path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_root_dir() -> Path:
    module = _load_module("backend.lib.constants", CONSTANTS_PATH)
    return module.ROOT_DIR


def _ensure_backend_package(root_dir: Path) -> None:
    if "backend" not in sys.modules:
        backend_pkg = ModuleType("backend")
        backend_pkg.__path__ = [str(root_dir / "backend")]
        sys.modules["backend"] = backend_pkg
    if "backend.ml_tooling" not in sys.modules:
        tooling_pkg = ModuleType("backend.ml_tooling")
        tooling_pkg.__path__ = [str(root_dir / "backend" / "ml_tooling")]
        sys.modules["backend.ml_tooling"] = tooling_pkg


ROOT_DIR = _load_root_dir()
_ensure_backend_package(ROOT_DIR)
_optuna_module = _load_module(
    "backend.ml_tooling.optuna", ROOT_DIR / "backend" / "ml_tooling" / "optuna.py"
)
_wandb_module = _load_module(
    "backend.ml_tooling.wandb", ROOT_DIR / "backend" / "ml_tooling" / "wandb.py"
)
OptunaOptimizer = _optuna_module.OptunaOptimizer
WandbTelemetry = _wandb_module.WandbTelemetry
DEFAULT_DATASET = (
    ROOT_DIR
    / "experiments"
    / "label_criteria_for_reward_model_2026_03_10"
    / "artifacts"
    / "step3_all_mirror_criteria_labels.csv"
)
RUNS_DIR = EXPERIMENT_DIR / "runs"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train reward model with six binary heads.")
    p.add_argument("--dataset-csv", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--model-name", type=str, default="microsoft/deberta-v3-base")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--learning-rate", type=float, default=2e-5)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--weight-decay", type=float, default=0.0)
    p.add_argument("--search-backend", type=str, choices=["grid", "optuna"], default="grid")
    p.add_argument("--n-trials", type=int, default=5)
    p.add_argument("--wandb", action="store_true", help="Enable Weights & Biases telemetry.")
    p.add_argument("--wandb-project", type=str, default="mirrorview-reward-model")
    p.add_argument("--smoke-test", action="store_true", help="Run with a tiny search space.")
    return p


def _run_id(prefix: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y_%m_%d-%H%M%S")
    return f"{prefix}-{timestamp}"


def _write_best_run(best: dict[str, Any]) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / "best_run.json").write_text(json.dumps(best, indent=2, sort_keys=True))


def _grid_search(args: argparse.Namespace) -> dict[str, Any]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    lr_grid = [1e-5, 2e-5, 5e-5]
    batch_grid = [8, 16]
    epoch_grid = [3, 5]
    length_grid = [128, 256]
    weight_decay_grid = [0.0, 0.01]

    if args.smoke_test:
        lr_grid = [args.learning_rate]
        batch_grid = [args.batch_size]
        epoch_grid = [1]
        length_grid = [args.max_length]
        weight_decay_grid = [args.weight_decay]

    best_run: dict[str, Any] | None = None

    for lr, bs, epochs, max_length, wd in itertools.product(
        lr_grid, batch_grid, epoch_grid, length_grid, weight_decay_grid
    ):
        config = TrainingConfig(
            dataset_csv=args.dataset_csv,
            model_name=args.model_name,
            epochs=epochs,
            batch_size=bs,
            learning_rate=lr,
            max_length=max_length,
            weight_decay=wd,
        )
        run_dir = RUNS_DIR / _run_id("grid")
        telemetry = WandbTelemetry(
            project=args.wandb_project,
            enabled=args.wandb,
            config=asdict(config),
        )
        result = train_once(config=config, run_dir=run_dir, telemetry=telemetry)
        current = {"config": asdict(config), **result}

        if best_run is None or current["best_metrics"]["macro_f1"] > best_run["best_metrics"]["macro_f1"]:
            best_run = current

    if best_run is None:
        raise ValueError("Grid search produced no runs.")
    _write_best_run(best_run)
    return best_run


def _optuna_search(args: argparse.Namespace) -> dict[str, Any]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    def objective(hparams: dict[str, Any]) -> float:
        config = TrainingConfig(
            dataset_csv=args.dataset_csv,
            model_name=args.model_name,
            epochs=hparams["epochs"],
            batch_size=hparams["batch_size"],
            learning_rate=hparams["learning_rate"],
            max_length=hparams["max_length"],
            weight_decay=hparams["weight_decay"],
        )
        run_dir = RUNS_DIR / _run_id("optuna")
        telemetry = WandbTelemetry(
            project=args.wandb_project,
            enabled=args.wandb,
            config=asdict(config),
        )
        result = train_once(config=config, run_dir=run_dir, telemetry=telemetry)
        return float(result["best_metrics"]["macro_f1"])

    optimizer = OptunaOptimizer(study_name="reward-model")
    study = optimizer.optimize(objective=objective, n_trials=args.n_trials)

    best = {
        "best_value": study.best_value,
        "best_params": study.best_params,
    }
    _write_best_run(best)
    return best


def main() -> None:
    args = _build_parser().parse_args()
    if args.search_backend == "grid":
        _grid_search(args)
    else:
        _optuna_search(args)


if __name__ == "__main__":
    main()
