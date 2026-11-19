"""open_pull_request: commit changes to an agent branch, push it, and open a PR (task B6)."""

import re
import subprocess
from pathlib import Path
from typing import Protocol

from pydantic import Field, ValidationError

from agent.tools.base import ErrorType, StrictArgs, ToolResult

BRANCH_RE = re.compile(r"^agent/[a-z0-9][a-z0-9_-]{0,60}$")
GIT_TIMEOUT_S = 60
GIT_IDENTITY = ["-c", "user.name=migration-agent", "-c", "user.email=agent@localhost"]
NETWORK_PREFIXES = ("http://", "https://", "ssh://", "git@")


class PullRequestApi(Protocol):
    def open_pr(self, branch: str, title: str, body: str) -> dict: ...


class OpenPullRequestArgs(StrictArgs):
    branch: str
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(max_length=5000)


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *GIT_IDENTITY, *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=GIT_TIMEOUT_S,
    )


def make_open_pull_request(pr_api: PullRequestApi):
    """Build open_pull_request around the PR API. The API is injected, like the model."""

    def open_pull_request(workspace: str, args: dict) -> ToolResult:
        try:
            parsed = OpenPullRequestArgs.model_validate(args)
        except ValidationError as e:
            return ToolResult.failure(
                ErrorType.BAD_ARGUMENTS,
                f"Invalid arguments: {e.errors()[0]['msg']}. Use 'branch', 'title' and 'body'.",
            )

        if not BRANCH_RE.match(parsed.branch):
            return ToolResult.failure(
                ErrorType.BAD_ARGUMENTS,
                "Branch names must start with 'agent/' and use lowercase letters, digits, '-' or '_' "
                "(for example 'agent/utcnow-migration').",
            )

        root = Path(workspace).resolve()

        remote = _git(root, "remote", "get-url", "origin")
        if remote.returncode != 0:
            return ToolResult.failure(ErrorType.INTERNAL, "The workspace has no 'origin' remote. Ask for the sandbox to be recreated.")
        if remote.stdout.strip().startswith(NETWORK_PREFIXES):
            return ToolResult.failure(
                ErrorType.NOT_ALLOWED,
                "The 'origin' remote is a network address. Pull requests go only to the local sandbox remote.",
            )

        if _git(root, "switch", "-c", parsed.branch).returncode != 0:
            # The branch may already exist from an earlier call, so switch to it instead.
            if _git(root, "switch", parsed.branch).returncode != 0:
                return ToolResult.failure(ErrorType.INTERNAL, f"Could not switch to branch '{parsed.branch}'.")

        _git(root, "add", "-A")
        commit = _git(root, "commit", "-m", parsed.title)
        output = commit.stdout + commit.stderr
        if commit.returncode != 0 and "nothing to commit" not in output:
            return ToolResult.failure(ErrorType.INTERNAL, f"Commit failed: {output.strip()[-300:]}")

        push = _git(root, "push", "-u", "origin", parsed.branch)
        if push.returncode != 0:
            return ToolResult.failure(ErrorType.INTERNAL, f"Push failed: {push.stderr.strip()[-300:]}")

        pr = pr_api.open_pr(parsed.branch, parsed.title, parsed.body)
        return ToolResult.success({"branch": parsed.branch, "pr": pr})

    return open_pull_request