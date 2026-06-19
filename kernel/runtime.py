from __future__ import annotations
import queue
import re
import sys
import threading
from typing import Any, Callable

from kernel.events import Tick


def _handler_name(event_type: type) -> str:
    """Convert CamelCase event name to on_snake_case handler name."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", event_type.__name__).lower()
    return "on_" + snake


class KernelRuntime:
    def __init__(self, tick_interval: int = 1800) -> None:
        self._bus: dict[type, list[Callable]] = {}
        self._apps: list[Any] = []
        self._tick_interval = tick_interval
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._stop = threading.Event()

    def load_apps(self, apps: list) -> None:
        for app in apps:
            self._apps.append(app)
            for event_type in app.subscribes:
                method_name = _handler_name(event_type)
                handler = getattr(app, method_name, None)
                if handler:
                    self._bus.setdefault(event_type, []).append(handler)

    def post_external(self, event: Any) -> None:
        """Thread-safe: safe to call from Discord's asyncio thread."""
        self._queue.put(event)

    def start(self) -> None:
        for app in self._apps:
            app.on_start()
        tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        tick_thread.start()
        self._main_loop()

    def stop(self) -> None:
        self._stop.set()
        for app in self._apps:
            app.on_stop()

    def _main_loop(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._queue.get(timeout=1.0)
                self._dispatch(event)
            except queue.Empty:
                pass

    def _tick_loop(self) -> None:
        # Fires immediately on start, then every tick_interval seconds.
        while not self._stop.is_set():
            self._queue.put(Tick(interval=self._tick_interval))
            self._stop.wait(self._tick_interval)

    def _dispatch(self, event: Any) -> None:
        for handler in self._bus.get(type(event), []):
            try:
                handler(event)
            except Exception as exc:
                print(
                    f"[kernel] handler error on {type(event).__name__}: {exc}",
                    file=sys.stderr,
                )
