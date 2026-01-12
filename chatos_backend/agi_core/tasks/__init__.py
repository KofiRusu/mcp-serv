"""
Task Management for AGI Core

Provides task tracking and management:
- Task dataclass with status, priority, dependencies
- TaskManager for CRUD operations
- Persistence to disk
"""

from .models import Task, TaskStatus, TaskPriority
from .manager import TaskManager

__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskManager",
]

