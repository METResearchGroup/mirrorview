from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]

MIRROR_ID_TO_COLUMN = {
    "human": "human_mirror",
    "llama": "llama_mirror",
    "qwen": "qwen_mirror",
    "claude": "claude_mirror",
    "gpt4o": "gpt4o_mirror",
}

REQUIRED_JOINED_COLUMNS = [
    "post_id",
    "post_primary_key",
    "original_text",
    "sampled_stance",
    "sample_toxicity_type",
    *MIRROR_ID_TO_COLUMN.values(),
]

DEFAULT_JOINED_INPUT = (
    ROOT_DIR
    / "experiments"
    / "train_prompt_optimization_2026_03_10"
    / "artifacts"
    / "step2_joined_mirrors.csv"
)


def make_label_id(*, post_id: str, mirror_id: str) -> str:
    return f"{post_id}::{mirror_id}"


def _validate_joined_columns(joined: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_JOINED_COLUMNS if c not in joined.columns]
    if missing:
        raise ValueError(f"Joined mirrors CSV missing expected columns: {missing}")


def dedupe_to_one_row_per_post(joined: pd.DataFrame) -> pd.DataFrame:
    """Reduce joined (participant-level) rows to one stable row per post_id."""
    _validate_joined_columns(joined)

    cols_to_check = [
        "post_primary_key",
        "original_text",
        "sampled_stance",
        "sample_toxicity_type",
        *MIRROR_ID_TO_COLUMN.values(),
    ]

    nunique = joined.groupby("post_id", dropna=False)[cols_to_check].nunique(dropna=False)
    bad = nunique[(nunique > 1).any(axis=1)]
    if not bad.empty:
        sample_post_id = str(bad.index[0])
        raise ValueError(
            "Joined mirrors CSV is not stable across participants for some posts. "
            f"Example post_id with conflicting values: {sample_post_id}"
        )

    sort_cols = ["post_id"]
    if "trial_index" in joined.columns:
        sort_cols.append("trial_index")
    stable = joined.sort_values(sort_cols, kind="mergesort").drop_duplicates(
        subset=["post_id"], keep="first"
    )
    return stable.reset_index(drop=True)


def build_unique_mirrors_to_label(joined: pd.DataFrame) -> pd.DataFrame:
    stable = dedupe_to_one_row_per_post(joined)

    rows: list[dict] = []
    for mirror_id, col in MIRROR_ID_TO_COLUMN.items():
        for r in stable.itertuples(index=False):
            post_id = getattr(r, "post_id")
            mirror_text = getattr(r, col)
            rows.append(
                {
                    "label_id": make_label_id(post_id=post_id, mirror_id=mirror_id),
                    "post_id": post_id,
                    "post_primary_key": getattr(r, "post_primary_key"),
                    "mirror_id": mirror_id,
                    "mirror_text": mirror_text,
                    "original_text": getattr(r, "original_text"),
                    "sampled_stance": getattr(r, "sampled_stance"),
                    "sample_toxicity_type": getattr(r, "sample_toxicity_type"),
                }
            )

    out = pd.DataFrame(rows)

    if out["label_id"].isna().any():
        raise ValueError("Generated label_id contains nulls.")

    if out["label_id"].nunique(dropna=False) != len(out):
        dupes = out.loc[out["label_id"].duplicated(), "label_id"].head(5).tolist()
        raise ValueError(f"label_id is not unique. Example duplicates: {dupes}")

    return out.reset_index(drop=True)


def step1_build_labeling_dataset(
    *,
    joined_input_csv: Path | str = DEFAULT_JOINED_INPUT,
    output_csv: Path | str,
) -> pd.DataFrame:
    joined = pd.read_csv(Path(joined_input_csv))
    unique_mirrors = build_unique_mirrors_to_label(joined)

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    unique_mirrors.to_csv(output_path, index=False)
    print(f"Wrote {len(unique_mirrors)} rows to {output_path}")
    return unique_mirrors


if __name__ == "__main__":
    artifacts_dir = Path(__file__).resolve().parent / "artifacts"
    step1_build_labeling_dataset(
        output_csv=artifacts_dir / "step1_unique_mirrors_to_label.csv",
    )
