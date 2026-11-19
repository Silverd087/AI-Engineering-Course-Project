import pytest
import importlib

from agent.tools.base import ErrorType
from agent.tools.run_tests import run_tests


run_tests_module = importlib.import_module("agent.tools.run_tests")

@pytest.fixture
def ws(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    (tmp_path / "tests" / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n", encoding="utf-8")
    (tmp_path / "tests" / "test_env.py").write_text(
        "import os\n\ndef test_no_secrets():\n    assert 'OPENAI_API_KEY' not in os.environ\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_warn.py").write_text(
        "import warnings\n\ndef test_deprecated():\n    warnings.warn('old', DeprecationWarning)\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_slow.py").write_text("import time\n\ndef test_slow():\n    time.sleep(5)\n", encoding="utf-8")
    return tmp_path


def test_passing_target_reports_passed(ws):
    result = run_tests(str(ws), {"target": "tests/test_ok.py"})
    assert result.ok
    assert result.result["passed"] is True
    assert result.result["exit_code"] == 0


def test_failing_target_reports_failure_with_output(ws):
    result = run_tests(str(ws), {"target": "tests/test_bad.py"})
    assert result.ok
    assert result.result["passed"] is False
    assert "test_bad" in result.result["output"]


def test_deprecation_warning_fails_the_test(ws):
    result = run_tests(str(ws), {"target": "tests/test_warn.py"})
    assert result.result["passed"] is False


def test_secrets_are_not_visible_to_tests(ws, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    result = run_tests(str(ws), {"target": "tests/test_env.py"})
    assert result.result["passed"] is True


def test_timeout_is_reported(ws, monkeypatch):
    monkeypatch.setattr(run_tests_module, "TIMEOUT_S", 1)
    result = run_tests(str(ws), {"target": "tests/test_slow.py"})
    assert result.error_type == ErrorType.TIMEOUT


def test_target_outside_workspace_is_refused(ws):
    result = run_tests(str(ws), {"target": "../elsewhere"})
    assert result.error_type == ErrorType.OUTSIDE_WORKSPACE


def test_missing_target_is_not_found(ws):
    result = run_tests(str(ws), {"target": "tests/missing.py"})
    assert result.error_type == ErrorType.NOT_FOUND