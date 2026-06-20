# tests/kernel/test_integration.py
"""Integration tests — exercises multiple apps on one runtime."""
from unittest.mock import MagicMock, patch, call
from kernel.runtime import KernelRuntime
from kernel.apps.heartbeat_app import HeartbeatApp
from kernel.events import Tick


def test_single_tick_processes_inbox_once():
    """HeartbeatApp owns inbox; a single Tick must call process_new_files exactly once."""
    rt = KernelRuntime(tick_interval=9999)
    app = HeartbeatApp(rt)
    rt.load_apps([app])

    with patch("kernel.apps.heartbeat_app.in_active_hours", return_value=True), \
         patch("kernel.apps.heartbeat_app._run_heartbeat_tick") as mock_tick:
        rt._dispatch(Tick(interval=1800))
        assert mock_tick.call_count == 1, (
            "Inbox must be processed exactly once per Tick — "
            "multiple apps calling process_new_files() causes data loss"
        )
