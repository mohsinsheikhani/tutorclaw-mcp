"""Shared fixtures for TutorClaw test suite.

Every test gets an isolated tmp_path so no test touches the production data directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tutorclaw import store
from tutorclaw.tools import content as content_mod

# ---------------------------------------------------------------------------
# Sample chapter markdown (mirrors content/chapters/01-variables.md structure)
# ---------------------------------------------------------------------------

SAMPLE_CHAPTER_MD = """\
# Chapter 1: Variables and Data Types

Variables store values.

## Code Examples

### Example 1: Assigning variables

```python
name = "Alice"
age = 25
print(name)
print(age)
```

**Output:**
```
Alice
25
```
"""

SAMPLE_PREMIUM_CHAPTER_MD = """\
# Chapter 6: Dictionaries

Dictionaries map keys to values.

## Code Examples

```python
d = {"a": 1}
print(d["a"])
```

**Output:**
```
1
```
"""

# ---------------------------------------------------------------------------
# Sample exercises JSON
# ---------------------------------------------------------------------------

SAMPLE_EXERCISES: list[dict] = [
    {
        "id": "ch01-ex01",
        "question": "Create a variable called city.",
        "hint": "Use = to assign.",
        "topic": "variables",
        "difficulty": "easy",
    },
    {
        "id": "ch01-ex02",
        "question": "Print your name.",
        "hint": "Use print().",
        "topic": "variables",
        "difficulty": "medium",
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    """Redirect all store and content paths to *tmp_path*.

    Returns *tmp_path* so tests can inspect the JSON files on disk.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    learners_file = data_dir / "learners.json"
    state_file = data_dir / "learner_state.json"

    monkeypatch.setattr(store, "DATA_DIR", data_dir)
    monkeypatch.setattr(store, "LEARNERS_FILE", learners_file)
    monkeypatch.setattr(store, "LEARNER_STATE_FILE", state_file)

    return tmp_path


@pytest.fixture()
def mock_stripe(monkeypatch):
    """Patch stripe.checkout.Session.create and set required env vars.

    Returns a dict with the captured kwargs from the most recent call,
    so tests can assert on price_id, metadata, etc.
    """
    import stripe

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PRICE_ID_PAID", "price_fake_123")

    captured: dict = {}

    class _FakeSession:
        url = "https://checkout.stripe.com/c/pay/cs_test_fake_session"

    def _fake_create(**kwargs):
        captured["kwargs"] = kwargs
        return _FakeSession()

    monkeypatch.setattr(stripe.checkout.Session, "create", _fake_create)
    return captured


@pytest.fixture()
def isolated_content(tmp_path, monkeypatch, isolated_store):
    """Set up isolated store *and* content directories with sample data.

    Writes one free-tier chapter (01) and one premium chapter (06),
    plus one exercise file (01).  Returns *tmp_path*.
    """
    chapters_dir = tmp_path / "content" / "chapters"
    chapters_dir.mkdir(parents=True)
    exercises_dir = tmp_path / "content" / "exercises"
    exercises_dir.mkdir(parents=True)

    # Write sample chapter files
    (chapters_dir / "01-variables.md").write_text(SAMPLE_CHAPTER_MD)
    (chapters_dir / "06-dictionaries.md").write_text(SAMPLE_PREMIUM_CHAPTER_MD)

    # Write sample exercises
    (exercises_dir / "01-exercises.json").write_text(json.dumps(SAMPLE_EXERCISES))

    monkeypatch.setattr(content_mod, "CHAPTERS_DIR", chapters_dir)
    monkeypatch.setattr(content_mod, "EXERCISES_DIR", exercises_dir)

    return tmp_path


def _seed_learner(tier: str = "free", exchanges: int = 50, code_subs: int = 0):
    """Helper: create a learner via the store and return the learner_id."""
    from datetime import date

    learner_id, _record = store.create_learner("Ada", None)

    # Optionally override tier
    if tier != "free":
        data = store._load()
        data[learner_id]["tier"] = tier
        store._save(data)

    # Optionally override state counters
    state = store._load_state()
    state[learner_id]["exchanges_remaining"] = exchanges
    state[learner_id]["code_submissions_today"] = code_subs
    state[learner_id]["exchanges_reset_date"] = date.today().isoformat()
    store._save_state(state)

    return learner_id
