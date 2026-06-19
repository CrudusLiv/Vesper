from pathlib import Path
from unittest.mock import MagicMock
from kernel.app import VesperApp
from kernel.events import Notify, Tick


class _EchoApp(VesperApp):
    name = "echo"
    subscribes = [Notify]
    received: list = []

    def on_notify(self, event: Notify) -> None:
        self.received.append(event)


def test_emit_calls_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    runtime = MagicMock()
    app = _EchoApp(runtime)
    evt = Notify(text="hi")
    app.emit(evt)
    runtime.post_external.assert_called_once_with(evt)


def test_log_does_not_raise(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    runtime = MagicMock()
    app = _EchoApp(runtime)
    app.log("test message")
    captured = capsys.readouterr()
    assert "echo" in captured.out
    assert "test message" in captured.out


def test_vault_property(tmp_vault, monkeypatch):
    runtime = MagicMock()
    app = _EchoApp(runtime)
    assert app.vault == tmp_vault


def test_data_property(tmp_data, monkeypatch):
    runtime = MagicMock()
    app = _EchoApp(runtime)
    assert app.data.name == "data"


def test_subscribes_default():
    runtime = MagicMock()
    app = _EchoApp(runtime)
    assert Notify in app.subscribes
