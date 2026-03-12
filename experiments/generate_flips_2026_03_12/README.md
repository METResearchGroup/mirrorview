# Generating flips

Generate flipped posts for the pilot dataset using the production flip prompt and schema.

## Steps

1. **Build input** – Extract unique `post_id` and `original_text` from `experiments/label_criteria_for_reward_model_2026_03_10/artifacts/step1_unique_mirrors_to_label.csv`, dedupe to one row per post, and write `artifacts/step1_posts_to_flip.csv`.

2. **Generate** – Run each `original_text` through `LLMService.structured_batch_completion(...)` with `FlipResponse` and `FLIP_PROMPT`, writing timestamped CSVs under `artifacts/generated_flips/` plus a sidecar `.metadata.json` per run.

3. **Resume** – Track completed `post_id` values in `artifacts/successfully_generated_posts.csv` so reruns skip already-generated posts.

4. **Finalize** – Concatenate all generated flip CSVs, add run timestamp from filename, dedupe by `post_id`, and write `artifacts/step3_finalized_flips.csv` with columns: `post_id`, `original_text`, `flipped_text`, `timestamp`.

## Artifacts

- `artifacts/step1_posts_to_flip.csv` – One row per unique post (post_id, original_text).
- `artifacts/generated_flips/<YYYY_MM_DD-HH:MM:SS>.csv` – Generated flips (post_id, original_text, flipped_text, explanation, model).
- `artifacts/generated_flips/<YYYY_MM_DD-HH:MM:SS>.metadata.json` – Run metadata: completed_at, model, git_hash, prompt_source, total_attempted, succeeded, failed.
- `artifacts/successfully_generated_posts.csv` – Post IDs already generated (for resume).
- `artifacts/step3_finalized_flips.csv` – Finalized output: post_id, original_text, flipped_text, timestamp.

## Usage

```bash
# Build deduped input
PYTHONPATH=backend:. uv run python -m experiments.generate_flips_2026_03_12.main --step build-input

# Smoke test (one batch of 10)
PYTHONPATH=backend:. uv run python -m experiments.generate_flips_2026_03_12.main --step generate --batch-size 10 --max-batches 1

# Full run
PYTHONPATH=backend:. uv run python -m experiments.generate_flips_2026_03_12.main --step generate --batch-size 10

# Finalize (after generation)
PYTHONPATH=backend:. uv run python -m experiments.generate_flips_2026_03_12.main --step finalize
```
