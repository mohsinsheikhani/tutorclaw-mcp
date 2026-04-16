from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.store import LEARNER_STATE_FILE, MOCK_LEARNER_ID
from tutorclaw.tools.assessment import assess_response
from tutorclaw.tools.learners import register_learner

CONCEPTS = ["range", "sequence", "loop"]


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    register_learner(name="Ada")
    yield
    store.reset()


# --- strong answer (ratio >= 0.8) ---

def test_strong_answer_positive_delta():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it prints numbers 1 through 5 because range generates a sequence in a loop",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["confidence_delta"] == pytest.approx(0.2)


def test_strong_answer_feedback_mentions_matched():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="range generates a sequence used by the loop",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert "Good answer" in result["feedback"]
    assert "range" in result["feedback"]


def test_strong_predict_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="range generates a sequence used by the loop",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Advance to the run stage."


def test_strong_run_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="range generates a sequence used by the loop",
        primm_stage="run",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Advance to the investigate stage."


def test_strong_investigate_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="range generates a sequence used by the loop",
        primm_stage="investigate",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Move to the next chapter or a harder example."


# --- partial answer (0.3 <= ratio < 0.8) ---

def test_partial_answer_small_positive_delta():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it uses a loop",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["confidence_delta"] == pytest.approx(0.1)


def test_partial_answer_feedback_mentions_unmatched():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it uses a loop",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert "range" in result["feedback"] or "sequence" in result["feedback"]
    assert "loop" in result["feedback"]


def test_partial_predict_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it uses a loop",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Stay in predict and revisit the prediction."


def test_partial_run_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it uses a loop",
        primm_stage="run",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Revisit the prediction before advancing."


def test_partial_investigate_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it uses a loop",
        primm_stage="investigate",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Stay in investigate and explore a modification."


# --- weak answer (ratio < 0.3, non-vague) ---

def test_weak_answer_negative_delta():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it outputs some numbers to the screen",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["confidence_delta"] == pytest.approx(-0.1)


def test_weak_answer_feedback_mentions_concepts():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it outputs some numbers to the screen",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert "range" in result["feedback"]


def test_weak_predict_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it outputs some numbers to the screen",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Stay in predict with a simpler example."


def test_weak_run_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it outputs some numbers to the screen",
        primm_stage="run",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Stay in run and review the output together."


def test_weak_investigate_recommendation():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it outputs some numbers to the screen",
        primm_stage="investigate",
        expected_concepts=CONCEPTS,
    )
    assert result["recommendation"] == "Stay in investigate and explore a modification."


# --- vague answer ---

def test_vague_phrase_idk():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="idk",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["confidence_delta"] == pytest.approx(-0.2)


def test_vague_phrase_stuff():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="it does stuff",
        primm_stage="run",
        expected_concepts=CONCEPTS,
    )
    assert result["confidence_delta"] == pytest.approx(-0.2)


def test_very_short_answer_is_vague():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="yes",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["confidence_delta"] == pytest.approx(-0.2)


def test_vague_feedback_mentions_first_concept():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="idk",
        primm_stage="predict",
        expected_concepts=["range", "sequence"],
    )
    assert "range" in result["feedback"]


# --- case insensitivity ---

def test_concept_match_is_case_insensitive():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="RANGE generates a SEQUENCE for the LOOP",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    assert result["confidence_delta"] == pytest.approx(0.2)


# --- error cases ---

def test_invalid_stage_raises():
    with pytest.raises(ValueError, match="stage must be one of"):
        assess_response(learner_id=MOCK_LEARNER_ID, 
            answer_text="some answer",
            primm_stage="modify",
            expected_concepts=["loops"],
        )


def test_empty_concepts_raises():
    with pytest.raises(ValueError, match="expected_concepts must not be empty"):
        assess_response(learner_id=MOCK_LEARNER_ID, 
            answer_text="some answer",
            primm_stage="predict",
            expected_concepts=[],
        )


# --- single concept ---

def test_single_concept_match_strong():
    result = assess_response(learner_id=MOCK_LEARNER_ID, 
        answer_text="the loop iterates",
        primm_stage="predict",
        expected_concepts=["loop"],
    )
    assert result["confidence_delta"] == pytest.approx(0.2)


def test_single_concept_no_match_weak():
    result = assess_response(learner_id=MOCK_LEARNER_ID,
        answer_text="the function returns a value",
        primm_stage="predict",
        expected_concepts=["loop"],
    )
    assert result["confidence_delta"] == pytest.approx(-0.1)


# --- tier gates ---

def test_exchange_decremented_on_success():
    before = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]["exchanges_remaining"]
    assess_response(
        learner_id=MOCK_LEARNER_ID,
        answer_text="range generates a sequence used by the loop",
        primm_stage="predict",
        expected_concepts=CONCEPTS,
    )
    after = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]["exchanges_remaining"]
    assert after == before - 1


def test_zero_exchanges_raises():
    state = json.loads(LEARNER_STATE_FILE.read_text())
    state[MOCK_LEARNER_ID]["exchanges_remaining"] = 0
    LEARNER_STATE_FILE.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="used all 50 free exchanges"):
        assess_response(
            learner_id=MOCK_LEARNER_ID,
            answer_text="range loop sequence",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )


def test_unknown_learner_raises():
    with pytest.raises(ValueError, match="learner not found"):
        assess_response(
            learner_id="nobody",
            answer_text="range loop sequence",
            primm_stage="predict",
            expected_concepts=CONCEPTS,
        )
