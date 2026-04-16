from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from tutorclaw import store
from tutorclaw.store import (
    DATA_DIR,
    LEARNER_STATE_FILE,
    LEARNERS_FILE,
    MOCK_LEARNER_ID,
    check_tier,
)

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TWO_DAYS_AGO = (date.today() - timedelta(days=2)).isoformat()


def _write_learner(tier: str = "free") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LEARNERS_FILE.write_text(
        json.dumps(
            {
                MOCK_LEARNER_ID: {
                    "name": "Test",
                    "email": None,
                    "tier": tier,
                    "api_key": "key",
                    "created_at": "2026-04-01T00:00:00Z",
                }
            }
        )
    )


def _write_state(exchanges_remaining: int = 50, reset_date: str | None = TODAY) -> None:
    record: dict = {
        "chapter": 1,
        "stage": "run",
        "confidence": 0.7,
        "exchanges_remaining": exchanges_remaining,
        "weak_areas": [],
    }
    if reset_date is not None:
        record["exchanges_reset_date"] = reset_date
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LEARNER_STATE_FILE.write_text(json.dumps({MOCK_LEARNER_ID: record}))


@pytest.fixture(autouse=True)
def _reset():
    store.reset()
    yield
    store.reset()


# --- Error cases ---

def test_unknown_learner_returns_error():
    result = check_tier("no-such-learner")
    assert result == {"error": "learner not found"}


def test_missing_state_returns_error():
    _write_learner()
    # Do NOT write a state file.
    result = check_tier(MOCK_LEARNER_ID)
    assert result == {"error": "learner state not found"}


# --- Free tier: no reset needed ---

def test_free_tier_reset_date_is_today_no_change():
    _write_learner("free")
    _write_state(exchanges_remaining=30, reset_date=TODAY)

    result = check_tier(MOCK_LEARNER_ID)

    assert result["tier"] == "free"
    assert result["exchanges_remaining"] == 30  # unchanged
    assert result["exchanges_reset_date"] == TODAY


# --- Free tier: reset fires ---

def test_free_tier_yesterday_resets_counter():
    _write_learner("free")
    _write_state(exchanges_remaining=3, reset_date=YESTERDAY)

    result = check_tier(MOCK_LEARNER_ID)

    assert result["tier"] == "free"
    assert result["exchanges_remaining"] == 50
    assert result["exchanges_reset_date"] == TODAY


def test_free_tier_older_date_resets_counter():
    _write_learner("free")
    _write_state(exchanges_remaining=0, reset_date=TWO_DAYS_AGO)

    result = check_tier(MOCK_LEARNER_ID)

    assert result["exchanges_remaining"] == 50
    assert result["exchanges_reset_date"] == TODAY


def test_free_tier_reset_persisted_to_disk():
    _write_learner("free")
    _write_state(exchanges_remaining=1, reset_date=YESTERDAY)

    check_tier(MOCK_LEARNER_ID)

    raw = json.loads(LEARNER_STATE_FILE.read_text())
    assert raw[MOCK_LEARNER_ID]["exchanges_remaining"] == 50
    assert raw[MOCK_LEARNER_ID]["exchanges_reset_date"] == TODAY


# --- Paid tier ---

def test_paid_tier_returns_unlimited():
    _write_learner("paid")
    _write_state(exchanges_remaining=-1, reset_date=YESTERDAY)

    result = check_tier(MOCK_LEARNER_ID)

    assert result["tier"] == "paid"
    assert result["exchanges_remaining"] == -1  # counter untouched


def test_paid_tier_old_date_does_not_reset():
    _write_learner("paid")
    _write_state(exchanges_remaining=-1, reset_date=TWO_DAYS_AGO)

    result = check_tier(MOCK_LEARNER_ID)

    # exchanges_remaining stays -1; reset_date is NOT advanced for paid
    assert result["exchanges_remaining"] == -1
    assert result["exchanges_reset_date"] == TWO_DAYS_AGO


# --- Migration: missing exchanges_reset_date field ---

def test_missing_reset_date_defaults_to_today():
    _write_learner("free")
    _write_state(exchanges_remaining=40, reset_date=None)  # field absent

    result = check_tier(MOCK_LEARNER_ID)

    assert result["exchanges_reset_date"] == TODAY
    assert result["exchanges_remaining"] == 40  # no reset, same day


def test_missing_reset_date_persisted_to_disk():
    _write_learner("free")
    _write_state(exchanges_remaining=40, reset_date=None)

    check_tier(MOCK_LEARNER_ID)

    raw = json.loads(LEARNER_STATE_FILE.read_text())
    assert raw[MOCK_LEARNER_ID]["exchanges_reset_date"] == TODAY
