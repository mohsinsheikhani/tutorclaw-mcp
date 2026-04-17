"""Tests for get_chapter_content and get_exercises."""

from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.tools.content import get_chapter_content, get_exercises

from .conftest import _seed_learner


# =========================================================================
# get_chapter_content
# =========================================================================


class TestGetChapterContentValid:
    def test_full_chapter_returned(self, isolated_content):
        lid = _seed_learner()
        result = get_chapter_content(learner_id=lid, chapter=1)
        assert result["learner_id"] == lid
        assert result["chapter"] == 1
        assert result["title"] == "Chapter 1: Variables and Data Types"
        assert result["section"] is None
        assert "variable" in result["content"].lower()

    def test_section_extraction(self, isolated_content):
        lid = _seed_learner()
        result = get_chapter_content(learner_id=lid, chapter=1, section="Code Examples")
        assert result["section"] == "Code Examples"
        assert "```python" in result["content"]

    def test_section_match_case_insensitive(self, isolated_content):
        lid = _seed_learner()
        result = get_chapter_content(learner_id=lid, chapter=1, section="code examples")
        assert result["section"] == "Code Examples"

    def test_section_partial_match(self, isolated_content):
        lid = _seed_learner()
        result = get_chapter_content(learner_id=lid, chapter=1, section="Example 1")
        assert "Example 1" in result["section"]


class TestGetChapterContentInvalid:
    def test_unknown_learner_raises(self, isolated_content):
        with pytest.raises(ValueError, match="learner not found"):
            get_chapter_content(learner_id="nobody", chapter=1)

    def test_chapter_not_found_raises(self, isolated_content):
        lid = _seed_learner(tier="paid", exchanges=-1)
        with pytest.raises(ValueError, match="chapter 99 not found"):
            get_chapter_content(learner_id=lid, chapter=99)

    def test_section_not_found_raises(self, isolated_content):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="section 'nonexistent' not found"):
            get_chapter_content(learner_id=lid, chapter=1, section="nonexistent")


class TestGetChapterContentTierGating:
    def test_free_tier_chapter_within_limit(self, isolated_content):
        lid = _seed_learner()
        result = get_chapter_content(learner_id=lid, chapter=1)
        assert result["chapter"] == 1

    def test_free_tier_chapter_beyond_limit_blocked(self, isolated_content):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="requires a paid plan"):
            get_chapter_content(learner_id=lid, chapter=6)

    def test_free_tier_gate_mentions_upgrade(self, isolated_content):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="get_upgrade_url"):
            get_chapter_content(learner_id=lid, chapter=6)

    def test_paid_tier_accesses_premium_chapter(self, isolated_content):
        lid = _seed_learner(tier="paid", exchanges=-1)
        result = get_chapter_content(learner_id=lid, chapter=6)
        assert result["chapter"] == 6
        assert "Dictionaries" in result["title"]

    def test_free_tier_exchange_decremented(self, isolated_content):
        lid = _seed_learner(exchanges=50)
        get_chapter_content(learner_id=lid, chapter=1)
        state = json.loads(store.LEARNER_STATE_FILE.read_text())
        assert state[lid]["exchanges_remaining"] == 49

    def test_free_tier_zero_exchanges_blocked(self, isolated_content):
        lid = _seed_learner(exchanges=0)
        with pytest.raises(ValueError, match="used all 50 free exchanges"):
            get_chapter_content(learner_id=lid, chapter=1)

    def test_paid_tier_no_exchange_decrement(self, isolated_content):
        lid = _seed_learner(tier="paid", exchanges=-1)
        get_chapter_content(learner_id=lid, chapter=6)
        state = json.loads(store.LEARNER_STATE_FILE.read_text())
        assert state[lid]["exchanges_remaining"] == -1


# =========================================================================
# get_exercises
# =========================================================================


class TestGetExercisesValid:
    def test_all_exercises_returned_no_filter(self, isolated_content):
        lid = _seed_learner()
        result = get_exercises(learner_id=lid, chapter=1)
        assert result["learner_id"] == lid
        assert result["chapter"] == 1
        assert result["filtered_by"] is None
        assert result["total"] == 2
        assert len(result["exercises"]) == 2

    def test_empty_weak_areas_returns_all(self, isolated_content):
        lid = _seed_learner()
        result = get_exercises(learner_id=lid, chapter=1, weak_areas=[])
        assert result["filtered_by"] is None
        assert result["total"] == 2

    def test_filter_by_matching_topic(self, isolated_content):
        lid = _seed_learner()
        result = get_exercises(learner_id=lid, chapter=1, weak_areas=["variables"])
        assert result["filtered_by"] == ["variables"]
        assert result["total"] == 2

    def test_filter_case_insensitive(self, isolated_content):
        lid = _seed_learner()
        result = get_exercises(learner_id=lid, chapter=1, weak_areas=["Variables"])
        assert result["total"] == 2

    def test_filter_no_match_returns_empty(self, isolated_content):
        lid = _seed_learner()
        result = get_exercises(learner_id=lid, chapter=1, weak_areas=["loops"])
        assert result["total"] == 0
        assert result["exercises"] == []

    def test_exercise_fields_present(self, isolated_content):
        lid = _seed_learner()
        result = get_exercises(learner_id=lid, chapter=1)
        for ex in result["exercises"]:
            assert "id" in ex
            assert "question" in ex
            assert "hint" in ex
            assert "topic" in ex
            assert "difficulty" in ex


class TestGetExercisesInvalid:
    def test_unknown_learner_raises(self, isolated_content):
        with pytest.raises(ValueError, match="learner not found"):
            get_exercises(learner_id="nobody", chapter=1)

    def test_chapter_not_found_raises(self, isolated_content):
        lid = _seed_learner(tier="paid", exchanges=-1)
        with pytest.raises(ValueError, match="exercises for chapter 99 not found"):
            get_exercises(learner_id=lid, chapter=99)


class TestGetExercisesTierGating:
    def test_free_tier_within_limit(self, isolated_content):
        lid = _seed_learner()
        result = get_exercises(learner_id=lid, chapter=1)
        assert result["chapter"] == 1

    def test_free_tier_beyond_limit_blocked(self, isolated_content):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="requires a paid plan"):
            get_exercises(learner_id=lid, chapter=6)

    def test_free_tier_exchange_decremented(self, isolated_content):
        lid = _seed_learner(exchanges=50)
        get_exercises(learner_id=lid, chapter=1)
        state = json.loads(store.LEARNER_STATE_FILE.read_text())
        assert state[lid]["exchanges_remaining"] == 49

    def test_free_tier_zero_exchanges_blocked(self, isolated_content):
        lid = _seed_learner(exchanges=0)
        with pytest.raises(ValueError, match="used all 50 free exchanges"):
            get_exercises(learner_id=lid, chapter=1)

    def test_paid_tier_accesses_premium_exercises(self, isolated_content):
        """Paid tier passes the gate but hits file-not-found (no exercise file for ch6)."""
        lid = _seed_learner(tier="paid", exchanges=-1)
        with pytest.raises(ValueError, match="exercises for chapter 6 not found"):
            get_exercises(learner_id=lid, chapter=6)
