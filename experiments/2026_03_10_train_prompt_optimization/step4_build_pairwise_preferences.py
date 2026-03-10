from __future__ import annotations

from typing import Iterable, Mapping

from .step2_join_mirrors import MIRROR_ID_TO_COLUMN

STEP4_COLUMNS = [
    "post_id",
    "post_primary_key",
    "original_text",
    "winner_mirror_id",
    "winner_text",
    "loser_mirror_id",
    "loser_text",
    "selected_mirror",
    "selected_mirror_text",
    "participant_id",
    "prolific_id",
    "trial_index",
    "post_number",
    "presentation_order",
    "selected_position",
    "response_time_ms",
    "selection_time_ms",
    "sampled_stance",
    "sample_toxicity_type",
]


def build_pairwise_preferences(
    selected_rows: Iterable[Mapping[str, str | None]],
) -> list[dict[str, str | None]]:
    """Turn selected mirror rows into pairwise preference examples."""

    pairwise: list[dict[str, str | None]] = []

    for row in selected_rows:
        winner_id = row.get("selected_mirror")
        winner_text = row.get("selected_mirror_text")
        if winner_id not in MIRROR_ID_TO_COLUMN:
            raise ValueError(f"Unsupported mirror id '{winner_id}'.")
        if winner_text is None:
            raise ValueError(
                f"Selected mirror text missing for mirror {winner_id} / post {row.get('post_id')}."
            )

        for mirror_id, column in MIRROR_ID_TO_COLUMN.items():
            if mirror_id == winner_id:
                continue
            loser_text = row.get(column)
            if loser_text is None:
                raise ValueError(
                    f"Mirror column {column} missing text for post {row.get('post_id')}."
                )

            pair = {
                "post_id": row.get("post_id"),
                "post_primary_key": row.get("post_primary_key"),
                "original_text": row.get("original_text"),
                "winner_mirror_id": winner_id,
                "winner_text": winner_text,
                "loser_mirror_id": mirror_id,
                "loser_text": loser_text,
                "selected_mirror": winner_id,
                "selected_mirror_text": winner_text,
                "participant_id": row.get("participant_id"),
                "prolific_id": row.get("prolific_id"),
                "trial_index": row.get("trial_index"),
                "post_number": row.get("post_number"),
                "presentation_order": row.get("presentation_order"),
                "selected_position": row.get("selected_position"),
                "response_time_ms": row.get("response_time_ms"),
                "selection_time_ms": row.get("selection_time_ms"),
                "sampled_stance": row.get("sampled_stance"),
                "sample_toxicity_type": row.get("sample_toxicity_type"),
            }
            pairwise.append(pair)

    return pairwise
