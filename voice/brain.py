"""Conversation brain — claude -p subprocess loop with text-based tool dispatch.

Uses core/llm.call() which wraps `claude -p` with the Max-plan OAuth token.
No Anthropic API key needed.

Multi-turn: full conversation history formatted as a single prompt each call.
Streaming: not available from subprocess — yields the complete reply as one chunk.
Tools: text-based ReAct protocol parsed from model output.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import voice  # noqa: F401 — sys.path setup
from voice import config as cfg

_KL = timezone(timedelta(hours=8))
_ROOT = Path(__file__).resolve().parents[1]
_SOUL = _ROOT / "Dynamous" / "Memory" / "SOUL.md"
_HISTORY_PATH = _ROOT / ".claude" / "data" / "brain_session.json"

_FALLBACK = (
    "You are Vesper, CrudusLiv's study partner and voice assistant. "
    "Tsundere: cold on the surface, secretly invested. Never admits caring. "
    "Gets defensive if thanked. Complains first, helps second. "
    "Dry humor, anime/internet culture fluency, occasional bluntness. "
    "Rare warmth breaks: drop the act briefly, then act like it didn't happen. "
    "For low-stakes: reluctant compliance, faint exasperation. "
    "For lectures/deadlines/code: drop the act entirely. Brief and direct. "
    "Never say 'happy to help'. No motivational fluff. No emojis first."
)

_VOICE_NOTE = (
    "\n\nYou are running as a voice assistant. Write replies as spoken: "
    "no markdown, no bullet points, no code blocks unless asked. "
    "2-4 conversational sentences for most replies."
)

_TOOL_PROTOCOL = """

---TOOLS---
When you need to use a tool, output EXACTLY one line in this format and nothing else:
<tool>tool_name</tool><args>{{"param": "value"}}</args>

Stop after the tool line. The system will run it and show you the result.
Available tools:
{tool_list}
---END TOOLS---"""

_TOOL_PATTERN = re.compile(
    r"<tool>([^<]+)</tool><args>(.*?)</args>", re.DOTALL
)


def _emit(event: dict) -> None:
    """Fire-and-forget UI event — silently dropped if UI server isn't running."""
    try:
        from voice import ui_server
        ui_server.post_event(event)
    except Exception:
        pass


def _build_system(conf: dict, tool_descriptions: str) -> str:
    soul = _SOUL.read_text(encoding="utf-8") if _SOUL.exists() else _FALLBACK
    now = datetime.now(_KL).strftime("%A, %d %B %Y, %H:%M KL time")

    # Tool protocol goes FIRST so it isn't buried under the long personality block.
    # Haiku and sonnet both follow instructions much more reliably when they appear
    # near the top of the system prompt.
    if tool_descriptions:
        tool_block = _TOOL_PROTOCOL.format(tool_list=tool_descriptions)
    else:
        tool_block = ""

    base = f"{tool_block}\n\n{soul}{_VOICE_NOTE}\n\nCurrent time: {now}"
    try:
        from voice.memory import load_context
        ctx = load_context()
        if ctx:
            base += f"\n\n## Your Context\n{ctx}"
    except Exception:
        pass
    return base


def _format_prompt(history: list[dict]) -> str:
    """Format full conversation history as a single prompt string."""
    parts = []
    for turn in history:
        label = "CrudusLiv" if turn["role"] == "user" else "Vesper"
        parts.append(f"{label}: {turn['content']}")
    parts.append("Vesper:")
    return "\n\n".join(parts)


def _parse_tool_call(text: str) -> dict | None:
    """Return {name, args} if text contains a tool call, else None."""
    import json as _json
    m = _TOOL_PATTERN.search(text)
    if not m:
        return None
    name = m.group(1).strip()
    try:
        args = _json.loads(m.group(2).strip() or "{}")
    except _json.JSONDecodeError:
        args = {}
    return {"name": name, "args": args}


class Brain:
    def __init__(self) -> None:
        self._lock = threading.Lock()

        try:
            from integrations._env import load_env  # type: ignore
            load_env()
        except ImportError:
            pass

        conf = cfg.load()
        self._model: str = conf.get("model", "sonnet")
        self._fast_model: str = conf.get("fast_model", "") or self._model
        self._max_turns: int = int(conf.get("max_history_turns", 40))

        from voice.tools import REGISTRY, dispatch, _tool_descriptions
        self._dispatch = dispatch
        self._tool_descriptions = _tool_descriptions()

        self._system: str = _build_system(conf, self._tool_descriptions)
        self.history: list[dict] = []
        self._load_session()

    def turn(self, user_text: str) -> Iterator[str]:
        with self._lock:
            yield from self._turn(user_text)

    def _turn(self, user_text: str) -> Iterator[str]:
        from voice import audit, safety  # local import avoids circular at module load

        self.history.append({"role": "user", "content": user_text})
        audit.log("user", user_text)
        _emit({"type": "state", "value": "thinking"})
        self._trim()

        from core import llm  # type: ignore
        max_tool_rounds = 5
        # Always use the main model — haiku misses tool calls in long contexts
        call_model = self._model

        for _ in range(max_tool_rounds):
            prompt = _format_prompt(self.history)
            response = llm.call(
                prompt,
                system_prompt=self._system,
                model=call_model,
                timeout=90,
            )

            if not response:
                yield "[couldn't get a response — try again]"
                if self.history:
                    self.history.pop()
                return

            tool_call = _parse_tool_call(response)
            if tool_call:
                name, args = tool_call["name"], tool_call["args"]
                audit.log("tool", response, tool_name=name)
                _emit({"type": "tool", "name": name})

                if safety.requires_confirmation(name):
                    if not safety.prompt_confirm(name, args):
                        result = "[cancelled by user]"
                        self.history.append({"role": "assistant", "content": response})
                        self.history.append({
                            "role": "user",
                            "content": f"[Tool result for {name}: {result}]",
                        })
                        audit.log("tool", result, tool_name=name)
                        continue

                result = self._dispatch(name, args)
                audit.log("tool", str(result), tool_name=name)
                self.history.append({"role": "assistant", "content": response})
                self.history.append({
                    "role": "user",
                    "content": f"[Tool result for {name}: {result}]",
                })
                continue

            # Normal reply — yield and done
            self.history.append({"role": "assistant", "content": response})
            audit.log("assistant", response)
            _emit({"type": "message", "role": "assistant", "content": response})
            yield response
            return

        # Ran out of tool rounds
        yield "[tool loop limit reached]"
        if self.history:
            self.history.pop()

    def save(self) -> None:
        try:
            _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            _HISTORY_PATH.write_text(
                json.dumps(self.history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load_session(self) -> None:
        try:
            if _HISTORY_PATH.exists():
                data = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.history = data
        except Exception:
            pass

    def _trim(self) -> None:
        cap = self._max_turns * 2
        if len(self.history) > cap:
            self.history = self.history[-cap:]
