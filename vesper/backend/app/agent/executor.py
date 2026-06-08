import logging
from .models import ToolCall
from .tools.vault import VaultToolExecutor

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Dispatches tool calls to specific executors"""

    def __init__(self):
        self.vault = VaultToolExecutor()

    def execute(self, tool_call: ToolCall) -> dict:
        """
        Execute a tool call and return result
        Returns: {"success": bool, "result": Any, "error": str | None}
        """
        try:
            if tool_call.tool_name.startswith("vault_"):
                return self.vault.execute(tool_call)
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
