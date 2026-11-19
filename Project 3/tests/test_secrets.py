import importlib

import pytest

from agent.tools.base import ErrorType
from agent.tools.denylist import is_secret_path
from agent.tools.list_files import list_files
from agent.tools.read_file import read_file
from agent.tools.search_code import search_code

search_code_module = importlib.import_module("agent.tools.search_code")


@pytest.fixture
def ws(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("token = 'utcnow'\n", encoding="utf-8")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-test utcnow\n", encoding="utf-8")
    (tmp_path / "deploy.pem").write_text("utcnow\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("name", [".env", ".env.local", "deploy.pem", "id_rsa", "credentials.json", "api.key"])
def test_secret_names_are_detected(name):
    assert is_secret_path(name)
    assert is_secret_path(f"config/{name}")


@pytest.mark.parametrize("name", ["src/app.py", ".envrc", "environment.py", "keyboard.py"])
def test_normal_names_are_not_detected(name):
    assert not is_secret_path(name)


def test_read_file_refuses_a_secret(ws):
    result = read_file(str(ws), {"path": ".env"})
    assert result.error_type == ErrorType.NOT_ALLOWED
    assert "OPENAI_API_KEY" not in result.to_json()


def test_list_files_hides_secrets(ws):
    assert list_files(str(ws), {"glob": "**/*"}).result["files"] == ["src/app.py"]


def test_search_code_skips_secrets(ws):
    result = search_code(str(ws), {"pattern": "utcnow"})
    assert [m["path"] for m in result.result["matches"]] == ["src/app.py"]


def test_catastrophic_regex_is_stopped_by_the_time_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(search_code_module, "SEARCH_TIMEOUT_S", 1)
    (tmp_path / "evil.txt").write_text("a" * 40 + "!\n", encoding="utf-8")
    result = search_code(str(tmp_path), {"pattern": "(a+)+$"})
    assert result.error_type == ErrorType.TIMEOUT