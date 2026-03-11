from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.optim import AdamW
from transformers import AutoModel

from .dataloader import DatasetSplit, TARGET_COLUMNS, create_dataloaders
from .evaluate import evaluate_model
from .logger import LogExperiment


@dataclass(frozen=True)
class TrainingConfig:
    dataset_csv: Path
    model_name: str
    epochs: int
    batch_size: int
    learning_rate: float
    max_length: int
    weight_decay: float = 0.0
    seed: int = 42
    eval_batch_size: int | None = None
    threshold: float = 0.5


class DebertaRewardModel(nn.Module):
    def __init__(self, model_name: str, num_labels: int = 6) -> None:
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(self.encoder.config.hidden_dropout_prob)
        self.classifier = nn.Linear(self.encoder.config.hidden_size, num_labels)
        self.loss_fn = nn.BCEWithLogitsLoss()

    def forward(
        self,
        *,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor | None]:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.last_hidden_state[:, 0]
        logits = self.classifier(self.dropout(pooled))
        loss = self.loss_fn(logits, labels) if labels is not None else None
        return {"loss": loss, "logits": logits}


def _set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def train_one_epoch(
    *,
    model: nn.Module,
    dataloader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    total_steps = 0
    for batch in dataloader:
        optimizer.zero_grad(set_to_none=True)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs["loss"]
        if loss is None:
            continue
        loss.backward()
        optimizer.step()
        total_loss += float(loss.item())
        total_steps += 1
    return total_loss / total_steps if total_steps else 0.0


def train_once(
    *,
    config: TrainingConfig,
    run_dir: Path,
    telemetry: Any | None = None,
) -> dict[str, Any]:
    _set_seed(config.seed)
    device = _get_device()

    data: DatasetSplit = create_dataloaders(
        csv_path=config.dataset_csv,
        tokenizer_name=config.model_name,
        batch_size=config.batch_size,
        max_length=config.max_length,
        seed=config.seed,
        eval_batch_size=config.eval_batch_size,
    )

    model = DebertaRewardModel(config.model_name, num_labels=len(TARGET_COLUMNS))
    model.to(device)

    optimizer = AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    logger = LogExperiment(run_dir)
    logger.write_hyperparameters(asdict(config))
    if telemetry is not None:
        telemetry.start()

    start = time.time()
    best_metrics: dict[str, Any] = {}
    best_macro_f1 = -1.0

    for epoch in range(1, config.epochs + 1):
        train_loss = train_one_epoch(
            model=model,
            dataloader=data.train_loader,
            optimizer=optimizer,
            device=device,
        )
        eval_metrics = evaluate_model(
            model=model,
            dataloader=data.eval_loader,
            device=device,
            threshold=config.threshold,
        )
        epoch_metrics = {"epoch": epoch, "train_loss": train_loss, **eval_metrics}
        logger.append_epoch_metrics(epoch_metrics)
        if telemetry is not None:
            telemetry.log_metrics(epoch_metrics, step=epoch)

        if eval_metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = float(eval_metrics["macro_f1"])
            best_metrics = eval_metrics

    runtime = time.time() - start
    logger.write_results(
        metrics=best_metrics,
        runtime_seconds=runtime,
        total_epochs=config.epochs,
    )
    if telemetry is not None:
        telemetry.finish(
            {
                "best_macro_f1": best_macro_f1,
                "total_runtime_seconds": runtime,
            }
        )

    return {
        "best_metrics": best_metrics,
        "runtime_seconds": runtime,
        "total_epochs": config.epochs,
        "run_dir": str(run_dir),
    }
