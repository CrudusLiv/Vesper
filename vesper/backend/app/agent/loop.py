import json
import logging
import subprocess
from datetime import datetime
from .models import AgentRequest, AgentResponse
from ..config import config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are Vesper, a personal assistant and study partner. "
    "You are direct and efficient, with a slightly dry tone. "
    "Today is {date}. "
    "The personal vault is at: {vault_path}. "
    "Files live under: notes/, lectures/<COURSE>/, finance/, schedule/. "
    "When displaying note or lecture content, present it directly using markdown — "
    "bullet points, headers, bold as appropriate. Do NOT paraphrase or summarise into prose."
)


class AgentLoop:
    """Main agent loop: user input → claude -p → response."""

    def process(self, request: AgentRequest) -> AgentResponse:
        prompt = self._build_prompt(request)
        system = _SYSTEM_PROMPT.format(
            date=datetime.now().strftime("%Y-%m-%d"),
            vault_path=config.VAULT_PATH,
        )
        try:
            response_text = self._call_claude(prompt, system)
            return AgentResponse(response=response_text, tool_calls=[], tool_results=[])
        except subprocess.TimeoutExpired:
            logger.warning("claude -p timed out after %ds", config.ANTHROPIC_TIMEOUT)
            return AgentResponse(
                response="Claude took too long to respond. Try again.",
                tool_calls=[], tool_results=[],
            )
        except FileNotFoundError:
            logger.error("claude CLI not found in PATH")
            return AgentResponse(
                response="The `claude` CLI isn't installed or not in PATH.",
                tool_calls=[], tool_results=[],
            )
        except Exception:
            logger.exception("Agent loop error")
            return AgentResponse(
                response="Something went wrong on my end. Check the backend logs.",
                tool_calls=[], tool_results=[],
            )

    def _build_prompt(self, request: AgentRequest) -> str:
        parts = []
        for msg in request.conversation_history or []:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            if isinstance(content, list):
                content = " ".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if content:
                parts.append(f"{role.upper()}: {content}")
        parts.append(f"USER: {request.input}")
        return "\n\n".join(parts)

    def _call_claude(self, prompt: str, system: str) -> str:
        cmd = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--system-prompt", system,
            "--model", config.ANTHROPIC_MODEL,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.ANTHROPIC_TIMEOUT,
        )
        if result.returncode != 0:
            logger.error("claude -p stderr: %s", result.stderr)
            raise RuntimeError(result.stderr or "claude exited non-zero")
        output = json.loads(result.stdout)
        if output.get("is_error"):
            raise RuntimeError(output.get("result", "Unknown error from claude"))
        return output.get("result", "Done.")
