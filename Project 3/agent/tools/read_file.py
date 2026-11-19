"""read_file: return the text of one file in the workspace (task B4)."""

from pathlib import Path

from pydantic import ValidationError

from agent.tools.base import ErrorType, StrictArgs, ToolResult
from sandbox.manager import PathEscapeError, resolve_in_workspace

MAX_CHARS = 20_000  # the model never sees more than this from one read


class ReadFileArgs(StrictArgs):
    path: str
    start_line: int | None = None  # 1-based, inclusive
    end_line: int | None = None    # 1-based, inclusive


def read_file(workspace: str, args: dict) -> ToolResult:
    try:
        parsed = ReadFileArgs.model_validate(args)
    except ValidationError as e:
        return ToolResult.failure(
            ErrorType.BAD_ARGUMENTS,
            f"Invalid arguments: {e.errors()[0]['msg']}. Use only 'path', 'start_line' and 'end_line'.",
        )

    if parsed.start_line is not None and parsed.end_line is not None and parsed.start_line > parsed.end_line:
        return ToolResult.failure(
            ErrorType.BAD_ARGUMENTS,
            f"start_line ({parsed.start_line}) is greater than end_line ({parsed.end_line}). Swap them.",
        )

    try:
        target = resolve_in_workspace(Path(workspace), parsed.path)
    except PathEscapeError:
        return ToolResult.failure(
            ErrorType.OUTSIDE_WORKSPACE,
            f"'{parsed.path}' is outside the workspace. Use a path inside the repository.",
        )

    if not target.is_file():
        return ToolResult.failure(
            ErrorType.NOT_FOUND,
            f"File '{parsed.path}' not found. Use list_files to see available paths.",
        )

    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    start = (parsed.start_line or 1) - 1
    end = parsed.end_line or len(lines)
    content = "\n".join(lines[start:end])

    return ToolResult.success({
        "path": parsed.path,
        "total_lines": len(lines),
        "first_line": start + 1,
        "content": content[:MAX_CHARS],
        "truncated": len(content) > MAX_CHARS,
    })