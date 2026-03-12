from __future__ import annotations

import argparse
from pathlib import Path

from .step1_build_generation_dataset import (
    DEFAULT_INPUT_CSV,
    build_generation_dataset,
)
from .step2_generate_with_llm import DEFAULT_MODEL, generate_with_llm
from .step3_finalize_flips import finalize_flips


EXPERIMENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate flipped posts for pilot dataset using production FlipResponse and FLIP_PROMPT."
    )
    p.add_argument(
        "--step",
        default="all",
        choices=["all", "build-input", "generate", "finalize"],
        help="Which step to run.",
    )
    p.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT_CSV,
        help="Path to step1_unique_mirrors_to_label.csv (source for post_id + original_text).",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for LLM generation.",
    )
    p.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Max batches for smoke tests (omit for full run).",
    )
    p.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="LLM model id to use for generation.",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing artifacts (default behavior).",
    )
    g.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume behavior (do not sync existing artifacts).",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    step1_out = ARTIFACTS_DIR / "step1_posts_to_flip.csv"
    flips_dir = ARTIFACTS_DIR / "generated_flips"
    success_csv = ARTIFACTS_DIR / "successfully_generated_posts.csv"

    resume = not args.no_resume

    if args.step in ("all", "build-input"):
        build_generation_dataset(
            input_csv=args.input_csv,
            output_csv=step1_out,
        )

    if args.step in ("all", "generate"):
        generate_with_llm(
            input_csv=step1_out,
            flips_dir=flips_dir,
            success_csv=success_csv,
            model=args.model,
            batch_size=args.batch_size,
            max_batches=args.max_batches,
            resume=resume,
        )

    if args.step in ("all", "finalize"):
        finalize_flips(
            flips_dir=flips_dir,
            output_csv=ARTIFACTS_DIR / "step3_finalized_flips.csv",
        )


if __name__ == "__main__":
    main()
