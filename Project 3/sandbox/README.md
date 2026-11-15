# Sandbox

Everything the agent writes goes here, never to a real repository or to GitHub.

| Folder | What | Committed? |
|---|---|---|
| `fixtures/` | sample repos the agent migrates (source of truth, never modified) | yes |
| `workspaces/<run_id>/` | throwaway copy of a fixture for one run, a git repo | no |
| `remotes/<run_id>.git` | local bare git remote the agent pushes its branch to | no |
| `prs/prs.json` | mock PR API store | no |

**Create** a workspace: `uv run python -m sandbox.manager create --fixture billing_service`
**Reset** everything: `make sandbox-reset` (or `uv run python -m sandbox.manager reset`)

Safety: every tool resolves paths through the path jail in `manager.py`; there is no shell tool and no network access.
