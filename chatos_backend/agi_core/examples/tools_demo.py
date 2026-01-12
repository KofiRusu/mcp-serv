"""
Tools SDK Demo for AGI Core

Demonstrates tool registration, execution, and routing.

Run with:
    python -m ChatOS.agi_core.examples.tools_demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from chatos_backend.agi_core.tools import Tool, ToolRegistry, ToolRouter, get_builtin_tools


def main():
    print("=" * 60)
    print("AGI Core - Tools SDK Demo")
    print("=" * 60)
    
    # Initialize registry with builtin tools
    print("\n1. Initializing Tool Registry...")
    registry = ToolRegistry()
    
    for tool in get_builtin_tools():
        registry.register(tool)
    
    print(f"   Registered {registry.count()} builtin tools:")
    for name in registry.list_names():
        print(f"   - {name}")
    
    # Direct tool execution
    print("\n2. Direct tool execution...")
    
    # Calculator
    print("\n   Calculator: 15 * 7 + 3")
    result = registry.execute("calculator", expression="15 * 7 + 3")
    print(f"   Result: {result.output} (success: {result.success})")
    
    # Current time
    print("\n   Getting current time...")
    result = registry.execute("current_time")
    print(f"   Time: {result.output}")
    
    # List files
    print("\n   Listing home directory...")
    result = registry.execute("list_files", path=str(Path.home()), pattern="*")
    if result.success:
        files = result.output[:5]
        print(f"   Found {len(result.output)} items (showing 5):")
        for f in files:
            print(f"   - {f}")
    
    # Tool Router
    print("\n3. Using Tool Router for automatic selection...")
    router = ToolRouter(registry)
    
    queries = [
        "What is 42 * 17?",
        "What time is it now?",
        "read the file /etc/hostname",
        "Search for 'def main' in ~/",
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        tool, args = router.select_tool(query)
        if tool:
            print(f"   Selected tool: {tool.name}")
            print(f"   Extracted args: {args}")
        else:
            print("   No suitable tool found")
    
    # Custom tool
    print("\n4. Registering custom tool...")
    
    def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}! Welcome to AGI Core."
    
    custom_tool = Tool(
        name="greet",
        description="Generate a greeting for a person",
        function=greet,
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "greeting": {"type": "string"},
            },
            "required": ["name"],
        },
    )
    
    registry.register(custom_tool)
    print(f"   Registered: {custom_tool.name}")
    
    result = custom_tool.execute(name="AGI User", greeting="Welcome")
    print(f"   Result: {result.output}")
    
    # Tool descriptions for LLM
    print("\n5. Tool descriptions for LLM context:")
    print("-" * 40)
    print(registry.get_tool_descriptions()[:500] + "...")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

