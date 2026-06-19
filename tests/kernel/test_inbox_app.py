from pathlib import Path
from unittest.mock import MagicMock, patch
from kernel.apps.inbox_app import InboxApp
from kernel.events import Tick, VaultWrite, Notify


def _make_app():
    runtime = MagicMock()
    app = InboxApp(runtime)
    return app, runtime


def test_no_files_emits_nothing(tmp_vault, monkeypatch):
    app, runtime = _make_app()
    with patch("kernel.apps.inbox_app.inbox.process_new_files", return_value=[]):
        app.on_tick(Tick(interval=1800))
    runtime.post_external.assert_not_called()


def test_one_file_emits_vault_write_and_notify(tmp_vault, monkeypatch):
    note_path = tmp_vault / "lectures" / "CS101" / "2026-06-18_sorting.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("# Sorting Algorithms", encoding="utf-8")

    result = {
        "path": note_path,
        "type": "lecture",
        "name": "CS101",
        "title": "Sorting Algorithms",
        "source": "lecture.pptx",
        "deadlines": [],
        "tldr": ["Merge sort is O(n log n)"],
        "date": "2026-06-18",
        "study_cards": 3,
    }

    app, runtime = _make_app()
    with patch("kernel.apps.inbox_app.inbox.process_new_files", return_value=[result]):
        app.on_tick(Tick(interval=1800))

    calls = [c.args[0] for c in runtime.post_external.call_args_list]
    vault_writes = [c for c in calls if isinstance(c, VaultWrite)]
    notifies = [c for c in calls if isinstance(c, Notify)]

    assert len(vault_writes) == 1
    assert vault_writes[0].path == note_path
    assert vault_writes[0].kind == "created"
    assert len(notifies) == 1
    assert "Sorting Algorithms" in notifies[0].text


def test_tick_is_subscribed():
    app, _ = _make_app()
    assert Tick in app.subscribes
