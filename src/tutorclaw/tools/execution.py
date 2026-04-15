from __future__ import annotations

import subprocess
import sys
from typing import Annotated, TypedDict

from pydantic import Field

_BLOCKED_IMPORTS = ("os", "subprocess", "shutil")
_BLOCKED_BUILTINS = ("open(",)


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
    """Run a learner's Python code in a mock sandbox and return stdout and stderr.

    Performs basic safety checks before execution:
    - Rejects imports of os, subprocess, and shutil.
    - Rejects calls to open() for file access.

    Execution is limited to 5 seconds. Returns stdout, stderr, timed_out flag,
    and blocked_reason (non-null when the code was rejected before running).
    """
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
