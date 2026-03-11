from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer

TARGET_COLUMNS = [
    "political_us",
    "opinion_not_news",
    "complete",
    "self_contained",
    "target_topic",
    "clear_political_stance",
]


class RewardModelDataset(Dataset):
    def __init__(self, encodings: dict[str, torch.Tensor], labels: torch.Tensor) -> None:
        self.encodings = encodings
        self.labels = labels

    def __len__(self) -> int:
        return self.labels.size(0)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


@dataclass(frozen=True)
class DatasetSplit:
    train_loader: DataLoader
    eval_loader: DataLoader
    train_df: pd.DataFrame
    eval_df: pd.DataFrame


def _validate_columns(df: pd.DataFrame) -> None:
    if "mirror_text" not in df.columns:
        raise ValueError("Dataset CSV missing required column `mirror_text`.")
    missing = [c for c in TARGET_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset CSV missing required target columns: {missing}")


def _tokenize_dataframe(
    df: pd.DataFrame,
    *,
    tokenizer_name: str,
    max_length: int,
) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    encodings = tokenizer(
        df["mirror_text"].tolist(),
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    labels = torch.tensor(df[TARGET_COLUMNS].values, dtype=torch.float32)
    return encodings, labels


def create_dataloaders(
    *,
    csv_path: Path | str,
    tokenizer_name: str,
    batch_size: int,
    max_length: int,
    seed: int = 42,
    eval_batch_size: int | None = None,
    max_samples: int | None = None,
) -> DatasetSplit:
    path = Path(csv_path)
    df = pd.read_csv(path)
    _validate_columns(df)

    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    if max_samples is not None:
        df = df.head(max_samples).reset_index(drop=True)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].reset_index(drop=True)
    eval_df = df.iloc[split_idx:].reset_index(drop=True)

    train_enc, train_labels = _tokenize_dataframe(
        train_df,
        tokenizer_name=tokenizer_name,
        max_length=max_length,
    )
    eval_enc, eval_labels = _tokenize_dataframe(
        eval_df,
        tokenizer_name=tokenizer_name,
        max_length=max_length,
    )

    train_ds = RewardModelDataset(train_enc, train_labels)
    eval_ds = RewardModelDataset(eval_enc, eval_labels)

    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
    )
    eval_loader = DataLoader(
        eval_ds,
        batch_size=eval_batch_size or batch_size,
        shuffle=False,
    )

    return DatasetSplit(
        train_loader=train_loader,
        eval_loader=eval_loader,
        train_df=train_df,
        eval_df=eval_df,
    )
