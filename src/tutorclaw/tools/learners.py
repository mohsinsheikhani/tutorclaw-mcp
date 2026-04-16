from __future__ import annotations

import re
from typing import Annotated, TypedDict

from pydantic import Field

from tutorclaw.store import create_learner, get_learner_tier, get_state, update_state

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LearnerStateResult(TypedDict):
    learner_id: str
    chapter: int
    stage: str
    confidence: float
    tier: str
    exchanges_remaining: int
    weak_areas: list[str]


class RegisterLearnerResult(TypedDict):
    learner_id: str
    name: str
    email: str | None
    tier: str
    api_key: str
    welcome_message: str
    created_at: str


def register_learner(
    name: Annotated[
        str,
        Field(
            description="Learner's display name. 1-100 characters, non-empty after trimming.",
            min_length=1,
            max_length=100,
        ),
    ],
    email: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional contact email. Must be a valid address if provided.",
            max_length=254,
        ),
    ] = None,
) -> RegisterLearnerResult:
    """Register a new learner and return their ID, API key, and welcome message.

    WHEN to call: At the very start of a conversation when a user wants to begin learning and has no learner_id yet.
    NEVER call for existing learners — use get_learner_state to look up a known learner_id instead.
    Related: get_learner_state (read existing learner), update_progress (change progress).
    """
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("name must not be empty")
    if len(cleaned_name) > 100:
        raise ValueError("name must be 100 characters or fewer")

    cleaned_email: str | None = None
    if email is not None:
        candidate = email.strip()
        if candidate:
            if len(candidate) > 254:
                raise ValueError("email must be 254 characters or fewer")
            if not _EMAIL_RE.match(candidate):
                raise ValueError("email is not a valid address")
            cleaned_email = candidate

    learner_id, record = create_learner(cleaned_name, cleaned_email)
    return {
        "learner_id": learner_id,
        "name": record["name"],
        "email": record["email"],
        "tier": record["tier"],
        "api_key": record["api_key"],
        "welcome_message": (
            f"Welcome to TutorClaw, {record['name']}! "
            f"Your learner ID is {learner_id}."
        ),
        "created_at": record["created_at"],
    }


def _build_state_result(learner_id: str, state: dict, tier: str) -> LearnerStateResult:
    return {
        "learner_id": learner_id,
        "chapter": state["chapter"],
        "stage": state["stage"],
        "confidence": state["confidence"],
        "tier": tier,
        "exchanges_remaining": state["exchanges_remaining"],
        "weak_areas": state["weak_areas"],
    }


def get_learner_state(
    learner_id: Annotated[
        str,
        Field(
            description="The learner's unique ID.",
            min_length=1,
        ),
    ],
) -> LearnerStateResult:
    """Return the current tutoring progress for a learner, including chapter, stage, confidence, and tier.

    WHEN to call: Before any tutoring action to check the learner's current chapter, stage, confidence, tier, and remaining exchanges.
    NEVER call to change progress — this is read-only. Use update_progress to advance chapter or stage.
    Related: update_progress (write progress), register_learner (create new learner).
    """
    return _build_state_result(learner_id, get_state(learner_id), get_learner_tier(learner_id))


def update_progress(
    learner_id: Annotated[
        str,
        Field(
            description="The learner's unique ID.",
            min_length=1,
        ),
    ],
    chapter: Annotated[
        int,
        Field(
            description="Chapter number to set.",
            ge=1,
        ),
    ],
    stage: Annotated[
        str,
        Field(
            description="PRIMM-Lite stage: predict, run, investigate, modify, or make.",
        ),
    ],
    confidence_delta: Annotated[
        float,
        Field(
            description="Value added to current confidence score. Result is clamped to [0.0, 1.0].",
            ge=-1.0,
            le=1.0,
        ),
    ],
) -> LearnerStateResult:
    """Advance a learner to a new chapter and stage, and apply a confidence score adjustment.

    WHEN to call: After assess_response returns a recommendation to advance, or when the tutor decides to move the learner forward or back.
    NEVER call to check current state — this is write-only. Use get_learner_state to read progress first.
    Related: get_learner_state (read current progress), assess_response (get recommendation before updating).
    """
    state = update_state(learner_id, chapter, stage, confidence_delta)
    return _build_state_result(learner_id, state, get_learner_tier(learner_id))
