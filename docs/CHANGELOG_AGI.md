# AGI Core Changelog

All notable changes to the AGI Core system are documented here.

## [0.1.0] - 2024-12-01

### Phase 0: Initial Setup
- Created `agi_core/` module structure
- Added `AGI_ARCHITECTURE_OVERVIEW.md` documentation
- Set up folder hierarchy for all components

### Phase 1: Memory System
- Implemented `MemoryItem` and `MemoryStore` base classes
- Created `ShortTermMemory` for session context
- Created `LongTermMemory` with JSON persistence
- Built `MemoryManager` unifying both memory types

### Phase 2: Tools & Tasks
- Implemented `Tool` dataclass and `ToolRegistry`
- Created built-in tools: calculator, file_read, file_write, search_memory
- Implemented `Task` model with status and priorities
- Created `TaskManager` with persistence

### Phase 3: Tool Router & Traces
- Implemented `ToolRouter` for automatic tool selection
- Created `TraceStep` and `TraceRecorder` for reasoning logs

### Phase 4: Multi-Agent System
- Implemented `BaseAgent` interface
- Created `PlannerAgent` for goal decomposition
- Created `WorkerAgent` for task execution
- Created `CriticAgent` for output review
- Built `AgentOrchestrator` for coordination

### Phase 5: Autonomous Loop & Reflection
- Implemented `AutonomousRunner` main loop
- Created `ReflectionEngine` for post-execution analysis

### Phase 6: RAG & World State
- Enhanced `RAGStore` with embedding support
- Implemented `WorldState` for context tracking

### Phase 7: Code Sandbox
- Created `SafeExecutor` wrapper with safety limits

### Phase 8: Goals & Metacognition
- Implemented `GoalManager` for high-level goals
- Created `MetacognitionEngine` for quality assessment

### Phase 9: Training Loop
- Implemented `TrainingDataCollector` for example extraction
- Created `export_training_dataset` utility

