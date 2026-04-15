from __future__ import annotations

import pytest

from tutorclaw import store
from tutorclaw.store import MOCK_API_KEY, MOCK_LEARNER_ID
from tutorclaw.tools.learners import get_learner_state, register_learner


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_get_state_after_registration():
    register_learner(name="Ada")
    result = get_learner_state(learner_id=MOCK_LEARNER_ID)
    assert result["learner_id"] == MOCK_LEARNER_ID
    assert result["chapter"] == 1
    assert result["stage"] == "predict"
    assert result["confidence"] == 0.5
    assert result["tier"] == "free"
    assert result["exchanges_remaining"] == 50
    assert result["weak_areas"] == []


def test_get_state_learner_not_found():
    with pytest.raises(ValueError, match="learner not found"):
        get_learner_state(learner_id="nonexistent")


def test_get_state_no_state_entry():
    """Learner exists but state file was wiped."""
    register_learner(name="Ada")
    # Remove only the state file
    if store.LEARNER_STATE_FILE.exists():
        store.LEARNER_STATE_FILE.unlink()
    with pytest.raises(ValueError, match="learner state not found"):
        get_learner_state(learner_id=MOCK_LEARNER_ID)


def test_get_state_returns_tier_from_learner_record():
    """Tier comes from learners.json, not learner_state.json."""
    register_learner(name="Ada")
    result = get_learner_state(learner_id=MOCK_LEARNER_ID)
    assert result["tier"] == "free"


def test_state_persisted_to_disk():
    register_learner(name="Ada")
    assert store.LEARNER_STATE_FILE.exists()
    data = store._load_state()
    assert MOCK_LEARNER_ID in data
    assert data[MOCK_LEARNER_ID]["chapter"] == 1
    assert data[MOCK_LEARNER_ID]["stage"] == "predict"


def test_reset_removes_state_file():
    register_learner(name="Ada")
    assert store.LEARNER_STATE_FILE.exists()
    store.reset()
    assert not store.LEARNER_STATE_FILE.exists()
