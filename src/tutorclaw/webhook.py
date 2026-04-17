from __future__ import annotations

import os

import stripe
from starlette.requests import Request
from starlette.responses import JSONResponse

from tutorclaw.store import upgrade_learner_to_paid


async def stripe_webhook(request: Request) -> JSONResponse:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        return JSONResponse({"error": "webhook not configured"}, status_code=500)

    sig = request.headers.get("Stripe-Signature")
    if not sig:
        return JSONResponse({"error": "missing signature header"}, status_code=400)

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except stripe.SignatureVerificationError:
        return JSONResponse({"error": "invalid signature"}, status_code=400)
    except ValueError:
        return JSONResponse({"error": "invalid payload"}, status_code=400)

    if event["type"] != "checkout.session.completed":
        return JSONResponse({"received": True, "action": "ignored"}, status_code=200)

    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    learner_id = metadata.get("learner_id")
    if not learner_id:
        return JSONResponse(
            {"error": "missing learner_id in metadata"}, status_code=400
        )

    try:
        changed = upgrade_learner_to_paid(learner_id)
    except ValueError:
        return JSONResponse(
            {
                "received": True,
                "action": "ignored",
                "reason": "unknown learner",
            },
            status_code=200,
        )

    return JSONResponse(
        {
            "received": True,
            "learner_id": learner_id,
            "action": "upgraded" if changed else "noop",
        },
        status_code=200,
    )
