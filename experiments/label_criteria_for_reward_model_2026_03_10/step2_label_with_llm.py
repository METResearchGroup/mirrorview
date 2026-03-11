from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ml_tooling.llm.llm_service import LLMService, get_llm_service

from .prompts import build_stage1_criteria_prompt
from .schemas import Stage1CriteriaLabel


DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_LABELS_SUBDIR = "llm_labels"

INPUT_COLUMNS = [
    "label_id",
    "post_id",
    "post_primary_key",
    "mirror_id",
    "mirror_text",
    "original_text",
    "sampled_stance",
    "sample_toxicity_type",
]

LABEL_COLUMNS = [
    "label_id",
    "model",
    "political_us",
    "opinion_not_news",
    "complete",
    "self_contained",
    "target_topic",
    "clear_political_stance",
]


def _read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def timestamp_for_filename(dt: datetime) -> str:
    aware_dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if aware_dt.tzinfo is not timezone.utc:
        aware_dt = aware_dt.astimezone(timezone.utc)
    return aware_dt.strftime("%Y_%m_%d-%H:%M:%S")


def list_label_csvs(labels_dir: Path) -> list[Path]:
    if not labels_dir.exists():
        return []
    return sorted([p for p in labels_dir.iterdir() if p.is_file() and p.suffix == ".csv"])


def load_label_ids(path: Path) -> set[str]:
    df = _read_csv_if_exists(path)
    if df is None or df.empty:
        return set()
    if "label_id" not in df.columns:
        raise ValueError(f"Expected column `label_id` in {path}")
    return set(df["label_id"].dropna().astype(str).tolist())


def load_success_ids(path: Path) -> set[str]:
    return load_label_ids(path)


def load_labeled_ids_from_labels_csv(path: Path) -> set[str]:
    return load_label_ids(path)


def load_labeled_ids_from_labels_dir(labels_dir: Path) -> set[str]:
    labeled: set[str] = set()
    for p in list_label_csvs(labels_dir):
        labeled |= load_labeled_ids_from_labels_csv(p)
    return labeled


def _append_dataframe(path: Path, df: pd.DataFrame) -> None:
    if df.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        df.to_csv(f, index=False, header=write_header)
        f.flush()
        try:
            import os

            os.fsync(f.fileno())
        except Exception:
            # Best-effort: fsync may not be available on all file-like objects.
            pass


def append_success_ids(path: Path, label_ids: list[str]) -> int:
    if not label_ids:
        return 0

    existing = load_success_ids(path)
    new_ids = [lid for lid in label_ids if lid not in existing]
    if not new_ids:
        return 0

    df = pd.DataFrame({"label_id": new_ids})
    _append_dataframe(path, df)
    return len(new_ids)


def sync_success_ids_from_labels_dir(*, labels_dir: Path, success_csv: Path) -> int:
    """Append any label_ids present in labels dir but missing in success CSV."""
    labeled = load_labeled_ids_from_labels_dir(labels_dir)
    if not labeled:
        return 0
    existing = load_success_ids(success_csv)
    missing = sorted(labeled - existing)
    if not missing:
        return 0
    df = pd.DataFrame({"label_id": missing})
    _append_dataframe(success_csv, df)
    return len(missing)


