import subprocess
from pathlib import Path 
import pytest

def assert_valid_workspace(ws,root):
    assert (ws.path / "src" / "a.py").read_text() == "print('hello world')\n"
    assert not (ws.path / "src" / "__pycache__").exists()
    assert not (root / "fixtures" / "mini" / ".git").exists()
    assert len(git(ws.path, "log", "--oneline").splitlines()) == 1
    assert git(ws.path,"status","--porcelain") == ""
    assert git(ws.path, "rev-parse", "main") == git(ws.remote, "rev-parse", "main")

def git(cwd: Path, *args: str) -> str:
    """Run git in the test to inspect what create_workspace built."""
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()
@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A fake sandbox root containing one sandbox fixture called 'mini'."""
    src = tmp_path / "fixtures" / "mini" / "src"
    src.mkdir(parents=True)
    (src / "a.py").write_text("print('hello world')\n")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "junk.pyc").write_text("junk")
    return tmp_path