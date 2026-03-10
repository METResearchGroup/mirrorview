from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .step1_filter_preferences import (
    STEP1_COLUMNS,
    filter_mirror_preference_rows,
)
from .step2_join_mirrors import (
    STEP2_COLUMNS,
    join_preferences_with_mirrors,
)
from .step3_build_selected_mirror_dataset import (
    STEP3_COLUMNS,
    build_selected_mirror_dataset,
)
from .step4_build_pairwise_preferences import (
    STEP4_COLUMNS,
    build_pairwise_preferences,
)

from backend.lib.constants import ROOT_DIR

RAW_DATA_DIR = ROOT_DIR / "data" / "raw" / "2026_01_01_pilot_data"
PREFERENCES_CSV = RAW_DATA_DIR / "user_preferences_pilot_data.csv"
MIRRORED_CSV = RAW_DATA_DIR / "mirrored_posts.csv"
CURRENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CURRENT_DIR / "artifacts"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader]


def _write_csv(
    path: Path, rows: Iterable[dict[str, str | None]], fieldnames: list[str]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (row.get(key) or "") for key in fieldnames})


def main(
    preferences_path: Path | str = PREFERENCES_CSV,
    mirror_path: Path | str = MIRRORED_CSV,
) -> list[int]:
    ARTIFACTS_DIR.mkdir(exist_ok=True)

    raw_preferences = _read_csv(Path(preferences_path))
    filtered = filter_mirror_preference_rows(raw_preferences)
    _write_csv(ARTIFACTS_DIR / "step1_mirror_preferences.csv", filtered, STEP1_COLUMNS)

    mirror_rows = _read_csv(Path(mirror_path))
    joined = join_preferences_with_mirrors(filtered, mirror_rows)
    _write_csv(ARTIFACTS_DIR / "step2_joined_mirrors.csv", joined, STEP2_COLUMNS)

    selected = build_selected_mirror_dataset(joined)
    _write_csv(
        ARTIFACTS_DIR / "step3_selected_mirror_dataset.csv", selected, STEP3_COLUMNS
    )

    pairwise = build_pairwise_preferences(selected)
    _write_csv(
        ARTIFACTS_DIR / "step4_pairwise_preferences.csv", pairwise, STEP4_COLUMNS
    )

    counts = [
        len(filtered),
        len(joined),
        len(selected),
        len(pairwise),
    ]
    print(
        "Pipeline row counts (filter/join/selected/pairwise): "
        + "/".join(str(count) for count in counts)
    )
    return counts


if __name__ == "__main__":
    main()
