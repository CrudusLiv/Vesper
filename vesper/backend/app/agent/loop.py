import logging
import requests
from datetime import datetime
from .models import AgentRequest, AgentResponse, ToolCall
from .registry import ToolRegistry
from .executor import ToolExecutor
from ..config import config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are Vesper, a personal assistant and study partner. "
    "You are direct and efficient, with a slightly dry tone. "
    "Today is {date}. "
    "Use tools to manage notes, finances, and schedules when asked. "
    "After executing a tool, confirm what you did in one short sentence."
)


class AgentLoop:
    """Main agent loop: user input → Ollama → tools → response."""

    def __init__(self, ollama_url: str = None):
        self.ollama_url = ollama_url or config.OLLAMA_URL
        self.model = config.OLLAMA_MODEL
        self.registry = ToolRegistry()
        self.executor = ToolExecutor()

    def process(self, request: AgentRequest) -> AgentResponse:
        messages = list(request.conversation_history or [])
        messages.append({"role": "user", "content": request.input})

        tools_schema = self.registry.to_ollama_schema()

        try:
            ollama_resp = self._call_ollama(messages, tools_schema)
            msg = ollama_resp.get("message", {})
            raw_tool_calls = msg.get("tool_calls") or []

            executed: list[ToolCall] = []
            results: list[dict] = []

            if raw_tool_calls:
                for tc in raw_tool_calls:
                    fn = tc.get("function", {})
                    tool_call = ToolCall(
                        tool_name=fn.get("name", ""),
                        parameters=fn.get("arguments", {}),
                    )
                    result = self.executor.execute(tool_call)
                    executed.append(tool_call)
                    results.append({"tool_name": tool_call.tool_name, "result": result})

                # Feed tool results back for a natural-language summary
                messages.append({
                    "role": "assistant",
                    "content": msg.get("content") or "",
                    "tool_calls": raw_tool_calls,
                })
                for r in results:
                    messages.append({"role": "tool", "content": str(r["result"])})

                final = self._call_ollama(messages, tools_schema)
                response_text = final.get("message", {}).get("content") or "Done."
            else:
                response_text = msg.get("content") or "Done."

            return AgentResponse(
                response=response_text,
                tool_calls=executed,
                tool_results=results,
            )

        except requests.ConnectionError:
            logger.warning("Ollama not reachable at %s", self.ollama_url)
            return AgentResponse(
                response="Ollama isn't reachable right now. Make sure it's running and a model is loaded.",
                tool_calls=[],
                tool_results=[],
            )
        except Exception:
            logger.exception("Agent loop error")
            return AgentResponse(
                response="Something went wrong on my end. Check the backend logs.",
                tool_calls=[],
                tool_results=[],
            )

    def _call_ollama(self, messages: list[dict], tools_schema: list[dict]) -> dict:
        system = _SYSTEM_PROMPT.format(date=datetime.now().strftime("%Y-%m-%d"))
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "tools": tools_schema,
            "stream": False,
        }
        resp = requests.post(
            f"{self.ollama_url}/api/chat",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
