"""
Autonomous Goal Runner Demo for AGI Core

Main entry point for running autonomous goals.

Run with:
    python -m ChatOS.agi_core.examples.run_goal "Your goal here"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from chatos_backend.agi_core import AutonomousRunner, MemoryManager, ToolRegistry, get_builtin_tools


async def main(goal: str):
    print("=" * 60)
    print("AGI Core - Autonomous Goal Runner")
    print("=" * 60)
    
    print(f"\nGoal: {goal}")
    print("-" * 60)
    
    # Initialize components
    print("\n1. Initializing AGI components...")
    
    # Tool registry with builtins
    registry = ToolRegistry()
    for tool in get_builtin_tools():
        registry.register(tool)
    print(f"   Tools: {registry.count()} registered")
    
    # Memory manager
    memory = MemoryManager(session_id="goal_runner")
    print(f"   Memory: initialized")
    
    # Create runner (no LLM provider - will use simulated responses)
    runner = AutonomousRunner(
        goal=goal,
        llm_provider=None,  # Would connect to actual LLM in production
        tool_registry=registry,
        memory_manager=memory,
        max_steps=10,
    )
    
    print(f"   Runner: ready")
    
    # Run the goal
    print("\n2. Executing goal...")
    print("-" * 60)
    
    result = await runner.run()
    
    # Show results
    print("\n3. Results:")
    print("-" * 60)
    print(f"   Success: {result.success}")
    print(f"   Confidence: {result.confidence:.2f}")
    
    if result.success:
        print(f"\n   Output:")
        output_str = str(result.output)[:500]
        print("   " + output_str.replace("\n", "\n   "))
    else:
        print(f"\n   Error: {result.error}")
    
    if result.actions_taken:
        print(f"\n   Actions taken:")
        for action in result.actions_taken[:5]:
            print(f"   - {action}")
    
    # Show progress
    print("\n4. Final Progress:")
    progress = runner.get_progress()
    for key, value in progress.items():
        print(f"   {key}: {value}")
    
    # Show memory state
    print("\n5. Memory after execution:")
    stats = memory.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Goal execution complete!")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        goal = " ".join(sys.argv[1:])
    else:
        goal = "Calculate the sum of numbers 1 through 10 and explain the result"
    
    asyncio.run(main(goal))

