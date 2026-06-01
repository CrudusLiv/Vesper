from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

from tray import task_scheduler


def _mock_run(stdout: str = "", returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


_ENABLED_CSV = (
    '"Scheduled Task State","Status","Last Run Time","Next Run Time"\n'
    '"Enabled","Ready","5/31/2026 10:30:00 AM","5/31/2026 11:00:00 AM"\n'
)
_DISABLED_CSV = (
    '"Scheduled Task State","Status","Last Run Time","Next Run Time"\n'
    '"Disabled","Disabled","N/A","N/A"\n'
)


class TestGetStatus:
    def test_enabled_task_returns_correct_fields(self):
        with patch("subprocess.run", return_value=_mock_run(_ENABLED_CSV)):
            s = task_scheduler.get_status("secondbrain-heartbeat")
        assert s["enabled"] is True
        assert s["status"] == "Ready"
        assert s["last_run"] == "5/31/2026 10:30:00 AM"
        assert s["next_run"] == "5/31/2026 11:00:00 AM"

    def test_disabled_task_returns_enabled_false(self):
        with patch("subprocess.run", return_value=_mock_run(_DISABLED_CSV)):
            s = task_scheduler.get_status("secondbrain-reflect")
        assert s["enabled"] is False
        assert s["status"] == "Disabled"

    def test_nonzero_returncode_returns_fallback(self):
        with patch("subprocess.run", return_value=_mock_run(returncode=1)):
            s = task_scheduler.get_status("secondbrain-reflect")
        assert s == {"enabled": False, "status": "unknown", "last_run": "N/A", "next_run": "N/A"}

    def test_subprocess_exception_returns_fallback(self):
        with patch("subprocess.run", side_effect=Exception("timeout")):
            s = task_scheduler.get_status("secondbrain-heartbeat")
        assert s == {"enabled": False, "status": "unknown", "last_run": "N/A", "next_run": "N/A"}

    def test_empty_csv_body_returns_fallback(self):
        with patch("subprocess.run", return_value=_mock_run("")):
            s = task_scheduler.get_status("secondbrain-heartbeat")
        assert s["status"] == "unknown"


class TestNoConsoleWindow:
    """The tray runs under pythonw.exe (no console); schtasks calls must not flash a cmd window."""

    def test_get_status_passes_create_no_window(self):
        with patch("subprocess.run", return_value=_mock_run(_ENABLED_CSV)) as mock:
            task_scheduler.get_status("secondbrain-heartbeat")
        assert mock.call_args.kwargs.get("creationflags") == task_scheduler._NO_WINDOW

    def test_set_enabled_passes_create_no_window(self):
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            task_scheduler.set_enabled("secondbrain-heartbeat", True)
        assert mock.call_args.kwargs.get("creationflags") == task_scheduler._NO_WINDOW

    def test_run_now_passes_create_no_window(self):
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            task_scheduler.run_now("secondbrain-heartbeat")
        assert mock.call_args.kwargs.get("creationflags") == task_scheduler._NO_WINDOW

    def test_set_interval_passes_create_no_window(self):
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            task_scheduler.set_interval("secondbrain-heartbeat", 30)
        assert mock.call_args.kwargs.get("creationflags") == task_scheduler._NO_WINDOW


class TestSetEnabled:
    def test_enable_passes_enable_flag(self):
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            task_scheduler.set_enabled("secondbrain-heartbeat", True)
        cmd = mock.call_args[0][0]
        assert "/enable" in cmd
        assert "secondbrain-heartbeat" in cmd

    def test_disable_passes_disable_flag(self):
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            task_scheduler.set_enabled("secondbrain-reflect", False)
        cmd = mock.call_args[0][0]
        assert "/disable" in cmd

    def test_returns_true_on_success(self):
        with patch("subprocess.run", return_value=_mock_run(returncode=0)):
            assert task_scheduler.set_enabled("secondbrain-heartbeat", True) is True

    def test_returns_false_on_failure(self):
        with patch("subprocess.run", return_value=_mock_run(returncode=1)):
            assert task_scheduler.set_enabled("secondbrain-heartbeat", True) is False


class TestRunNow:
    def test_calls_schtasks_run_with_task_name(self):
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            task_scheduler.run_now("secondbrain-heartbeat")
        cmd = mock.call_args[0][0]
        assert "schtasks" in cmd
        assert "/run" in cmd
        assert "secondbrain-heartbeat" in cmd

    def test_returns_true_on_success(self):
        with patch("subprocess.run", return_value=_mock_run(returncode=0)):
            assert task_scheduler.run_now("secondbrain-heartbeat") is True

    def test_returns_false_on_failure(self):
        with patch("subprocess.run", return_value=_mock_run(returncode=1)):
            assert task_scheduler.run_now("secondbrain-heartbeat") is False


class TestSetInterval:
    def test_passes_ri_flag_and_minutes(self):
        with patch("subprocess.run", return_value=_mock_run()) as mock:
            task_scheduler.set_interval("secondbrain-heartbeat", 15)
        cmd = mock.call_args[0][0]
        assert "/ri" in cmd
        assert "15" in cmd

    def test_returns_true_on_success(self):
        with patch("subprocess.run", return_value=_mock_run(returncode=0)):
            assert task_scheduler.set_interval("secondbrain-heartbeat", 30) is True

    def test_returns_false_on_failure(self):
        with patch("subprocess.run", return_value=_mock_run(returncode=1)):
            assert task_scheduler.set_interval("secondbrain-heartbeat", 30) is False
