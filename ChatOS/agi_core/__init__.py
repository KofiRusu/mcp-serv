"""
AGI Core - Autonomous General Intelligence System for ChatOS

This module provides AGI-style capabilities including:
- Memory System (short-term + long-term)
- Tool/Function Calling SDK
- Task & Goal Management
- Multi-Agent Orchestration
- Autonomous Execution Loop
- Reasoning Traces & Reflection
- Knowledge Base (RAG)
- Metacognition & Self-Improvement

Usage:
    from ChatOS.agi_core import AutonomousRunner, MemoryManager, ToolRegistry
    
    runner = AutonomousRunner(goal="Research quantum computing")
    result = await runner.run(max_steps=10)
"""

__version__ = "0.1.0"

# Memory System
from .memory.base import MemoryItem, MemoryStore
from .memory.short_term import ShortTermMemory
from .memory.long_term import LongTermMemory
from .memory.manager import MemoryManager

# Tools
from .tools.base import Tool, ToolRegistry, ToolResult
from .tools.builtin import get_builtin_tools
from .tools.router import ToolRouter

# Tasks
from .tasks.models import Task, TaskStatus, TaskPriority
from .tasks.manager import TaskManager

# Agents
from .agents.base import BaseAgent, AgentContext, AgentResult
from .agents.planner import PlannerAgent
from .agents.worker import WorkerAgent
from .agents.critic import CriticAgent
from .agents.orchestrator import AgentOrchestrator

# Traces
from .traces.recorder import TraceStep, TraceSession, TraceRecorder

# Reflection
from .reflection.engine import ReflectionEngine, Reflection

# Knowledge
from .knowledge.rag_store import RAGStore, Document

# Goals
from .goals.manager import Goal, GoalStatus, GoalManager

# State
from .state.world import WorldState, StateEvent

# Sandbox
from .sandbox.executor import SafeExecutor, ExecutionResult

# Metacognition
from .meta.metacognition import MetacognitionEngine, QualityMetrics

# Training
from .training.loop import TrainingDataCollector, TrainingExample, export_training_dataset

# Notes
from .notes.models import Note, ActionItem, NoteType, SourceType, ActionStatus, ActionPriority
from .notes.store import NoteStore
from .notes.classifier import NoteClassifier
from .notes.extractor import ActionItemExtractor

# Orchestrator (main entry point)
from .orchestrator import AutonomousRunner, RunnerStatus, run_goal

__all__ = [
    # Version
    "__version__",
    
    # Memory
    "MemoryItem",
    "MemoryStore",
    "ShortTermMemory",
    "LongTermMemory",
    "MemoryManager",
    
    # Tools
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "ToolRouter",
    "get_builtin_tools",
    
    # Tasks
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskManager",
    
    # Agents
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "PlannerAgent",
    "WorkerAgent",
    "CriticAgent",
    "AgentOrchestrator",
    
    # Traces
    "TraceStep",
    "TraceSession",
    "TraceRecorder",
    
    # Reflection
    "ReflectionEngine",
    "Reflection",
    
    # Knowledge
    "RAGStore",
    "Document",
    
    # Goals
    "Goal",
    "GoalStatus",
    "GoalManager",
    
    # State
    "WorldState",
    "StateEvent",
    
    # Sandbox
    "SafeExecutor",
    "ExecutionResult",
    
    # Metacognition
    "MetacognitionEngine",
    "QualityMetrics",
    
    # Training
    "TrainingDataCollector",
    "TrainingExample",
    "export_training_dataset",
    
    # Notes
    "Note",
    "ActionItem",
    "NoteType",
    "SourceType",
    "ActionStatus",
    "ActionPriority",
    "NoteStore",
    "NoteClassifier",
    "ActionItemExtractor",
    
    # Orchestrator
    "AutonomousRunner",
    "RunnerStatus",
    "run_goal",
]
