from __future__ import annotations

from typing import Iterable

import numpy as np
import torch
from sklearn.metrics import f1_score

from .dataloader import TARGET_COLUMNS


def _sigmoid(x: torch.Tensor) -> torch.Tensor:
    return 1 / (1 + torch.exp(-x))


def _label_prevalence(y_true: np.ndarray) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for idx, name in enumerate(TARGET_COLUMNS):
        positives = float(y_true[:, idx].sum())
        total = float(y_true.shape[0])
        stats[name] = {
            "positives": positives,
            "total": total,
            "rate": positives / total if total else 0.0,
        }
    return stats


def evaluate_model(
    *,
    model: torch.nn.Module,
    dataloader: Iterable[dict[str, torch.Tensor]],
    device: torch.device,
    threshold: float = 0.5,
) -> dict[str, object]:
    model.eval()
    losses: list[float] = []
    all_logits: list[torch.Tensor] = []
    all_labels: list[torch.Tensor] = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            if outputs.get("loss") is not None:
                losses.append(float(outputs["loss"].item()))
            all_logits.append(outputs["logits"].detach().cpu())
            all_labels.append(labels.detach().cpu())

    if not all_logits:
        raise ValueError("Evaluation dataloader produced no batches.")

    logits = torch.cat(all_logits, dim=0)
    labels = torch.cat(all_labels, dim=0)
    probs = _sigmoid(logits).numpy()
    y_true = labels.numpy()
    y_pred = (probs >= threshold).astype(int)

    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    micro_f1 = float(f1_score(y_true, y_pred, average="micro", zero_division=0))
    per_label_f1 = f1_score(y_true, y_pred, average=None, zero_division=0).tolist()
    per_label_accuracy = (y_true == y_pred).mean(axis=0).tolist()

    return {
        "eval_loss": float(np.mean(losses)) if losses else 0.0,
        "macro_f1": macro_f1,
        "micro_f1": micro_f1,
        "per_label_f1": per_label_f1,
        "per_label_accuracy": per_label_accuracy,
        "label_prevalence": _label_prevalence(y_true),
    }
