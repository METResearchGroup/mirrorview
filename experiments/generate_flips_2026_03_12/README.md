# Generating flips

Right now, we want to generate the flips for the posts that were used in the original pilot.

Steps:

1. Grab the original texts (in the "original_text") column, and their post ID (in "post_id"), in `experiments/label_criteria_for_reward_model_2026_03_10/artifacts/step1_unique_mirrors_to_label.csv`.
2. Run them through the classification in `llm_service.py`. We have a similar approach already in `experiments/label_criteria_for_reward_model_2026_03_10/step2_label_with_llm.py` for how to do the labels.
3. Return the labels. Put them in artifacts/llm_labels/, following the same sort of approach for this (timestamped .csv file), and metadata (total number of labeled content, timestamp for label completion, number success/failed, git hash (so we can know what version of the prompt we used)).
