"""edit_file: replace exact text in one allowed file (task B6)."""

from fnmatch import fnmatch
from pathlib import Path

from pydantic import Field, ValidationError

from agent.tools.base import ErrorType, StrictArgs, ToolResult
from sandbox.manager import PathEscapeError, resolve_in_workspace


class EditFileArgs(StrictArgs):
    path: str
    old: str = Field(min_length=1)
    new: str


def make_edit_file(allowed_files: list[str]):
    """Build edit_file for one migration. allowed_files are glob patterns from the spec, e.g. ['src/**']."""

    def edit_file(workspace: str, args: dict) -> ToolResult:
        try:
            parsed = EditFileArgs.model_validate(args)
        except ValidationError as e:
            return ToolResult.failure(
                ErrorType.BAD_ARGUMENTS,
                f"Invalid arguments: {e.errors()[0]['msg']}. Use 'path', 'old' and 'new'.",
            )

        if parsed.old in parsed.new:
            return ToolResult.failure(
                ErrorType.BAD_ARGUMENTS,
                "The new text contains the old text, so repeating this edit would keep changing the file. "
                "Use an 'old' text that does not appear inside 'new'.",
            )

        root = Path(workspace).resolve()
        try:
            target = resolve_in_workspace(root, parsed.path)
        except PathEscapeError:
            return ToolResult.failure(
                ErrorType.OUTSIDE_WORKSPACE,
                f"'{parsed.path}' is outside the workspace. Edit only files inside the repository.",
            )

        rel = target.relative_to(root).as_posix()
        if not any(fnmatch(rel, pattern) for pattern in allowed_files):
            return ToolResult.failure(
                ErrorType.NOT_ALLOWED,
                f"'{parsed.path}' is not a file this migration may edit. Allowed: {', '.join(allowed_files)}.",
            )

        if not target.is_file():
            return ToolResult.failure(
                ErrorType.NOT_FOUND,
                f"File '{parsed.path}' not found. Use list_files to see available paths.",
            )

        # newline="" keeps \r\n line endings exactly as they are on disk.
        with target.open("r", encoding="utf-8", newline="") as f:
            text = f.read()

        count = text.count(parsed.old)
        if count == 0:
            if parsed.new in text:
                return ToolResult.success({"changed": False, "note": "The change was already applied."})
            return ToolResult.failure(
                ErrorType.NO_MATCH,
                f"The 'old' text was not found in '{parsed.path}'. Use read_file to copy the exact current text.",
            )
        if count > 1:
            return ToolResult.failure(
                ErrorType.AMBIGUOUS_MATCH,
                f"The 'old' text appears {count} times in '{parsed.path}'. Include more surrounding lines so it matches once.",
            )

        with target.open("w", encoding="utf-8", newline="") as f:
            f.write(text.replace(parsed.old, parsed.new, 1))
        return ToolResult.success({"changed": True, "path": rel})

    return edit_file