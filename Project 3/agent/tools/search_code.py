"""search_code: find lines matching a regex in the workspace (task B4).

The search runs in a child process with a time limit, because Python's re module cannot
be interrupted, and a catastrophic regex would otherwise hang the whole run.
"""

import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

from pydantic import Field, ValidationError

from agent.tools.base import ErrorType, StrictArgs, ToolResult

MAX_PATTERN_CHARS = 200
SEARCH_TIMEOUT_S = 5
PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # the folder that contains the 'agent' package


class SearchCodeArgs(StrictArgs):
    pattern: str = Field(min_length=1, max_length=MAX_PATTERN_CHARS)
    glob: str = "**/*"  # which files to search, relative to the repository root


def search_code(workspace: str, args: dict) -> ToolResult:
    try:
        parsed = SearchCodeArgs.model_validate(args)
    except ValidationError as e:
        return ToolResult.failure(
            ErrorType.BAD_ARGUMENTS,
            f"Invalid arguments: {e.errors()[0]['msg']}. Use 'pattern' and optionally 'glob'.",
        )

    try:
        re.compile(parsed.pattern)
    except re.error as e:
        return ToolResult.failure(
            ErrorType.BAD_ARGUMENTS,
            f"'{parsed.pattern}' is not a valid regular expression ({e}). Simplify it or escape special characters.",
        )

    pattern = parsed.glob.replace("\\", "/")
    if (
        not pattern
        or PurePosixPath(pattern).is_absolute()
        or PureWindowsPath(pattern).drive
        or ".." in PurePosixPath(pattern).parts
    ):
        return ToolResult.failure(
            ErrorType.BAD_ARGUMENTS,
            "The glob must be relative to the repository root, such as 'src/**/*.py'. Do not use '..' or absolute paths.",
        )

    request = json.dumps({"workspace": str(workspace), "pattern": parsed.pattern, "glob": parsed.glob})
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "agent.tools.search_worker"],
            input=request,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=PACKAGE_ROOT,
            timeout=SEARCH_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return ToolResult.failure(
            ErrorType.TIMEOUT,
            f"The search took longer than {SEARCH_TIMEOUT_S} seconds and was stopped. Use a simpler pattern.",
        )

    if proc.returncode != 0:
        return ToolResult.failure(
            ErrorType.INTERNAL,
            "The search failed unexpectedly. Try a simpler pattern or another tool.",
        )
    return ToolResult.success(json.loads(proc.stdout))