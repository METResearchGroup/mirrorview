---
name: prompt optimization data prep
overview: Build a small, dependency-light Python experiment pipeline that converts the pilot preference CSVs into training-ready pairwise preference data for prompt optimization. The implementation will live under `/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization`, keep each requested transformation in its own script, and expose a single `main.py` DAG that materializes intermediate CSV artifacts for inspection.
todos:
  - id: create-experiment-package
    content: Add the new `experiments/2026_03_10_train_prompt_optimization` package with importable step modules and `main.py`.
    status: completed
  - id: implement-step-logic
    content: Implement the four pure transformation scripts for filter, join, selected-mirror resolution, and pairwise expansion.
    status: completed
  - id: add-pipeline-tests
    content: Add pytest coverage for the new data-prep pipeline under `backend/tests/test_prompt_optimization_pipeline.py`.
    status: completed
  - id: verify-dag-output
    content: Run the DAG end-to-end and verify the intermediate and final CSV artifacts and row counts.
    status: completed
isProject: false
---

# Prompt Optimization Data Prep Plan

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview
We will turn the pilot preference export in [`/Users/mark/Documents/work/mirrorview-worktree/data/raw/2026_01_01_pilot_data/user_preferences_pilot_data.csv`](/Users/mark/Documents/work/mirrorview-worktree/data/raw/2026_01_01_pilot_data/user_preferences_pilot_data.csv) and the mirror text table in [`/Users/mark/Documents/work/mirrorview-worktree/data/raw/2026_01_01_pilot_data/mirrored_posts.csv`](/Users/mark/Documents/work/mirrorview-worktree/data/raw/2026_01_01_pilot_data/mirrored_posts.csv) into a clean, reproducible pairwise preference dataset for reward-model or prompt-optimization work. The plan uses only Python stdlib CSV utilities unless inspection during implementation shows a compelling need otherwise, because the existing backend environment in [`/Users/mark/Documents/work/mirrorview-worktree/backend/pyproject.toml`](/Users/mark/Documents/work/mirrorview-worktree/backend/pyproject.toml) does not currently depend on `pandas` or `polars`.

## Happy Flow
1. `main.py` in [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/main.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/main.py) reads the two raw CSV inputs and creates an `artifacts/` directory under the same experiment folder.
2. `step1_filter_preferences.py` filters the raw preference export down to rows where `trial_type == "mirror-preference"` and retains only the columns needed downstream, especially `post_id`, `original_text`, `selected_mirror`, and presentation metadata from [`user_preferences_pilot_data.csv`](/Users/mark/Documents/work/mirrorview-worktree/data/raw/2026_01_01_pilot_data/user_preferences_pilot_data.csv).
3. `step2_join_mirrors.py` joins those filtered rows against [`mirrored_posts.csv`](/Users/mark/Documents/work/mirrorview-worktree/data/raw/2026_01_01_pilot_data/mirrored_posts.csv) by `post_id == post_primary_key` so each preference row now has the full set of mirror texts (`human_mirror`, `llama_mirror`, `qwen_mirror`, `claude_mirror`, `gpt4o_mirror`) plus the original post text.
4. `step3_build_selected_mirror_dataset.py` resolves `selected_mirror` into the actual selected response text by mapping values like `human`, `llama`, `qwen`, `claude`, and `gpt4o` onto their corresponding joined text columns, producing one row per trial with `post_id`, original text, selected mirror id, and selected mirror text.
5. `step4_build_pairwise_preferences.py` expands each selected row into pairwise preference records using the chosen convention: create one training row for each non-selected mirror in that trial, where the selected mirror is the winner and the non-selected mirror is the loser.
6. `main.py` writes each stage to CSV so the pipeline is inspectable end-to-end and prints row counts per stage for quick sanity checks.

## Files To Add
- [`/Users/mark/Documents/work/mirrorview-worktree/experiments/__init__.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/__init__.py)
- [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/__init__.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/__init__.py)
- [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step1_filter_preferences.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step1_filter_preferences.py)
- [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step2_join_mirrors.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step2_join_mirrors.py)
- [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step3_build_selected_mirror_dataset.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step3_build_selected_mirror_dataset.py)
- [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step4_build_pairwise_preferences.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/step4_build_pairwise_preferences.py)
- [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/main.py`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/main.py)
- [`/Users/mark/Documents/work/mirrorview-worktree/backend/tests/test_prompt_optimization_pipeline.py`](/Users/mark/Documents/work/mirrorview-worktree/backend/tests/test_prompt_optimization_pipeline.py)

