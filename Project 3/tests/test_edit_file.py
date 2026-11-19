import pytest

from agent.tools.base import ErrorType
from agent.tools.edit_file import make_edit_file

ALLOWED = ["src/**"]


@pytest.fixture
def ws(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    (tmp_path / "src" / "dup.py").write_text("v = 0\nv = 0\n", encoding="utf-8")
    (tmp_path / "src" / "crlf.py").write_bytes(b"a = 1\r\nb = 2\r\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def edit(ws):
    return make_edit_file(ALLOWED)


def test_replaces_text_once(ws, edit):
    result = edit(str(ws), {"path": "src/a.py", "old": "y = 2", "new": "y = 3"})
    assert result.ok and result.result["changed"] is True
    assert (ws / "src" / "a.py").read_text(encoding="utf-8") == "x = 1\ny = 3\n"


def test_preserves_windows_line_endings(ws, edit):
    edit(str(ws), {"path": "src/crlf.py", "old": "a = 1", "new": "a = 9"})
    assert (ws / "src" / "crlf.py").read_bytes() == b"a = 9\r\nb = 2\r\n"


def test_file_outside_allowed_patterns_is_refused(ws, edit):
    result = edit(str(ws), {"path": "tests/test_a.py", "old": "x = 1", "new": "x = 2"})
    assert result.error_type == ErrorType.NOT_ALLOWED
    assert (ws / "tests" / "test_a.py").read_text(encoding="utf-8") == "x = 1\n"


def test_path_outside_workspace_is_refused(ws, edit):
    result = edit(str(ws), {"path": "../x.py", "old": "a", "new": "b"})
    assert result.error_type == ErrorType.OUTSIDE_WORKSPACE


def test_missing_text_is_no_match_and_file_is_unchanged(ws, edit):
    result = edit(str(ws), {"path": "src/a.py", "old": "z = 9", "new": "z = 8"})
    assert result.error_type == ErrorType.NO_MATCH
    assert (ws / "src" / "a.py").read_text(encoding="utf-8") == "x = 1\ny = 2\n"


def test_repeated_text_is_ambiguous_and_file_is_unchanged(ws, edit):
    result = edit(str(ws), {"path": "src/dup.py", "old": "v = 0", "new": "v = 1"})
    assert result.error_type == ErrorType.AMBIGUOUS_MATCH
    assert (ws / "src" / "dup.py").read_text(encoding="utf-8") == "v = 0\nv = 0\n"


def test_already_applied_edit_is_a_no_op(ws, edit):
    result = edit(str(ws), {"path": "src/a.py", "old": "x = 0", "new": "x = 1"})
    assert result.ok and result.result["changed"] is False


def test_new_text_containing_old_text_is_refused(ws, edit):
    result = edit(str(ws), {"path": "src/a.py", "old": "x", "new": "xx"})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


def test_unknown_argument_is_rejected(ws, edit):
    result = edit(str(ws), {"path": "src/a.py", "old": "x", "new": "y", "sneaky": 1})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


def test_missing_file_is_not_found(ws, edit):
    result = edit(str(ws), {"path": "src/missing.py", "old": "a", "new": "b"})
    assert result.error_type == ErrorType.NOT_FOUND