import os
from pathlib import Path

import pytest

from sandbox.manager import PathEscapeError, resolve_in_workspace


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    workspace = tmp_path / "ws"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "a.py").write_text("x = 1\n")
    return workspace

@pytest.mark.parametrize(
    ("agent_path", "expected_rel_path"),
    [
        ("src/a.py", "src/a.py"),
        ("src/../src/a.py", "src/a.py"),
        ("src/new_file.py", "src/new_file.py"),
        ("./src/a.py", "src/a.py"),
        ("src\\a.py", "src/a.py"),
        # "." is the workspace root itself. Allowed on purpose: list_files and
        # search_code need to start from the repo root. It is still safe because
        # it resolves to the workspace, which is_relative_to(ws) accepts.
        (".", "."),
    ],
)
def test_resolve_in_workspace_allowed_paths(ws,agent_path,expected_rel_path):
    result = resolve_in_workspace(ws,agent_path)
    assert result == (ws/expected_rel_path).resolve()

    
@pytest.mark.parametrize(
    "agent_path",
    [
        pytest.param("../outside.txt", id="plain-climb-out"),
        pytest.param("src/../../x", id="disguised-climb-out"),
        pytest.param("", id="empty"),
        pytest.param("/etc/passwd", id="posix-absolute"),
        pytest.param("C:\\Windows\\win.ini", id="windows-absolute"),
        pytest.param("C:foo", id="windows-drive-relative"),
        pytest.param("\\foo", id="windows-root-relative"),
        pytest.param(".git/config", id="forbidden-git-top-level"),
        pytest.param("src/../.git/config", id="forbidden-git-disguised-top-level"),
        pytest.param(".GIT/config", id="forbidden-git-uppercase"),
        pytest.param("src/.git/x", id="forbidden-git-nested"),
        pytest.param("src/a.py\x00", id="null-byte"),
        
    ],
)
def test_resolve_in_workspace_rejected_paths(ws,agent_path):
    with pytest.raises(PathEscapeError):
        resolve_in_workspace(ws, agent_path)

def test_resolve_in_workspace_rejected_sibling_path(ws):
    secret_path = (ws.parent / "ws_evil" / "x.txt")
    secret_path.parent.mkdir()
    secret_path.touch()
    with pytest.raises(PathEscapeError):
        resolve_in_workspace(ws, "../ws_evil/x.txt")


def test_resolve_in_workspace_symlink_escape(ws):
    target = ws.parent / "outside_secret_dir"
    target.mkdir()
    (target / "secret.txt").write_text("top secret\n")
    link = ws / "src" / "link"

    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
         pytest.skip("symlinks need admin / Developer Mode on Windows")
    with pytest.raises(PathEscapeError):
        resolve_in_workspace(ws,"src/link/secret.txt")

def test_resolve_in_workspace_workspace_not_resolved_format(ws):
    result = resolve_in_workspace(ws/ "src" / "..", 'src/a.py')
    assert result == (ws/'src/a.py').resolve()