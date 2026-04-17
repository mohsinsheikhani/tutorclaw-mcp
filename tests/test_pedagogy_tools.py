"""Tests for generate_guidance and assess_response."""

from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.tools.assessment import assess_response
from tutorclaw.tools.guidance import generate_guidance

from .conftest import SAMPLE_CHAPTER_MD, _seed_learner

NO_CODE_CONTENT = "# Chapter with no code\n\nJust text here."

CONCEPTS = ["range", "sequence", "loop"]


# =========================================================================
# generate_guidance
# =========================================================================


class TestGenerateGuidanceValid:
    def test_predict_returns_code_without_output(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="predict", confidence=0.5, chapter_content=SAMPLE_CHAPTER_MD,
        )
        assert result["stage"] == "predict"
        assert "```python" in result["content"]
        assert "**Output:**" not in result["content"]
        assert "PREDICT" in result["system_prompt_addition"]

    def test_run_returns_code_and_output(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="run", confidence=0.5, chapter_content=SAMPLE_CHAPTER_MD,
        )
        assert "```python" in result["content"]
        assert "**Output:**" in result["content"]
        assert "RUN" in result["system_prompt_addition"]

    def test_investigate_returns_code_and_output(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="investigate", confidence=0.5, chapter_content=SAMPLE_CHAPTER_MD,
        )
        assert "```python" in result["content"]
        assert "INVESTIGATE" in result["system_prompt_addition"]

    def test_low_confidence_adds_encouraging(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="predict", confidence=0.2, chapter_content=SAMPLE_CHAPTER_MD,
        )
        assert "encouraging" in result["system_prompt_addition"].lower()

    def test_high_confidence_adds_challenge(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="predict", confidence=0.8, chapter_content=SAMPLE_CHAPTER_MD,
        )
        assert "challenge" in result["system_prompt_addition"].lower()

    def test_mid_confidence_neutral(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="predict", confidence=0.5, chapter_content=SAMPLE_CHAPTER_MD,
        )
        prompt = result["system_prompt_addition"].lower()
        assert "encouraging" not in prompt
        assert "challenge" not in prompt

    def test_boundary_0_4_is_neutral(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="run", confidence=0.4, chapter_content=SAMPLE_CHAPTER_MD,
        )
        prompt = result["system_prompt_addition"].lower()
        assert "encouraging" not in prompt
        assert "challenge" not in prompt

    def test_boundary_0_7_is_challenge(self, isolated_store):
        lid = _seed_learner()
        result = generate_guidance(
            learner_id=lid, stage="run", confidence=0.7, chapter_content=SAMPLE_CHAPTER_MD,
        )
        assert "challenge" in result["system_prompt_addition"].lower()

    def test_run_without_output_block_returns_code_only(self, isolated_store):
        lid = _seed_learner()
        content_no_output = "# Ch\n\n```python\nprint('hi')\n```\n"
        result = generate_guidance(
            learner_id=lid, stage="run", confidence=0.5, chapter_content=content_no_output,
        )
        assert "```python" in result["content"]
        assert "**Output:**" not in result["content"]


class TestGenerateGuidanceInvalid:
    def test_invalid_stage_raises(self, isolated_store):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="stage must be one of"):
            generate_guidance(
                learner_id=lid, stage="modify", confidence=0.5, chapter_content=SAMPLE_CHAPTER_MD,
            )

    def test_no_code_block_raises(self, isolated_store):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="chapter content contains no code block"):
            generate_guidance(
                learner_id=lid, stage="predict", confidence=0.5, chapter_content=NO_CODE_CONTENT,
            )

    def test_unknown_learner_raises(self, isolated_store):
        with pytest.raises(ValueError, match="learner not found"):
            generate_guidance(
                learner_id="nobody", stage="predict", confidence=0.5,
                chapter_content=SAMPLE_CHAPTER_MD,
            )

    def test_zero_exchanges_raises(self, isolated_store):
        lid = _seed_learner(exchanges=0)
        with pytest.raises(ValueError, match="used all 50 free exchanges"):
            generate_guidance(
                learner_id=lid, stage="predict", confidence=0.5,
                chapter_content=SAMPLE_CHAPTER_MD,
            )


