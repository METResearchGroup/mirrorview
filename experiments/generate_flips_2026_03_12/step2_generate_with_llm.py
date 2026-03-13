"""Batched flip generation using LLMService and FlipResponse."""

# pyright: reportArgumentType=false

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import pandas as pd

from backend.app.schemas import FlipResponse
from backend.lib.batcher import BatchLoader
from backend.lib.constants import ROOT_DIR
from backend.lib.git_utils import get_git_hash
from backend.lib.timestamp_utils import get_current_timestamp
from backend.prompts import FLIP_PROMPT
from backend.ml_tooling.llm.llm_service import LLMService, get_llm_service

from .constants import DEFAULT_MODEL, DEFAULT_FLIPS_SUBDIR, OUTPUT_COLUMNS
from .models import GenerationRunStats, GenerationRunMetadata, SingleBatchGenerationStats
from .dataloader import load_post_batches_to_flip


def run_generate_step(
    *,
    input_csv: Path | str,
    flips_dir: Path | str,
    model: str = DEFAULT_MODEL,
    batch_size: int = 10,
    max_batches: int | None = None,
    resume: bool = True,
) -> GenerationRunStats:
    """End-to-end runner for the generation step (step2).

    Creates a timestamped output directory under flips_dir, generates flips in batches,
    and writes run metadata.
    """
    input_csv_path = Path(input_csv)
    flips_dir_path = Path(flips_dir)

    start_timestamp_str = get_current_timestamp()
    output_csv_dir = flips_dir_path / start_timestamp_str

    posts_to_flip_batches = load_post_batches_to_flip(
        input_csv_path=str(input_csv_path),
        flips_dir_path=str(flips_dir_path),
        batch_size=batch_size,
        max_batches=max_batches,
        resume=resume,
    )

    llm_service = get_llm_service(model=model)
    stats = generate_with_llm(
        posts_to_flip_batches=posts_to_flip_batches,
        output_csv_dir=str(output_csv_dir),
        llm_service=llm_service,
    )
    record_metadata(
        generation_run_stats=stats,
        model=model,
        input_csv_path=str(input_csv_path),
        output_csv_dir=str(output_csv_dir),
    )
    return stats


def generate_with_llm(
    posts_to_flip_batches: BatchLoader[pd.DataFrame],
    output_csv_dir: str,
    llm_service: LLMService,
) -> GenerationRunStats:
    """Generate flips with LLM."""

    os.makedirs(output_csv_dir, exist_ok=True)

    processed = 0
    succeeded = 0
    total_records = posts_to_flip_batches.total_records

    for batch_idx, batch_df in enumerate(posts_to_flip_batches, start=1):
        single_batch_stats = generate_single_batch_flips(
            batch_df=batch_df,
            llm_service=llm_service,
            batch_idx=batch_idx,
            output_csv_dir=output_csv_dir,
            total_records_across_all_batches=total_records,
            processed_so_far=processed,
        )
        processed += single_batch_stats.processed
        succeeded += single_batch_stats.succeeded
        remaining = total_records - processed

        print(
            f"Batch {batch_idx}: processed={processed} succeeded={succeeded} "
            f"remaining={max(remaining, 0)}"
        )

    return GenerationRunStats(
        total_attempted=processed,
        succeeded=succeeded,
        failed=0,
    )


def generate_single_batch_flips(
    batch_df: pd.DataFrame,
    llm_service: LLMService,
    batch_idx: int,
    output_csv_dir: str,
    total_records_across_all_batches: int,
    processed_so_far: int,
) -> SingleBatchGenerationStats:
    try:
        batch_results_df = _process_batch(
            batch_df=batch_df,
            llm_service=llm_service,
            batch_idx=batch_idx,
        )
        _export_batch_results(batch_results_df, output_csv_dir, batch_idx)
    except Exception as e:
        print(f"Batch {batch_idx} failed; stopping cleanly. Error: {e}")
        raise

    processed = len(batch_df)
    succeeded = len(batch_results_df)
    remaining = total_records_across_all_batches - (processed_so_far + processed)

    return SingleBatchGenerationStats(
        processed=processed,
        succeeded=succeeded,
        remaining=remaining,
    )

