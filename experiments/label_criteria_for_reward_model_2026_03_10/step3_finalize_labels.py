from __future__ import annotations

from pathlib import Path

import pandas as pd

CRITERIA_COLUMNS = [
    "political_us",
    "opinion_not_news",
    "complete",
    "self_contained",
    "target_topic",
    "clear_political_stance",
]


def _read_and_validate_labels_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        return df
    if "label_id" not in df.columns:
        raise ValueError(f"Labels CSV missing required column `label_id`: {path}")
    missing_cols = [c for c in CRITERIA_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Labels CSV missing required criteria columns {missing_cols}: {path}")
    return df


def load_labels_from_dir(labels_dir: Path) -> pd.DataFrame:
    if not labels_dir.exists():
        return pd.DataFrame()
    parts = []
    for p in sorted(labels_dir.iterdir()):
        if p.is_file() and p.suffix == ".csv":
            parts.append(_read_and_validate_labels_csv(p))
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def finalize_labels(
    *,
    input_csv: Path | str,
    labels_dir: Path | str,
    output_csv: Path | str,
    require_all_labeled: bool = True,
) -> pd.DataFrame:
    input_path = Path(input_csv)
    labels_dir_path = Path(labels_dir)
    output_path = Path(output_csv)

    inputs = pd.read_csv(input_path)
    labels = load_labels_from_dir(labels_dir_path)

    if "label_id" not in inputs.columns:
        raise ValueError("Input CSV missing required column `label_id`.")
    if inputs["label_id"].nunique(dropna=False) != len(inputs):
        raise ValueError("Input CSV must have exactly one row per label_id.")

    if labels.empty:
        raise ValueError(f"No labels found under {labels_dir_path}")
    if labels["label_id"].nunique(dropna=False) != len(labels):
        dupes = labels.loc[labels["label_id"].duplicated(), "label_id"].head(5).tolist()
        raise ValueError(f"Labels CSV must have one row per label_id. Example dupes: {dupes}")

    merged = inputs.merge(labels, how="left", on="label_id", validate="one_to_one")

    missing_labels = merged.loc[merged[CRITERIA_COLUMNS].isna().any(axis=1), "label_id"].tolist()
    if missing_labels and require_all_labeled:
        sample = ", ".join(missing_labels[:5])
        raise ValueError(
            f"{len(missing_labels)} label_id values are missing LLM labels (e.g. {sample})."
        )

    for c in CRITERIA_COLUMNS:
        merged[c] = merged[c].fillna(0).astype(int)

    merged["criteria_sum"] = merged[CRITERIA_COLUMNS].sum(axis=1).astype(int)
    merged["passes_stage1_filter"] = (merged["criteria_sum"] >= 5).astype(int)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"Wrote {len(merged)} rows to {output_path}")
    return merged


if __name__ == "__main__":
    artifacts_dir = Path(__file__).resolve().parent / "artifacts"
    finalize_labels(
        input_csv=artifacts_dir / "step1_unique_mirrors_to_label.csv",
        labels_dir=artifacts_dir / "llm_labels",
        output_csv=artifacts_dir / "step3_all_mirror_criteria_labels.csv",
        require_all_labeled=True,
    )

