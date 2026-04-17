"""End-to-end payment flow tests: checkout URL creation, webhook, and post-upgrade access."""

from __future__ import annotations

import pytest
import stripe
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from tutorclaw import store
from tutorclaw.tools.billing import get_upgrade_url
from tutorclaw.tools.content import get_chapter_content
from tutorclaw.webhook import stripe_webhook

from .conftest import _seed_learner


@pytest.fixture()
def webhook_client(monkeypatch):
    """Minimal Starlette app wired to the Stripe webhook handler."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")
    app = Starlette(routes=[Route("/webhook", stripe_webhook, methods=["POST"])])
    return TestClient(app)


def _install_fake_event(monkeypatch, learner_id: str) -> None:
    def _fake_construct(payload, sig, secret):
        return {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"learner_id": learner_id}}},
        }
    monkeypatch.setattr(stripe.Webhook, "construct_event", _fake_construct)


def test_get_upgrade_url_creates_session_for_free_learner(isolated_store, mock_stripe):
    lid = _seed_learner()

    result = get_upgrade_url(learner_id=lid)

    assert result["learner_id"] == lid
    assert result["tier"] == "free"
    assert result["upgrade_url"].startswith("https://checkout.stripe.com/")
    assert mock_stripe["kwargs"]["metadata"] == {"learner_id": lid}


def test_get_upgrade_url_rejects_paid_learner(isolated_store, mock_stripe):
    lid = _seed_learner(tier="paid", exchanges=-1)

    with pytest.raises(ValueError, match="already on the paid tier"):
        get_upgrade_url(learner_id=lid)


def test_webhook_upgrades_tier(isolated_store, webhook_client, monkeypatch):
    lid = _seed_learner()
    assert store.get_learner_tier(lid) == "free"

    _install_fake_event(monkeypatch, lid)

    resp = webhook_client.post(
        "/webhook", content=b"{}", headers={"Stripe-Signature": "sig"}
    )

    assert resp.status_code == 200
    assert resp.json()["action"] == "upgraded"
    assert store.get_learner_tier(lid) == "paid"


def test_gated_tool_after_upgrade(isolated_content, webhook_client, monkeypatch):
    lid = _seed_learner()

    with pytest.raises(ValueError, match="paid plan"):
        get_chapter_content(learner_id=lid, chapter=6)

    _install_fake_event(monkeypatch, lid)
    resp = webhook_client.post(
        "/webhook", content=b"{}", headers={"Stripe-Signature": "sig"}
    )
    assert resp.status_code == 200

    result = get_chapter_content(learner_id=lid, chapter=6)

    assert result["learner_id"] == lid
    assert result["chapter"] == 6
    assert "Dictionaries" in result["title"]
    assert result["content"]
