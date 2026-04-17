"""Tests for submit_code."""

from __future__ import annotations

import json

import pytest

from tutorclaw import store
from tutorclaw.tools.execution import submit_code

from .conftest import _seed_learner


# =========================================================================
# submit_code — valid input
# =========================================================================


class TestSubmitCodeValid:
    def test_hello_world(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code='print("hello")')
        assert result["stdout"].strip() == "hello"
        assert result["stderr"] == ""
        assert not result["timed_out"]
        assert result["blocked_reason"] is None

    def test_arithmetic(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="print(2 + 3)")
        assert result["stdout"].strip() == "5"

    def test_multiline_code(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="x = 10\ny = 20\nprint(x + y)")
        assert result["stdout"].strip() == "30"

    def test_stderr_captured(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="import sys; sys.stderr.write('err\\n')")
        assert result["stderr"].strip() == "err"

    def test_runtime_error_in_stderr(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="x = 1/0")
        assert "ZeroDivisionError" in result["stderr"]
        assert not result["timed_out"]
        assert result["blocked_reason"] is None


# =========================================================================
# submit_code — safety blocks
# =========================================================================


class TestSubmitCodeSafety:
    def test_blocks_import_os(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="import os")
        assert result["blocked_reason"] is not None
        assert "os" in result["blocked_reason"]
        assert result["stdout"] == ""

    def test_blocks_import_subprocess(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="import subprocess")
        assert "subprocess" in result["blocked_reason"]

    def test_blocks_import_shutil(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="import shutil")
        assert "shutil" in result["blocked_reason"]

    def test_blocks_from_os_import(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="from os import path")
        assert "os" in result["blocked_reason"]

    def test_blocks_open_call(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="f = open('file.txt')")
        assert "open()" in result["blocked_reason"]

    def test_blocked_code_not_executed(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="import os\nprint('nope')")
        assert result["stdout"] == ""

    def test_variable_named_os_is_allowed(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="os_name = 'linux'\nprint(os_name)")
        assert result["blocked_reason"] is None
        assert result["stdout"].strip() == "linux"


# =========================================================================
# submit_code — timeout
# =========================================================================


class TestSubmitCodeTimeout:
    def test_infinite_loop_times_out(self, isolated_store):
        lid = _seed_learner()
        result = submit_code(learner_id=lid, code="while True: pass")
        assert result["timed_out"]
        assert result["stdout"] == ""
        assert result["blocked_reason"] is None


# =========================================================================
# submit_code — invalid input
# =========================================================================


class TestSubmitCodeInvalid:
    def test_unknown_learner_raises(self, isolated_store):
        with pytest.raises(ValueError, match="learner not found"):
            submit_code(learner_id="nobody", code="print(1)")


# =========================================================================
# submit_code — tier gating
# =========================================================================


class TestSubmitCodeTierGating:
    def test_counters_decremented_on_success(self, isolated_store):
        lid = _seed_learner(exchanges=50, code_subs=0)
        submit_code(learner_id=lid, code="print(1)")
        state = json.loads(store.LEARNER_STATE_FILE.read_text())
        assert state[lid]["code_submissions_today"] == 1
        assert state[lid]["exchanges_remaining"] == 49

    def test_submission_limit_at_10_raises(self, isolated_store):
        lid = _seed_learner(code_subs=10)
        with pytest.raises(ValueError, match="used all 10 free code submissions"):
            submit_code(learner_id=lid, code="print(1)")

    def test_zero_exchanges_raises(self, isolated_store):
        lid = _seed_learner(exchanges=0)
        with pytest.raises(ValueError, match="used all 50 free exchanges"):
            submit_code(learner_id=lid, code="print(1)")

    def test_paid_tier_skips_all_limits(self, isolated_store):
        lid = _seed_learner(tier="paid", exchanges=-1, code_subs=999)
        result = submit_code(learner_id=lid, code="print('ok')")
        assert result["stdout"].strip() == "ok"
        state = json.loads(store.LEARNER_STATE_FILE.read_text())
        assert state[lid]["exchanges_remaining"] == -1
        assert state[lid]["code_submissions_today"] == 999
