"""
memory.py - Conversation memory utilities.

This module provides a sliding-window memory that stores recent user
and assistant turns. It enables the assistant to remember the
conversation context for follow-up questions.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ChatOS.config import MEMORY_MAX_TURNS


@dataclass
class ChatMemory:
    """
    Maintain a history of recent conversation turns.
    
    Uses a sliding window approach to keep memory bounded while
    preserving recent context. Each turn is a (user_message, assistant_message)
    tuple.
    
    Attributes:
        max_turns: Maximum number of turns to retain
        history: List of (user, assistant) message tuples
    """
    
    max_turns: int = field(default=MEMORY_MAX_TURNS)
    history: List[Tuple[str, str]] = field(default_factory=list)

    def add_turn(self, user_message: str, assistant_message: str) -> None:
        """
        Add a new conversation turn and truncate if necessary.
        
        Args:
            user_message: The user's input message
            assistant_message: The assistant's response
        """
        self.history.append((user_message, assistant_message))
        
        # Keep only the last `max_turns` turns
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns:]

    def get_context(self) -> str:
        """
        Return a formatted string of recent conversation turns.
        
        Returns:
            Formatted conversation history, or empty string if no history
        """
        if not self.history:
            return ""
            
        lines = []
        for user_msg, assistant_msg in self.history:
            lines.append(f"User: {user_msg}")
            lines.append(f"Assistant: {assistant_msg}")
        
        return "\n".join(lines)

    def get_summary(self) -> str:
        """
        Get a brief summary of the conversation state.
        
        Returns:
            Summary string describing conversation length and topics
        """
        if not self.history:
            return "No conversation history"
        
        turn_count = len(self.history)
        last_topic = self.history[-1][0][:30] + "..." if len(self.history[-1][0]) > 30 else self.history[-1][0]
        
        return f"{turn_count} turns, last topic: '{last_topic}'"

    def clear(self) -> None:
        """Clear all conversation history."""
        self.history.clear()

    def get_last_n_turns(self, n: int) -> List[Tuple[str, str]]:
        """
        Get the last N conversation turns.
        
        Args:
            n: Number of turns to retrieve
            
        Returns:
            List of (user, assistant) tuples
        """
        return self.history[-n:] if n > 0 else []

    def __len__(self) -> int:
        """Return the number of stored turns."""
        return len(self.history)


# Session-based memory storage
# Maps session_id -> ChatMemory instance
_session_memories: dict[str, ChatMemory] = {}


def get_memory(session_id: Optional[str] = None) -> ChatMemory:
    """
    Get or create a memory instance for a session.
    
    Args:
        session_id: Optional session identifier. If None, uses default session.
        
    Returns:
        ChatMemory instance for the session
    """
    session_key = session_id or "default"
    
    if session_key not in _session_memories:
        _session_memories[session_key] = ChatMemory()
    
    return _session_memories[session_key]


def clear_session(session_id: Optional[str] = None) -> None:
    """
    Clear memory for a specific session or all sessions.
    
    Args:
        session_id: Session to clear. If None, clears the default session.
    """
    session_key = session_id or "default"
    
    if session_key in _session_memories:
        _session_memories[session_key].clear()

