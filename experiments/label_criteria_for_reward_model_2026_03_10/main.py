from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
for p in (str(BACKEND_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        # Keep the script directory (sys.path[0]) first so local modules like
        # prompts.py/schemas.py resolve to this experiment, not backend/.
        insert_at = 1 if len(sys.path) > 0 else 0
        sys.path.insert(insert_at, p)

try:
    # When imported as a package module (pytest).
    from .step1_build_labeling_dataset import DEFAULT_JOINED_INPUT, step1_build_labeling_dataset
    from .step2_label_with_llm import DEFAULT_MODEL, label_with_llm
    from .step3_finalize_labels import finalize_labels
except ImportError:  # pragma: no cover
    # When executed as a script.
    from step1_build_labeling_dataset import DEFAULT_JOINED_INPUT, step1_build_labeling_dataset
    from step2_label_with_llm import DEFAULT_MODEL, label_with_llm
    from step3_finalize_labels import finalize_labels


EXPERIMENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = EXPERIMENT_DIR / "artifacts"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Label unique mirrors on Stage-1 reward-model criteria (issue #28)."
    )
    p.add_argument(
        "--step",
        default="all",
        choices=["all", "build-input", "label", "finalize"],
        help="Which step to run.",
    )
    p.add_argument(
        "--joined-input",
        type=Path,
        default=DEFAULT_JOINED_INPUT,
        help="Path to step2_joined_mirrors.csv (source of truth).",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for LLM labeling.",
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
        help="LLM model id to use for labeling.",
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

    step1_out = ARTIFACTS_DIR / "step1_unique_mirrors_to_label.csv"
    step2_labels = ARTIFACTS_DIR / "step2_llm_labels.csv"
    step2_success = ARTIFACTS_DIR / "successfully_labeled_flips.csv"
    step3_out = ARTIFACTS_DIR / "step3_all_mirror_criteria_labels.csv"

    resume = True if not args.no_resume else False

    if args.step in ("all", "build-input"):
        step1_build_labeling_dataset(
            joined_input_csv=args.joined_input,
            output_csv=step1_out,
        )

    if args.step in ("all", "label"):
        label_with_llm(
            input_csv=step1_out,
            labels_csv=step2_labels,
            success_csv=step2_success,
            model=args.model,
            batch_size=args.batch_size,
            max_batches=args.max_batches,
            resume=resume,
        )

    if args.step in ("all", "finalize"):
        finalize_labels(
            input_csv=step1_out,
            labels_csv=step2_labels,
            output_csv=step3_out,
            require_all_labeled=True,
        )


if __name__ == "__main__":
    main()

