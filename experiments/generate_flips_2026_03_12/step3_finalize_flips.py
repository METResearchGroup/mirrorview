"""Finalize generated flips into a single CSV with post_id, original_text, flipped_text, timestamp."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FINAL_COLUMNS = ["post_id", "original_text", "flipped_text", "timestamp"]


def _list_flip_csvs(flips_dir: Path) -> list[Path]:
    if not flips_dir.exists():
        return []
    return sorted([p for p in flips_dir.rglob("*.csv") if p.is_file()])


def _extract_timestamp_from_path(*, csv_path: Path, flips_dir: Path) -> str:
    """Extract a run timestamp for a generated flip CSV.

    - If CSVs are stored under a run folder like flips_dir/<run_timestamp>/*.csv,
      use the run folder name.
    - Otherwise, fall back to the filename stem (stripping any `_batch_<n>` suffix).
    """
    try:
        rel = csv_path.relative_to(flips_dir)
    except Exception:
        rel = csv_path

    if len(rel.parts) >= 2:
        return rel.parts[0]

    stem = csv_path.stem
    if "_batch_" in stem:
        return stem.split("_batch_", 1)[0]
    return stem


def _read_flip_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if (
        "post_id" not in df.columns
        or "original_text" not in df.columns
        or "flipped_text" not in df.columns
    ):
        raise ValueError(
            f"Flip CSV missing required columns (post_id, original_text, flipped_text): {path}"
        )
    return df


def finalize_flips(
    *,
    flips_dir: Path | str,
    output_csv: Path | str,
) -> pd.DataFrame:
    """Load all generated flip CSVs, add run timestamp, dedupe by post_id, write finalized output."""
    flips_dir_path = Path(flips_dir)
    output_path = Path(output_csv)

    csv_paths = _list_flip_csvs(flips_dir_path)
    if not csv_paths:
        raise ValueError(f"No flip CSVs found under {flips_dir_path}")

    parts: list[pd.DataFrame] = []
    for p in csv_paths:
        timestamp = _extract_timestamp_from_path(csv_path=p, flips_dir=flips_dir_path)
        df = _read_flip_csv(p)
        df["timestamp"] = timestamp
        parts.append(df)

    combined = pd.concat(parts, ignore_index=True)

    # Dedupe by post_id (keep first occurrence)
    finalized = (
        combined.drop_duplicates(subset=["post_id"], keep="first")
        .loc[:, FINAL_COLUMNS]
        .sort_values("post_id", kind="mergesort")
        .reset_index(drop=True)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    finalized.to_csv(output_path, index=False)
    print(f"Wrote {len(finalized)} rows to {output_path}")
    return finalized


if __name__ == "__main__":
    artifacts_dir = Path(__file__).resolve().parent / "artifacts"
    finalize_flips(
        flips_dir=artifacts_dir / "generated_flips",
        output_csv=artifacts_dir / "step3_finalized_flips.csv",
    )
