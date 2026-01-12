"""
Tools Base Classes for AGI Core

Provides the foundation for defining and executing tools.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolResult:
    """
    Result of executing a tool.
    
    Attributes:
        success: Whether the tool executed successfully
        output: The tool's output (if successful)
        error: Error message (if failed)
        metadata: Additional result metadata
    """
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class Tool:
    """
    A tool that can be executed by the AGI system.
    
    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description of what the tool does
        function: The callable that implements the tool
        input_schema: JSON schema describing expected inputs
        requires_confirmation: Whether to ask for confirmation before execution
        is_dangerous: Whether this tool can cause irreversible changes
    """
    name: str
    description: str
    function: Callable[..., Any]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    is_dangerous: bool = False
    
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the given arguments.
        
        Args:
            **kwargs: Arguments to pass to the tool function
            
        Returns:
            ToolResult with success status and output/error
        """
        try:
            # Validate inputs if schema provided
            if self.input_schema:
                self._validate_inputs(kwargs)
            
            # Execute the function
            output = self.function(**kwargs)
            
            return ToolResult(
                success=True,
                output=output,
                metadata={"tool": self.name, "args": kwargs},
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool": self.name, "args": kwargs},
            )
    
    def _validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate inputs against schema."""
        required = self.input_schema.get("required", [])
        properties = self.input_schema.get("properties", {})
        
        # Check required fields
        for field_name in required:
            if field_name not in inputs:
                raise ValueError(f"Missing required argument: {field_name}")
        
        # Type validation (basic)
        for field_name, value in inputs.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    raise ValueError(
                        f"Invalid type for {field_name}: expected {expected_type}"
                    )
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        python_type = type_map.get(expected_type)
        if python_type:
            return isinstance(value, python_type)
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM context."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "requires_confirmation": self.requires_confirmation,
            "is_dangerous": self.is_dangerous,
        }
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            }
        }


class ToolRegistry:
    """
    Registry for managing available tools.
    
    Usage:
        registry = ToolRegistry()
        registry.register(Tool(name="calculator", ...))
        
        tool = registry.get("calculator")
        result = registry.execute("calculator", expression="2+2")
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool.
        
        Args:
            tool: The tool to register
        """
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool by name.
        
        Args:
            name: The tool name to unregister
            
        Returns:
            True if removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            name: The tool name
            
        Returns:
            The tool, or None if not found
        """
        return self._tools.get(name)
    
    def list(self) -> List[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())
    
    def list_names(self) -> List[str]:
        """Return all tool names."""
        return list(self._tools.keys())
    
    def execute(self, name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            name: The tool name
            **kwargs: Arguments to pass to the tool
            
        Returns:
            ToolResult with success status and output/error
        """
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {name}",
            )
        
        return tool.execute(**kwargs)
    
    def get_tool_descriptions(self) -> str:
        """
        Get formatted descriptions of all tools for LLM context.
        
        Returns:
            Formatted string describing all available tools
        """
        lines = ["Available tools:"]
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
            if tool.input_schema.get("properties"):
                params = list(tool.input_schema["properties"].keys())
                lines.append(f"  Parameters: {', '.join(params)}")
        
        return "\n".join(lines)
    
    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """Convert all tools to OpenAI function calling format."""
        return [tool.to_openai_format() for tool in self._tools.values()]
    
    def count(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

