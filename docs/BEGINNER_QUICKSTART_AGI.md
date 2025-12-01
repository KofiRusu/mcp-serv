# AGI Core - Beginner Quickstart Guide

Welcome to AGI Core! This guide will help you get started with the autonomous agent system.

## Prerequisites

- Python 3.9+
- ChatOS-0.1 project set up
- (Optional) sentence-transformers for embedding-based memory search

## Quick Start

### 1. Run the Memory Demo

Test that the memory system works:

```bash
cd ChatOS-0.1
python -m ChatOS.agi_core.examples.memory_demo
```

You should see output showing memories being stored and recalled.

### 2. Run the Task Demo

Test task management:

```bash
python -m ChatOS.agi_core.examples.task_demo
```

### 3. Run the Tools Demo

Test the built-in tools:

```bash
python -m ChatOS.agi_core.examples.tools_demo
```

### 4. Run a Goal (Autonomous Mode)

Run the main autonomous goal runner:

```bash
python -m ChatOS.agi_core.examples.run_goal "Calculate the sum of 1 to 10"
```

Or with a custom goal:

```bash
python -m ChatOS.agi_core.examples.run_goal "Research best practices for Python code organization"
```

## Basic Usage in Code

### Memory System

```python
from ChatOS.agi_core import MemoryManager

# Create memory manager
memory = MemoryManager(session_id="my_session")

# Store information
memory.remember("User prefers Python examples", importance=0.8)

# Recall relevant memories
results = memory.recall("What programming language?")
for mem in results:
    print(f"Found: {mem.content}")

# Add conversation turns
memory.add_turn("Hello!", "Hi there! How can I help?")
```

### Task Management

```python
from ChatOS.agi_core import TaskManager, TaskPriority

# Create task manager
tm = TaskManager()

# Create a task
task = tm.create_task(
    title="Build feature",
    description="Implement the new user dashboard",
    priority=TaskPriority.HIGH,
)

# Work on it
tm.start_task(task.id)

# Complete it
tm.complete_task(task.id, result="Dashboard implemented!")
```

### Using Tools

```python
from ChatOS.agi_core import ToolRegistry, get_builtin_tools

# Set up registry with built-in tools
registry = ToolRegistry()
for tool in get_builtin_tools():
    registry.register(tool)

# Execute tools
result = registry.execute("calculator", expression="15 * 7")
print(f"Result: {result.output}")  # Output: 105

result = registry.execute("current_time")
print(f"Time: {result.output}")
```

### Goal Manager

```python
from ChatOS.agi_core import GoalManager

# Create goal manager
gm = GoalManager()

# Create a high-level goal
goal = gm.create_goal(
    description="Learn machine learning fundamentals",
    priority=8,
)

# Track progress
gm.update_progress(goal.id, 25.0)

# Complete when done
gm.complete_goal(goal.id)
```

### Autonomous Runner

```python
import asyncio
from ChatOS.agi_core import AutonomousRunner

async def main():
    runner = AutonomousRunner(
        goal="Research Python best practices and summarize",
        max_steps=10,
    )
    
    result = await runner.run()
    
    if result.success:
        print(f"Result: {result.output}")
    else:
        print(f"Failed: {result.error}")

asyncio.run(main())
```

## Running Tests

Run the AGI Core tests:

```bash
cd ChatOS-0.1
pytest tests/test_agi_*.py -v
```

## Data Storage

All AGI data is stored under `~/ChatOS-Memory/agi/`:

- `memory/` - Long-term memories
- `tasks/` - Task database
- `goals/` - Goal tracking
- `traces/` - Reasoning traces
- `knowledge/` - RAG document index
- `training/` - Extracted training examples

## Connecting to an LLM

For full autonomous capabilities, connect an LLM provider:

```python
async def my_llm_provider(prompt: str) -> str:
    # Your LLM API call here
    # Example with OpenAI:
    # response = await openai.ChatCompletion.create(...)
    # return response.choices[0].message.content
    pass

runner = AutonomousRunner(
    goal="My goal",
    llm_provider=my_llm_provider,
)
```

## Troubleshooting

### Import Errors

Make sure you're in the ChatOS-0.1 directory:

```bash
cd ~/ChatOS-0.1
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Memory Not Persisting

Check that the storage directory is writable:

```bash
ls -la ~/ChatOS-Memory/agi/
```

### Tools Not Working

Some tools require specific permissions. Check the tool's `is_dangerous` and `requires_confirmation` flags.

## Next Steps

1. Read `docs/AGI_ARCHITECTURE_OVERVIEW.md` for system design
2. Explore the source code in `ChatOS/agi_core/`
3. Try creating custom tools for your use case
4. Connect to your LLM of choice for full autonomy

Happy building! 🚀

