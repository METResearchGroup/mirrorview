# Generating flips

Generate flipped posts for the pilot dataset using the production flip prompt and schema.

## Steps

1. **Build input** – Extract unique `post_id` and `original_text` from `experiments/label_criteria_for_reward_model_2026_03_10/artifacts/step1_unique_mirrors_to_label.csv`, dedupe to one row per post, and write `artifacts/step1_posts_to_flip.csv`.

2. **Generate (batched)** – Run each `original_text` through `LLMService.structured_batch_completion(...)` with `FlipResponse` and `FLIP_PROMPT`, writing per-batch CSVs under a run directory in `artifacts/generated_flips/` and a single `metadata.json` for the run.

3. **Resume (default)** – By default, generation scans previously generated flip CSVs under `artifacts/generated_flips/` and skips `post_id` values that have already been generated. Use `--no-resume` to disable this behavior.

4. **Finalize** – Concatenate all generated flip CSVs under `artifacts/generated_flips/`, add run timestamp, dedupe by `post_id`, and write `artifacts/step3_finalized_flips.csv` with columns: `post_id`, `original_text`, `flipped_text`, `timestamp`.

## Artifacts

- `artifacts/step1_posts_to_flip.csv` – One row per unique post (post_id, original_text).
- `artifacts/generated_flips/<RUN_TIMESTAMP>/` – Run folder.
  - `<YYYY_MM_DD-HH:MM:SS>_batch_<N>.csv` – Generated flips (post_id, original_text, flipped_text, explanation, model).
  - `metadata.json` – Run metadata: completed_at, model, git_hash, input_csv, output_csv_dir, total_attempted, succeeded, failed.
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
