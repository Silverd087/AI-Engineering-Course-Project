import os

import pytest

from agent.tools.base import ErrorType
from agent.tools.list_files import list_files


@pytest.fixture
def ws(tmp_path):
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "pkg" / "b.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("docs\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    return tmp_path


def test_finds_files_matching_glob(ws):
    result = list_files(str(ws), {"glob": "src/**/*.py"})
    assert result.ok
    assert result.result["files"] == ["src/a.py", "src/pkg/b.py"]


def test_git_folder_is_never_listed(ws):
    result = list_files(str(ws), {"glob": "**/*"})
    assert not any(f.startswith(".git") for f in result.result["files"])


@pytest.mark.parametrize("glob", ["../*", "src/../../*", "/etc/*", "C:/*", ""])
def test_unsafe_globs_are_refused(ws, glob):
    result = list_files(str(ws), {"glob": glob})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


def test_unknown_argument_is_rejected(ws):
    result = list_files(str(ws), {"glob": "*", "sneaky": "x"})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


def test_symlink_pointing_outside_is_skipped(ws, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.txt").write_text("top secret\n", encoding="utf-8")
    try:
        os.symlink(outside / "secret.txt", ws / "link.txt")
    except OSError:
        pytest.skip("symlinks need admin or Developer Mode on Windows")
    result = list_files(str(ws), {"glob": "*.txt"})
    assert "link.txt" not in result.result["files"]