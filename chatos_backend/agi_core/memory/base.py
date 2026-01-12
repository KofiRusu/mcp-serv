"""
Memory Base Classes for AGI Core

Provides foundational data structures and interfaces for the memory system.
"""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """
    A single memory item stored in the memory system.
    
    Attributes:
        id: Unique identifier for the memory
        content: The actual memory content (text)
        source: Where this memory came from (user, system, tool, etc.)
        timestamp: When this memory was created
        importance: How important this memory is (0.0 to 1.0)
        metadata: Additional structured data about the memory
        embedding: Optional vector embedding for semantic search
    """
    content: str
    source: str = "system"
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    id: str = ""
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            data = f"{self.content}{self.timestamp}{self.source}"
            self.id = hashlib.sha256(data.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "metadata": self.metadata,
            # Don't serialize embeddings by default (too large)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            content=data["content"],
            source=data.get("source", "system"),
            timestamp=data.get("timestamp", time.time()),
            importance=data.get("importance", 0.5),
            metadata=data.get("metadata", {}),
        )
    
    def age_seconds(self) -> float:
        """Return age of this memory in seconds."""
        return time.time() - self.timestamp
    
    def age_hours(self) -> float:
        """Return age of this memory in hours."""
        return self.age_seconds() / 3600
    
    def formatted_time(self) -> str:
        """Return human-readable timestamp."""
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")


class MemoryStore(ABC):
    """
    Abstract base class for memory storage backends.
    
    Implementations must provide methods for adding, searching,
    and managing memories.
    """
    
    @abstractmethod
    def add(self, item: MemoryItem) -> str:
        """
        Add a memory item to the store.
        
        Args:
            item: The memory item to add
            
        Returns:
            The ID of the added memory
        """
        pass
    
    @abstractmethod
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            The memory item, or None if not found
        """
        pass
    
    @abstractmethod
    def search(self, query: str, k: int = 5) -> List[MemoryItem]:
        """
        Search for memories matching a query.
        
        Args:
            query: The search query
            k: Maximum number of results to return
            
        Returns:
            List of matching memories, sorted by relevance
        """
        pass
    
    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def all(self) -> List[MemoryItem]:
        """
        Return all memories in the store.
        
        Returns:
            List of all memory items
        """
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """
        Clear all memories from the store.
        
        Returns:
            Number of memories cleared
        """
        pass
    
    def count(self) -> int:
        """Return the number of memories in the store."""
        return len(self.all())
    
    def search_by_source(self, source: str) -> List[MemoryItem]:
        """Search for memories from a specific source."""
        return [m for m in self.all() if m.source == source]
    
    def search_by_importance(self, min_importance: float = 0.5) -> List[MemoryItem]:
        """Search for memories with importance above threshold."""
        return [m for m in self.all() if m.importance >= min_importance]
    
    def recent(self, hours: float = 24, k: int = 10) -> List[MemoryItem]:
        """Get recent memories within the specified time window."""
        cutoff = time.time() - (hours * 3600)
        recent_memories = [m for m in self.all() if m.timestamp >= cutoff]
        # Sort by timestamp descending and take top k
        recent_memories.sort(key=lambda m: m.timestamp, reverse=True)
        return recent_memories[:k]

