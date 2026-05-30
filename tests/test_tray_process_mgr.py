from __future__ import annotations
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    (tmp_path / ".claude" / "data").mkdir(parents=True)
    import importlib, tray.process_mgr
    importlib.reload(tray.process_mgr)


def _pid_file(tmp_path: Path) -> Path:
    return tmp_path / ".claude" / "data" / "bot.pid"


def test_bot_status_stopped_when_no_pid_file():
    from tray import process_mgr
    assert process_mgr.bot_status() == "stopped"


def test_bot_status_stopped_when_pid_dead(tmp_path):
    _pid_file(tmp_path).write_text("99999999", encoding="utf-8")
    from tray import process_mgr
    with patch("tray.process_mgr._pid_alive", return_value=False):
        assert process_mgr.bot_status() == "stopped"


def test_bot_status_running_when_pid_alive(tmp_path):
    _pid_file(tmp_path).write_text("1234", encoding="utf-8")
    from tray import process_mgr
    with patch("tray.process_mgr._pid_alive", return_value=True):
        assert process_mgr.bot_status() == "running"


def test_start_bot_skips_if_already_running(tmp_path):
    _pid_file(tmp_path).write_text("1234", encoding="utf-8")
    from tray import process_mgr
    with patch("tray.process_mgr._pid_alive", return_value=True), \
         patch("subprocess.Popen") as mock_popen:
        process_mgr.start_bot()
        mock_popen.assert_not_called()


def test_stop_bot_noop_when_no_pid_file():
    from tray import process_mgr
    process_mgr.stop_bot()  # must not raise


def test_stop_bot_terminates_and_removes_pid(tmp_path):
    _pid_file(tmp_path).write_text("1234", encoding="utf-8")
    from tray import process_mgr
    mock_proc = MagicMock()
    with patch("tray.process_mgr._pid_alive", return_value=True), \
         patch("psutil.Process", return_value=mock_proc):
        process_mgr.stop_bot()
    assert not _pid_file(tmp_path).exists()
    mock_proc.terminate.assert_called_once()


def test_start_bot_launches_vbs(tmp_path):
    from tray import process_mgr
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    with patch("tray.process_mgr._pid_alive", return_value=False), \
         patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        process_mgr.start_bot()
    call_args = mock_popen.call_args[0][0]  # first positional arg is the command list
    assert call_args[0].lower().endswith("wscript.exe")
    assert "start_discord_bot.vbs" in call_args[1]


def test_stop_bot_terminates_process_tree(tmp_path):
    _pid_file(tmp_path).write_text("1234", encoding="utf-8")
    from tray import process_mgr
    mock_child = MagicMock()
    mock_proc = MagicMock()
    mock_proc.children.return_value = [mock_child]
    with patch("tray.process_mgr._pid_alive", return_value=True), \
         patch("psutil.Process", return_value=mock_proc):
        process_mgr.stop_bot()
    assert not _pid_file(tmp_path).exists()
    mock_proc.terminate.assert_called_once()
    mock_child.terminate.assert_called_once()
