from __future__ import annotations

from typing import Annotated, TypedDict

from pydantic import Field

from tutorclaw.store import get_learner_tier

_MOCK_CHECKOUT_URL = "https://checkout.stripe.com/mock-session-id"


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
    return {
        "learner_id": learner_id,
        "tier": tier,
        "upgrade_url": _MOCK_CHECKOUT_URL,
    }
