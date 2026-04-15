from __future__ import annotations

import re
from typing import Annotated, TypedDict

from pydantic import Field

from tutorclaw.store import create_learner

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterLearnerResult(TypedDict):
    learner_id: str
    name: str
    email: str | None
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
    """Register a new learner on the TutorClaw platform.

    Returns a unique learner ID and a welcome message. The email is optional
    but stored when provided.
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
        "welcome_message": (
            f"Welcome to TutorClaw, {record['name']}! "
            f"Your learner ID is {learner_id}."
        ),
        "created_at": record["created_at"],
    }
