from __future__ import annotations

import pytest

from tutorclaw import store
from tutorclaw.store import MOCK_API_KEY, MOCK_LEARNER_ID
from tutorclaw.tools.learners import register_learner


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_register_with_name_only():
    result = register_learner(name="Ada")
    assert result["learner_id"] == MOCK_LEARNER_ID
    assert result["name"] == "Ada"
    assert result["email"] is None
    assert result["tier"] == "free"
    assert result["api_key"] == MOCK_API_KEY
    assert "Ada" in result["welcome_message"]
    assert result["learner_id"] in result["welcome_message"]
    assert result["created_at"].endswith("Z")


def test_register_with_email():
    result = register_learner(name="Ada", email="ada@example.com")
    assert result["email"] == "ada@example.com"


def test_register_trims_name():
    result = register_learner(name="  Grace  ")
    assert result["name"] == "Grace"


def test_empty_name_rejected():
    with pytest.raises(ValueError, match="name must not be empty"):
        register_learner(name="   ")


def test_invalid_email_rejected():
    with pytest.raises(ValueError, match="email is not a valid address"):
        register_learner(name="Ada", email="not-an-email")


def test_empty_email_string_treated_as_none():
    result = register_learner(name="Ada", email="   ")
    assert result["email"] is None


def test_idempotent_registration():
    """Calling register_learner twice returns the same record (mock ID is reused)."""
    first = register_learner(name="Ada")
    second = register_learner(name="Bob")
    assert first["learner_id"] == second["learner_id"]
    assert second["name"] == "Ada"  # original record preserved


def test_persists_to_disk():
    """Data survives a fresh _load after create."""
    register_learner(name="Ada", email="ada@example.com")
    data = store._load()
    assert MOCK_LEARNER_ID in data
    assert data[MOCK_LEARNER_ID]["name"] == "Ada"
    assert data[MOCK_LEARNER_ID]["email"] == "ada@example.com"
    assert data[MOCK_LEARNER_ID]["tier"] == "free"
    assert data[MOCK_LEARNER_ID]["api_key"] == MOCK_API_KEY


def test_reset_removes_file():
    register_learner(name="Ada")
    assert store.LEARNERS_FILE.exists()
    store.reset()
    assert not store.LEARNERS_FILE.exists()
