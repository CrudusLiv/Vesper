import logging
from .models import ToolCall
from .tools.vault import VaultToolExecutor
from .tools.integrations import GCalToolExecutor

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Dispatches tool calls to specific executors"""

    def __init__(self):
        self.vault = VaultToolExecutor()
        self.gcal = GCalToolExecutor()

    def execute(self, tool_call: ToolCall) -> dict:
        """
        Execute a tool call and return result
        Returns: {"success": bool, "result": Any, "error": str | None}
        """
        try:
            if tool_call.tool_name.startswith("vault_"):
                return self.vault.execute(tool_call)
            elif tool_call.tool_name == "gcal_sync":
                return self.gcal.execute(tool_call)
            else:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Unknown tool: {tool_call.tool_name}"
                }
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_call.tool_name}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
