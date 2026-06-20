# kernel/__main__.py
"""Entry point: python -m kernel

Loads all apps and starts the kernel loop. Add new app instances to _build_apps()
when new kernel/apps/*.py files are created."""
from __future__ import annotations
import signal
import sys
import threading
from pathlib import Path

_CLAUDE = Path(__file__).resolve().parents[1] / ".claude"
sys.path.insert(0, str(_CLAUDE))
sys.path.insert(0, str(_CLAUDE / "scripts"))

from kernel.runtime import KernelRuntime
from kernel.apps.heartbeat_app import HeartbeatApp
from kernel.apps.dashboard_app import DashboardApp
from kernel.apps.discord_shell_app import DiscordShellApp

TICK_INTERVAL = 1800  # 30 minutes


def _build_apps(runtime: KernelRuntime) -> list:
    # InboxApp is not registered here yet: its on_tick calls process_new_files()
    # which conflicts with heartbeat.tick() doing the same (destructively). Until
    # InboxApp fully replicates heartbeat's inbox-processing path (including
    # deadlines.promote), HeartbeatApp owns inbox processing exclusively.
    return [
        HeartbeatApp(runtime),
        DashboardApp(runtime),
        DiscordShellApp(runtime),
    ]


def main() -> None:
    runtime = KernelRuntime(tick_interval=TICK_INTERVAL)
    apps = _build_apps(runtime)
    runtime.load_apps(apps)

    shell_app = next(a for a in apps if isinstance(a, DiscordShellApp))

    def _start_discord():
        from chat import discord_bot
        discord_bot.set_kernel_shell(shell_app)
        discord_bot.main()

    discord_thread = threading.Thread(target=_start_discord, daemon=True, name="discord-bot")
    discord_thread.start()

    def _shutdown(sig, frame):
        print("\n[kernel] shutting down…", flush=True)
        runtime.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    try:
        signal.signal(signal.SIGTERM, _shutdown)
    except OSError:
        pass  # SIGTERM not supported on Windows

    print(f"[kernel] starting — tick interval {TICK_INTERVAL}s", flush=True)
    runtime.start()


if __name__ == "__main__":
    main()
