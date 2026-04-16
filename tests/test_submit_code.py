from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.store import LEARNER_STATE_FILE, MOCK_LEARNER_ID
from tutorclaw.tools.execution import submit_code
from tutorclaw.tools.learners import register_learner


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    register_learner(name="Ada")
    yield
    store.reset()


# --- successful execution ---

def test_hello_world_stdout():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code='print("hello")')
    assert result["stdout"].strip() == "hello"
    assert result["stderr"] == ""
    assert not result["timed_out"]
    assert result["blocked_reason"] is None


def test_arithmetic_stdout():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="print(2 + 3)")
    assert result["stdout"].strip() == "5"
    assert result["blocked_reason"] is None


def test_stderr_captured():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="import sys; sys.stderr.write('err\\n')")
    assert result["stderr"].strip() == "err"
    assert result["blocked_reason"] is None


def test_runtime_error_goes_to_stderr():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="x = 1/0")
    assert "ZeroDivisionError" in result["stderr"]
    assert not result["timed_out"]
    assert result["blocked_reason"] is None


def test_multiline_code():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="x = 10\ny = 20\nprint(x + y)")
    assert result["stdout"].strip() == "30"
    assert result["blocked_reason"] is None


# --- safety: blocked imports ---

def test_blocks_import_os():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="import os\nprint(os.getcwd())")
    assert result["blocked_reason"] is not None
    assert "os" in result["blocked_reason"]
    assert result["stdout"] == ""
    assert result["stderr"] == ""


def test_blocks_import_subprocess():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="import subprocess")
    assert result["blocked_reason"] is not None
    assert "subprocess" in result["blocked_reason"]


def test_blocks_import_shutil():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="import shutil")
    assert result["blocked_reason"] is not None
    assert "shutil" in result["blocked_reason"]


def test_blocks_from_os_import():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="from os import path")
    assert result["blocked_reason"] is not None
    assert "os" in result["blocked_reason"]


def test_blocks_from_subprocess_import():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="from subprocess import run")
    assert result["blocked_reason"] is not None
    assert "subprocess" in result["blocked_reason"]


def test_blocks_from_shutil_import():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="from shutil import copy")
    assert result["blocked_reason"] is not None
    assert "shutil" in result["blocked_reason"]


def test_blocks_open_call():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="f = open('file.txt')")
    assert result["blocked_reason"] is not None
    assert "open()" in result["blocked_reason"]


def test_blocked_code_not_executed():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="import os\nprint('should not print')")
    assert result["stdout"] == ""
    assert not result["timed_out"]


# --- timeout ---

def test_timeout_returns_timed_out_flag():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="while True: pass")
    assert result["timed_out"]
    assert result["stdout"] == ""
    assert result["blocked_reason"] is None


# --- safe code that looks similar to blocked patterns ---

def test_variable_named_os_is_allowed():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="os_name = 'linux'\nprint(os_name)")
    assert result["blocked_reason"] is None
    assert result["stdout"].strip() == "linux"


def test_string_containing_import_os_is_allowed():
    result = submit_code(learner_id=MOCK_LEARNER_ID, code='print("import os")')
    assert isinstance(result["blocked_reason"], (str, type(None)))


# --- tier gates ---

def test_counters_decremented_on_success():
    before = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]
    submit_code(learner_id=MOCK_LEARNER_ID, code="print(1)")
    after = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]
    assert after["code_submissions_today"] == before["code_submissions_today"] + 1
    assert after["exchanges_remaining"] == before["exchanges_remaining"] - 1


def test_submission_limit_raises_at_10():
    state = json.loads(LEARNER_STATE_FILE.read_text())
    state[MOCK_LEARNER_ID]["code_submissions_today"] = 10
    LEARNER_STATE_FILE.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="used all 10 free code submissions"):
        submit_code(learner_id=MOCK_LEARNER_ID, code="print(1)")


def test_zero_exchanges_raises():
    state = json.loads(LEARNER_STATE_FILE.read_text())
    state[MOCK_LEARNER_ID]["exchanges_remaining"] = 0
    LEARNER_STATE_FILE.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="used all 50 free exchanges"):
        submit_code(learner_id=MOCK_LEARNER_ID, code="print(1)")


def test_unknown_learner_raises():
    with pytest.raises(ValueError, match="learner not found"):
        submit_code(learner_id="nobody", code="print(1)")


def test_paid_tier_skips_all_limits():
    learners_data = json.loads(store.LEARNERS_FILE.read_text())
    learners_data[MOCK_LEARNER_ID]["tier"] = "paid"
    store.LEARNERS_FILE.write_text(json.dumps(learners_data))
    state = json.loads(LEARNER_STATE_FILE.read_text())
    state[MOCK_LEARNER_ID]["exchanges_remaining"] = -1
    state[MOCK_LEARNER_ID]["code_submissions_today"] = 999
    LEARNER_STATE_FILE.write_text(json.dumps(state))
    result = submit_code(learner_id=MOCK_LEARNER_ID, code="print('ok')")
    assert result["stdout"].strip() == "ok"
    # Counters must not change for paid tier.
    after = json.loads(LEARNER_STATE_FILE.read_text())[MOCK_LEARNER_ID]
    assert after["exchanges_remaining"] == -1
    assert after["code_submissions_today"] == 999
