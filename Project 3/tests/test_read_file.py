import pytest

from agent.tools.base import ErrorType
from agent.tools.read_file import read_file


@pytest.fixture
def ws(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    return tmp_path


def test_reads_whole_file(ws):
    result = read_file(str(ws), {"path": "src/a.py"})
    assert result.ok
    assert result.result["content"] == "one\ntwo\nthree\nfour"
    assert result.result["total_lines"] == 4


def test_reads_line_range(ws):
    result = read_file(str(ws), {"path": "src/a.py", "start_line": 2, "end_line": 3})
    assert result.result["content"] == "two\nthree"
    assert result.result["first_line"] == 2


def test_missing_file_is_not_found(ws):
    result = read_file(str(ws), {"path": "src/missing.py"})
    assert result.error_type == ErrorType.NOT_FOUND


def test_path_outside_workspace_is_refused(ws):
    result = read_file(str(ws), {"path": "../secret.txt"})
    assert result.error_type == ErrorType.OUTSIDE_WORKSPACE


def test_unknown_argument_is_rejected(ws):
    result = read_file(str(ws), {"path": "src/a.py", "sneaky": "x"})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


def test_backwards_range_is_rejected(ws):
    result = read_file(str(ws), {"path": "src/a.py", "start_line": 3, "end_line": 1})
    assert result.error_type == ErrorType.BAD_ARGUMENTS