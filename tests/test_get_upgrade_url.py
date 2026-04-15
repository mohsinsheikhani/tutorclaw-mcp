from __future__ import annotations

import pytest

from tutorclaw import store
from tutorclaw.store import MOCK_LEARNER_ID
from tutorclaw.tools.billing import get_upgrade_url


@pytest.fixture(autouse=True)
def clean_store():
    store.reset()
    yield
    store.reset()


def _register():
    store.create_learner("Ada", None)


# --- free tier ---

def test_free_tier_returns_upgrade_url():
    _register()
    result = get_upgrade_url(learner_id=MOCK_LEARNER_ID)
    assert result["upgrade_url"].startswith("https://checkout.stripe.com/")


def test_free_tier_echoes_learner_id():
    _register()
    result = get_upgrade_url(learner_id=MOCK_LEARNER_ID)
    assert result["learner_id"] == MOCK_LEARNER_ID


def test_free_tier_echoes_tier():
    _register()
    result = get_upgrade_url(learner_id=MOCK_LEARNER_ID)
    assert result["tier"] == "free"


# --- already paid ---

def test_paid_tier_raises():
    _register()
    # Manually flip the tier to "paid" in the store
    data = store._load()
    data[MOCK_LEARNER_ID]["tier"] = "paid"
    store._save(data)

    with pytest.raises(ValueError, match="already on the paid tier"):
        get_upgrade_url(learner_id=MOCK_LEARNER_ID)


# --- learner not found ---

def test_unknown_learner_raises():
    with pytest.raises(ValueError, match="learner not found"):
        get_upgrade_url(learner_id="nonexistent")
