"""
Short-Term Memory for AGI Core

Provides session-scoped memory for immediate context.
Wraps and extends the existing ChatOS memory system.
"""

from typing import Dict, List, Optional, Tuple

from .base import MemoryItem, MemoryStore


class ShortTermMemory(MemoryStore):
    """
    Session-scoped short-term memory.
    
    Uses a sliding window approach to maintain recent context.
    Data is not persisted across sessions.
    
    Attributes:
        max_items: Maximum number of items to retain
        session_id: Identifier for this memory session
    """
    
    def __init__(self, max_items: int = 50, session_id: str = "default"):
        """
        Initialize short-term memory.
        
        Args:
            max_items: Maximum items to retain in memory
            session_id: Session identifier
        """
        self.max_items = max_items
        self.session_id = session_id
        self._memories: Dict[str, MemoryItem] = {}
        self._order: List[str] = []  # Track insertion order
        
        # Conversation history (for backward compatibility)
        self._conversation: List[Tuple[str, str]] = []
        self.max_turns = 10
    
    def add(self, item: MemoryItem) -> str:
        """Add a memory item, evicting oldest if at capacity."""
        # Add to storage
        self._memories[item.id] = item
        self._order.append(item.id)
        
        # Evict oldest if over capacity
        while len(self._order) > self.max_items:
            oldest_id = self._order.pop(0)
            self._memories.pop(oldest_id, None)
        
        return item.id
    
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory by ID."""
        return self._memories.get(memory_id)
    
    def search(self, query: str, k: int = 5) -> List[MemoryItem]:
        """
        Search memories using simple keyword matching.
        
        For short-term memory, we use basic keyword search
        since the dataset is small and recent.
        """
        query_lower = query.lower()
        keywords = query_lower.split()
        
        scored = []
        for memory in self._memories.values():
            content_lower = memory.content.lower()
            # Count keyword matches
            score = sum(1 for kw in keywords if kw in content_lower)
            # Boost recent memories
            recency_boost = max(0, 1 - (memory.age_hours() / 24))
            # Boost by importance
            importance_boost = memory.importance
            
            total_score = score + (recency_boost * 0.5) + (importance_boost * 0.3)
            if score > 0 or total_score > 0.5:
                scored.append((memory, total_score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:k]]
    
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            self._order = [id for id in self._order if id != memory_id]
            return True
        return False
    
    def all(self) -> List[MemoryItem]:
        """Return all memories in order."""
        return [self._memories[id] for id in self._order if id in self._memories]
    
    def clear(self) -> int:
        """Clear all memories."""
        count = len(self._memories)
        self._memories.clear()
        self._order.clear()
        self._conversation.clear()
        return count
    
    # ==========================================================================
    # Conversation History (backward compatibility with ChatOS memory)
    # ==========================================================================
    
    def add_turn(self, user_message: str, assistant_message: str) -> None:
        """
        Add a conversation turn.
        
        Args:
            user_message: The user's input
            assistant_message: The assistant's response
        """
        self._conversation.append((user_message, assistant_message))
        
        # Keep only recent turns
        if len(self._conversation) > self.max_turns:
            self._conversation = self._conversation[-self.max_turns:]
        
        # Also add to memory items for searchability
        self.add(MemoryItem(
            content=f"User: {user_message}\nAssistant: {assistant_message}",
            source="conversation",
            importance=0.6,
        ))
    
    def get_context(self) -> str:
        """Return formatted conversation history."""
        if not self._conversation:
            return ""
        
        lines = []
        for user_msg, assistant_msg in self._conversation:
            lines.append(f"User: {user_msg}")
            lines.append(f"Assistant: {assistant_msg}")
        
        return "\n".join(lines)
    
    def get_turns(self, n: int = 5) -> List[Tuple[str, str]]:
        """Get the last N conversation turns."""
        return self._conversation[-n:] if n > 0 else []
    
    def summarize(self) -> str:
        """Get a summary of the session."""
        memory_count = len(self._memories)
        turn_count = len(self._conversation)
        
        summary_parts = [f"Session '{self.session_id}'"]
        summary_parts.append(f"- {memory_count} memory items")
        summary_parts.append(f"- {turn_count} conversation turns")
        
        if self._conversation:
            last_topic = self._conversation[-1][0][:50]
            summary_parts.append(f"- Last topic: '{last_topic}...'")
        
        return "\n".join(summary_parts)

