# tests/kernel/test_discord_shell_app.py
from unittest.mock import MagicMock, patch
from kernel.apps.discord_shell_app import DiscordShellApp
from kernel.events import DiscordMessage, Notify


def _make_app():
    runtime = MagicMock()
    return DiscordShellApp(runtime), runtime


def test_discord_message_subscribed():
    app, _ = _make_app()
    assert DiscordMessage in app.subscribes


def test_post_from_discord_enqueues_event():
    app, runtime = _make_app()
    app.post_from_discord(
        channel_id="111", user_id="222", content="hello", message_obj=None
    )
    evt = runtime.post_external.call_args[0][0]
    assert isinstance(evt, DiscordMessage)
    assert evt.content == "hello"


def test_on_discord_message_calls_handler():
    app, _ = _make_app()
    with patch("kernel.apps.discord_shell_app.handler.process_message", return_value="hi back") as mock_h, \
         patch.object(app, "_send_reply") as mock_send:
        evt = DiscordMessage(channel_id="1", user_id="2", content="hey")
        app.on_discord_message(evt)
        mock_h.assert_called_once_with("2", "1", "hey")
        mock_send.assert_called_once_with(evt, "hi back")


def test_on_discord_message_empty_reply_no_send():
    app, _ = _make_app()
    with patch("kernel.apps.discord_shell_app.handler.process_message", return_value=""), \
         patch.object(app, "_send_reply") as mock_send:
        app.on_discord_message(DiscordMessage(channel_id="1", user_id="2", content="x"))
        mock_send.assert_not_called()
