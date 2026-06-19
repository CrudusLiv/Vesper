import queue
import threading
import time
from unittest.mock import MagicMock, patch
from kernel.runtime import KernelRuntime
from kernel.app import VesperApp
from kernel.events import Tick, Notify


class _CapApp(VesperApp):
    name = "cap"
    subscribes = [Notify]
    calls: list

    def __init__(self, runtime):
        super().__init__(runtime)
        self.calls = []

    def on_notify(self, event: Notify) -> None:
        self.calls.append(event)


def _make_runtime():
    rt = KernelRuntime(tick_interval=9999)  # won't fire in tests
    return rt


def test_subscribe_and_dispatch():
    rt = _make_runtime()
    app = _CapApp(rt)
    rt.load_apps([app])
    evt = Notify(text="hello")
    rt._dispatch(evt)
    assert len(app.calls) == 1
    assert app.calls[0].text == "hello"


def test_post_external_enqueues():
    rt = _make_runtime()
    evt = Notify(text="x")
    rt.post_external(evt)
    assert rt._queue.get_nowait() is evt


def test_handler_exception_does_not_break_others():
    rt = _make_runtime()
    received = []

    class _BrokenApp(VesperApp):
        name = "broken"
        subscribes = [Notify]
        def on_notify(self, e):
            raise RuntimeError("boom")

    class _GoodApp(VesperApp):
        name = "good"
        subscribes = [Notify]
        def on_notify(self, e):
            received.append(e)

    rt.load_apps([_BrokenApp(rt), _GoodApp(rt)])
    rt._dispatch(Notify(text="test"))
    assert len(received) == 1


def test_on_start_called_for_all_apps():
    rt = _make_runtime()
    started = []

    class _StartApp(VesperApp):
        name = "s"
        subscribes = []
        def on_start(self):
            started.append(True)

    rt.load_apps([_StartApp(rt), _StartApp(rt)])
    for app in rt._apps:
        app.on_start()
    assert started == [True, True]


def test_multiple_subscribers_for_same_event():
    rt = _make_runtime()
    log = []

    class _A(VesperApp):
        name = "a"
        subscribes = [Tick]
        def on_tick(self, e):
            log.append("a")

    class _B(VesperApp):
        name = "b"
        subscribes = [Tick]
        def on_tick(self, e):
            log.append("b")

    rt.load_apps([_A(rt), _B(rt)])
    rt._dispatch(Tick(interval=30))
    assert sorted(log) == ["a", "b"]