# =========================================================================
# assess_response
# =========================================================================


class TestAssessResponseValid:
    # --- strong (ratio >= 0.8) ---

    def test_strong_answer_positive_delta(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="it prints numbers because range generates a sequence in a loop",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert result["confidence_delta"] == pytest.approx(0.2)

    def test_strong_feedback_mentions_matched(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="range generates a sequence used by the loop",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert "Good answer" in result["feedback"]

    def test_strong_predict_advances_to_run(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="range generates a sequence used by the loop",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert result["recommendation"] == "Advance to the run stage."

    def test_strong_run_advances_to_investigate(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="range generates a sequence used by the loop",
            primm_stage="run",
            expected_concepts=CONCEPTS,
        )
        assert result["recommendation"] == "Advance to the investigate stage."

    def test_strong_investigate_advances_to_next_chapter(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="range generates a sequence used by the loop",
            primm_stage="investigate",
            expected_concepts=CONCEPTS,
        )
        assert result["recommendation"] == "Move to the next chapter or a harder example."

    # --- partial (0.3 <= ratio < 0.8) ---

    def test_partial_answer_small_delta(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="it uses a loop to iterate",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert result["confidence_delta"] == pytest.approx(0.1)

    def test_partial_feedback_mentions_unmatched(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="it uses a loop to iterate",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert "range" in result["feedback"] or "sequence" in result["feedback"]

    # --- weak (ratio < 0.3, non-vague) ---

    def test_weak_answer_negative_delta(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="it outputs some numbers to the screen",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert result["confidence_delta"] == pytest.approx(-0.1)

    def test_weak_feedback_lists_concepts(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="it outputs some numbers to the screen",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert "range" in result["feedback"]

    # --- vague ---

    def test_vague_idk_large_negative_delta(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid, answer_text="idk",
            primm_stage="predict", expected_concepts=CONCEPTS,
        )
        assert result["confidence_delta"] == pytest.approx(-0.2)

    def test_vague_short_answer(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid, answer_text="yes",
            primm_stage="predict", expected_concepts=CONCEPTS,
        )
        assert result["confidence_delta"] == pytest.approx(-0.2)

    def test_vague_stuff_phrase(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid, answer_text="it does stuff",
            primm_stage="run", expected_concepts=CONCEPTS,
        )
        assert result["confidence_delta"] == pytest.approx(-0.2)

    # --- case insensitivity ---

    def test_concept_match_case_insensitive(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid,
            answer_text="RANGE generates a SEQUENCE for the LOOP",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
        assert result["confidence_delta"] == pytest.approx(0.2)

    # --- single concept ---

    def test_single_concept_match_strong(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid, answer_text="the loop iterates over values",
            primm_stage="predict", expected_concepts=["loop"],
        )
        assert result["confidence_delta"] == pytest.approx(0.2)

    def test_single_concept_no_match_weak(self, isolated_store):
        lid = _seed_learner()
        result = assess_response(
            learner_id=lid, answer_text="the function returns a value",
            primm_stage="predict", expected_concepts=["loop"],
        )
        assert result["confidence_delta"] == pytest.approx(-0.1)


class TestAssessResponseInvalid:
    def test_invalid_stage_raises(self, isolated_store):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="stage must be one of"):
            assess_response(
                learner_id=lid, answer_text="answer",
                primm_stage="modify", expected_concepts=["loop"],
            )

    def test_empty_concepts_raises(self, isolated_store):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="expected_concepts must not be empty"):
            assess_response(
                learner_id=lid, answer_text="answer",
                primm_stage="predict", expected_concepts=[],
            )

    def test_unknown_learner_raises(self, isolated_store):
        with pytest.raises(ValueError, match="learner not found"):
            assess_response(
                learner_id="nobody", answer_text="answer",
                primm_stage="predict", expected_concepts=["loop"],
            )

    def test_zero_exchanges_raises(self, isolated_store):
        lid = _seed_learner(exchanges=0)
        with pytest.raises(ValueError, match="used all 50 free exchanges"):
            assess_response(
                learner_id=lid, answer_text="range loop sequence",
                primm_stage="predict", expected_concepts=CONCEPTS,
            )
