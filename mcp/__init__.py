"""Cursor MCP - Multi-Context Protocol for Persistent Cross-Chat Memory"""

from mcp.memory_store import MemoryStore
from mcp.classifier import MemoryClassifier
from mcp.agent_integration import AgentMemory, get_memory

__all__ = [
    'MemoryStore',
    'MemoryClassifier',
    'AgentMemory',
    'get_memory',
]

__version__ = '1.0.0'
