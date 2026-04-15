from __future__ import annotations

import pytest

from tutorclaw import store
from tutorclaw.store import MOCK_LEARNER_ID
from tutorclaw.tools.learners import register_learner, update_progress


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_basic_update():
    register_learner(name="Ada")
    result = update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=2, stage="run", confidence_delta=0.1
    )
    assert result["learner_id"] == MOCK_LEARNER_ID
    assert result["chapter"] == 2
    assert result["stage"] == "run"
    assert result["confidence"] == pytest.approx(0.6)
    assert result["tier"] == "free"
    assert result["exchanges_remaining"] == 50
    assert result["weak_areas"] == []


def test_confidence_clamp_upper():
    register_learner(name="Ada")
    result = update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=1, stage="predict", confidence_delta=0.9
    )
    assert result["confidence"] == pytest.approx(1.0)


def test_confidence_clamp_lower():
    register_learner(name="Ada")
    result = update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=1, stage="predict", confidence_delta=-0.8
    )
    assert result["confidence"] == pytest.approx(0.0)


def test_negative_delta():
    register_learner(name="Ada")
    result = update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=1, stage="predict", confidence_delta=-0.2
    )
    assert result["confidence"] == pytest.approx(0.3)


def test_learner_not_found():
    with pytest.raises(ValueError, match="learner not found"):
        update_progress(
            learner_id="nonexistent", chapter=1, stage="predict", confidence_delta=0.0
        )


def test_invalid_stage():
    register_learner(name="Ada")
    with pytest.raises(ValueError, match="stage must be one of"):
        update_progress(
            learner_id=MOCK_LEARNER_ID, chapter=1, stage="invalid", confidence_delta=0.0
        )


def test_creates_default_state_if_missing():
    """If learner exists but state file was wiped, update creates default then applies."""
    register_learner(name="Ada")
    if store.LEARNER_STATE_FILE.exists():
        store.LEARNER_STATE_FILE.unlink()
    result = update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=3, stage="modify", confidence_delta=0.2
    )
    assert result["chapter"] == 3
    assert result["stage"] == "modify"
    assert result["confidence"] == pytest.approx(0.7)


def test_successive_updates():
    register_learner(name="Ada")
    update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=1, stage="run", confidence_delta=0.1
    )
    result = update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=1, stage="investigate", confidence_delta=0.1
    )
    assert result["confidence"] == pytest.approx(0.7)
    assert result["stage"] == "investigate"


def test_all_valid_stages():
    register_learner(name="Ada")
    for stage in ("predict", "run", "investigate", "modify", "make"):
        result = update_progress(
            learner_id=MOCK_LEARNER_ID, chapter=1, stage=stage, confidence_delta=0.0
        )
        assert result["stage"] == stage


def test_state_persisted_to_disk():
    register_learner(name="Ada")
    update_progress(
        learner_id=MOCK_LEARNER_ID, chapter=4, stage="make", confidence_delta=0.3
    )
    data = store._load_state()
    assert data[MOCK_LEARNER_ID]["chapter"] == 4
    assert data[MOCK_LEARNER_ID]["stage"] == "make"
    assert data[MOCK_LEARNER_ID]["confidence"] == pytest.approx(0.8)
