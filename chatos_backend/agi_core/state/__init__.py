"""
World State for AGI Core

Tracks the current state of the system:
- Active goals and tasks
- Recent events
- Environment variables
"""

from .world import WorldState, StateEvent

__all__ = [
    "WorldState",
    "StateEvent",
]

