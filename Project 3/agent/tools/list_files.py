"""list_files: find files in the workspace by glob pattern (task B4)."""

from pathlib import Path, PurePosixPath, PureWindowsPath

from pydantic import ValidationError

from agent.tools.base import ErrorType, StrictArgs, ToolResult

MAX_RESULTS = 500


class ListFilesArgs(StrictArgs):
    glob: str  # relative to the repository root, e.g. "src/**/*.py"


def list_files(workspace: str, args: dict) -> ToolResult:
    try:
        parsed = ListFilesArgs.model_validate(args)
    except ValidationError as e:
        return ToolResult.failure(
            ErrorType.BAD_ARGUMENTS,
            f"Invalid arguments: {e.errors()[0]['msg']}. Use only the 'glob' field.",
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
    for path in root.glob(pattern):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root):
            continue  # a symlink that points outside the workspace
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        matches.append(rel.as_posix())

    matches.sort()
    return ToolResult.success({
        "files": matches[:MAX_RESULTS],
        "total": len(matches),
        "truncated": len(matches) > MAX_RESULTS,
    })