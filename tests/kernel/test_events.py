from pathlib import Path
from kernel.events import (
    Tick, DiscordMessage, InboxDrop, VaultWrite,
    AgentDone, IntegrationResult, Notify,
)

def test_tick_fields():
    e = Tick(interval=1800)
    assert e.interval == 1800

def test_discord_message_fields():
    e = DiscordMessage(channel_id="123", user_id="456", content="hi")
    assert e.content == "hi"
    assert e.message_obj is None

def test_inbox_drop_fields():
    p = Path("/tmp/file.pptx")
    e = InboxDrop(path=p)
    assert e.path == p

def test_vault_write_fields():
    e = VaultWrite(path=Path("/tmp/note.md"), kind="created")
    assert e.kind == "created"

def test_agent_done_fields():
    e = AgentDone(agent="deadline_tracker", result="3 items")
    assert e.agent == "deadline_tracker"

def test_integration_result_fields():
    e = IntegrationResult(name="github", data={"pushes": []})
    assert e.data == {"pushes": []}

def test_notify_defaults():
    e = Notify(text="hello")
    assert e.channel == "heartbeat"
    assert e.embed is None

def test_notify_custom():
    e = Notify(text="hi", channel="vesper", embed={"title": "t"})
    assert e.channel == "vesper"
