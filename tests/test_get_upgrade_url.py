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

def test_free_tier_returns_upgrade_url(mock_stripe):
    _register()
    result = get_upgrade_url(learner_id=MOCK_LEARNER_ID)
    assert result["upgrade_url"].startswith("https://checkout.stripe.com/")


def test_free_tier_echoes_learner_id(mock_stripe):
    _register()
    result = get_upgrade_url(learner_id=MOCK_LEARNER_ID)
    assert result["learner_id"] == MOCK_LEARNER_ID


def test_free_tier_echoes_tier(mock_stripe):
    _register()
    result = get_upgrade_url(learner_id=MOCK_LEARNER_ID)
    assert result["tier"] == "free"


def test_session_created_with_learner_id_metadata(mock_stripe):
    _register()
    get_upgrade_url(learner_id=MOCK_LEARNER_ID)
    kwargs = mock_stripe["kwargs"]
    assert kwargs["metadata"] == {"learner_id": MOCK_LEARNER_ID}
    assert kwargs["line_items"][0]["price"] == "price_fake_123"
    assert kwargs["mode"] == "subscription"


# --- already paid ---

def test_paid_tier_raises(mock_stripe):
    _register()
    # Manually flip the tier to "paid" in the store
    data = store._load()
    data[MOCK_LEARNER_ID]["tier"] = "paid"
    store._save(data)

    with pytest.raises(ValueError, match="already on the paid tier"):
        get_upgrade_url(learner_id=MOCK_LEARNER_ID)


# --- learner not found ---

def test_unknown_learner_raises(mock_stripe):
    with pytest.raises(ValueError, match="learner not found"):
        get_upgrade_url(learner_id="nonexistent")


# --- missing env vars ---

def test_missing_secret_key_raises(monkeypatch):
    _register()
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("STRIPE_PRICE_ID_PAID", "price_fake_123")
    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY"):
        get_upgrade_url(learner_id=MOCK_LEARNER_ID)


def test_missing_price_id_raises(monkeypatch):
    _register()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.delenv("STRIPE_PRICE_ID_PAID", raising=False)
    with pytest.raises(RuntimeError, match="STRIPE_PRICE_ID_PAID"):
        get_upgrade_url(learner_id=MOCK_LEARNER_ID)
