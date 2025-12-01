"""
Tests for AGI Core Tools System
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ChatOS.agi_core.tools import (
    Tool,
    ToolRegistry,
    ToolResult,
    ToolRouter,
    get_builtin_tools,
)


class TestTool:
    """Tests for Tool dataclass."""
    
    def test_create_tool(self):
        def my_func(x: int) -> int:
            return x * 2
        
        tool = Tool(
            name="double",
            description="Doubles a number",
            function=my_func,
        )
        
        assert tool.name == "double"
        assert tool.description == "Doubles a number"
    
    def test_execute_tool(self):
        tool = Tool(
            name="add",
            description="Add two numbers",
            function=lambda a, b: a + b,
        )
        
        result = tool.execute(a=2, b=3)
        assert result.success
        assert result.output == 5
    
    def test_execute_with_error(self):
        def failing_func():
            raise ValueError("Test error")
        
        tool = Tool(
            name="fail",
            description="Always fails",
            function=failing_func,
        )
        
        result = tool.execute()
        assert not result.success
        assert "Test error" in result.error


class TestToolRegistry:
    """Tests for ToolRegistry."""
    
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = Tool(name="test", description="Test", function=lambda: "ok")
        
        registry.register(tool)
        
        retrieved = registry.get("test")
        assert retrieved is not None
        assert retrieved.name == "test"
    
    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(Tool(name="a", description="A", function=lambda: 1))
        registry.register(Tool(name="b", description="B", function=lambda: 2))
        
        tools = registry.list()
        assert len(tools) == 2
    
    def test_execute_by_name(self):
        registry = ToolRegistry()
        registry.register(Tool(
            name="greet",
            description="Greet",
            function=lambda person: f"Hello, {person}!"
        ))
        
        result = registry.execute("greet", person="World")
        assert result.success
        assert result.output == "Hello, World!"
    
    def test_execute_missing_tool(self):
        registry = ToolRegistry()
        result = registry.execute("nonexistent")
        
        assert not result.success
        assert "not found" in result.error.lower()


class TestBuiltinTools:
    """Tests for builtin tools."""
    
    def test_get_builtin_tools(self):
        tools = get_builtin_tools()
        assert len(tools) > 0
        
        names = [t.name for t in tools]
        assert "calculator" in names
        assert "current_time" in names
    
    def test_calculator_tool(self):
        registry = ToolRegistry()
        for tool in get_builtin_tools():
            registry.register(tool)
        
        result = registry.execute("calculator", expression="2 + 3 * 4")
        assert result.success
        assert result.output == 14
    
    def test_calculator_safe_eval(self):
        registry = ToolRegistry()
        for tool in get_builtin_tools():
            registry.register(tool)
        
        # Should not allow dangerous operations
        result = registry.execute("calculator", expression="__import__('os')")
        assert not result.success
    
    def test_current_time_tool(self):
        registry = ToolRegistry()
        for tool in get_builtin_tools():
            registry.register(tool)
        
        result = registry.execute("current_time")
        assert result.success
        assert len(result.output) > 0


class TestToolRouter:
    """Tests for ToolRouter."""
    
    def test_select_calculator(self):
        registry = ToolRegistry()
        for tool in get_builtin_tools():
            registry.register(tool)
        
        router = ToolRouter(registry)
        
        tool, args = router.select_tool("What is 15 + 27?")
        assert tool is not None
        assert tool.name == "calculator"
    
    def test_select_time(self):
        registry = ToolRegistry()
        for tool in get_builtin_tools():
            registry.register(tool)
        
        router = ToolRouter(registry)
        
        tool, args = router.select_tool("What time is it?")
        assert tool is not None
        assert tool.name == "current_time"
    
    def test_no_match(self):
        registry = ToolRegistry()
        router = ToolRouter(registry)
        
        tool, args = router.select_tool("Tell me a joke")
        assert tool is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

