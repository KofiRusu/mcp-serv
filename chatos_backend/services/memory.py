"""
memory.py - Memory storage service for notes.

Provides functionality to store note summaries in the AGI memory system
for later recall and context building.
"""

import logging
from typing import Dict, Any, Optional, Set

from chatos_backend.database.notes_models import NoteDB
from chatos_backend.agi_core.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

# Session-scoped memory managers
_memory_managers: Dict[str, MemoryManager] = {}

# Track which notes have been stored to avoid duplicates
_stored_note_ids: Set[str] = set()


def get_memory_manager(session_id: str) -> MemoryManager:
    """
    Get or create a MemoryManager for a session.
    
    Args:
        session_id: User session ID
        
    Returns:
        MemoryManager instance for the session
    """
    if session_id not in _memory_managers:
        _memory_managers[session_id] = MemoryManager(
            session_id=session_id,
            use_embeddings=False,  # Start with keyword-based for speed
        )
    return _memory_managers[session_id]


def store_note_memory(note: NoteDB) -> Optional[str]:
    """
    Store a note in the AGI memory system.
    
    This creates a memory entry with the note's title, summary, and metadata.
    The memory is stored in both short-term and long-term memory for recall.
    
    Args:
        note: The NoteDB object to store
        
    Returns:
        Memory ID if stored successfully, None if already stored or error
    """
    # Create a unique key for this note
    note_key = f"{note.session_id}:{note.id}"
    
    # Check if already stored
    if note_key in _stored_note_ids:
        logger.debug(f"Note {note.id} already stored in memory")
        return None
    
    try:
        memory_manager = get_memory_manager(note.session_id)
        
        # Parse summary from content if it's a transcript note
        summary = _extract_summary(note.content)
        
        # Build memory content
        memory_content = f"Note: {note.title}\n\n{summary}"
        
        # Add tags if present
        if note.tags:
            memory_content += f"\n\nTags: {', '.join(note.tags)}"
        
        # Calculate importance based on tags and content length
        importance = _calculate_importance(note)
        
        # Store in memory
        memory_id = memory_manager.remember(
            content=memory_content,
            importance=importance,
            source="note",
            metadata={
                "note_id": note.id,
                "note_title": note.title,
                "tags": note.tags,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "type": "note_summary",
            },
            persist=True,  # Store in long-term memory
        )
        
        # Mark as stored
        _stored_note_ids.add(note_key)
        
        logger.info(f"Stored note {note.id} in memory as {memory_id}")
        return memory_id
        
    except Exception as e:
        logger.error(f"Failed to store note {note.id} in memory: {e}")
        # TODO: Implement fallback storage if memory system is unavailable
        return None


def _extract_summary(content: str) -> str:
    """
    Extract the summary portion from note content.
    
    For transcript notes, the format is:
    <summary>
    
    Action Items:
    - ...
    
    Args:
        content: Full note content
        
    Returns:
        Summary portion of the content
    """
    if "Action Items:" in content:
        parts = content.split("Action Items:")
        return parts[0].strip()
    return content


def _calculate_importance(note: NoteDB) -> float:
    """
    Calculate importance score for a note.
    
    Higher importance for:
    - Notes with action items
    - Notes with specific tags (meeting, auto)
    - Longer content
    
    Args:
        note: The note to score
        
    Returns:
        Importance score between 0.0 and 1.0
    """
    importance = 0.5  # Base importance
    
    # Boost for action items
    if "Action Items:" in note.content:
        importance += 0.2
    
    # Boost for transcript notes (auto-generated)
    if "auto" in note.tags:
        importance += 0.1
    
    # Boost for meeting notes
    if "meeting" in note.tags:
        importance += 0.1
    
    # Small boost for longer content
    if len(note.content) > 500:
        importance += 0.05
    
    return min(importance, 1.0)


def recall_notes(session_id: str, query: str, k: int = 5) -> list:
    """
    Recall notes relevant to a query from memory.
    
    Args:
        session_id: User session ID
        query: Search query
        k: Maximum number of results
        
    Returns:
        List of relevant MemoryItem objects
    """
    memory_manager = get_memory_manager(session_id)
    
    # Search memory
    results = memory_manager.recall(query, k=k, include_long_term=True)
    
    # Filter to only note memories
    note_memories = [
        m for m in results
        if m.metadata.get("type") == "note_summary"
    ]
    
    return note_memories


def get_note_context(session_id: str, query: str, max_tokens: int = 1000) -> str:
    """
    Get relevant note context for a query.
    
    This is useful for providing context to the LLM when answering questions.
    
    Args:
        session_id: User session ID
        query: The query to get context for
        max_tokens: Approximate maximum context length
        
    Returns:
        Formatted context string
    """
    memory_manager = get_memory_manager(session_id)
    return memory_manager.get_relevant_context(query, max_tokens=max_tokens)


def clear_session_memory(session_id: str) -> int:
    """
    Clear short-term memory for a session.
    
    Args:
        session_id: User session ID
        
    Returns:
        Number of items cleared
    """
    if session_id in _memory_managers:
        return _memory_managers[session_id].clear_session()
    return 0


def get_memory_stats(session_id: str) -> Dict[str, Any]:
    """
    Get memory statistics for a session.
    
    Args:
        session_id: User session ID
        
    Returns:
        Dictionary with memory stats
    """
    if session_id in _memory_managers:
        return _memory_managers[session_id].get_stats()
    return {
        "session_id": session_id,
        "short_term_count": 0,
        "long_term_count": 0,
        "conversation_turns": 0,
    }

