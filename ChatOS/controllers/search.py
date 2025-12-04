"""
search.py - Unified search controller.

Provides search functionality across notes, transcripts, and chat history.
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from ChatOS.database.notes_models import NoteDB, TranscriptDB

logger = logging.getLogger(__name__)


def search_notes(
    db: Session,
    session_id: str,
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search notes by title and content.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        query: Search query
        limit: Maximum results
        
    Returns:
        List of matching note results
    """
    search_pattern = f"%{query.lower()}%"
    
    notes = (
        db.query(NoteDB)
        .filter(NoteDB.session_id == session_id)
        .filter(
            or_(
                NoteDB.title.ilike(search_pattern),
                NoteDB.content.ilike(search_pattern),
            )
        )
        .order_by(NoteDB.updated_at.desc())
        .limit(limit)
        .all()
    )
    
    results = []
    for note in notes:
        # Calculate relevance score (simple keyword count)
        title_matches = note.title.lower().count(query.lower())
        content_matches = note.content.lower().count(query.lower())
        score = title_matches * 2 + content_matches  # Title matches weighted higher
        
        # Extract snippet around first match
        snippet = _extract_snippet(note.content, query)
        
        results.append({
            "type": "note",
            "id": note.id,
            "title": note.title,
            "snippet": snippet,
            "score": score,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            "tags": note.tags,
        })
    
    return results


def search_transcripts(
    db: Session,
    session_id: str,
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search transcripts by text content.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        query: Search query
        limit: Maximum results
        
    Returns:
        List of matching transcript results
    """
    search_pattern = f"%{query.lower()}%"
    
    transcripts = (
        db.query(TranscriptDB)
        .filter(TranscriptDB.session_id == session_id)
        .filter(TranscriptDB.transcript_text.ilike(search_pattern))
        .filter(TranscriptDB.status == "done")  # Only search completed transcripts
        .order_by(TranscriptDB.created_at.desc())
        .limit(limit)
        .all()
    )
    
    results = []
    for transcript in transcripts:
        if not transcript.transcript_text:
            continue
            
        # Calculate relevance score
        text_matches = transcript.transcript_text.lower().count(query.lower())
        score = text_matches
        
        # Extract snippet
        snippet = _extract_snippet(transcript.transcript_text, query)
        
        results.append({
            "type": "transcript",
            "id": transcript.id,
            "title": f"Transcript: {transcript.audio_path.split('/')[-1]}",
            "snippet": snippet,
            "score": score,
            "audio_path": transcript.audio_path,
            "created_at": transcript.created_at.isoformat() if transcript.created_at else None,
            "status": transcript.status,
        })
    
    return results


def search_memory(
    session_id: str,
    query: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search AGI memory for relevant memories.
    
    Args:
        session_id: User session ID
        query: Search query
        limit: Maximum results
        
    Returns:
        List of matching memory results
    """
    try:
        from ChatOS.services.memory import recall_notes
        
        memories = recall_notes(session_id, query, k=limit)
        
        results = []
        for memory in memories:
            results.append({
                "type": "memory",
                "id": memory.id,
                "title": memory.metadata.get("note_title", "Memory"),
                "snippet": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                "score": memory.importance,
                "source": memory.source,
                "note_id": memory.metadata.get("note_id"),
                "tags": memory.metadata.get("tags", []),
            })
        
        return results
        
    except Exception as e:
        logger.warning(f"Memory search failed: {e}")
        return []


def search_all(
    db: Session,
    session_id: str,
    query: str,
    limit: int = 20,
    include_notes: bool = True,
    include_transcripts: bool = True,
    include_memory: bool = True,
) -> Dict[str, Any]:
    """
    Unified search across all content types.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        query: Search query
        limit: Maximum total results
        include_notes: Include notes in search
        include_transcripts: Include transcripts in search
        include_memory: Include memory in search
        
    Returns:
        Dictionary with results grouped by type and combined ranked list
    """
    if not query or len(query.strip()) < 2:
        return {
            "query": query,
            "results": [],
            "by_type": {
                "notes": [],
                "transcripts": [],
                "memory": [],
            },
            "total": 0,
        }
    
    query = query.strip()
    per_type_limit = max(5, limit // 3)
    
    all_results = []
    by_type = {
        "notes": [],
        "transcripts": [],
        "memory": [],
    }
    
    # Search notes
    if include_notes:
        notes_results = search_notes(db, session_id, query, limit=per_type_limit)
        by_type["notes"] = notes_results
        all_results.extend(notes_results)
    
    # Search transcripts
    if include_transcripts:
        transcript_results = search_transcripts(db, session_id, query, limit=per_type_limit)
        by_type["transcripts"] = transcript_results
        all_results.extend(transcript_results)
    
    # Search memory
    if include_memory:
        memory_results = search_memory(session_id, query, limit=per_type_limit)
        by_type["memory"] = memory_results
        all_results.extend(memory_results)
    
    # Sort all results by score
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Limit total results
    all_results = all_results[:limit]
    
    return {
        "query": query,
        "results": all_results,
        "by_type": by_type,
        "total": len(all_results),
    }


def _extract_snippet(text: str, query: str, context_chars: int = 100) -> str:
    """
    Extract a snippet from text around the first occurrence of query.
    
    Args:
        text: Full text to extract from
        query: Query to find
        context_chars: Characters of context on each side
        
    Returns:
        Snippet with context
    """
    text_lower = text.lower()
    query_lower = query.lower()
    
    pos = text_lower.find(query_lower)
    
    if pos == -1:
        # Query not found, return start of text
        return text[:context_chars * 2] + "..." if len(text) > context_chars * 2 else text
    
    start = max(0, pos - context_chars)
    end = min(len(text), pos + len(query) + context_chars)
    
    snippet = text[start:end]
    
    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet.strip()

