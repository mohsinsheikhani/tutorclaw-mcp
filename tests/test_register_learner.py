from __future__ import annotations

import pytest

from tutorclaw import store
from tutorclaw.tools.learners import register_learner


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_register_with_name_only():
    result = register_learner(name="Ada")
    assert result["learner_id"].startswith("lrn_")
    assert len(result["learner_id"]) == len("lrn_") + 8
    assert result["name"] == "Ada"
    assert result["email"] is None
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


def test_unique_ids():
    a = register_learner(name="A")["learner_id"]
    b = register_learner(name="B")["learner_id"]
    assert a != b


def test_empty_email_string_treated_as_none():
    result = register_learner(name="Ada", email="   ")
    assert result["email"] is None
