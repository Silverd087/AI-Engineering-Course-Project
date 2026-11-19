"""search_code: find lines matching a regex in the workspace (task B4)."""

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from pydantic import Field, ValidationError

from agent.tools.base import ErrorType, StrictArgs, ToolResult

MAX_PATTERN_CHARS = 200
MAX_MATCHES = 100
MAX_LINE_CHARS = 200
MAX_FILE_BYTES = 1_000_000


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
        regex = re.compile(parsed.pattern)
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

    root = Path(workspace).resolve()
    matches = []
    total = 0
    for path in sorted(root.glob(pattern)):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root):
            continue  # a symlink that points outside the workspace
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue  # too large to be source code worth searching
        data = path.read_bytes()
        if b"\x00" in data[:8000]:
            continue  # binary file

        text = data.decode("utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                total += 1
                if len(matches) < MAX_MATCHES:
                    matches.append({
                        "path": rel.as_posix(),
                        "line": number,
                        "text": line.strip()[:MAX_LINE_CHARS],
                    })

    return ToolResult.success({
        "matches": matches,
        "total": total,
        "truncated": total > MAX_MATCHES,
    })