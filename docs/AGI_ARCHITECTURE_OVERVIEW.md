# AGI Core Architecture Overview

## Introduction

AGI Core is an autonomous agent system built on top of ChatOS that provides AGI-style capabilities. It enables the local LLM to:

- Remember information across sessions
- Use tools to interact with the world
- Plan and execute multi-step tasks
- Reflect on its actions and improve
- Collaborate through multiple specialized agents

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AutonomousRunner                            │
│  (Main orchestration loop: Plan → Act → Reflect → Repeat)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ GoalManager  │  │ TaskManager  │  │ WorldState   │           │
│  │ (High-level) │  │ (Execution)  │  │ (Context)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Multi-Agent Orchestrator                    │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │    │
│  │  │ Planner │  │ Worker  │  │ Critic  │  │ Memory  │    │    │
│  │  │  Agent  │  │  Agent  │  │  Agent  │  │  Agent  │    │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ ToolRegistry │  │ RAGStore     │  │ TraceRecorder│           │
│  │ + Router     │  │ (Knowledge)  │  │ (Logging)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │MemoryManager │  │ Reflection   │  │Metacognition │           │
│  │ (STM + LTM)  │  │   Engine     │  │   Engine     │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                     ChatOS LLM Core                              │
│  (Model loading, inference, training integration)                │
└─────────────────────────────────────────────────────────────────┘
```

## Module Overview

### 1. Memory System (`agi_core/memory/`)

Provides short-term and long-term memory:

- **ShortTermMemory**: Session-scoped conversation context (sliding window)
- **LongTermMemory**: Persistent storage with JSON files + optional embeddings
- **MemoryManager**: Unified API with `remember()`, `recall()`, `summarize_session()`

```python
from ChatOS.agi_core.memory import MemoryManager

memory = MemoryManager()
memory.remember("User prefers Python code examples")
results = memory.recall("What does the user prefer?")
```

### 2. Tools SDK (`agi_core/tools/`)

Framework for defining and executing tools:

- **Tool**: Dataclass defining name, description, input schema, function
- **ToolRegistry**: Register and lookup tools
- **ToolRouter**: Automatically selects best tool based on context
- **Built-in tools**: calculator, read_file, write_file, search_memory, run_python

```python
from ChatOS.agi_core.tools import Tool, ToolRegistry

registry = ToolRegistry()
registry.register(Tool(
    name="calculator",
    description="Perform math calculations",
    function=lambda expr: eval(expr, {"__builtins__": {}})
))
```

### 3. Task Manager (`agi_core/tasks/`)

Task tracking with priorities and dependencies:

- **Task**: Dataclass with id, title, status, priority, subtasks
- **TaskManager**: CRUD operations with JSON persistence

```python
from ChatOS.agi_core.tasks import TaskManager, Task, TaskPriority

tm = TaskManager()
task = tm.create_task("Write documentation", priority=TaskPriority.HIGH)
tm.update_status(task.id, "completed")
```

### 4. Multi-Agent System (`agi_core/agents/`)

Specialized agents collaborating on tasks:

- **PlannerAgent**: Decomposes goals into actionable tasks
- **WorkerAgent**: Executes tasks using tools
- **CriticAgent**: Reviews outputs, suggests improvements
- **AgentOrchestrator**: Coordinates the workflow

```python
from ChatOS.agi_core.agents import AgentOrchestrator

