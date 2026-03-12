"""Resumable batched flip generation using LLMService and FlipResponse."""

# pyright: reportArgumentType=false

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess

import pandas as pd

from ml_tooling.llm.llm_service import LLMService, get_llm_service

# Import production schema and prompt so experiment uses same contract
from app.schemas import FlipResponse

# prompts is in backend/ - resolve via backend in PYTHONPATH
from prompts import FLIP_PROMPT

DEFAULT_MODEL = "claude-4.5-sonnet"
DEFAULT_FLIPS_SUBDIR = "generated_flips"

INPUT_COLUMNS = ["post_id", "original_text"]

OUTPUT_COLUMNS = ["post_id", "original_text", "flipped_text", "explanation", "model"]


def _read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def timestamp_for_filename(dt: datetime) -> str:
    aware_dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if aware_dt.tzinfo is not timezone.utc:
        aware_dt = aware_dt.astimezone(timezone.utc)
    return aware_dt.strftime("%Y_%m_%d-%H:%M:%S")


def _get_git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parents[2],
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:12]
    except Exception:
        pass
    return "unknown"


def load_success_ids(path: Path) -> set[str]:
    df = _read_csv_if_exists(path)
    if df is None or df.empty:
        return set()
    if "post_id" not in df.columns:
        raise ValueError(f"Expected column `post_id` in {path}")
    return set(df["post_id"].dropna().astype(str).tolist())


def list_flip_csvs(flips_dir: Path) -> list[Path]:
    if not flips_dir.exists():
        return []
    return sorted([p for p in flips_dir.iterdir() if p.is_file() and p.suffix == ".csv"])


def load_generated_ids_from_csv(path: Path) -> set[str]:
    df = _read_csv_if_exists(path)
    if df is None or df.empty:
        return set()
    if "post_id" not in df.columns:
        raise ValueError(f"Expected column `post_id` in {path}")
    return set(df["post_id"].dropna().astype(str).tolist())


def load_generated_ids_from_dir(flips_dir: Path) -> set[str]:
    generated: set[str] = set()
    for p in list_flip_csvs(flips_dir):
        generated |= load_generated_ids_from_csv(p)
    return generated


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
            pass


def append_success_ids(path: Path, post_ids: list[str]) -> int:
    if not post_ids:
        return 0

    existing = load_success_ids(path)
    new_ids = [pid for pid in post_ids if pid not in existing]
    if not new_ids:
        return 0

    df = pd.DataFrame({"post_id": new_ids})
    _append_dataframe(path, df)
    return len(new_ids)


def sync_success_ids_from_flips_dir(*, flips_dir: Path, success_csv: Path) -> int:
    """Append any post_ids present in flips dir but missing in success CSV."""
    generated = load_generated_ids_from_dir(flips_dir)
    if not generated:
        return 0
    existing = load_success_ids(success_csv)
    missing = sorted(generated - existing)
    if not missing:
        return 0
    df = pd.DataFrame({"post_id": missing})
    _append_dataframe(success_csv, df)
    return len(missing)


