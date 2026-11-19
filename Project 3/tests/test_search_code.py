import pytest

from agent.tools.base import ErrorType
from agent.tools.search_code import search_code


@pytest.fixture
def ws(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("import os\nx = datetime.utcnow()\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("utcnow is deprecated\n", encoding="utf-8")
    (tmp_path / "src" / "image.bin").write_bytes(b"utcnow\x00\x01")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("utcnow\n", encoding="utf-8")
    return tmp_path


def test_finds_matching_line_with_path_and_number(ws):
    result = search_code(str(ws), {"pattern": "utcnow", "glob": "src/**/*.py"})
    assert result.ok
    assert result.result["matches"] == [{"path": "src/a.py", "line": 2, "text": "x = datetime.utcnow()"}]


def test_default_glob_searches_everything_except_git_and_binary(ws):
    result = search_code(str(ws), {"pattern": "utcnow"})
    paths = [m["path"] for m in result.result["matches"]]
    assert sorted(paths) == ["notes.txt", "src/a.py"]
    

def test_invalid_regex_is_refused(ws):
    result = search_code(str(ws), {"pattern": "utcnow("})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


def test_overlong_pattern_is_refused(ws):
    result = search_code(str(ws), {"pattern": "a" * 201})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


@pytest.mark.parametrize("glob", ["../*", "/etc/*", "C:/*", ""])
def test_unsafe_glob_is_refused(ws, glob):
    result = search_code(str(ws), {"pattern": "x", "glob": glob})
    assert result.error_type == ErrorType.BAD_ARGUMENTS


def test_results_are_capped_but_total_is_kept(tmp_path):
    (tmp_path / "big.py").write_text("hit\n" * 150, encoding="utf-8")
    result = search_code(str(tmp_path), {"pattern": "hit"})
    assert len(result.result["matches"]) == 100
    assert result.result["total"] == 150
    assert result.result["truncated"] is True