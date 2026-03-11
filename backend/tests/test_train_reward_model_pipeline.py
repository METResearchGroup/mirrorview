from __future__ import annotations

# test uses dynamic module loading and mocks; suppress unknown/private diagnostics
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownLambdaType=false
# pyright: reportArgumentType=false
# pyright: reportMissingParameterType=false
# pyright: reportPrivateUsage=false

from pathlib import Path
import sys
from types import ModuleType
import importlib.util

import pandas as pd
import pytest

pytest.importorskip("torch")
import torch

from backend.lib.constants import ROOT_DIR
from backend.lib.load_env_vars import _load_api_keys
from backend.ml_tooling.optuna import OptunaOptimizer
from backend.ml_tooling.wandb import WandbTelemetry


def _ensure_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EXPERIMENTS_DIR = ROOT_DIR / "experiments"
TRAIN_DIR = EXPERIMENTS_DIR / "train_reward_model_2026_03_11"
_ensure_package("experiments", EXPERIMENTS_DIR)
_ensure_package("experiments.train_reward_model_2026_03_11", TRAIN_DIR)

dataloader = _load_module(
    "experiments.train_reward_model_2026_03_11.dataloader", TRAIN_DIR / "dataloader.py"
)
evaluate = _load_module(
    "experiments.train_reward_model_2026_03_11.evaluate", TRAIN_DIR / "evaluate.py"
)
logger_mod = _load_module(
    "experiments.train_reward_model_2026_03_11.logger", TRAIN_DIR / "logger.py"
)

TARGET_COLUMNS = dataloader.TARGET_COLUMNS
create_dataloaders = dataloader.create_dataloaders
evaluate_model = evaluate.evaluate_model
LogExperiment = logger_mod.LogExperiment


def _write_dummy_csv(path: Path) -> None:
    rows = []
    for i in range(10):
        row = {"mirror_text": f"mirror {i}"}
        for idx, col in enumerate(TARGET_COLUMNS):
            row[col] = 1 if i % 2 == idx % 2 else 0
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_dataloader_split_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "labels.csv"
    _write_dummy_csv(csv_path)

    class DummyTokenizer:
        def __call__(self, texts, padding, truncation, max_length, return_tensors):
            batch = len(texts)
            return {
                "input_ids": torch.zeros((batch, 4), dtype=torch.long),
                "attention_mask": torch.ones((batch, 4), dtype=torch.long),
            }

    monkeypatch.setattr(
        dataloader.AutoTokenizer,
        "from_pretrained",
        lambda _: DummyTokenizer(),
    )

    split1 = create_dataloaders(
        csv_path=csv_path,
        tokenizer_name="dummy",
        batch_size=2,
        max_length=8,
        seed=42,
    )
    split2 = create_dataloaders(
        csv_path=csv_path,
        tokenizer_name="dummy",
        batch_size=2,
        max_length=8,
        seed=42,
    )
    assert split1.train_df["mirror_text"].tolist() == split2.train_df["mirror_text"].tolist()
    assert split1.eval_df["mirror_text"].tolist() == split2.eval_df["mirror_text"].tolist()


def test_evaluate_model_reports_per_label_accuracy() -> None:
    class DummyModel(torch.nn.Module):
        def forward(self, input_ids, attention_mask, labels=None):
            logits = torch.tensor(
                [
                    [10.0, -10.0, 10.0, -10.0, 10.0, -10.0],
                    [-10.0, 10.0, -10.0, 10.0, -10.0, 10.0],
                ]
            )
            loss = torch.tensor(0.5)
            return {"loss": loss, "logits": logits}

    model = DummyModel()
    batch = {
        "input_ids": torch.zeros((2, 2), dtype=torch.long),
        "attention_mask": torch.ones((2, 2), dtype=torch.long),
        "labels": torch.tensor(
            [
                [1.0, 0.0, 1.0, 0.0, 1.0, 0.0],
                [0.0, 1.0, 0.0, 1.0, 0.0, 1.0],
            ]
        ),
    }
    metrics = evaluate_model(model=model, dataloader=[batch], device=torch.device("cpu"))
    assert "per_label_accuracy" in metrics
    assert metrics["per_label_accuracy"] == [1.0] * len(TARGET_COLUMNS)


def test_log_experiment_writes_json(tmp_path: Path) -> None:
    logger = LogExperiment(tmp_path)
    logger.write_hyperparameters({"learning_rate": 1e-5})
    logger.write_results(metrics={"macro_f1": 0.5}, runtime_seconds=1.5, total_epochs=2)
    assert (tmp_path / "hyperparameters.json").exists()
    assert (tmp_path / "run_results.json").exists()


def test_load_api_keys_includes_wandb_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WANDB_API_KEY", "test-key")
    keys = _load_api_keys()
    assert keys["WANDB_API_KEY"] == "test-key"


def test_wandb_telemetry_noop_when_disabled() -> None:
    telemetry = WandbTelemetry(project="test", enabled=False, config={})
    telemetry.start()
    telemetry.log_metrics({"macro_f1": 0.1}, step=1)
    telemetry.finish({"best_macro_f1": 0.1})


def test_optuna_optimizer_objective_plumbing(monkeypatch: pytest.MonkeyPatch) -> None:
    optuna = pytest.importorskip("optuna")

    class DummyStudy:
        def __init__(self) -> None:
            self.best_value = 0.0
            self.best_params = {}

        def optimize(self, func, n_trials):
            trial = optuna.trial.FixedTrial(
                {
                    "learning_rate": 2e-5,
                    "batch_size": 8,
                    "epochs": 3,
                    "max_length": 128,
                    "weight_decay": 0.0,
                }
            )
            self.best_value = func(trial)
            self.best_params = trial.params

    monkeypatch.setattr(optuna, "create_study", lambda direction, study_name: DummyStudy())

    optimizer = OptunaOptimizer(study_name="test")
    study = optimizer.optimize(objective=lambda cfg: float(cfg["batch_size"]), n_trials=1)
    assert study.best_value == 8.0
