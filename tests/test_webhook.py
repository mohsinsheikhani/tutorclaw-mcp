"""Tests for the Stripe webhook endpoint and the store upgrade helper."""

from __future__ import annotations

import json

import pytest
import stripe
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from tutorclaw import store
from tutorclaw.webhook import stripe_webhook

from .conftest import _seed_learner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(isolated_store, monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")
    app = Starlette(
        routes=[Route("/webhook", stripe_webhook, methods=["POST"])]
    )
    return TestClient(app)


def _mock_event(monkeypatch, event: dict) -> None:
    def _fake_construct(payload, sig, secret):
        return event
    monkeypatch.setattr(stripe.Webhook, "construct_event", _fake_construct)


def _mock_error(monkeypatch, exc: Exception) -> None:
    def _raise(payload, sig, secret):
        raise exc
    monkeypatch.setattr(stripe.Webhook, "construct_event", _raise)


def _checkout_event(learner_id: str | None) -> dict:
    metadata = {"learner_id": learner_id} if learner_id is not None else {}
    return {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": metadata}},
    }


# ---------------------------------------------------------------------------
# store.upgrade_learner_to_paid
# ---------------------------------------------------------------------------


class TestUpgradeLearnerToPaid:
    def test_changes_tier_to_paid(self, isolated_store):
        lid = _seed_learner()
        changed = store.upgrade_learner_to_paid(lid)
        assert changed is True
        assert store.get_learner_tier(lid) == "paid"

    def test_sets_exchanges_remaining_to_unlimited(self, isolated_store):
        lid = _seed_learner(exchanges=10)
        store.upgrade_learner_to_paid(lid)
        state = store._load_state()[lid]
        assert state["exchanges_remaining"] == -1

    def test_idempotent_when_already_paid(self, isolated_store):
        lid = _seed_learner(tier="paid", exchanges=-1)
        changed = store.upgrade_learner_to_paid(lid)
        assert changed is False
        assert store.get_learner_tier(lid) == "paid"

    def test_unknown_learner_raises(self, isolated_store):
        with pytest.raises(ValueError, match="learner not found"):
            store.upgrade_learner_to_paid("nonexistent")


# ---------------------------------------------------------------------------
# webhook — happy paths
# ---------------------------------------------------------------------------


class TestWebhookSuccess:
    def test_completed_event_upgrades_learner(self, client, monkeypatch):
        lid = _seed_learner()
        _mock_event(monkeypatch, _checkout_event(lid))

        resp = client.post("/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"received": True, "learner_id": lid, "action": "upgraded"}
        assert store.get_learner_tier(lid) == "paid"

    def test_already_paid_returns_noop(self, client, monkeypatch):
        lid = _seed_learner(tier="paid", exchanges=-1)
        _mock_event(monkeypatch, _checkout_event(lid))

        resp = client.post("/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 200
        assert resp.json()["action"] == "noop"

    def test_other_event_type_ignored(self, client, monkeypatch):
        lid = _seed_learner()
        _mock_event(monkeypatch, {"type": "invoice.paid", "data": {"object": {}}})

        resp = client.post("/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 200
        assert resp.json() == {"received": True, "action": "ignored"}
        assert store.get_learner_tier(lid) == "free"

    def test_unknown_learner_returns_200_ignored(self, client, monkeypatch):
        _mock_event(monkeypatch, _checkout_event("learner-does-not-exist"))

        resp = client.post("/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["action"] == "ignored"
        assert body["reason"] == "unknown learner"


# ---------------------------------------------------------------------------
# webhook — error paths
# ---------------------------------------------------------------------------


class TestWebhookErrors:
    def test_invalid_signature_returns_400(self, client, monkeypatch):
        _mock_error(
            monkeypatch,
            stripe.SignatureVerificationError("bad", "sig", http_body=b"{}"),
        )
        resp = client.post("/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 400
        assert resp.json() == {"error": "invalid signature"}

    def test_invalid_payload_returns_400(self, client, monkeypatch):
        _mock_error(monkeypatch, ValueError("bad json"))
        resp = client.post("/webhook", content=b"nope", headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 400
        assert resp.json() == {"error": "invalid payload"}

    def test_missing_signature_header_returns_400(self, client):
        resp = client.post("/webhook", content=b"{}")
        assert resp.status_code == 400
        assert resp.json() == {"error": "missing signature header"}

    def test_missing_learner_id_metadata_returns_400(self, client, monkeypatch):
        _mock_event(monkeypatch, _checkout_event(None))
        resp = client.post("/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert resp.status_code == 400
        assert resp.json() == {"error": "missing learner_id in metadata"}

    def test_missing_webhook_secret_returns_500(self, isolated_store, monkeypatch):
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        app = Starlette(routes=[Route("/webhook", stripe_webhook, methods=["POST"])])
        with TestClient(app) as bare_client:
            resp = bare_client.post(
                "/webhook", content=b"{}", headers={"Stripe-Signature": "sig"}
            )
        assert resp.status_code == 500
        assert resp.json() == {"error": "webhook not configured"}


# ---------------------------------------------------------------------------
# webhook — raw-body handling (signature is computed on bytes, not parsed JSON)
# ---------------------------------------------------------------------------


class TestWebhookRawBody:
    def test_raw_body_passed_to_construct_event(self, client, monkeypatch):
        lid = _seed_learner()
        captured: dict = {}

        def _fake(payload, sig, secret):
            captured["payload"] = payload
            captured["sig"] = sig
            captured["secret"] = secret
            return _checkout_event(lid)

        monkeypatch.setattr(stripe.Webhook, "construct_event", _fake)

        raw = json.dumps({"hello": "world"}).encode()
        client.post("/webhook", content=raw, headers={"Stripe-Signature": "sig-123"})

        assert captured["payload"] == raw
        assert captured["sig"] == "sig-123"
        assert captured["secret"] == "whsec_test_fake"
