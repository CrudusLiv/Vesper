import logging
from .models import AgentRequest, AgentResponse
from .registry import ToolRegistry
from .executor import ToolExecutor

logger = logging.getLogger(__name__)


class AgentLoop:
    """Main agent loop that processes user input and executes tools"""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.registry = ToolRegistry()
        self.executor = ToolExecutor()

    def process(self, request: AgentRequest) -> AgentResponse:
        """
        Main agent loop:
        1. Accept user input
        2. Call Ollama with input + available tools
        3. Ollama decides which tools to invoke
        4. Execute tools
        5. Send results back to Ollama
        6. Return response

        For now, returns a simple response without Ollama integration.
        This will be enhanced in Phase 3 when Ollama is available.
        """

        # For now, return a simple response without Ollama integration
        # This will be enhanced in Phase 3 when Ollama is available
        return AgentResponse(
            response=f"Received: {request.input}",
            tool_calls=[],
            tool_results=[]
        )
