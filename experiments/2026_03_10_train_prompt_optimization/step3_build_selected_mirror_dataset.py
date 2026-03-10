from __future__ import annotations

import numpy as np
import pandas as pd

from step2_join_mirrors import MIRROR_ID_TO_COLUMN, STEP2_COLUMNS

STEP3_COLUMNS = [*STEP2_COLUMNS, "selected_mirror_text"]


def build_selected_mirror_dataset(
    joined: pd.DataFrame,
) -> pd.DataFrame:
    """Add the selected mirror text to each joined row."""

    df = joined.copy()
    if "selected_mirror" not in df.columns:
        raise ValueError("Joined dataset missing required column `selected_mirror`.")

    mirror_columns = list(MIRROR_ID_TO_COLUMN.values())
    missing = [c for c in mirror_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Joined dataset missing mirror text columns: {missing}")

    mirror_id_to_idx = {mirror_id: idx for idx, mirror_id in enumerate(MIRROR_ID_TO_COLUMN.keys())}
    mirror_idx = df["selected_mirror"].map(mirror_id_to_idx)
    if mirror_idx.isna().any():
        bad = df.loc[mirror_idx.isna(), "selected_mirror"].dropna().unique()
        sample = ", ".join(map(str, bad[:5]))
        raise ValueError(f"Unsupported mirror id(s) in `selected_mirror` (e.g. {sample})")

    values = df.loc[:, mirror_columns].to_numpy()
    row_idx = np.arange(len(df))
    col_idx = mirror_idx.astype(int).to_numpy()
    selected_text = values[row_idx, col_idx]

    if pd.isna(selected_text).any():
        raise ValueError("One or more selected mirror texts are missing after resolution.")

    df["selected_mirror_text"] = selected_text

    missing_after = [col for col in STEP3_COLUMNS if col not in df.columns]
    if missing_after:
        raise ValueError(f"Selected-mirror dataset missing expected columns: {missing_after}")

    return df.loc[:, STEP3_COLUMNS].reset_index(drop=True)
