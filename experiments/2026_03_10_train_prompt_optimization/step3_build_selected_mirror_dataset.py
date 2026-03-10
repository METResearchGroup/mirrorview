from __future__ import annotations

from typing import Iterable, Mapping

from .step2_join_mirrors import MIRROR_ID_TO_COLUMN, STEP2_COLUMNS

STEP3_COLUMNS = [*STEP2_COLUMNS, "selected_mirror_text"]


def build_selected_mirror_dataset(
    joined_rows: Iterable[Mapping[str, str | None]],
) -> list[dict[str, str | None]]:
    """Add the selected mirror text to each joined row."""

    dataset: list[dict[str, str | None]] = []
    for row in joined_rows:
        selected = row.get("selected_mirror")
        if selected not in MIRROR_ID_TO_COLUMN:
            raise ValueError(f"Unsupported mirror id '{selected}' in selected_mirror.")

        mirror_column = MIRROR_ID_TO_COLUMN[selected]
        selected_text = row.get(mirror_column)
        if selected_text is None:
            raise ValueError(
                f"Mirror column {mirror_column} missing text for post {row.get('post_id')}."
            )

        enriched = dict(row)
        enriched["selected_mirror_text"] = selected_text
        dataset.append(enriched)

    return dataset
