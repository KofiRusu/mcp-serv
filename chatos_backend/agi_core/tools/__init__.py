"""
Tools SDK for AGI Core

Provides a framework for defining and executing tools:
- Tool dataclass for defining tools
- ToolRegistry for managing available tools
- Built-in tools (calculator, file ops, memory search, etc.)
- ToolRouter for automatic tool selection
"""

from .base import Tool, ToolRegistry, ToolResult
from .builtin import get_builtin_tools
from .router import ToolRouter

__all__ = [
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "ToolRouter",
    "get_builtin_tools",
]

