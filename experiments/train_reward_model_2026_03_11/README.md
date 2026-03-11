### Train reward model (2026-03-11)

This experiment fine-tunes `microsoft/deberta-v3-base` to predict the six Stage-1 criteria labels
using a multi-label (6-logit) BCE objective on `mirror_text` only.

**Labels:** `political_us`, `opinion_not_news`, `complete`, `self_contained`, `target_topic`, `clear_political_stance`

---

#### Key inputs

- `../label_criteria_for_reward_model_2026_03_10/artifacts/step3_all_mirror_criteria_labels.csv`

#### Key outputs

- `runs/<run_id>/hyperparameters.json`
- `runs/<run_id>/run_results.json`
- `runs/best_run.json` (best config from last search)

---

#### Training results

| Run | macro_f1 | micro_f1 | Config | Eval N |
|-----|----------|----------|--------|--------|
| **grid-2026_03_11-153112** | **0.967** | **0.969** | lr=2e-5, bs=8, epochs=1, max_len=128, wd=0 | 959 |
| optuna-2026_03_11-153558 | 0.934 | 0.939 | lr≈1.52e-5, bs=16, epochs=5, max_len=128, wd=0 | 26 (smoke) |
| grid-2026_03_11-153424 | 0.934 | 0.939 | smoke test | 26 |
| grid-2026_03_11-153514 | 0.934 | 0.939 | smoke test | 26 |

**Best full-dataset run:** `grid-2026_03_11-153112` — macro_f1 **0.967**, micro_f1 **0.969** on 959 eval samples.

**Per-label F1 (best run):**

| Label | F1 |
|-------|-----|
| political_us | 0.90 |
| opinion_not_news | 0.99 |
| complete | 0.99 |
| self_contained | 0.99 |
| target_topic | 0.99 |
| clear_political_stance | 0.93 |

Harder labels: `political_us`, `clear_political_stance` (lower F1). Others near ceiling.

---

#### Example run (from repo root)

```bash
uv run python experiments/train_reward_model_2026_03_11/main.py \
  --dataset-csv experiments/label_criteria_for_reward_model_2026_03_10/artifacts/step3_all_mirror_criteria_labels.csv \
  --model-name microsoft/deberta-v3-base \
  --epochs 1 \
  --batch-size 8 \
  --max-length 128
```

Grid search (default):

```bash
uv run python experiments/train_reward_model_2026_03_11/main.py --search-backend grid
```

Optuna search:

```bash
uv run python experiments/train_reward_model_2026_03_11/main.py --search-backend optuna --n-trials 5
```
