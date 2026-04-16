from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.store import LEARNER_STATE_FILE, MOCK_LEARNER_ID
from tutorclaw.tools.content import get_chapter_content
from tutorclaw.tools.learners import register_learner


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_full_chapter_returned():
    register_learner(name="Ada")
    result = get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=1)
    assert result["learner_id"] == MOCK_LEARNER_ID
    assert result["chapter"] == 1
    assert result["title"] == "Chapter 1: Variables and Data Types"
    assert result["section"] is None
    assert "variable" in result["content"].lower()


def test_section_extraction():
    register_learner(name="Ada")
    result = get_chapter_content(
        learner_id=MOCK_LEARNER_ID, chapter=1, section="Code Examples"
    )
    assert result["section"] == "Code Examples"
    assert "```python" in result["content"]
    # Should not include the H1 title block
    assert "Chapter 1" not in result["content"]


def test_section_match_is_case_insensitive():
    register_learner(name="Ada")
    result = get_chapter_content(
        learner_id=MOCK_LEARNER_ID, chapter=1, section="code examples"
    )
    assert result["section"] == "Code Examples"


def test_section_partial_match():
    register_learner(name="Ada")
    # "Example 1" is a substring of "Example 1: Assigning variables"
    result = get_chapter_content(
        learner_id=MOCK_LEARNER_ID, chapter=1, section="Example 1"
    )
    assert "Example 1" in result["section"]
    assert result["content"].startswith("###")


def test_section_not_found_raises():
    register_learner(name="Ada")
    with pytest.raises(ValueError, match="section 'nonexistent' not found in chapter 1"):
        get_chapter_content(
            learner_id=MOCK_LEARNER_ID, chapter=1, section="nonexistent"
        )


def test_chapter_not_found_raises():
    # Chapter 4 exists on disk but we remove it temporarily to test the error path.
    # For the free tier, chapters > 5 hit the tier gate first, so we must test
    # file-not-found against a chapter that passes the gate (1–5).
    from tutorclaw.tools.content import _find_chapter_file

    with pytest.raises(ValueError, match="chapter 99 not found"):
        _find_chapter_file(99)


def test_learner_not_found_raises():
    with pytest.raises(ValueError, match="learner not found"):
        get_chapter_content(learner_id="unknown", chapter=1)


def test_free_tier_chapter_within_limit():
    register_learner(name="Ada")
    result = get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=5)
    assert result["chapter"] == 5


def test_free_tier_chapter_beyond_limit_raises():
    register_learner(name="Ada")
    with pytest.raises(ValueError, match="requires a paid plan"):
        get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=6)


def test_tier_gate_error_message_includes_upgrade_url():
    register_learner(name="Ada")
    with pytest.raises(ValueError, match="get_upgrade_url"):
        get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=10)


def test_all_five_chapters_accessible_for_free_tier():
    register_learner(name="Ada")
    for ch in range(1, 6):
        result = get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=ch)
        assert result["chapter"] == ch
        assert result["content"]


def test_exchange_counter_decremented_on_success():
    register_learner(name="Ada")
    before = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]["exchanges_remaining"]
    get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=1)
    after = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]["exchanges_remaining"]
    assert after == before - 1


def test_zero_exchanges_raises_before_content():
    register_learner(name="Ada")
    state = json.loads(LEARNER_STATE_FILE.read_text())
    state[MOCK_LEARNER_ID]["exchanges_remaining"] = 0
    LEARNER_STATE_FILE.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="used all 50 free exchanges"):
        get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=1)


def test_paid_tier_chapter_above_5_allowed(tmp_path, monkeypatch):
    register_learner(name="Ada")
    learners_data = json.loads(store.LEARNERS_FILE.read_text())
    learners_data[MOCK_LEARNER_ID]["tier"] = "paid"
    store.LEARNERS_FILE.write_text(json.dumps(learners_data))
    # Chapter 6 is only blocked for free tier; paid should reach file-not-found.
    with pytest.raises(ValueError, match="chapter 6 not found"):
        get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=6)


def test_paid_tier_no_exchange_decrement():
    register_learner(name="Ada")
    learners_data = json.loads(store.LEARNERS_FILE.read_text())
    learners_data[MOCK_LEARNER_ID]["tier"] = "paid"
    store.LEARNERS_FILE.write_text(json.dumps(learners_data))
    state = json.loads(LEARNER_STATE_FILE.read_text())
    state[MOCK_LEARNER_ID]["exchanges_remaining"] = -1
    LEARNER_STATE_FILE.write_text(json.dumps(state))
    # Should not raise and should not touch the counter.
    with pytest.raises(ValueError, match="chapter 6 not found"):
        get_chapter_content(learner_id=MOCK_LEARNER_ID, chapter=6)
    after = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]["exchanges_remaining"]
    assert after == -1
