"""
Multi-Agent System for AGI Core

Provides specialized agents for different tasks:
- BaseAgent interface
- PlannerAgent - turns goals into tasks
- WorkerAgent - executes tasks with tools
- CriticAgent - reviews and improves outputs
- AgentOrchestrator - coordinates multi-agent workflows
"""

from .base import BaseAgent, AgentContext, AgentResult
from .planner import PlannerAgent
from .worker import WorkerAgent
from .critic import CriticAgent
from .orchestrator import AgentOrchestrator

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "PlannerAgent",
    "WorkerAgent",
    "CriticAgent",
    "AgentOrchestrator",
]

