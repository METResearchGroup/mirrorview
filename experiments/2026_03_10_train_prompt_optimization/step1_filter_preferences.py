from __future__ import annotations

import pandas as pd

STEP1_COLUMNS = [
    "participant_id",
    "post_id",
    "post_number",
    "original_text",
    "selected_mirror",
    "selected_position",
    "presentation_order",
    "response_time_ms",
    "selection_time_ms",
]


def filter_mirror_preference_rows(
    preferences: pd.DataFrame,
) -> pd.DataFrame:
    """Filter to mirror-preference trials and return a stable column subset."""

    df = preferences.copy()
    if "trial_type" not in df.columns:
        raise ValueError("Expected column `trial_type` in preferences CSV.")

    filtered = df.loc[df["trial_type"] == "mirror-preference", :]

    missing = [col for col in STEP1_COLUMNS if col not in filtered.columns]
    if missing:
        raise ValueError(f"Preferences CSV missing expected columns: {missing}")

    return filtered.loc[:, STEP1_COLUMNS].reset_index(drop=True)