orchestrator = AgentOrchestrator(llm_provider=llm)
result = await orchestrator.execute_goal("Research quantum computing")
```

### 5. Traces (`agi_core/traces/`)

Records reasoning for debugging and training:

- **TraceStep**: Single step with input, output, tools used
- **TraceSession**: Complete session with all steps
- **TraceRecorder**: Manages recording and persistence

### 6. Reflection (`agi_core/reflection/`)

Post-execution analysis for learning:

- Analyzes what worked and what failed
- Generates improvement suggestions
- Stores learnings in long-term memory

### 7. Knowledge Base (`agi_core/knowledge/`)

RAG capabilities for document retrieval:

- **RAGStore**: Index and search documents
- Supports embeddings (sentence-transformers) when available
- Falls back to keyword search

### 8. Goals (`agi_core/goals/`)

High-level goal management:

- **Goal**: Dataclass with description, status, deadline
- **GoalManager**: Track goals over time, decompose into tasks

### 9. Metacognition (`agi_core/meta/`)

Self-monitoring and quality assessment:

- Rate factual accuracy
- Detect potential hallucinations
- Track performance metrics

### 10. World State (`agi_core/state/`)

Current system context:

- Active goals and tasks
- Recent events
- Environment configuration

### 11. Code Sandbox (`agi_core/sandbox/`)

Safe code execution:

- Restricted Python environment
- Time and memory limits
- File system isolation

### 12. Training Loop (`agi_core/training/`)

Autonomous training data extraction:

- Collect examples from traces
- Export datasets for fine-tuning
- Integration with existing QLoRA pipeline

## Data Flow

### Autonomous Execution Loop

```
1. GOAL RECEIVED
   ↓
2. PLANNER decomposes goal → Tasks
   ↓
3. For each Task:
   a. WORKER executes with tools
   b. CRITIC reviews output
   c. If rejected → back to WORKER
   ↓
4. REFLECTION analyzes results
   ↓
5. MEMORY stores learnings
   ↓
6. Check: Goal complete?
   - Yes → Return result
   - No → Back to step 2 with updated state
```

### Tool Selection Flow

```
User Query → Tool Router → LLM suggests tool → 
Validate args → Execute tool → Return result
```

## File Storage

All AGI data is stored under `~/ChatOS-Memory/agi/`:

```
~/ChatOS-Memory/agi/
├── memory/
│   ├── long_term.json       # Persistent memories
│   └── embeddings/          # Optional vector store
├── tasks/
│   └── tasks.json           # Task database
├── goals/
│   └── goals.json           # Goal database
├── traces/
│   └── session_*.json       # Reasoning traces
├── knowledge/
│   └── index/               # RAG document index
└── training/
    └── examples.jsonl       # Extracted training data
```

## Integration with ChatOS

AGI Core integrates with existing ChatOS components:

- Uses `ChatOS.controllers.llm_client` for LLM inference
- Extends `ChatOS.utils.rag` for knowledge retrieval
- Wraps `ChatOS.controllers.sandbox` for code execution
- Feeds training data to `ChatOS.training` pipeline

## Usage Examples

### Basic Autonomous Execution

```python
from ChatOS.agi_core import AutonomousRunner

async def main():
    runner = AutonomousRunner(
        goal="Research the latest AI safety papers and summarize key findings",
        max_steps=10,
    )
    result = await runner.run()
    print(result.summary)

asyncio.run(main())
```

### Using Memory

```python
from ChatOS.agi_core.memory import MemoryManager

memory = MemoryManager()

# Store information
memory.remember("User is working on a Python web app", importance=0.8)

# Retrieve relevant info
results = memory.recall("What project is the user working on?", k=3)
```

### Running Tools

```python
from ChatOS.agi_core.tools import ToolRegistry, get_builtin_tools

registry = ToolRegistry()
for tool in get_builtin_tools():
    registry.register(tool)

# Execute a tool
result = registry.execute("calculator", {"expression": "2 + 2"})
```

## Testing

Run tests with:

```bash
cd ChatOS-0.1
pytest tests/test_agi_*.py -v
```

Run demos:

```bash
python -m ChatOS.agi_core.examples.memory_demo
python -m ChatOS.agi_core.examples.task_demo
python -m ChatOS.agi_core.examples.run_goal "Your goal here"
```

## Future Improvements

1. **Multi-day planning**: Goals that span multiple sessions
2. **Dynamic agent creation**: Spawn specialized agents on demand
3. **Hierarchical goals**: Goal trees with sub-goals
4. **Browser automation**: Web interaction tools
5. **External API integration**: Connect to external services
6. **Collaborative agents**: Multiple agents negotiating task allocation

