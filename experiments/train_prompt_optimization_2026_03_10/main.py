from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.lib.constants import ROOT_DIR
from experiments.train_prompt_optimization_2026_03_10.step1_filter_preferences import (
    filter_mirror_preference_rows,
)
from experiments.train_prompt_optimization_2026_03_10.step2_join_mirrors import (
    join_preferences_with_mirrors,
)
from experiments.train_prompt_optimization_2026_03_10.step3_build_selected_mirror_dataset import (
    build_selected_mirror_dataset,
)
from experiments.train_prompt_optimization_2026_03_10.step4_build_pairwise_preferences import (
    build_pairwise_preferences,
)

RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "2026_01_01_pilot_data"
PREFERENCES_CSV = RAW_DATA_DIR / "user_preferences_pilot_data.csv"
MIRRORED_CSV = RAW_DATA_DIR / "mirrored_posts.csv"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


def main(
    preferences_path: Path | str = PREFERENCES_CSV,
    mirror_path: Path | str = MIRRORED_CSV,
) -> list[int]:
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    raw_preferences = pd.read_csv(Path(preferences_path))
    filtered = filter_mirror_preference_rows(raw_preferences)
    filtered.to_csv(ARTIFACTS_DIR / "step1_mirror_preferences.csv", index=False)

    mirror_rows = pd.read_csv(Path(mirror_path))
    joined = join_preferences_with_mirrors(filtered, mirror_rows)
    joined.to_csv(ARTIFACTS_DIR / "step2_joined_mirrors.csv", index=False)

    selected = build_selected_mirror_dataset(joined)
    selected.to_csv(ARTIFACTS_DIR / "step3_selected_mirror_dataset.csv", index=False)

    pairwise = build_pairwise_preferences(selected)
    pairwise.to_csv(ARTIFACTS_DIR / "step4_pairwise_preferences.csv", index=False)

    counts = [
        int(filtered.shape[0]),
        int(joined.shape[0]),
        int(selected.shape[0]),
        int(pairwise.shape[0]),
    ]
    print(
        "Pipeline row counts (filter/join/selected/pairwise): "
        + "/".join(str(count) for count in counts)
    )
    return counts


if __name__ == "__main__":
    main()
