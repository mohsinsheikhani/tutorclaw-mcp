from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

MOCK_LEARNER_ID = "learner-001"
MOCK_API_KEY = "test-key-001"

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
LEARNERS_FILE = DATA_DIR / "learners.json"
LEARNER_STATE_FILE = DATA_DIR / "learner_state.json"

_EXCHANGES_BY_TIER: dict[str, int] = {
    "free": 50,
}
_EXCHANGES_DEFAULT_PAID = -1  # unlimited


class LearnerRecord(TypedDict):
    name: str
    email: str | None
    tier: str
    api_key: str
    created_at: str


class LearnerStateRecord(TypedDict):
    chapter: int
    stage: str
    confidence: float
    exchanges_remaining: int
    weak_areas: list[str]


def _load() -> dict[str, LearnerRecord]:
    if not LEARNERS_FILE.exists():
        return {}
    text = LEARNERS_FILE.read_text()
    if not text.strip():
        return {}
    return json.loads(text)


def _save(data: dict[str, LearnerRecord]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LEARNERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, LEARNERS_FILE)


def _load_state() -> dict[str, LearnerStateRecord]:
    if not LEARNER_STATE_FILE.exists():
        return {}
    text = LEARNER_STATE_FILE.read_text()
    if not text.strip():
        return {}
    return json.loads(text)


def _save_state(data: dict[str, LearnerStateRecord]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LEARNER_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, LEARNER_STATE_FILE)


def _default_exchanges(tier: str) -> int:
    return _EXCHANGES_BY_TIER.get(tier, _EXCHANGES_DEFAULT_PAID)


def create_learner(name: str, email: str | None) -> tuple[str, LearnerRecord]:
    data = _load()

    if MOCK_LEARNER_ID in data:
        return MOCK_LEARNER_ID, data[MOCK_LEARNER_ID]

    record: LearnerRecord = {
        "name": name,
        "email": email,
        "tier": "free",
        "api_key": MOCK_API_KEY,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    data[MOCK_LEARNER_ID] = record
    _save(data)

    # Initialize default learner state
    state_data = _load_state()
    state_data[MOCK_LEARNER_ID] = {
        "chapter": 1,
        "stage": "predict",
        "confidence": 0.5,
        "exchanges_remaining": _default_exchanges("free"),
        "weak_areas": [],
    }
    _save_state(state_data)

    return MOCK_LEARNER_ID, record


def get_state(learner_id: str) -> LearnerStateRecord:
    learners = _load()
    if learner_id not in learners:
        raise ValueError("learner not found")

    state_data = _load_state()
    if learner_id not in state_data:
        raise ValueError("learner state not found")

    return state_data[learner_id]


def get_learner_tier(learner_id: str) -> str:
    learners = _load()
    if learner_id not in learners:
        raise ValueError("learner not found")
    return learners[learner_id]["tier"]


def reset() -> None:
    if LEARNERS_FILE.exists():
        LEARNERS_FILE.unlink()
    if LEARNER_STATE_FILE.exists():
        LEARNER_STATE_FILE.unlink()
