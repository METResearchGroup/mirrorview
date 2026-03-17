"""Pytest coverage for the generate flips experiment pipeline."""

# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.schemas import FlipResponse


class TestStep1BuildGenerationDataset:
    """Tests for step1 dedupe from many mirror rows to one row per post_id."""

    def test_step1_dedupe_to_one_row_per_post_id(self, tmp_path: Path) -> None:
        from experiments.generate_flips_2026_03_12.step1_build_generation_dataset import (
            build_generation_dataset,
        )

        input_csv = tmp_path / "step1_unique_mirrors_to_label.csv"
        output_csv = tmp_path / "step1_posts_to_flip.csv"

        # Simulate 3 mirrors per post (same original_text for each post)
        df = pd.DataFrame(
            [
                {"post_id": "p1", "original_text": "orig one", "mirror_id": "human"},
                {"post_id": "p1", "original_text": "orig one", "mirror_id": "llama"},
                {"post_id": "p1", "original_text": "orig one", "mirror_id": "qwen"},
                {"post_id": "p2", "original_text": "orig two", "mirror_id": "human"},
                {"post_id": "p2", "original_text": "orig two", "mirror_id": "llama"},
            ]
        )
        df.to_csv(input_csv, index=False)

        out = build_generation_dataset(input_csv=input_csv, output_csv=output_csv)

        assert len(out) == 2
        assert out["post_id"].nunique() == 2
        assert set(out["post_id"].tolist()) == {"p1", "p2"}
        assert out.loc[out["post_id"] == "p1", "original_text"].iloc[0] == "orig one"
        assert out.loc[out["post_id"] == "p2", "original_text"].iloc[0] == "orig two"

        written = pd.read_csv(output_csv)
        assert len(written) == 2
        assert written["post_id"].is_monotonic_increasing or list(written["post_id"]) == sorted(
            written["post_id"].tolist()
        )

    def test_step1_raises_when_post_id_has_multiple_original_texts(self, tmp_path: Path) -> None:
        from experiments.generate_flips_2026_03_12.step1_build_generation_dataset import (
            build_generation_dataset,
        )

        input_csv = tmp_path / "bad_input.csv"
        output_csv = tmp_path / "out.csv"

        df = pd.DataFrame(
            [
                {"post_id": "p1", "original_text": "orig one"},
                {"post_id": "p1", "original_text": "orig two"},
            ]
        )
        df.to_csv(input_csv, index=False)

        import pytest

        with pytest.raises(ValueError, match="multiple original_text"):
            build_generation_dataset(input_csv=input_csv, output_csv=output_csv)


