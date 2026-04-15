from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import TypedDict


class LearnerRecord(TypedDict):
    name: str
    email: str | None
    created_at: str


_learners: dict[str, LearnerRecord] = {}


def _new_id() -> str:
    while True:
        candidate = f"lrn_{secrets.token_hex(4)}"
        if candidate not in _learners:
            return candidate


def create_learner(name: str, email: str | None) -> tuple[str, LearnerRecord]:
    learner_id = _new_id()
    record: LearnerRecord = {
        "name": name,
        "email": email,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _learners[learner_id] = record
    return learner_id, record


def reset() -> None:
    _learners.clear()
