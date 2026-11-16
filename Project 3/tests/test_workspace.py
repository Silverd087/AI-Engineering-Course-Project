import subprocess
from pathlib import Path

import pytest

from sandbox.manager import create_workspace,SandboxError
from conftest import assert_valid_workspace

def test_create_workspace_happy_path(root:Path):
    ws = create_workspace("mini", "run1", root=root)
    assert_valid_workspace(ws,root)


def test_create_workspace_clean_clone(root:Path,monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(root / "no_global_config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    ws = create_workspace("mini", "run1", root=root)
    assert_valid_workspace(ws,root)

@pytest.mark.parametrize(
    "run_id",
    [
        pytest.param("", id="empty"),
        pytest.param("../x", id="parent-dir"),
        pytest.param("a/b", id="slash"),
        pytest.param("a b", id="space"),
        pytest.param("run1\n", id="trailing-newline"),
        pytest.param("x"*65, id="too-long"),
    ],
)
def test_create_workspace_bad_run_id(root,run_id):
    with pytest.raises(SandboxError):
        create_workspace("mini",run_id,root)

@pytest.mark.parametrize(
    "fixture",
    [
        pytest.param("../fixtures", id="parent-dir"),
        pytest.param("..\\..", id="backslash-parent"),
        pytest.param("", id="empty"),
    ],
)
def test_create_workspace_bad_fixture(root,fixture):
    with pytest.raises(SandboxError):
        create_workspace(fixture,"run1",root)

def test_create_workspace_missing_fixture(root):
    with pytest.raises(SandboxError):
        create_workspace("nope","run1",root)

def test_create_workspace_duplicate_run(root):
    create_workspace("mini","run1",root)
    with pytest.raises(SandboxError):
        create_workspace("mini","run1",root)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("commit", id="empty-run-id"),
        pytest.param("push", id="plain-climb-out"),
    ],
)
def test_failed_create_leaves_nothing_behind(root, monkeypatch,command):
    import sandbox.manager as m
    real_git = m._git

    def failing_git(cwd, *args):
        if args[0] == command:
            raise subprocess.CalledProcessError(1, ["git", *args], stderr="simulated push failure")
        return real_git(cwd, *args)

    monkeypatch.setattr(m, "_git", failing_git)

    with pytest.raises(SandboxError):
        create_workspace("mini", "run1", root=root)
    assert not (root / "workspaces" / "run1").exists()
    assert not (root / "remotes" / "run1.git").exists()