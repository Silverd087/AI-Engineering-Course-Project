import pytest

from eval.approvers import APPROVER_NAMES, make_approver

ALLOWED = ["src/**"]


def edit(path):
    return {"tool": "edit_file", "args": {"path": path, "old": "a", "new": "b"}, "diff": ""}


def pr():
    return {"tool": "open_pull_request", "args": {"branch": "agent/x", "title": "t", "body": "b"}, "diff": ""}


def test_approve_all_says_yes_every_time():
    approve = make_approver("approve_all", ALLOWED)
    assert [approve(edit("src/a.py")), approve(edit("tests/t.py")), approve(pr())] == ["y", "y", "y"]


def test_reject_first_write_rejects_once_then_approves():
    decide = make_approver("reject_first_write", ALLOWED)
    assert decide(edit("src/a.py")) == "n"
    assert decide(edit("src/a.py")) == "y"
    assert decide.decisions == ["n", "y"]


def test_quit_at_first_write_quits():
    decide = make_approver("quit_at_first_write", ALLOWED)
    assert decide(edit("src/a.py")) == "q"


def test_reject_outside_allowed_only_rejects_disallowed_files():
    decide = make_approver("reject_outside_allowed", ALLOWED)
    assert decide(edit("src/a.py")) == "y"
    assert decide(edit("tests/test_a.py")) == "n"
    assert decide(pr()) == "y"


def test_windows_paths_are_matched_as_allowed():
    decide = make_approver("reject_outside_allowed", ALLOWED)
    assert decide(edit("src\\pkg\\a.py")) == "y"


def test_unknown_approver_name_is_an_error():
    with pytest.raises(ValueError, match="Unknown approver"):
        make_approver("nobody", ALLOWED)


def test_all_names_are_accepted():
    for name in APPROVER_NAMES:
        assert callable(make_approver(name, ALLOWED))