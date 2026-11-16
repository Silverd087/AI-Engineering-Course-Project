from pathlib import Path
import pytest

from sandbox.manager import create_workspace,reset
from conftest import assert_valid_workspace


@pytest.fixture
def populated_root(root: Path) -> Path:
    """A root with a workspace, a remote and a PR store: everything reset() should delete."""
    create_workspace("mini", "run1", root)
    (root / "prs").mkdir()
    (root / "prs" / "prs.json").write_text('{"pr": 1}')
    return root

def test_reset_source_file_survive(populated_root):
    root = populated_root
    (root/"manager.py").write_text("some text")
    (root/"README.md").write_text("Readme")
    reset(root)
    assert (root/"manager.py").exists()
    assert (root/"README.md").exists()

def test_reset_empty_root(tmp_path):
    result = reset(tmp_path)
    assert result == []

def test_reset_idempotency(populated_root):
    root = populated_root
    reset(root)
    for name in ("workspaces", "remotes", "prs"):
        assert not (root/name).exists()
    assert reset(root) == []

def test_reset_duplicate_run_id_after_reset(populated_root):
    root = populated_root
    reset(root)                                 
    ws = create_workspace("mini", "run1", root)  
    assert_valid_workspace(ws, root)

def test_reset_deletes_runtime_state(populated_root: Path):
    root = populated_root
    result = reset(root)
    assert set(result) == {root / "workspaces", root / "remotes", root / "prs"}
    for name in ("workspaces", "remotes", "prs"):
        assert not (root / name).exists()          # root / name, not just name
    assert (root / "fixtures" / "mini" / "src" / "a.py").read_text() == "print('hello world')\n"