def _validate_input(df: pd.DataFrame) -> None:
    missing = [c for c in INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Labeling input CSV missing expected columns: {missing}")
    if df["label_id"].nunique(dropna=False) != len(df):
        raise ValueError("Input labeling dataset must have exactly one row per label_id.")


@dataclass(frozen=True)
class LabelingRunStats:
    processed: int
    succeeded: int
    remaining: int


def label_with_llm(
    *,
    input_csv: Path | str,
    labels_dir: Path | str,
    success_csv: Path | str,
    model: str = DEFAULT_MODEL,
    batch_size: int = 10,
    max_batches: int | None = None,
    resume: bool = True,
    llm_service: LLMService | None = None,
    output_csv: Path | str | None = None,
    run_timestamp: datetime | None = None,
) -> LabelingRunStats:
    input_path = Path(input_csv)
    labels_dir_path = Path(labels_dir)
    success_path = Path(success_csv)

    df = pd.read_csv(input_path)
    _validate_input(df)

    if resume:
        synced = sync_success_ids_from_labels_dir(
            labels_dir=labels_dir_path, success_csv=success_path
        )
        if synced:
            print(f"Synced {synced} label_id values into {success_path} from {labels_dir_path}")

    completed_ids = load_success_ids(success_path) | load_labeled_ids_from_labels_dir(
        labels_dir_path
    )
    pending = df.loc[~df["label_id"].astype(str).isin(completed_ids), :].reset_index(drop=True)

    if pending.empty:
        print("No pending rows to label.")
        return LabelingRunStats(processed=0, succeeded=0, remaining=0)

    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")

    service = llm_service or get_llm_service()

    labels_dir_path.mkdir(parents=True, exist_ok=True)
    if output_csv is None:
        dt = run_timestamp or datetime.now(tz=timezone.utc)
        output_path = labels_dir_path / f"{timestamp_for_filename(dt)}.csv"
    else:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    succeeded = 0

    batches = [
        pending.iloc[i : i + batch_size, :].reset_index(drop=True)
        for i in range(0, len(pending), batch_size)
    ]
    if max_batches is not None:
        if max_batches <= 0:
            raise ValueError("max_batches must be > 0 when provided")
        batches = batches[:max_batches]

    for batch_idx, batch_df in enumerate(batches, start=1):
        prompts = [
            build_stage1_criteria_prompt(
                original_text=str(row["original_text"]),
                mirror_text=str(row["mirror_text"]),
            )
            for _, row in batch_df.iterrows()
        ]

        try:
            results = service.structured_batch_completion(
                prompts=prompts,
                response_model=Stage1CriteriaLabel,
                model=model,
            )
        except Exception as e:
            print(f"Batch {batch_idx} failed; stopping cleanly. Error: {e}")
            raise

        if len(results) != len(batch_df):
            raise ValueError(
                f"Batch {batch_idx} returned {len(results)} results for {len(batch_df)} inputs."
            )

        label_rows = []
        label_ids = []
        for row, label in zip(batch_df.itertuples(index=False), results, strict=True):
            label_id = str(getattr(row, "label_id"))
            label_ids.append(label_id)
            label_rows.append(
                {
                    "label_id": label_id,
                    "model": model,
                    "political_us": int(label.political_us),
                    "opinion_not_news": int(label.opinion_not_news),
                    "complete": int(label.complete),
                    "self_contained": int(label.self_contained),
                    "target_topic": int(label.target_topic),
                    "clear_political_stance": int(label.clear_political_stance),
                }
            )

        labels_out = pd.DataFrame(label_rows).loc[:, LABEL_COLUMNS]

        # Write labels durably first.
        _append_dataframe(output_path, labels_out)
        newly_appended = append_success_ids(success_path, label_ids)

        processed += len(batch_df)
        succeeded += len(labels_out)

        remaining = int(len(pending) - processed)
        print(
            f"Batch {batch_idx}: processed={processed} succeeded={succeeded} "
            f"remaining={max(remaining, 0)} ids_appended={newly_appended}"
        )

    remaining = int(len(pending) - processed)
    return LabelingRunStats(processed=processed, succeeded=succeeded, remaining=max(remaining, 0))


if __name__ == "__main__":
    artifacts_dir = Path(__file__).resolve().parent / "artifacts"
    label_with_llm(
        input_csv=artifacts_dir / "step1_unique_mirrors_to_label.csv",
        labels_dir=artifacts_dir / DEFAULT_LABELS_SUBDIR,
        success_csv=artifacts_dir / "successfully_labeled_flips.csv",
        batch_size=10,
        max_batches=1,
        model=DEFAULT_MODEL,
        resume=True,
    )

