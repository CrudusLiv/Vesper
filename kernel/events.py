from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Tick:
    interval: int  # seconds between ticks


@dataclass
class DiscordMessage:
    channel_id: str
    user_id: str
    content: str
    message_obj: Any = None  # discord.Message if available


@dataclass
class InboxDrop:
    path: Path


@dataclass
class VaultWrite:
    path: Path
    kind: str  # "created" | "updated"


@dataclass
class AgentDone:
    agent: str
    result: str


@dataclass
class IntegrationResult:
    name: str
    data: dict = field(default_factory=dict)


@dataclass
class Notify:
    text: str
    channel: str = "heartbeat"
    embed: dict | None = None