## Implementation Steps
1. Create the new experiment package under [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization) and make it importable with `__init__.py` files so both `main.py` and pytest can import the step functions cleanly.
2. In `step1_filter_preferences.py`, implement a pure function that accepts iterable CSV rows or an input path and returns filtered dictionaries for only `mirror-preference` trials. Normalize the leading unnamed CSV index column away if present and define the exact step-1 output schema explicitly.
3. In `step2_join_mirrors.py`, implement a keyed join on `post_id` to `post_primary_key`, fail loudly or count mismatches if a post is missing from the mirror table, and preserve both the joined mirror columns and the user-selected mirror id.
4. In `step3_build_selected_mirror_dataset.py`, centralize the mirror-id-to-column mapping in one dictionary, derive `selected_mirror_text`, and validate that every `selected_mirror` is one of the supported ids seen in the mirror table.
5. In `step4_build_pairwise_preferences.py`, generate one row per loser mirror for every selected example. Each output row should include at minimum `post_id`, `original_text`, `winner_mirror_id`, `winner_text`, `loser_mirror_id`, `loser_text`, and enough provenance columns to trace back to the original trial if needed.
6. In `main.py`, wire the four steps as a simple linear DAG, define default input and output paths, write intermediate artifacts to:
   - [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step1_mirror_preferences.csv`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step1_mirror_preferences.csv)
   - [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step2_joined_mirrors.csv`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step2_joined_mirrors.csv)
   - [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step3_selected_mirror_dataset.csv`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step3_selected_mirror_dataset.csv)
   - [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step4_pairwise_preferences.csv`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step4_pairwise_preferences.csv)
7. Add focused pytest coverage in [`/Users/mark/Documents/work/mirrorview-worktree/backend/tests/test_prompt_optimization_pipeline.py`](/Users/mark/Documents/work/mirrorview-worktree/backend/tests/test_prompt_optimization_pipeline.py) for:
   - filtering only `mirror-preference` rows
   - joining `post_id` to `post_primary_key`
   - resolving `selected_mirror` to the correct text column
   - expanding one selected mirror into the expected number of pairwise rows

## Data Assumptions To Encode
- `user_preferences_pilot_data.csv` uses `trial_type` to distinguish relevant rows.
- Relevant user choice columns are `post_id`, `original_text`, and `selected_mirror`.
- `mirrored_posts.csv` uses `post_primary_key` as the join key and stores one text column per mirror model.
- Supported mirror ids are expected to match the joined columns: `human`, `llama`, `qwen`, `claude`, `gpt4o`.
- Pairwise output uses the confirmed convention: `selected_mirror` beats each non-selected mirror from the same joined row.

## Alternative Approaches
We could add `pandas` and express the pipeline as dataframe transforms, but the simpler first pass is stdlib CSV processing because the repo’s Python environment already exists under [`/Users/mark/Documents/work/mirrorview-worktree/backend/pyproject.toml`](/Users/mark/Documents/work/mirrorview-worktree/backend/pyproject.toml) without extra data-stack dependencies. We could also skip intermediate CSVs and only emit the final pairwise dataset, but keeping step artifacts makes debugging data quality issues much easier for this first experiment.

## Manual Verification
- [ ] Sync the existing Python environment: `cd /Users/mark/Documents/work/mirrorview-worktree/backend && uv sync`.
  Expected result: the backend virtual environment resolves successfully with no new dependency additions required for the experiment scripts.
- [ ] Run the unit tests: `cd /Users/mark/Documents/work/mirrorview-worktree/backend && uv run pytest tests/test_prompt_optimization_pipeline.py -q`.
  Expected result: tests pass and verify the four requested transformations on small fixtures.
- [ ] Run the DAG end-to-end: `cd /Users/mark/Documents/work/mirrorview-worktree/backend && uv run python ../experiments/2026_03_10_train_prompt_optimization/main.py`.
  Expected result: the script prints stage row counts and writes the four CSV artifacts under `../experiments/2026_03_10_train_prompt_optimization/artifacts/`.
- [ ] Inspect the final artifact: open [`/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step4_pairwise_preferences.csv`](/Users/mark/Documents/work/mirrorview-worktree/experiments/2026_03_10_train_prompt_optimization/artifacts/step4_pairwise_preferences.csv).
  Expected result: each row contains the original post text plus a winner/loser mirror pair, and each source trial contributes one row for every non-selected mirror.
- [ ] Spot-check one joined example against the raw inputs.
  Expected result: `post_id` from step 1 matches `post_primary_key` in `mirrored_posts.csv`, and the `selected_mirror_text` in step 3 exactly matches the correct mirror column for that post.

## Plan Assets
Use [`/Users/mark/Documents/work/mirrorview-worktree/docs/plans/2026-03-10_train_prompt_optimization_280028/`](/Users/mark/Documents/work/mirrorview-worktree/docs/plans/2026-03-10_train_prompt_optimization_280028/) for any notes or validation artifacts associated with this work. No UI screenshots are required because this task is data-processing only.