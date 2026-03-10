from __future__ import annotations

from typing import Iterable, Mapping

STEP1_COLUMNS = [
    "trial_index",
    "participant_id",
    "prolific_id",
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
    rows: Iterable[Mapping[str, str]],
) -> list[dict[str, str | None]]:
    """Return a list of mirror-preference rows with a sane column subset."""

    filtered: list[dict[str, str | None]] = []
    for row in rows:
        if row.get("trial_type") != "mirror-preference":
            continue
        filtered_row = {column: row.get(column) for column in STEP1_COLUMNS}
        filtered.append(filtered_row)
    return filtered
