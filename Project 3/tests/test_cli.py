import pytest

from agent.__main__ import ask_human, find_scenario


def test_ask_human_repeats_until_valid(monkeypatch, capsys):
    answers = iter(["maybe", "Y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert ask_human({"tool": "edit_file", "diff": "-a\n+b"}) == "y"
    assert "Please type y, n or q." in capsys.readouterr().out

    
def test_unknown_scenario_is_a_clear_error():
    with pytest.raises(SystemExit, match="No scenario named"):
        find_scenario("does_not_exist")


def test_known_scenario_is_found():
    assert find_scenario("utcnow_fault_tests_timeout").fixture == "billing_service"