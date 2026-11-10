"""
Tool Registry and Execution Safety System for JARVIS.
Enforces Section 6 & 9 of the architecture specification:
- Deterministic risk levels (safe, confirm, blocked)
- Execution and logging
- JSON Schema generation for Claude Haiku
"""

import logging
from typing import Callable, Dict, Any, List, Tuple
from tools.mac import (
    open_app,
    quit_app,
    open_url,
    set_volume,
    get_volume,
    mute_volume,
    unmute_volume,
    find_file,
    open_file,
)

logger = logging.getLogger("jarvis.tools")

# Risk definitions
RISK_SAFE = "safe"          # Read-only or trivially reversible
RISK_CONFIRM = "confirm"    # Has side effects, requires explicit verbal confirmation
RISK_BLOCKED = "blocked"    # Always refused (system wipe, payment, destructive shell)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register(self, name: str, fn: Callable, risk: str, description: str, input_schema: Dict[str, Any]):
        """Register a tool with its implementation, risk level, and schema."""
        self._tools[name] = {
            "name": name,
            "fn": fn,
            "risk": risk,
            "schema": {
                "name": name,
                "description": description,
                "input_schema": input_schema,
            }
        }

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def get_claude_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions in Claude API format."""
        return [tool["schema"] for tool in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any], confirmed: bool = False) -> Tuple[str, str]:
        """
        Executes a registered tool.
        Returns (result_message, status): status can be 'executed', 'needs_confirmation', or 'blocked'.
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' is not recognized.", "error"

        risk = tool["risk"]

        # 1. Blocked check
        if risk == RISK_BLOCKED:
            return f"Action '{name}' is permanently blocked for safety.", "blocked"

        # 2. Confirmation check
        if risk == RISK_CONFIRM and not confirmed:
            return (
                f"Action '{name}' requires confirmation with arguments {arguments}. "
                f"Please confirm to proceed.",
                "needs_confirmation"
            )

        # 3. Safe or confirmed execution
        try:
            fn = tool["fn"]
            result = fn(**arguments)
            return str(result), "executed"
        except Exception as e:
            logger.exception(f"Tool execution failed for {name}")
            return f"Execution of {name} failed: {e}", "error"

    def _register_default_tools(self):
        # Native macOS tools
        self.register(
            name="open_app",
            fn=open_app,
            risk=RISK_SAFE,
            description="Open a macOS application by name (e.g. Spotify, Chrome, Terminal, Notes, Safari)",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The exact name of the application to launch"}
                },
                "required": ["name"]
            }
        )

        self.register(
            name="quit_app",
            fn=quit_app,
            risk=RISK_SAFE,
            description="Quit or close a macOS application by name",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the application to quit"}
                },
                "required": ["name"]
            }
        )

        self.register(
            name="open_url",
            fn=open_url,
            risk=RISK_SAFE,
            description="Open a website URL in the default web browser (e.g., youtube.com, github.com, mail.google.com)",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL or website domain to open"}
                },
                "required": ["url"]
            }
        )

        self.register(
            name="set_volume",
            fn=set_volume,
            risk=RISK_SAFE,
            description="Set the macOS master volume level between 0 and 100 percent",
            input_schema={
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume percentage level from 0 to 100"}
                },
                "required": ["level"]
            }
        )

        self.register(
            name="get_volume",
            fn=get_volume,
            risk=RISK_SAFE,
            description="Get the current macOS master volume percentage",
            input_schema={"type": "object", "properties": {}}
        )

        self.register(
            name="mute_volume",
            fn=mute_volume,
            risk=RISK_SAFE,
            description="Mute system audio",
            input_schema={"type": "object", "properties": {}}
        )

        self.register(
            name="unmute_volume",
            fn=unmute_volume,
            risk=RISK_SAFE,
            description="Unmute system audio",
            input_schema={"type": "object", "properties": {}}
        )

        self.register(
            name="find_file",
            fn=find_file,
            risk=RISK_SAFE,
            description="Search for files by name on the Mac using Spotlight",
            input_schema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename pattern to search for"}
                },
                "required": ["filename"]
            }
        )

        self.register(
            name="open_file",
            fn=open_file,
            risk=RISK_SAFE,
            description="Open a file using its default macOS application",
            input_schema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Full path to the file"}
                },
                "required": ["filepath"]
            }
        )


# Global instance
registry = ToolRegistry()

