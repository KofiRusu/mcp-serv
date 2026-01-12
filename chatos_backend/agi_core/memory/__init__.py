"""
Memory System for AGI Core

Provides short-term and long-term memory capabilities with:
- Session-scoped short-term memory
- Persistent long-term memory with optional embeddings
- Unified MemoryManager interface
"""

from .base import MemoryItem, MemoryStore
from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .manager import MemoryManager

__all__ = [
    "MemoryItem",
    "MemoryStore",
    "ShortTermMemory",
    "LongTermMemory",
    "MemoryManager",
]

