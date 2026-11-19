import subprocess

import pytest

from agent.tools.base import ErrorType
from agent.tools.open_pull_request import make_open_pull_request
from sandbox.mock_pr_server import MockPrServer


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", str(remote))
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init")
    git(work, "symbolic-ref", "HEAD", "refs/heads/main")
    (work / "a.py").write_text("x = 1\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-m", "initial")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "origin", "main")
    return work, remote


@pytest.fixture
def pr_api(tmp_path):
    return MockPrServer(tmp_path / "prs.json")


def remote_branches(remote):
    out = subprocess.run(["git", "--git-dir", str(remote), "branch", "--list"], capture_output=True, text=True)
    return out.stdout


def test_commits_pushes_and_opens_pr(repo, pr_api):
    work, remote = repo
    (work / "a.py").write_text("x = 2\n", encoding="utf-8")

    result = make_open_pull_request(pr_api)(
        str(work), {"branch": "agent/utcnow", "title": "Migrate utcnow", "body": "Replaces utcnow."}
    )

    assert result.ok
    prs = pr_api.list_prs()
    assert [(p["branch"], p["title"]) for p in prs] == [("agent/utcnow", "Migrate utcnow")]
    assert "agent/utcnow" in remote_branches(remote)


def test_repeated_call_returns_same_pr(repo, pr_api):
    work, _ = repo
    (work / "a.py").write_text("x = 2\n", encoding="utf-8")
    tool = make_open_pull_request(pr_api)

    first = tool(str(work), {"branch": "agent/utcnow", "title": "Migrate", "body": "b"})
    second = tool(str(work), {"branch": "agent/utcnow", "title": "Migrate", "body": "b"})

    assert first.ok and second.ok
    assert first.result["pr"]["number"] == second.result["pr"]["number"]
    assert len(pr_api.list_prs()) == 1


@pytest.mark.parametrize("branch", ["main", "master", "feature/x", "agent/Bad Name", "agent/" + "a" * 70])
def test_bad_branch_names_are_refused(repo, pr_api, branch):
    work, _ = repo
    result = make_open_pull_request(pr_api)(str(work), {"branch": branch, "title": "t", "body": "b"})
    assert result.error_type == ErrorType.BAD_ARGUMENTS
    assert pr_api.list_prs() == []


def test_network_remote_is_refused(repo, pr_api):
    work, _ = repo
    git(work, "remote", "set-url", "origin", "https://example.com/repo.git")
    result = make_open_pull_request(pr_api)(str(work), {"branch": "agent/x", "title": "t", "body": "b"})
    assert result.error_type == ErrorType.NOT_ALLOWED
    assert pr_api.list_prs() == []


def test_empty_title_is_refused(repo, pr_api):
    work, _ = repo
    result = make_open_pull_request(pr_api)(str(work), {"branch": "agent/x", "title": "", "body": "b"})
    assert result.error_type == ErrorType.BAD_ARGUMENTS