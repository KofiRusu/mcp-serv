"""
Memory Manager for AGI Core

Unified interface for managing both short-term and long-term memory.
"""

from typing import Any, Dict, List, Optional

from .base import MemoryItem
from .short_term import ShortTermMemory
from .long_term import LongTermMemory


class MemoryManager:
    """
    Unified memory manager combining short-term and long-term memory.
    
    Provides a simple API for remembering and recalling information,
    with automatic routing to the appropriate memory store.
    
    Usage:
        memory = MemoryManager(session_id="user_123")
        
        # Remember something
        memory.remember("User prefers Python code examples", importance=0.8)
        
        # Recall relevant memories
        results = memory.recall("What programming language does the user prefer?")
        
        # Add conversation turn
        memory.add_turn("Hello", "Hi! How can I help?")
    """
    
    def __init__(
        self,
        session_id: str = "default",
        use_embeddings: bool = False,
        short_term_max: int = 50,
    ):
        """
        Initialize the memory manager.
        
        Args:
            session_id: Identifier for this session
            use_embeddings: Enable embedding-based search for long-term memory
            short_term_max: Maximum items in short-term memory
        """
        self.session_id = session_id
        
        self.short_term = ShortTermMemory(
            max_items=short_term_max,
            session_id=session_id,
        )
        
        self.long_term = LongTermMemory(
            use_embeddings=use_embeddings,
        )
    
    def remember(
        self,
        content: str,
        importance: float = 0.5,
        source: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> str:
        """
        Store a memory.
        
        Args:
            content: The information to remember
            importance: How important this memory is (0.0 to 1.0)
            source: Where this memory came from
            metadata: Additional structured data
            persist: If True, also store in long-term memory
            
        Returns:
            The ID of the created memory
        """
        item = MemoryItem(
            content=content,
            importance=importance,
            source=source,
            metadata=metadata or {},
        )
        
        # Always add to short-term
        self.short_term.add(item)
        
        # Add to long-term if important or persistence requested
        if persist and importance >= 0.5:
            self.long_term.add(item)
        
        return item.id
    
    def recall(
        self,
        query: str,
        k: int = 5,
        include_long_term: bool = True,
    ) -> List[MemoryItem]:
        """
        Retrieve relevant memories.
        
        Args:
            query: The search query
            k: Maximum number of results
            include_long_term: Whether to also search long-term memory
            
        Returns:
            List of relevant memories, deduplicated
        """
        # Search short-term first
        short_results = self.short_term.search(query, k=k)
        
        if not include_long_term:
            return short_results
        
        # Also search long-term
        long_results = self.long_term.search(query, k=k)
        
        # Deduplicate by ID
        seen_ids = set()
        combined = []
        
        for memory in short_results + long_results:
            if memory.id not in seen_ids:
                seen_ids.add(memory.id)
                combined.append(memory)
        
        # Sort by importance and recency
        combined.sort(
            key=lambda m: (m.importance, -m.age_hours()),
            reverse=True,
        )
        
        return combined[:k]
    
    def add_turn(self, user_message: str, assistant_message: str) -> None:
        """
        Add a conversation turn to memory.
        
        Args:
            user_message: The user's input
            assistant_message: The assistant's response
        """
        self.short_term.add_turn(user_message, assistant_message)
    
    def get_context(self) -> str:
        """Get formatted conversation context."""
        return self.short_term.get_context()
    
    def summarize_session(self) -> str:
        """
        Generate a summary of the current session.
        
        Returns:
            Human-readable summary
        """
        short_summary = self.short_term.summarize()
        long_count = self.long_term.count()
        
        return f"{short_summary}\n- {long_count} long-term memories"
    
    def get_relevant_context(self, query: str, max_tokens: int = 2000) -> str:
        """
        Get relevant context for a query, formatted for LLM input.
        
        Args:
            query: The current user query
            max_tokens: Approximate maximum context length
            
        Returns:
            Formatted context string
        """
        parts = []
        
        # Add conversation history
        context = self.get_context()
        if context:
            parts.append("Recent conversation:\n" + context)
        
        # Add relevant memories
        memories = self.recall(query, k=5)
        if memories:
            memory_text = "\n".join([
                f"- {m.content}" for m in memories
            ])
            parts.append("Relevant memories:\n" + memory_text)
        
        # Combine and truncate if needed
        full_context = "\n\n".join(parts)
        
        # Simple truncation (should use tokenizer in production)
        if len(full_context) > max_tokens * 4:  # Rough char estimate
            full_context = full_context[:max_tokens * 4] + "..."
        
        return full_context
    
    def forget(self, memory_id: str) -> bool:
        """
        Remove a memory from both stores.
        
        Args:
            memory_id: The ID of the memory to remove
            
        Returns:
            True if found and removed
        """
        short_deleted = self.short_term.delete(memory_id)
        long_deleted = self.long_term.delete(memory_id)
        return short_deleted or long_deleted
    
    def clear_session(self) -> int:
        """
        Clear short-term memory for this session.
        
        Returns:
            Number of items cleared
        """
        return self.short_term.clear()
    
    def promote_to_long_term(self, memory_id: str) -> bool:
        """
        Promote a short-term memory to long-term storage.
        
        Args:
            memory_id: The ID of the memory to promote
            
        Returns:
            True if promoted successfully
        """
        memory = self.short_term.get(memory_id)
        if memory:
            self.long_term.add(memory)
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "session_id": self.session_id,
            "short_term_count": self.short_term.count(),
            "long_term_count": self.long_term.count(),
            "conversation_turns": len(self.short_term._conversation),
        }

