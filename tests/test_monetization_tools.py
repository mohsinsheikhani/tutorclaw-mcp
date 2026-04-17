"""Tests for get_upgrade_url."""

from __future__ import annotations

import pytest

from tutorclaw.tools.billing import get_upgrade_url

from .conftest import _seed_learner


# =========================================================================
# get_upgrade_url — valid input
# =========================================================================


class TestGetUpgradeUrlValid:
    def test_free_tier_returns_checkout_url(self, isolated_store, mock_stripe):
        lid = _seed_learner()
        result = get_upgrade_url(learner_id=lid)
        assert result["upgrade_url"].startswith("https://checkout.stripe.com/")

    def test_echoes_learner_id(self, isolated_store, mock_stripe):
        lid = _seed_learner()
        result = get_upgrade_url(learner_id=lid)
        assert result["learner_id"] == lid

    def test_echoes_tier_as_free(self, isolated_store, mock_stripe):
        lid = _seed_learner()
        result = get_upgrade_url(learner_id=lid)
        assert result["tier"] == "free"

    def test_session_metadata_includes_learner_id(self, isolated_store, mock_stripe):
        lid = _seed_learner()
        get_upgrade_url(learner_id=lid)
        assert mock_stripe["kwargs"]["metadata"] == {"learner_id": lid}

    def test_session_uses_price_id_from_env(self, isolated_store, mock_stripe):
        lid = _seed_learner()
        get_upgrade_url(learner_id=lid)
        line_items = mock_stripe["kwargs"]["line_items"]
        assert line_items[0]["price"] == "price_fake_123"


# =========================================================================
# get_upgrade_url — invalid input
# =========================================================================


class TestGetUpgradeUrlInvalid:
    def test_unknown_learner_raises(self, isolated_store, mock_stripe):
        with pytest.raises(ValueError, match="learner not found"):
            get_upgrade_url(learner_id="nonexistent")

    def test_paid_tier_raises(self, isolated_store, mock_stripe):
        lid = _seed_learner(tier="paid", exchanges=-1)
        with pytest.raises(ValueError, match="already on the paid tier"):
            get_upgrade_url(learner_id=lid)
