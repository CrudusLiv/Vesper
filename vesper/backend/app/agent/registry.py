from .models import Tool, ToolParameter


class ToolRegistry:
    """Registry for managing available tools in the agent system"""

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register all core tools"""
        # Vault tools
        self.register(
            Tool(
                name="vault_add_note",
                description="Add or update a note in the vault",
                parameters=[
                    ToolParameter(
                        name="path",
                        type="string",
                        description="Vault file path (e.g., 'notes/reminders.md')",
                        required=True,
                    ),
                    ToolParameter(
                        name="content",
                        type="string",
                        description="Note content (markdown)",
                        required=True,
                    ),
                    ToolParameter(
                        name="overwrite",
                        type="boolean",
                        description="Replace file if exists",
                        required=False,
                    ),
                ],
            )
        )

        self.register(
            Tool(
                name="vault_add_finance",
                description="Log a financial transaction",
                parameters=[
                    ToolParameter(
                        name="amount",
                        type="number",
                        description="Transaction amount",
                        required=True,
                    ),
                    ToolParameter(
                        name="category",
                        type="string",
                        description="Category (e.g., food, transport)",
                        required=True,
                    ),
                    ToolParameter(
                        name="date",
                        type="string",
                        description="Date (YYYY-MM-DD)",
                        required=True,
                    ),
                    ToolParameter(
                        name="description",
                        type="string",
                        description="Transaction description",
                        required=False,
                    ),
                ],
            )
        )

        self.register(
            Tool(
                name="vault_add_schedule",
                description="Add an event or deadline to the schedule",
                parameters=[
                    ToolParameter(
                        name="title",
                        type="string",
                        description="Event title",
                        required=True,
                    ),
                    ToolParameter(
                        name="date",
                        type="string",
                        description="Event date (YYYY-MM-DD or relative like 'Friday')",
                        required=True,
                    ),
                    ToolParameter(
                        name="start_time",
                        type="string",
                        description="Start time (HH:MM in 24h format)",
                        required=True,
                    ),
                    ToolParameter(
                        name="end_time",
                        type="string",
                        description="End time (HH:MM in 24h format)",
                        required=True,
                    ),
                    ToolParameter(
                        name="priority",
                        type="string",
                        enum=["low", "medium", "high"],
                        description="Priority level",
                        required=False,
                    ),
                    ToolParameter(
                        name="location",
                        type="string",
                        description="Location",
                        required=False,
                    ),
                    ToolParameter(
                        name="description",
                        type="string",
                        description="Event description",
                        required=False,
                    ),
                ],
            )
        )

        self.register(
            Tool(
                name="vault_search",
                description="Search the vault for existing content",
                parameters=[
                    ToolParameter(
                        name="query",
                        type="string",
                        description="Search query",
                        required=True,
                    ),
                    ToolParameter(
                        name="search_type",
                        type="string",
                        enum=["all", "notes", "finances", "schedule"],
                        description="What to search",
                        required=False,
                    ),
                    ToolParameter(
                        name="limit",
                        type="number",
                        description="Max results",
                        required=False,
                    ),
                ],
            )
        )

        self.register(
            Tool(
                name="summarize_document",
                description="Summarize a lecture, PDF, or document",
                parameters=[
                    ToolParameter(
                        name="file_path",
                        type="string",
                        description="Path to file to summarize",
                        required=True,
                    ),
                    ToolParameter(
                        name="file_type",
                        type="string",
                        enum=["pptx", "pdf", "txt", "md"],
                        description="File type",
                        required=True,
                    ),
                ],
            )
        )

        self.register(
            Tool(
                name="categorize_item",
                description="Auto-categorize an item (note, finance, schedule)",
                parameters=[
                    ToolParameter(
                        name="item_type",
                        type="string",
                        enum=["finance", "note", "schedule"],
                        description="What to categorize",
                        required=True,
                    ),
                    ToolParameter(
                        name="content",
                        type="string",
                        description="Item content",
                        required=True,
                    ),
                ],
            )
        )

    def register(self, tool: Tool):
        """Register a tool"""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools"""
        return list(self.tools.values())

    def to_ollama_schema(self) -> list[dict]:
        """Export all tools to Ollama function-calling schema"""
        return [tool.to_ollama_schema() for tool in self.tools.values()]
