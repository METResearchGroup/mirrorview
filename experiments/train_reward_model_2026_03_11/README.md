### Train reward model (2026-03-11)

This experiment fine-tunes `microsoft/deberta-v3-base` to predict the six Stage-1 criteria labels
using a multi-label (6-logit) BCE objective on `mirror_text` only.

Key inputs:
- `../label_criteria_for_reward_model_2026_03_10/artifacts/step3_all_mirror_criteria_labels.csv`

Key outputs:
- `runs/<run_id>/hyperparameters.json`
- `runs/<run_id>/run_results.json`

Example run (from `backend/`):

```
uv run python ../experiments/train_reward_model_2026_03_11/main.py \
  --dataset-csv ../experiments/label_criteria_for_reward_model_2026_03_10/artifacts/step3_all_mirror_criteria_labels.csv \
  --model-name microsoft/deberta-v3-base \
  --epochs 1 \
  --batch-size 8 \
  --max-length 128
```
