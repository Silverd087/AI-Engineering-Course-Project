"""run_tests: run the repository's tests inside the workspace (task B5)."""

import os
import subprocess
import sys
from pathlib import Path

from pydantic import ValidationError

from agent.tools.base import ErrorType, StrictArgs, ToolResult
from sandbox.manager import PathEscapeError, resolve_in_workspace

TIMEOUT_S = 120
MAX_OUTPUT_CHARS = 4_000
SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


class RunTestsArgs(StrictArgs):
    target: str | None = None  # a test file or folder inside the repo; None runs everything


def _clean_env() -> dict:
    # The repo's test code runs with this environment, so secrets are removed first.
    return {k: v for k, v in os.environ.items() if not any(m in k.upper() for m in SECRET_MARKERS)}


def run_tests(workspace: str, args: dict) -> ToolResult:
    try:
        parsed = RunTestsArgs.model_validate(args)
    except ValidationError as e:
        return ToolResult.failure(
            ErrorType.BAD_ARGUMENTS,
            f"Invalid arguments: {e.errors()[0]['msg']}. Use only the 'target' field.",
        )

    root = Path(workspace).resolve()
    target = str(root)
    if parsed.target:
        try:
            resolved = resolve_in_workspace(root, parsed.target)
        except PathEscapeError:
            return ToolResult.failure(
                ErrorType.OUTSIDE_WORKSPACE,
                f"'{parsed.target}' is outside the workspace. Use a test path inside the repository.",
            )
        if not resolved.exists():
            return ToolResult.failure(
                ErrorType.NOT_FOUND,
                f"Test path '{parsed.target}' not found. Use list_files to find the test files.",
            )
        target = str(resolved)

    command = [sys.executable, "-m", "pytest", "-W", "error", "-q", "-p", "no:cacheprovider", target]
    try:
        proc = subprocess.run(
            command,
            cwd=root,
            env=_clean_env(),
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return ToolResult.failure(
            ErrorType.TIMEOUT,
            f"The test run took longer than {TIMEOUT_S} seconds and was stopped. Run a smaller target.",
        )

    output = proc.stdout + proc.stderr
    return ToolResult.success({
        "passed": proc.returncode == 0,
        "exit_code": proc.returncode,
        "output": output[-MAX_OUTPUT_CHARS:],
        "truncated": len(output) > MAX_OUTPUT_CHARS,
    })