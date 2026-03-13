import pandas as pd

from backend.lib.batcher import BatchLoader

from .constants import INPUT_COLUMNS


def load_post_batches_to_flip(
    *,
    input_csv_path: str,
    flips_dir_path: str,
    batch_size: int,
    max_batches: int | None = None,
) -> BatchLoader[pd.DataFrame]:
    posts_to_flip = _load_posts_to_flip(input_csv_path)
    previously_generated_flips = load_previously_generated_flips(flips_dir_path)
    posts_to_flip = filter_only_rows_pending_generation(
        posts_to_flip=posts_to_flip,
        previously_generated_flips=previously_generated_flips,
    )
    return BatchLoader(
        data=posts_to_flip,
        batch_size=batch_size,
        max_batches=max_batches,
    )


def load_posts_to_flip(input_csv_path: str, flips_dir_path: str) -> pd.DataFrame:
    """Load posts to flip and filter out rows that have already been generated."""
    posts_to_flip = _load_posts_to_flip(input_csv_path)
    previously_generated_flips = load_previously_generated_flips(flips_dir_path)
    return filter_only_rows_pending_generation(posts_to_flip, previously_generated_flips)


def load_previously_generated_flips(flips_dir_path: str) -> set[str]:
    df = pd.read_csv(flips_dir_path, dtype={"post_id": str})
    if "post_id" not in df.columns:
        raise ValueError(f"Expected column `post_id` in {flips_dir_path}")
    return set(df["post_id"].dropna().astype(str).tolist())


def filter_only_rows_pending_generation(
    posts_to_flip: pd.DataFrame,
    previously_generated_flips: set[str],
) -> pd.DataFrame:
    """Compute rows that have not yet been generated."""
    post_filter = ~posts_to_flip["post_id"].astype(str).isin(list(previously_generated_flips))
    return posts_to_flip.loc[post_filter, :].reset_index(drop=True)


def _load_posts_to_flip(input_csv_path: str) -> pd.DataFrame:
    posts_to_flip: pd.DataFrame = pd.read_csv(input_csv_path, dtype={"post_id": str, "original_text": str})
    _validate_input(posts_to_flip)
    return posts_to_flip

def _validate_input(df: pd.DataFrame) -> None:
    missing = [c for c in INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Generation input CSV missing expected columns: {missing}")
    if df["post_id"].nunique(dropna=False) != len(df):
        raise ValueError("Input must have exactly one row per post_id.")
