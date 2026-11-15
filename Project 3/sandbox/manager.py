"""Workspace manager (task B2): `uv run python -m sandbox.manager {create,reset}`.

TODO:
- create_workspace(fixture, run_id) -> Path: copy sandbox/fixtures/<fixture> to
  sandbox/workspaces/<run_id>, `git init` + initial commit, add a local bare
  remote in sandbox/remotes/<run_id>.git
- resolve_in_workspace(workspace, path) -> Path: the path jail; reject absolute
  paths and anything that resolves outside the workspace
- reset(): delete sandbox/workspaces, sandbox/remotes and sandbox/prs
"""


def main() -> None:
    raise SystemExit("Sandbox manager not implemented yet.")


if __name__ == "__main__":
    main()
