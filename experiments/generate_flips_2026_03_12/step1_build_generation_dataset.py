"""Build deduped post_id + original_text dataset from the March 10 labeling artifact."""

# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.lib.constants import ROOT_DIR

DEFAULT_INPUT_CSV = (
    ROOT_DIR
    / "experiments"
    / "label_criteria_for_reward_model_2026_03_10"
    / "artifacts"
    / "step1_unique_mirrors_to_label.csv"
)

REQUIRED_COLUMNS = ["post_id", "original_text"]


def _validate_input(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Input CSV missing expected columns: {missing}")

    # Each post_id must map to exactly one original_text
    per_post = df.groupby("post_id", dropna=False)["original_text"].nunique(dropna=False)
    bad = per_post[per_post > 1]
    if not bad.empty:
        sample = str(bad.index[0])
        raise ValueError(
            f"Input has post_id values with multiple original_text values. Example: {sample}"
        )


def build_generation_dataset(
    *,
    input_csv: Path | str = DEFAULT_INPUT_CSV,
    output_csv: Path | str,
) -> pd.DataFrame:
    """Dedupe to one row per post_id, keeping post_id and original_text."""
    input_path = Path(input_csv)
    output_path = Path(output_csv)

    df = pd.read_csv(input_path)
    _validate_input(df)

    deduped = (
        df[REQUIRED_COLUMNS]
        .drop_duplicates(subset=["post_id"], keep="first")
        .sort_values("post_id", kind="mergesort")
        .reset_index(drop=True)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    deduped.to_csv(output_path, index=False)
    print(f"Wrote {len(deduped)} rows to {output_path}")
    return deduped


if __name__ == "__main__":
    artifacts_dir = Path(__file__).resolve().parent / "artifacts"
    build_generation_dataset(output_csv=artifacts_dir / "step1_posts_to_flip.csv")
