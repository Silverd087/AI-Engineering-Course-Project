"""Workspace manager (task B2): `uv run python -m sandbox.manager {create,reset}`.

TODO:
- create_workspace(fixture, run_id) -> Path: copy sandbox/fixtures/<fixture> to
  sandbox/workspaces/<run_id>, `git init` + initial commit, add a local bare
  remote in sandbox/remotes/<run_id>.git
- resolve_in_workspace(workspace, path) -> Path: the path jail; reject absolute
  paths and anything that resolves outside the workspace
- reset(): delete sandbox/workspaces, sandbox/remotes and sandbox/prs
"""
from pathlib import Path,PurePosixPath, PureWindowsPath

class PathEscapeError(Exception):
  """Raised when a path resolves outside the allowed workspace."""

def create_workspace(fixture,run_id)->Path:
  raise NotImplementedError("Create workspace")

def resolve_in_workspace(workspace:Path, path:str)->Path:
  """
    Return the resolved absolute path of path inside workspace. 
    Raises PathEscapeError if it is empty, contains a null byte, is absolute, 
    resolves outside the workspace, or points into .git.
  """
  if not path:
    raise PathEscapeError("Path cannot be empty")
  path = path.replace("\\", "/")
  if "\x00" in path:
    raise PathEscapeError("Null bytes are not allowed in path")
  win_p = PureWindowsPath(path)
  posix_p = PurePosixPath(path)
  if (
    win_p.drive
    or win_p.root        
    or win_p.is_absolute()
    or posix_p.is_absolute()  
  ):
    raise PathEscapeError(f"Absolute or drive-anchored path not allowed: {path!r}")

  ws= workspace.resolve()
  try:
    candidate = (ws/path).resolve()
  except (OSError,ValueError) as e:
    raise PathEscapeError(f"Invalid or inaccessible path: {path!r}") from e
  if not candidate.is_relative_to(ws):
    raise PathEscapeError(f"Path escapes workspace: {path!r}")
  if any(part.lower() == ".git" for part in candidate.relative_to(ws).parts):
    raise PathEscapeError(f"Access to .git is forbidden: {path!r}")
  return candidate

def reset():
  raise NotImplementedError("Reset")

def main() -> None:
    raise SystemExit("Sandbox manager not implemented yet.")


if __name__ == "__main__":
    main()