def _process_batch(
    batch_df: pd.DataFrame,
    llm_service: LLMService,
    batch_idx: int = 1,
) -> pd.DataFrame:
    prompts = _build_prompts_for_batch(batch_df)
    results = llm_service.structured_batch_completion(
        prompts=prompts, response_model=FlipResponse,
    )
    _validate_batch_results(results, batch_df, batch_idx)
    return _transform_batch_results_for_output(results, batch_df, llm_service=llm_service)


def _build_prompts_for_batch(
    batch_df: pd.DataFrame,
) -> list[str]:
    return [_build_prompt(str(row["original_text"])) for _, row in batch_df.iterrows()]


def _build_prompt(original_text: str) -> str:
    """Build prompt with FLIP_PROMPT + user text. structured_batch_completion uses user role only, so we embed the system instructions."""
    text = (original_text or "").strip()
    return f"{FLIP_PROMPT}\n\n---\n\nPost to flip:\n{text}"


def _validate_batch_results(
    results: list[FlipResponse],
    batch_df: pd.DataFrame,
    batch_idx: int
) -> None:
    if len(results) != len(batch_df):
        raise ValueError(
            f"Batch {batch_idx} returned {len(results)} results for {len(batch_df)} inputs."
        )

def _transform_batch_results_for_output(
    results: list[FlipResponse],
    batch_df: pd.DataFrame,
    *,
    llm_service: LLMService,
) -> pd.DataFrame:
    rows_out = []
    for row, flip in zip(batch_df.itertuples(index=False), results, strict=True):
        rows_out.append(
            {
                "post_id": str(getattr(row, "post_id")),
                "original_text": str(getattr(row, "original_text")),
                "flipped_text": flip.flipped_text,
                "explanation": flip.explanation,
                "model": llm_service._model,
            }
        )
    output_df = pd.DataFrame(rows_out).loc[:, OUTPUT_COLUMNS]
    return output_df

def _export_batch_results(
    output_df: pd.DataFrame,
    output_csv_dir: str,
    batch_idx: int,
) -> None:
    """Exports batch results to CSV."""
    os.makedirs(output_csv_dir, exist_ok=True)
    current_timestamp = get_current_timestamp()
    output_path = os.path.join(
        output_csv_dir, f"{current_timestamp}_batch_{batch_idx}.csv")
    output_df.to_csv(output_path, index=False)


def record_metadata(
    generation_run_stats: GenerationRunStats,
    model: str,
    input_csv_path: str,
    output_csv_dir: str
) -> None:
    completed_dt = datetime.now(tz=timezone.utc)
    os.makedirs(output_csv_dir, exist_ok=True)
    metadata_path = os.path.join(output_csv_dir, "metadata.json")

    metadata = GenerationRunMetadata(
        completed_at=completed_dt.isoformat(),
        model=model,
        git_hash=get_git_hash(),
        input_csv=input_csv_path,
        output_csv_dir=output_csv_dir,
        total_attempted=generation_run_stats.total_attempted,
        succeeded=generation_run_stats.succeeded,
        failed=generation_run_stats.failed,
    )
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata.__dict__, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate flips with LLM.")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of items per batch.")
    parser.add_argument("--max-batches", type=int, default=1, help="The maximum number of batches to process.")

    args = parser.parse_args()
    batch_size = args.batch_size
    max_batches = args.max_batches

    start_timestamp_str = get_current_timestamp()

    artifacts_dir = f"{ROOT_DIR}/experiments/generate_flips_2026_03_12/artifacts"
    input_csv_path = f"{artifacts_dir}/step1_posts_to_flip.csv"
    flips_dir = f"{artifacts_dir}/{DEFAULT_FLIPS_SUBDIR}"
    output_csv_dir = f"{flips_dir}/{start_timestamp_str}/"

    posts_to_flip_batches = load_post_batches_to_flip(
        input_csv_path=input_csv_path,
        flips_dir_path=flips_dir,
        batch_size=batch_size,
        max_batches=max_batches,
    )

    llm_service = get_llm_service(model=DEFAULT_MODEL)

    generation_run_stats: GenerationRunStats = generate_with_llm(
        posts_to_flip_batches=posts_to_flip_batches,
        output_csv_dir=output_csv_dir,
        llm_service=llm_service,
    )

    record_metadata(
        generation_run_stats=generation_run_stats,
        model=DEFAULT_MODEL,
        input_csv_path=input_csv_path,
        output_csv_dir=output_csv_dir,
    )
