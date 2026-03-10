from __future__ import annotations

import pandas as pd

from step2_join_mirrors import MIRROR_ID_TO_COLUMN

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
    selected: pd.DataFrame,
) -> pd.DataFrame:
    """Turn selected-mirror rows into pairwise preference examples."""

    df = selected.copy()
    required = ["selected_mirror", "selected_mirror_text", *MIRROR_ID_TO_COLUMN.values()]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Selected dataset missing required columns: {missing}")

    inverse_col_to_id = {col: mirror_id for mirror_id, col in MIRROR_ID_TO_COLUMN.items()}

    long = df.melt(
        id_vars=[c for c in df.columns if c not in MIRROR_ID_TO_COLUMN.values()],
        value_vars=list(MIRROR_ID_TO_COLUMN.values()),
        var_name="loser_mirror_col",
        value_name="loser_text",
    )
    long["loser_mirror_id"] = long["loser_mirror_col"].map(inverse_col_to_id)
    long = long.drop(columns=["loser_mirror_col"])

    long = long.loc[long["loser_mirror_id"] != long["selected_mirror"], :].reset_index(drop=True)

    long["winner_mirror_id"] = long["selected_mirror"]
    long["winner_text"] = long["selected_mirror_text"]

    missing_after = [c for c in STEP4_COLUMNS if c not in long.columns]
    if missing_after:
        raise ValueError(f"Pairwise dataset missing expected columns: {missing_after}")

    return long.loc[:, STEP4_COLUMNS].reset_index(drop=True)
