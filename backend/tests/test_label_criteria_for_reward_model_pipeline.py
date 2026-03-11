"""Pytest coverage for the label criteria reward model pipeline."""

# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class TestLabelCriteriaForRewardModel:
    """Encapsulates expectations for label criteria deduplication and reshaping."""

    def test_step1_dedupe_and_reshape_to_five_mirrors_per_post(self) -> None:
        """Ensures step one produces each mirror once per post."""
        from experiments.label_criteria_for_reward_model_2026_03_10.step1_build_labeling_dataset import (
            MIRROR_ID_TO_COLUMN,
            build_unique_mirrors_to_label,
            make_label_id,
        )

        base_row = {
            "trial_index": 1,
            "post_id": "post_1",
            "post_primary_key": "post_1",
            "original_text": "Original text",
            "sampled_stance": "left",
            "sample_toxicity_type": "sample_low_toxicity",
            "human_mirror": "H",
            "llama_mirror": "L",
            "qwen_mirror": "Q",
            "claude_mirror": "C",
            "gpt4o_mirror": "G",
        }
        # Duplicate participant-level rows for the same post_id with identical mirror text.
        joined = pd.DataFrame([base_row, {**base_row, "trial_index": 2}])

        out = build_unique_mirrors_to_label(joined)
        assert len(out) == 5
        assert out["post_id"].nunique() == 1
        assert set(out["mirror_id"].tolist()) == set(MIRROR_ID_TO_COLUMN.keys())
        assert out["label_id"].nunique() == 5

        expected_ids = {make_label_id(post_id="post_1", mirror_id=m) for m in MIRROR_ID_TO_COLUMN}
        assert set(out["label_id"].tolist()) == expected_ids


class TestStep2LabelWithLlm:
    """Tests for step2_label_with_llm resume and deduplication behavior."""

    def test_step2_skip_resume_appends_without_duplicates(self, tmp_path: Path) -> None:
        from experiments.label_criteria_for_reward_model_2026_03_10.schemas import Stage1CriteriaLabel
        from experiments.label_criteria_for_reward_model_2026_03_10.step2_label_with_llm import (
            label_with_llm,
        )

        input_csv = tmp_path / "step1_unique_mirrors_to_label.csv"
        labels_dir = tmp_path / "llm_labels"
        success_csv = tmp_path / "successfully_labeled_flips.csv"

        df = pd.DataFrame(
            [
                {
                    "label_id": "p1::human",
                    "post_id": "p1",
                    "post_primary_key": "p1",
                    "mirror_id": "human",
                    "mirror_text": "mirror one",
                    "original_text": "orig one",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "sample_low_toxicity",
                },
                {
                    "label_id": "p1::llama",
                    "post_id": "p1",
                    "post_primary_key": "p1",
                    "mirror_id": "llama",
                    "mirror_text": "mirror two",
                    "original_text": "orig one",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "sample_low_toxicity",
                },
                {
                    "label_id": "p1::qwen",
                    "post_id": "p1",
                    "post_primary_key": "p1",
                    "mirror_id": "qwen",
                    "mirror_text": "mirror three",
                    "original_text": "orig one",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "sample_low_toxicity",
                },
            ],
        )
        df.to_csv(input_csv, index=False)

        # Pretend one label already succeeded.
        pd.DataFrame({"label_id": ["p1::human"]}).to_csv(success_csv, index=False)

        class DummyLLM:
            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def structured_batch_completion(
                self,
                *,
                prompts: list[str],
                response_model: type[Stage1CriteriaLabel],
                model: str | None = None,
                **kwargs: Any,
            ) -> list[Stage1CriteriaLabel]:
                self.calls.append(list(prompts))
                return [
                    Stage1CriteriaLabel(
                        political_us=1,
                        opinion_not_news=1,
                        complete=1,
                        self_contained=1,
                        target_topic=1,
                        clear_political_stance=1,
                    )
                    for _ in prompts
                ]

        dummy = DummyLLM()

        stats = label_with_llm(
            input_csv=input_csv,
            labels_dir=labels_dir,
            success_csv=success_csv,
            model="gpt-5-nano",
            batch_size=10,
            max_batches=1,
            resume=True,
            llm_service=dummy,  # type: ignore[arg-type]
        )
        assert stats.processed == 2
        assert stats.succeeded == 2

        label_files = sorted(labels_dir.glob("*.csv"))
        assert len(label_files) == 1
        labeled = pd.read_csv(label_files[0])
        assert set(labeled["label_id"].tolist()) == {"p1::llama", "p1::qwen"}

        success = pd.read_csv(success_csv)
        assert success["label_id"].nunique() == len(success)
        assert set(success["label_id"].tolist()) == {"p1::human", "p1::llama", "p1::qwen"}

        # Rerun: should skip everything and not append duplicates.
        stats2 = label_with_llm(
            input_csv=input_csv,
            labels_dir=labels_dir,
            success_csv=success_csv,
            model="gpt-5-nano",
            batch_size=10,
            max_batches=1,
            resume=True,
            llm_service=dummy,  # type: ignore[arg-type]
        )
        assert stats2.processed == 0
        assert stats2.succeeded == 0

        success2 = pd.read_csv(success_csv)
        assert success2["label_id"].nunique() == len(success2)
        assert set(success2["label_id"].tolist()) == {"p1::human", "p1::llama", "p1::qwen"}

        # Prompt integration: each prompt should contain both ORIGINAL and MIRROR texts.
        assert dummy.calls, "Expected at least one LLM call"
        first_call_prompts = dummy.calls[0]
        assert any("ORIGINAL POST" in p and "MIRROR" in p for p in first_call_prompts)
        assert any("orig one" in p for p in first_call_prompts)


