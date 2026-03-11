from __future__ import annotations

import pandas as pd

from step1_filter_preferences import STEP1_COLUMNS

MIRROR_ID_TO_COLUMN = {
    "human": "human_mirror",
    "llama": "llama_mirror",
    "qwen": "qwen_mirror",
    "claude": "claude_mirror",
    "gpt4o": "gpt4o_mirror",
}

JOIN_COLUMNS = ["post_primary_key", "sampled_stance", "sample_toxicity_type"]

STEP2_COLUMNS = [*STEP1_COLUMNS, *JOIN_COLUMNS, *MIRROR_ID_TO_COLUMN.values()]


def join_preferences_with_mirrors(
    preferences: pd.DataFrame,
    mirrors: pd.DataFrame,
) -> pd.DataFrame:
    """Join preference rows to mirror texts by post_id."""

    if "post_id" not in preferences.columns:
        raise ValueError("Preferences data missing required column `post_id`.")
    if "post_primary_key" not in mirrors.columns:
        raise ValueError("Mirrors data missing required column `post_primary_key`.")

    expected_mirror_cols = list(MIRROR_ID_TO_COLUMN.values())
    missing_mirrors_cols = [
        c for c in [*JOIN_COLUMNS, *expected_mirror_cols] if c not in mirrors.columns
    ]
    if missing_mirrors_cols:
        raise ValueError(f"Mirrors CSV missing expected columns: {missing_mirrors_cols}")

    merged = preferences.merge(
        mirrors.loc[:, [*JOIN_COLUMNS, *expected_mirror_cols]],
        how="left",
        left_on="post_id",
        right_on="post_primary_key",
        validate="many_to_one",
    )

    missing_posts = merged.loc[merged["post_primary_key"].isna(), "post_id"].dropna().unique()
    if len(missing_posts) > 0:
        sample = ", ".join(map(str, missing_posts[:5]))
        raise KeyError(
            f"{len(missing_posts)} post_id values missing from mirrored_posts.csv (e.g. {sample})"
        )

    missing_after = [col for col in STEP2_COLUMNS if col not in merged.columns]
    if missing_after:
        raise ValueError(f"Joined dataset missing expected columns: {missing_after}")

    return merged.loc[:, STEP2_COLUMNS].reset_index(drop=True)
