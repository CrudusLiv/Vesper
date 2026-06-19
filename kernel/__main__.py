# kernel/__main__.py
"""Entry point: python -m kernel

Loads all apps and starts the kernel loop. Add new app instances to _build_apps()
when new kernel/apps/*.py files are created."""
from __future__ import annotations
import signal
import sys

from kernel.runtime import KernelRuntime
from kernel.apps.inbox_app import InboxApp

TICK_INTERVAL = 1800  # 30 minutes


def _build_apps(runtime: KernelRuntime) -> list:
    return [
        InboxApp(runtime),
    ]


def main() -> None:
    runtime = KernelRuntime(tick_interval=TICK_INTERVAL)
    apps = _build_apps(runtime)
    runtime.load_apps(apps)

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
