"""Scripted approvers (task C3). They answer the checkpoint pause in place of a human.

An approver takes the checkpoint payload ({"tool", "args", "diff"}) and returns "y", "n" or "q".
Every decision is recorded in `decisions`, so the trace can show what the approver did.
"""

from fnmatch import fnmatch

APPROVER_NAMES = ("approve_all", "reject_first_write", "reject_outside_allowed", "quit_at_first_write")


def _inside_allowed(payload: dict, allowed_files: list[str]) -> bool:
    if payload["tool"] != "edit_file":
        return True  # a pull request has no file path, so it is not a file outside the allowed set
    path = str(payload["args"].get("path", "")).replace("\\", "/")
    return any(fnmatch(path, pattern) for pattern in allowed_files)


def make_approver(name: str, allowed_files: list[str]):
    if name not in APPROVER_NAMES:
        raise ValueError(f"Unknown approver {name!r}. Use one of: {', '.join(APPROVER_NAMES)}.")

    decisions: list[str] = []

    def decide(payload: dict) -> str:
        if name == "approve_all":
            answer = "y"
        elif name == "reject_first_write":
            answer = "n" if not decisions else "y"
        elif name == "quit_at_first_write":
            answer = "q"
        else:  # reject_outside_allowed
            answer = "y" if _inside_allowed(payload, allowed_files) else "n"
        decisions.append(answer)
        return answer

    decide.decisions = decisions
    return decide