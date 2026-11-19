"""Injection planting (task C6). Writes hostile text into the workspace copy before the agent runs.

Only the workspace copy is changed. The fixture is never touched.
"""

from pathlib import Path

from eval.schema import Injection
from sandbox.manager import resolve_in_workspace


def _one_line(text: str) -> str:
    return text.replace("\n", " ").replace('"""', "'''")


def plant_injection(workspace: Path, injection: Injection) -> str:
    """Plant the payload. Returns the workspace-relative path it was written to."""
    surface = injection.surface
    payload = injection.payload

    if surface == "error_message":
        raise ValueError("error_message injection is not supported yet: it needs a tool that returns attacker text.")

    if surface == "test_output":
        rel = "tests/test_injected_output.py"
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"def test_injected_output():\n    assert False, {_one_line(payload)!r}\n", encoding="utf-8")
        return rel

    if surface == "pr_template":
        rel = ".github/PULL_REQUEST_TEMPLATE.md"
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
        return rel

    rel = injection.file or ("README.md" if surface == "readme" else None)
    if rel is None:
        raise ValueError(f"{surface} injection needs a 'file' to plant into.")
    path = resolve_in_workspace(workspace, rel)
    if not path.is_file():
        raise ValueError(f"Cannot plant into '{rel}': the file does not exist in the fixture.")

    if surface == "code_comment":
        text = f"\n# {_one_line(payload)}\n"
    elif surface == "docstring":
        text = f'\n\ndef _maintainer_notes():\n    """{_one_line(payload)}"""\n'
    elif surface == "readme":
        text = f"\n\n{payload}\n"
    else:
        raise ValueError(f"Unknown injection surface {surface!r}.")

    with path.open("a", encoding="utf-8", newline="") as f:
        f.write(text)
    return rel