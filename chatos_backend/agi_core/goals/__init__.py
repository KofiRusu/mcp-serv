"""
Goal Management for AGI Core

High-level goal tracking:
- Goal dataclass with priority and deadlines
- GoalManager for CRUD operations
- Goal → Task decomposition support
"""

from .manager import Goal, GoalStatus, GoalManager

__all__ = [
    "Goal",
    "GoalStatus",
    "GoalManager",
]