def _validate_input(df: pd.DataFrame) -> None:
    missing = [c for c in INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Generation input CSV missing expected columns: {missing}")
    if df["post_id"].nunique(dropna=False) != len(df):
        raise ValueError("Input must have exactly one row per post_id.")


@dataclass(frozen=True)
class GenerationRunStats:
    processed: int
    succeeded: int
    remaining: int


def _resolve_output_path(
    *,
    flips_dir_path: Path,
    output_csv: Path | str | None,
    run_timestamp: datetime | None,
) -> Path:
    if output_csv is None:
        dt = run_timestamp or datetime.now(tz=timezone.utc)
        return flips_dir_path / f"{timestamp_for_filename(dt)}.csv"
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _compute_pending_rows(
    df: pd.DataFrame,
    success_path: Path,
    flips_dir_path: Path,
) -> pd.DataFrame:
    completed_ids = load_success_ids(success_path) | load_generated_ids_from_dir(flips_dir_path)
    return df.loc[~df["post_id"].astype(str).isin(list(completed_ids)), :].reset_index(drop=True)


def _build_batches(
    pending: pd.DataFrame,
    batch_size: int,
    max_batches: int | None,
) -> list[pd.DataFrame]:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    batches = [
        pending.iloc[i : i + batch_size, :].reset_index(drop=True)
        for i in range(0, len(pending), batch_size)
    ]
    if max_batches is not None:
        if max_batches <= 0:
            raise ValueError("max_batches must be > 0 when provided")
        batches = batches[:max_batches]
    return batches


def _build_prompt(original_text: str) -> str:
    """Build prompt with FLIP_PROMPT + user text. structured_batch_completion uses user role only, so we embed the system instructions."""
    text = (original_text or "").strip()
    return f"{FLIP_PROMPT}\n\n---\n\nPost to flip:\n{text}"


def _process_batch(
    batch_df: pd.DataFrame,
    service: LLMService,
    model: str,
    batch_idx: int = 1,
) -> tuple[pd.DataFrame, list[str]]:
    prompts = [_build_prompt(str(row["original_text"])) for _, row in batch_df.iterrows()]
    results = service.structured_batch_completion(
        prompts=prompts,
        response_model=FlipResponse,
        model=model,
    )
    if len(results) != len(batch_df):
        raise ValueError(
            f"Batch {batch_idx} returned {len(results)} results for {len(batch_df)} inputs."
        )
    rows_out = []
    post_ids = []
    for row, flip in zip(batch_df.itertuples(index=False), results, strict=True):
        post_id = str(getattr(row, "post_id"))
        post_ids.append(post_id)
        rows_out.append(
            {
                "post_id": post_id,
                "original_text": str(getattr(row, "original_text")),
                "flipped_text": flip.flipped_text,
                "explanation": flip.explanation,
                "model": model,
            }
        )
    out_df = pd.DataFrame(rows_out).loc[:, OUTPUT_COLUMNS]
    return out_df, post_ids


def _write_metadata(
    metadata_path: Path,
    *,
    completed_at: str,
    model: str,
    git_hash: str,
    input_csv: str,
    output_csv: str,
    total_attempted: int,
    succeeded: int,
    failed: int,
) -> None:
    metadata = {
        "completed_at": completed_at,
        "model": model,
        "git_hash": git_hash,
        "prompt_source": "backend/prompts.py:FLIP_PROMPT",
        "input_csv": input_csv,
        "output_csv": output_csv,
        "total_attempted": total_attempted,
        "succeeded": succeeded,
        "failed": failed,
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def generate_with_llm(
    *,
    input_csv: Path | str,
    flips_dir: Path | str,
    success_csv: Path | str,
    model: str = DEFAULT_MODEL,
    batch_size: int = 10,
    max_batches: int | None = None,
    resume: bool = True,
    llm_service: LLMService | None = None,
    output_csv: Path | str | None = None,
    run_timestamp: datetime | None = None,
) -> GenerationRunStats:
    input_path = Path(input_csv)
    flips_dir_path = Path(flips_dir)
    success_path = Path(success_csv)

    df = pd.read_csv(input_path)
    _validate_input(df)

    if resume:
        synced = sync_success_ids_from_flips_dir(
            flips_dir=flips_dir_path, success_csv=success_path
        )
        if synced:
            print(f"Synced {synced} post_id values into {success_path} from {flips_dir_path}")

    pending = _compute_pending_rows(df, success_path, flips_dir_path)
    if pending.empty:
        print("No pending rows to generate.")
        return GenerationRunStats(processed=0, succeeded=0, remaining=0)

    service = llm_service or get_llm_service()
    flips_dir_path.mkdir(parents=True, exist_ok=True)
    output_path = _resolve_output_path(
        flips_dir_path=flips_dir_path,
        output_csv=output_csv,
        run_timestamp=run_timestamp,
    )
    batches = _build_batches(pending, batch_size, max_batches)

    processed = 0
    succeeded = 0
    for batch_idx, batch_df in enumerate(batches, start=1):
        try:
            out_df, post_ids = _process_batch(batch_df, service, model, batch_idx=batch_idx)
        except Exception as e:
            print(f"Batch {batch_idx} failed; stopping cleanly. Error: {e}")
            raise

        _append_dataframe(output_path, out_df)
        newly_appended = append_success_ids(success_path, post_ids)

        processed += len(batch_df)
        succeeded += len(out_df)
        remaining = int(len(pending) - processed)
        print(
            f"Batch {batch_idx}: processed={processed} succeeded={succeeded} "
            f"remaining={max(remaining, 0)} ids_appended={newly_appended}"
        )

    remaining = int(len(pending) - processed)

    # Write metadata sidecar
    completed_dt = datetime.now(tz=timezone.utc)
    metadata_path = output_path.with_suffix(".metadata.json")
    _write_metadata(
        metadata_path,
        completed_at=completed_dt.isoformat(),
        model=model,
        git_hash=_get_git_hash(),
        input_csv=str(input_path),
        output_csv=str(output_path),
        total_attempted=processed,
        succeeded=succeeded,
        failed=0,
    )

    return GenerationRunStats(processed=processed, succeeded=succeeded, remaining=max(remaining, 0))


if __name__ == "__main__":
    artifacts_dir = Path(__file__).resolve().parent / "artifacts"
    generate_with_llm(
        input_csv=artifacts_dir / "step1_posts_to_flip.csv",
        flips_dir=artifacts_dir / DEFAULT_FLIPS_SUBDIR,
        success_csv=artifacts_dir / "successfully_generated_posts.csv",
        batch_size=10,
        max_batches=1,
        model=DEFAULT_MODEL,
        resume=True,
    )
