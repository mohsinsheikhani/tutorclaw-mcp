from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.store import LEARNER_STATE_FILE, MOCK_LEARNER_ID
from tutorclaw.tools.content import get_exercises
from tutorclaw.tools.learners import register_learner


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_all_exercises_returned_when_no_filter():
    register_learner(name="Ada")
    result = get_exercises(learner_id=MOCK_LEARNER_ID, chapter=1)
    assert result["learner_id"] == MOCK_LEARNER_ID
    assert result["chapter"] == 1
    assert result["filtered_by"] is None
    assert result["total"] == 3
    assert len(result["exercises"]) == 3
    assert all(e["topic"] == "variables" for e in result["exercises"])


def test_all_exercises_returned_when_weak_areas_empty():
    register_learner(name="Ada")
    result = get_exercises(learner_id=MOCK_LEARNER_ID, chapter=1, weak_areas=[])
    assert result["filtered_by"] is None
    assert result["total"] == 3


def test_filter_by_weak_areas():
    register_learner(name="Ada")
    result = get_exercises(
        learner_id=MOCK_LEARNER_ID, chapter=2, weak_areas=["conditionals"]
    )
    assert result["filtered_by"] == ["conditionals"]
    assert result["total"] == 3
    assert all(e["topic"] == "conditionals" for e in result["exercises"])


def test_filter_by_weak_areas_case_insensitive():
    register_learner(name="Ada")
    result = get_exercises(
        learner_id=MOCK_LEARNER_ID, chapter=2, weak_areas=["Conditionals"]
    )
    assert result["total"] == 3


def test_filter_by_non_matching_topic_returns_empty():
    register_learner(name="Ada")
    result = get_exercises(
        learner_id=MOCK_LEARNER_ID, chapter=1, weak_areas=["loops"]
    )
    assert result["total"] == 0
    assert result["exercises"] == []
    assert result["filtered_by"] == ["loops"]


def test_exercise_fields_present():
    register_learner(name="Ada")
    result = get_exercises(learner_id=MOCK_LEARNER_ID, chapter=4)
    for ex in result["exercises"]:
        assert "id" in ex
        assert "question" in ex
        assert "hint" in ex
        assert "topic" in ex
        assert "difficulty" in ex


def test_difficulty_values_valid():
    register_learner(name="Ada")
    result = get_exercises(learner_id=MOCK_LEARNER_ID, chapter=4)
    valid = {"easy", "medium", "hard"}
    for ex in result["exercises"]:
        assert ex["difficulty"] in valid


def test_chapter_not_found_raises():
    register_learner(name="Ada")
    with pytest.raises(ValueError, match="exercises for chapter 3 not found"):
        # Temporarily rename to simulate missing file
        from tutorclaw.tools.content import EXERCISES_DIR
        target = EXERCISES_DIR / "03-exercises.json"
        tmp = target.with_suffix(".bak")
        target.rename(tmp)
        try:
            get_exercises(learner_id=MOCK_LEARNER_ID, chapter=3)
        finally:
            tmp.rename(target)


def test_learner_not_found_raises():
    with pytest.raises(ValueError, match="learner not found"):
        get_exercises(learner_id="nobody", chapter=1)


def test_free_tier_chapter_within_limit():
    register_learner(name="Ada")
    result = get_exercises(learner_id=MOCK_LEARNER_ID, chapter=5)
    assert result["chapter"] == 5


def test_free_tier_chapter_beyond_limit_raises():
    register_learner(name="Ada")
    with pytest.raises(ValueError, match="requires a paid plan"):
        get_exercises(learner_id=MOCK_LEARNER_ID, chapter=6)


def test_tier_gate_upgrade_url_present():
    register_learner(name="Ada")
    with pytest.raises(ValueError, match="get_upgrade_url"):
        get_exercises(learner_id=MOCK_LEARNER_ID, chapter=6)


def test_all_five_chapters_accessible():
    register_learner(name="Ada")
    for ch in range(1, 6):
        result = get_exercises(learner_id=MOCK_LEARNER_ID, chapter=ch)
        assert result["chapter"] == ch
        assert result["total"] > 0


def test_exchange_counter_decremented_on_success():
    register_learner(name="Ada")
    before = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]["exchanges_remaining"]
    get_exercises(learner_id=MOCK_LEARNER_ID, chapter=1)
    after = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]["exchanges_remaining"]
    assert after == before - 1


def test_zero_exchanges_raises():
    register_learner(name="Ada")
    state = json.loads(LEARNER_STATE_FILE.read_text())
    state[MOCK_LEARNER_ID]["exchanges_remaining"] = 0
    LEARNER_STATE_FILE.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="used all 50 free exchanges"):
        get_exercises(learner_id=MOCK_LEARNER_ID, chapter=1)
