"""Workspace manager (task B2): `uv run python -m sandbox.manager {create,reset}`.

TODO:
- create_workspace(fixture, run_id) -> Path: copy sandbox/fixtures/<fixture> to
  sandbox/workspaces/<run_id>, `git init` + initial commit, add a local bare
  remote in sandbox/remotes/<run_id>.git
- resolve_in_workspace(workspace, path) -> Path: the path jail; reject absolute
  paths and anything that resolves outside the workspace
- reset(): delete sandbox/workspaces, sandbox/remotes and sandbox/prs
"""
import os
import stat
from pathlib import Path,PurePosixPath, PureWindowsPath
from dataclasses import dataclass
import re
import shutil
import subprocess


_SAFE_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")
_RESETTABLE = ("workspaces", "remotes", "prs")

def _force_remove(func, path, exc):
    """rmtree error handler: git marks object files read-only on Windows.
    Make the file writable, then retry the operation that failed."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def _rmtree(path: Path) -> None:
    """Delete a folder tree. Missing folders are fine; read-only files are handled."""
    if path.exists():
        shutil.rmtree(path, onexc=_force_remove)

SANDBOX_ROOT = Path(__file__).parent

@dataclass(frozen=True)
class Workspace:
    run_id: str
    path: Path
    remote: Path

class SandboxError(Exception):
    """Bad fixture name, bad run id, or workspace already exists."""

class PathEscapeError(Exception):
  """Raised when a path resolves outside the allowed workspace."""

def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()

def create_workspace(fixture:str,run_id:str,root: Path = SANDBOX_ROOT)->Workspace:
  if not re.fullmatch(_SAFE_NAME,run_id):
    raise SandboxError(f"Bad run_id {run_id}")
  if not re.fullmatch(_SAFE_NAME,fixture):
    raise SandboxError(f"Bad fixture {fixture}")
  if not Path(root/"fixtures"/fixture).is_dir():
    raise SandboxError(f"fixture not found {fixture}")
  if Path(root/"workspaces"/run_id).exists():
    raise SandboxError(f"workspace already exists {run_id}")
  if Path(root/"remotes"/f"{run_id}.git").exists():
    raise SandboxError(f"remote repository exists {run_id}")

  fixture_path = root/"fixtures"/fixture
  ws_path = root/"workspaces"/run_id
  remote_path = root/"remotes"/f"{run_id}.git"
  try:
    shutil.copytree(fixture_path, ws_path, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".venv", ".git"))
    _git(ws_path,"init","-b","main")
    _git(ws_path,"config","user.name","Operator Agent")
    _git(ws_path,"config","user.email","agent@sandbox.local")
    _git(ws_path,"config","core.autocrlf","false")
    _git(ws_path,"add","-A")
    _git(ws_path,"commit","-m",f"baseline: fixture {fixture}")
    _git(root,"init","--bare",str(remote_path))
    _git(ws_path,"remote","add","origin",remote_path)
    _git(ws_path,"push","origin","main")
  except subprocess.CalledProcessError as e:
    _rmtree(ws_path); _rmtree(remote_path)
    raise SandboxError(f"git {' '.join(map(str, e.args[1][1:]))} failed: {(e.stderr or '').strip()}") from e
  except Exception as e:
    _rmtree(ws_path)
    _rmtree(remote_path)
    raise SandboxError(f"Failed to create workspace {run_id!r}: {e}") from e

  return Workspace(run_id,ws_path,remote_path)
  


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

def reset(root:Path = SANDBOX_ROOT)->list[Path]:
  """Delete all runtime state under root. Never touches fixtures/ or source files.
  Returns the folders that were actually deleted."""
  result = []
  for name in _RESETTABLE:
    if (root / name).exists():
      _rmtree(root/name)
      result.append(root / name)
  return result
  

   
  
def main() -> None:
    raise SystemExit("Sandbox manager not implemented yet.")


if __name__ == "__main__":
    main()
