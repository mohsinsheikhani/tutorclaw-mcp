from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TypedDict

MOCK_LEARNER_ID = "learner-001"
MOCK_API_KEY = "test-key-001"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
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
    exchanges_reset_date: str  # ISO date, e.g. "2026-04-16"
    code_submissions_today: int
    weak_areas: list[str]


class TierInfo(TypedDict):
    tier: str
    exchanges_remaining: int
    exchanges_reset_date: str
    code_submissions_today: int


class TierError(TypedDict):
    error: str


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


def _default_state(tier: str) -> LearnerStateRecord:
    return {
        "chapter": 1,
        "stage": "predict",
        "confidence": 0.5,
        "exchanges_remaining": _default_exchanges(tier),
        "exchanges_reset_date": date.today().isoformat(),
        "code_submissions_today": 0,
        "weak_areas": [],
    }


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

    state_data = _load_state()
    state_data[MOCK_LEARNER_ID] = _default_state("free")
    _save_state(state_data)

    return MOCK_LEARNER_ID, record


_VALID_STAGES = ("predict", "run", "investigate", "modify", "make")


def update_state(
    learner_id: str,
    chapter: int,
    stage: str,
    confidence_delta: float,
) -> LearnerStateRecord:
    learners = _load()
    if learner_id not in learners:
        raise ValueError("learner not found")

    if stage not in _VALID_STAGES:
        raise ValueError(
            f"stage must be one of: {', '.join(_VALID_STAGES)}"
        )

    state_data = _load_state()
    if learner_id not in state_data:
        state_data[learner_id] = _default_state(learners[learner_id]["tier"])

    record = state_data[learner_id]
    record["chapter"] = chapter
    record["stage"] = stage
    record["confidence"] = max(0.0, min(1.0, record["confidence"] + confidence_delta))
    _save_state(state_data)
    return record


def get_state(learner_id: str) -> LearnerStateRecord:
    learners = _load()
    if learner_id not in learners:
        raise ValueError("learner not found")

    state_data = _load_state()
    if learner_id not in state_data:
        raise ValueError("learner state not found")

    return state_data[learner_id]


def upgrade_learner_to_paid(learner_id: str) -> bool:
    """Flip learner tier to 'paid' and reset exchanges to unlimited.

    Returns True if the tier was changed, False if the learner was already paid.
    Raises ValueError if the learner is unknown.
    """
    learners = _load()
    if learner_id not in learners:
        raise ValueError("learner not found")

    if learners[learner_id]["tier"] == "paid":
        return False

    learners[learner_id]["tier"] = "paid"
    _save(learners)

    state_data = _load_state()
    if learner_id in state_data:
        state_data[learner_id]["exchanges_remaining"] = _EXCHANGES_DEFAULT_PAID
        _save_state(state_data)

    return True


def get_learner_tier(learner_id: str) -> str:
    learners = _load()
    if learner_id not in learners:
        raise ValueError("learner not found")
    return learners[learner_id]["tier"]


def check_tier(learner_id: str) -> TierInfo | TierError:
    learners = _load()
    if learner_id not in learners:
        return {"error": "learner not found"}

    state_data = _load_state()
    if learner_id not in state_data:
        return {"error": "learner state not found"}

    tier = learners[learner_id]["tier"]
    record = state_data[learner_id]
    today = date.today().isoformat()

    # Migrate records that pre-date this field.
    if "exchanges_reset_date" not in record:
        record["exchanges_reset_date"] = today
        _save_state(state_data)

    # Reset daily counters for free-tier learners whose window has passed.
    if tier == "free" and today > record["exchanges_reset_date"]:
        record["exchanges_remaining"] = _EXCHANGES_BY_TIER["free"]
        record["exchanges_reset_date"] = today
        record["code_submissions_today"] = 0
        _save_state(state_data)

    return {
        "tier": tier,
        "exchanges_remaining": record["exchanges_remaining"],
        "exchanges_reset_date": record["exchanges_reset_date"],
        "code_submissions_today": record.get("code_submissions_today", 0),
    }


def decrement_exchanges(learner_id: str) -> None:
    """Subtract 1 from exchanges_remaining. Caller is responsible for checking tier and quota."""
    state_data = _load_state()
    record = state_data.get(learner_id)
    if record is not None and record.get("exchanges_remaining", 0) > 0:
        record["exchanges_remaining"] -= 1
        _save_state(state_data)


def spend_code_submission(learner_id: str) -> None:
    """Increment code_submissions_today by 1 and decrement exchanges_remaining by 1."""
    state_data = _load_state()
    record = state_data.get(learner_id)
    if record is None:
        return
    record["code_submissions_today"] = record.get("code_submissions_today", 0) + 1
    if record.get("exchanges_remaining", 0) > 0:
        record["exchanges_remaining"] -= 1
    _save_state(state_data)


def reset() -> None:
    if LEARNERS_FILE.exists():
        LEARNERS_FILE.unlink()
    if LEARNER_STATE_FILE.exists():
        LEARNER_STATE_FILE.unlink()
