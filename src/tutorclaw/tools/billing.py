from __future__ import annotations

import os
from typing import Annotated, TypedDict

import stripe
from pydantic import Field

from tutorclaw.store import get_learner_tier


class UpgradeUrlResult(TypedDict):
    learner_id: str
    tier: str
    upgrade_url: str


def get_upgrade_url(
    learner_id: Annotated[
        str,
        Field(
            description="The learner's unique ID.",
            min_length=1,
        ),
    ],
) -> UpgradeUrlResult:
    """Return a Stripe checkout URL to upgrade a free-tier learner to the paid plan.

    WHEN to call: When a free-tier learner hits a content gate (chapter > 5) or exhausts daily exchanges, and needs an upgrade link.
    NEVER call for paid-tier learners — they already have full access. Use get_learner_state to check tier first.
    Related: get_learner_state (check current tier before calling).
    """
    tier = get_learner_tier(learner_id)  # raises ValueError if not found
    if tier != "free":
        raise ValueError("learner is already on the paid tier")

    secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not set")
    price_id = os.environ.get("STRIPE_PRICE_ID_PAID")
    if not price_id:
        raise RuntimeError("STRIPE_PRICE_ID_PAID is not set")

    stripe.api_key = secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="https://tutorclaw.io/upgrade/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://tutorclaw.io/upgrade/cancel",
        metadata={"learner_id": learner_id},
    )
    return {
        "learner_id": learner_id,
        "tier": tier,
        "upgrade_url": session.url,
    }
