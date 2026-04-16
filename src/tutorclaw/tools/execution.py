from __future__ import annotations

import subprocess
import sys
from typing import Annotated, TypedDict

from pydantic import Field

from tutorclaw.store import check_tier, spend_code_submission

_BLOCKED_IMPORTS = ("os", "subprocess", "shutil")
_BLOCKED_BUILTINS = ("open(",)

_MSG_SUBMISSIONS_EXHAUSTED = (
    "You have used all 10 free code submissions for today. "
    "Call get_upgrade_url to upgrade, or try again tomorrow."
)
_MSG_EXCHANGES_EXHAUSTED = (
    "You have used all 50 free exchanges for today. "
    "Call get_upgrade_url to upgrade, or try again tomorrow."
)


class CodeExecutionResult(TypedDict):
    stdout: str
    stderr: str
    timed_out: bool
    blocked_reason: str | None


def _safety_check(code: str) -> str | None:
    """Return a human-readable reason if the code should be blocked, else None."""
    for module in _BLOCKED_IMPORTS:
        # Match both `import os` and `from os import ...`
        if f"import {module}" in code or f"from {module}" in code:
            return f"import '{module}' is not allowed in the sandbox"
    for pattern in _BLOCKED_BUILTINS:
        if pattern in code:
            return "open() for file access is not allowed in the sandbox"
    return None


def submit_code(
    learner_id: Annotated[
        str,
        Field(
            description="The learner's unique ID.",
            min_length=1,
        ),
    ],
    code: Annotated[
        str,
        Field(
            description=(
                "The Python source code submitted by the learner. "
                "Must not import os, subprocess, or shutil, "
                "and must not call open() for file access."
            ),
            min_length=1,
        ),
    ],
) -> CodeExecutionResult:
    """Execute a learner's Python code in a sandbox and return stdout, stderr, and execution status.

    WHEN to call: When a learner submits Python code to run, typically during the modify or make PRIMM-Lite stages.
    NEVER call for non-code messages — use assess_response to evaluate natural-language answers instead.
    Related: assess_response (evaluate text answers), get_exercises (get problems that may require code submissions).
    """
    tier_info = check_tier(learner_id)
    if "error" in tier_info:
        raise ValueError(tier_info["error"])

    if tier_info["tier"] == "free":
        if tier_info["code_submissions_today"] >= 10:
            raise ValueError(_MSG_SUBMISSIONS_EXHAUSTED)
        if tier_info["exchanges_remaining"] == 0:
            raise ValueError(_MSG_EXCHANGES_EXHAUSTED)
        spend_code_submission(learner_id)

    blocked = _safety_check(code)
    if blocked:
        return {
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "blocked_reason": blocked,
        }

    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
            "blocked_reason": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "",
            "timed_out": True,
            "blocked_reason": None,
        }
