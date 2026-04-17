"""Tests for register_learner, get_learner_state, and update_progress."""

from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.store import MOCK_LEARNER_ID
from tutorclaw.tools.learners import get_learner_state, register_learner, update_progress

from .conftest import _seed_learner


# =========================================================================
# register_learner
# =========================================================================


class TestRegisterLearnerValid:
    def test_returns_expected_fields(self, isolated_store):
        result = register_learner(name="Ada")
        assert result["learner_id"] == MOCK_LEARNER_ID
        assert result["name"] == "Ada"
        assert result["email"] is None
        assert result["tier"] == "free"
        assert result["api_key"]
        assert "Ada" in result["welcome_message"]
        assert result["created_at"].endswith("Z")

    def test_with_email(self, isolated_store):
        result = register_learner(name="Ada", email="ada@example.com")
        assert result["email"] == "ada@example.com"

    def test_trims_whitespace_in_name(self, isolated_store):
        result = register_learner(name="  Grace  ")
        assert result["name"] == "Grace"

    def test_empty_email_treated_as_none(self, isolated_store):
        result = register_learner(name="Ada", email="   ")
        assert result["email"] is None

    def test_idempotent_second_call_returns_original(self, isolated_store):
        first = register_learner(name="Ada")
        second = register_learner(name="Bob")
        assert first["learner_id"] == second["learner_id"]
        assert second["name"] == "Ada"


class TestRegisterLearnerInvalid:
    def test_empty_name_raises(self, isolated_store):
        with pytest.raises(ValueError, match="name must not be empty"):
            register_learner(name="   ")

    def test_invalid_email_raises(self, isolated_store):
        with pytest.raises(ValueError, match="email is not a valid address"):
            register_learner(name="Ada", email="not-an-email")

    def test_email_too_long_raises(self, isolated_store):
        with pytest.raises(ValueError, match="email must be 254 characters or fewer"):
            register_learner(name="Ada", email="a" * 250 + "@b.co")


class TestRegisterLearnerPersistence:
    def test_learner_written_to_disk(self, isolated_store):
        register_learner(name="Ada", email="ada@example.com")
        data = json.loads(store.LEARNERS_FILE.read_text())
        assert MOCK_LEARNER_ID in data
        assert data[MOCK_LEARNER_ID]["name"] == "Ada"
        assert data[MOCK_LEARNER_ID]["email"] == "ada@example.com"
        assert data[MOCK_LEARNER_ID]["tier"] == "free"

    def test_state_file_created_on_register(self, isolated_store):
        register_learner(name="Ada")
        data = json.loads(store.LEARNER_STATE_FILE.read_text())
        assert MOCK_LEARNER_ID in data
        assert data[MOCK_LEARNER_ID]["chapter"] == 1
        assert data[MOCK_LEARNER_ID]["stage"] == "predict"

    def test_reload_from_disk_matches(self, isolated_store):
        register_learner(name="Ada")
        raw = json.loads(store.LEARNERS_FILE.read_text())
        reloaded = store._load()
        assert raw == reloaded


# =========================================================================
# get_learner_state
# =========================================================================


class TestGetLearnerStateValid:
    def test_default_state_after_registration(self, isolated_store):
        lid = _seed_learner()
        result = get_learner_state(learner_id=lid)
        assert result["learner_id"] == lid
        assert result["chapter"] == 1
        assert result["stage"] == "predict"
        assert result["confidence"] == 0.5
        assert result["tier"] == "free"
        assert result["exchanges_remaining"] == 50
        assert result["weak_areas"] == []

    def test_tier_comes_from_learner_record(self, isolated_store):
        lid = _seed_learner(tier="paid", exchanges=-1)
        result = get_learner_state(learner_id=lid)
        assert result["tier"] == "paid"


class TestGetLearnerStateInvalid:
    def test_unknown_learner_raises(self, isolated_store):
        with pytest.raises(ValueError, match="learner not found"):
            get_learner_state(learner_id="nonexistent")

    def test_missing_state_file_raises(self, isolated_store):
        lid = _seed_learner()
        store.LEARNER_STATE_FILE.unlink()
        with pytest.raises(ValueError, match="learner state not found"):
            get_learner_state(learner_id=lid)


# =========================================================================
# update_progress
# =========================================================================


class TestUpdateProgressValid:
    def test_basic_advance(self, isolated_store):
        lid = _seed_learner()
        result = update_progress(learner_id=lid, chapter=2, stage="run", confidence_delta=0.1)
        assert result["chapter"] == 2
        assert result["stage"] == "run"
        assert result["confidence"] == pytest.approx(0.6)

    def test_confidence_clamps_to_one(self, isolated_store):
        lid = _seed_learner()
        result = update_progress(learner_id=lid, chapter=1, stage="predict", confidence_delta=0.9)
        assert result["confidence"] == pytest.approx(1.0)

    def test_confidence_clamps_to_zero(self, isolated_store):
        lid = _seed_learner()
        result = update_progress(learner_id=lid, chapter=1, stage="predict", confidence_delta=-0.8)
        assert result["confidence"] == pytest.approx(0.0)

    def test_negative_delta(self, isolated_store):
        lid = _seed_learner()
        result = update_progress(learner_id=lid, chapter=1, stage="predict", confidence_delta=-0.2)
        assert result["confidence"] == pytest.approx(0.3)

    def test_successive_updates_accumulate(self, isolated_store):
        lid = _seed_learner()
        update_progress(learner_id=lid, chapter=1, stage="run", confidence_delta=0.1)
        result = update_progress(learner_id=lid, chapter=1, stage="investigate", confidence_delta=0.1)
        assert result["confidence"] == pytest.approx(0.7)
        assert result["stage"] == "investigate"

    def test_all_valid_stages_accepted(self, isolated_store):
        lid = _seed_learner()
        for stage in ("predict", "run", "investigate", "modify", "make"):
            result = update_progress(learner_id=lid, chapter=1, stage=stage, confidence_delta=0.0)
            assert result["stage"] == stage


class TestUpdateProgressInvalid:
    def test_unknown_learner_raises(self, isolated_store):
        with pytest.raises(ValueError, match="learner not found"):
            update_progress(learner_id="nobody", chapter=1, stage="predict", confidence_delta=0.0)

    def test_invalid_stage_raises(self, isolated_store):
        lid = _seed_learner()
        with pytest.raises(ValueError, match="stage must be one of"):
            update_progress(learner_id=lid, chapter=1, stage="invalid", confidence_delta=0.0)


class TestUpdateProgressPersistence:
    def test_state_persisted_to_disk(self, isolated_store):
        lid = _seed_learner()
        update_progress(learner_id=lid, chapter=4, stage="make", confidence_delta=0.3)
        data = json.loads(store.LEARNER_STATE_FILE.read_text())
        assert data[lid]["chapter"] == 4
        assert data[lid]["stage"] == "make"
        assert data[lid]["confidence"] == pytest.approx(0.8)

    def test_reload_state_from_disk(self, isolated_store):
        lid = _seed_learner()
        update_progress(learner_id=lid, chapter=3, stage="modify", confidence_delta=0.2)
        raw = json.loads(store.LEARNER_STATE_FILE.read_text())
        reloaded = store._load_state()
        assert raw == reloaded

    def test_creates_default_state_if_missing(self, isolated_store):
        lid = _seed_learner()
        store.LEARNER_STATE_FILE.unlink()
        result = update_progress(learner_id=lid, chapter=3, stage="modify", confidence_delta=0.2)
        assert result["chapter"] == 3
        assert result["confidence"] == pytest.approx(0.7)
