from pathlib import Path
from types import SimpleNamespace

import sys

import sandbox.manager as manager


def test_reset_command_reports_removed_items(monkeypatch, capsys):
    monkeypatch.setattr(manager, "reset", lambda: [Path("a"), Path("b")])
    monkeypatch.setattr(sys, "argv", ["sandbox.manager", "reset"])
    manager.main()
    assert "Removed 2 item(s)." in capsys.readouterr().out


def test_create_command_uses_given_run_id(monkeypatch, capsys):
    calls = []

    def fake_create(fixture, run_id):
        calls.append((fixture, run_id))
        return SimpleNamespace(path=Path("ws"), remote=Path("remote.git"))

    monkeypatch.setattr(manager, "create_workspace", fake_create)
    monkeypatch.setattr(sys, "argv", ["sandbox.manager", "create", "--fixture", "billing_service", "--run-id", "r1"])
    manager.main()
    assert calls == [("billing_service", "r1")]