class TestStep2GenerateWithLlm:
    """Tests for step2 resume, output writing, and metadata generation."""

    def test_step2_skip_resume_appends_without_duplicates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import experiments.generate_flips_2026_03_12.step2_generate_with_llm as step2_module

        input_csv = tmp_path / "step1_posts_to_flip.csv"
        flips_dir = tmp_path / "generated_flips"
        existing_run_dir = flips_dir / "2026_03_11-18:00:00"
        existing_run_dir.mkdir(parents=True)

        df = pd.DataFrame(
            [
                {"post_id": "p1", "original_text": "orig one"},
                {"post_id": "p2", "original_text": "orig two"},
                {"post_id": "p3", "original_text": "orig three"},
            ]
        )
        df.to_csv(input_csv, index=False)

        pd.DataFrame(
            [
                {
                    "post_id": "p1",
                    "original_text": "orig one",
                    "flipped_text": "already flipped",
                    "explanation": "existing",
                    "model": "gpt-5-nano",
                }
            ]
        ).to_csv(existing_run_dir / "existing_batch_1.csv", index=False)

        class DummyLLM:
            model = "gpt-5-nano"

            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def structured_batch_completion(
                self,
                *,
                prompts: list[str],
                response_model: type[FlipResponse],
                model: str | None = None,
                **kwargs: Any,
            ) -> list[FlipResponse]:
                self.calls.append(list(prompts))
                return [
                    FlipResponse(flipped_text=f"flipped {i}", explanation="because")
                    for i in range(len(prompts))
                ]

        dummy = DummyLLM()

        def fake_get_current_timestamp() -> str:
            return "2026_03_12-19:31:32"

        def fake_get_llm_service(*, model: str | None = None, verbose: bool = False) -> Any:
            assert model == "gpt-5-nano"
            assert verbose is False
            return dummy

        monkeypatch.setattr(step2_module, "get_current_timestamp", fake_get_current_timestamp)
        monkeypatch.setattr(step2_module, "get_llm_service", fake_get_llm_service)

        stats = step2_module.run_generate_step(
            input_csv=input_csv,
            flips_dir=flips_dir,
            model="gpt-5-nano",
            batch_size=10,
            max_batches=1,
            resume=True,
        )
        assert stats.total_attempted == 2
        assert stats.succeeded == 2

        run_dir = flips_dir / "2026_03_12-19:31:32"
        flip_files = sorted(run_dir.glob("*_batch_*.csv"))
        assert len(flip_files) == 1
        generated = pd.read_csv(flip_files[0])
        assert set(generated["post_id"].tolist()) == {"p2", "p3"}
        assert "flipped_text" in generated.columns
        assert "explanation" in generated.columns
        assert "model" in generated.columns

        # Rerun: should skip everything and not append duplicates.
        stats2 = step2_module.run_generate_step(
            input_csv=input_csv,
            flips_dir=flips_dir,
            model="gpt-5-nano",
            batch_size=10,
            max_batches=1,
            resume=True,
        )
        assert stats2.total_attempted == 0
        assert stats2.succeeded == 0

        # Prompt integration: each prompt should contain FLIP_PROMPT and original text.
        assert len(dummy.calls) == 1, "Expected exactly one LLM call across both runs"
        first_call_prompts = dummy.calls[0]
        assert any("Post to flip" in p for p in first_call_prompts)
        assert any("orig two" in p for p in first_call_prompts)

    def test_step2_writes_metadata_json_with_git_hash_and_provenance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import experiments.generate_flips_2026_03_12.step2_generate_with_llm as step2_module

        input_csv = tmp_path / "step1_posts_to_flip.csv"
        flips_dir = tmp_path / "generated_flips"

        df = pd.DataFrame(
            [
                {"post_id": "p1", "original_text": "orig one"},
            ]
        )
        df.to_csv(input_csv, index=False)

        class DummyLLM:
            model = "gpt-5-nano"

            def structured_batch_completion(
                self,
                *,
                prompts: list[str],
                response_model: type[FlipResponse],
                model: str | None = None,
                **kwargs: Any,
            ) -> list[FlipResponse]:
                return [FlipResponse(flipped_text="flipped", explanation="because")]

        def fake_get_current_timestamp() -> str:
            return "2026_03_12-19:31:32"

        def fake_get_git_hash() -> str:
            return "abc123def456"

        def fake_get_llm_service(*, model: str | None = None, verbose: bool = False) -> Any:
            assert model == "gpt-5-nano"
            assert verbose is False
            return DummyLLM()

        monkeypatch.setattr(step2_module, "get_current_timestamp", fake_get_current_timestamp)
        monkeypatch.setattr(step2_module, "get_git_hash", fake_get_git_hash)
        monkeypatch.setattr(step2_module, "get_llm_service", fake_get_llm_service)

        step2_module.run_generate_step(
            input_csv=input_csv,
            flips_dir=flips_dir,
            model="gpt-5-nano",
            batch_size=10,
            max_batches=1,
            resume=True,
        )

        metadata_path = flips_dir / "2026_03_12-19:31:32" / "metadata.json"
        assert metadata_path.exists()
        with metadata_path.open() as f:
            meta = json.load(f)

        assert meta["git_hash"] == "abc123def456"
        assert "completed_at" in meta
        assert meta["model"] == "gpt-5-nano"
        assert meta["total_attempted"] == 1
        assert meta["succeeded"] == 1
        assert meta["failed"] == 0
        assert meta["input_csv"] == str(input_csv)
        assert meta["output_csv_dir"] == str(flips_dir / "2026_03_12-19:31:32")


class TestStep3FinalizeFlips:
    """Tests for step3 finalize: concatenates flip CSVs, adds timestamp, outputs post_id, original_text, flipped_text, timestamp."""

    def test_step3_concatenates_and_adds_timestamp(self, tmp_path: Path) -> None:
        from experiments.generate_flips_2026_03_12.step3_finalize_flips import (
            finalize_flips,
        )

        flips_dir = tmp_path / "generated_flips"
        flips_dir.mkdir(parents=True)
        output_csv = tmp_path / "step3_finalized_flips.csv"

        # Simulate two run files
        run1 = pd.DataFrame(
            [
                {
                    "post_id": "p1",
                    "original_text": "orig one",
                    "flipped_text": "flipped one",
                    "explanation": "e1",
                    "model": "gpt-5-nano",
                },
            ]
        )
        run2 = pd.DataFrame(
            [
                {
                    "post_id": "p2",
                    "original_text": "orig two",
                    "flipped_text": "flipped two",
                    "explanation": "e2",
                    "model": "gpt-5-nano",
                },
            ]
        )
        run1.to_csv(flips_dir / "2026_03_12-19:31:32.csv", index=False)
        run2.to_csv(flips_dir / "2026_03_12-19:32:12.csv", index=False)

        out = finalize_flips(flips_dir=flips_dir, output_csv=output_csv)

        assert len(out) == 2
        assert list(out.columns) == ["post_id", "original_text", "flipped_text", "timestamp"]
        assert set(out["post_id"].tolist()) == {"p1", "p2"}
        assert out.loc[out["post_id"] == "p1", "timestamp"].iloc[0] == "2026_03_12-19:31:32"
        assert out.loc[out["post_id"] == "p2", "timestamp"].iloc[0] == "2026_03_12-19:32:12"
        assert out.loc[out["post_id"] == "p1", "flipped_text"].iloc[0] == "flipped one"

        written = pd.read_csv(output_csv)
        assert len(written) == 2
        assert "timestamp" in written.columns
