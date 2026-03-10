from __future__ import annotations

from typing import Iterable, Mapping

from .step1_filter_preferences import STEP1_COLUMNS

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
    preference_rows: Iterable[Mapping[str, str | None]],
    mirrors: Iterable[Mapping[str, str]],
) -> list[dict[str, str | None]]:
    """Join preference rows to mirror texts by post_id."""

    mirror_index: dict[str, Mapping[str, str]] = {
        mirror["post_primary_key"]: mirror for mirror in mirrors
    }
    joined: list[dict[str, str | None]] = []

    for pref in preference_rows:
        post_id = pref.get("post_id")
        if not post_id:
            raise ValueError("Each preference row must contain a `post_id`.")
        mirror = mirror_index.get(post_id)
        if mirror is None:
            raise KeyError(f"Post ID {post_id} missing from mirrored_posts.csv")

        row = dict(pref)
        row["post_primary_key"] = mirror.get("post_primary_key")
        row["sampled_stance"] = mirror.get("sampled_stance")
        row["sample_toxicity_type"] = mirror.get("sample_toxicity_type")
        for mirror_column in MIRROR_ID_TO_COLUMN.values():
            row[mirror_column] = mirror.get(mirror_column)
        joined.append(row)

    return joined