class TestStep3FinalizeLabels:
    """Tests for step3_finalize_labels criteria sum and stage1 filter."""

    def test_step3_criteria_sum_and_passes_stage1_filter(self, tmp_path: Path) -> None:
        from experiments.label_criteria_for_reward_model_2026_03_10.step3_finalize_labels import (
            finalize_labels,
        )

        input_csv = tmp_path / "step1_unique_mirrors_to_label.csv"
        labels_dir = tmp_path / "llm_labels"
        output_csv = tmp_path / "step3_all_mirror_criteria_labels.csv"

        inputs = pd.DataFrame(
            [
                {"label_id": "a::human", "mirror_text": "m1", "original_text": "o1"},
                {"label_id": "b::human", "mirror_text": "m2", "original_text": "o2"},
            ]
        )
        inputs.to_csv(input_csv, index=False)

        labels = pd.DataFrame(
            [
                {
                    "label_id": "a::human",
                    "model": "gpt-5-nano",
                    "political_us": 1,
                    "opinion_not_news": 1,
                    "complete": 1,
                    "self_contained": 1,
                    "target_topic": 1,
                    "clear_political_stance": 1,
                },
                {
                    "label_id": "b::human",
                    "model": "gpt-5-nano",
                    "political_us": 1,
                    "opinion_not_news": 1,
                    "complete": 1,
                    "self_contained": 1,
                    "target_topic": 0,
                    "clear_political_stance": 0,
                },
            ]
        )
        labels_dir.mkdir(parents=True, exist_ok=True)
        labels.to_csv(labels_dir / "2026_03_10-00:00:00.csv", index=False)

        out = finalize_labels(
            input_csv=input_csv,
            labels_dir=labels_dir,
            output_csv=output_csv,
            require_all_labeled=True,
        )
        assert set(out["label_id"].tolist()) == {"a::human", "b::human"}
        sums = dict(zip(out["label_id"], out["criteria_sum"], strict=True))
        passes = dict(zip(out["label_id"], out["passes_stage1_filter"], strict=True))

        assert sums["a::human"] == 6
        assert passes["a::human"] == 1
        assert sums["b::human"] == 4
        assert passes["b::human"] == 0
