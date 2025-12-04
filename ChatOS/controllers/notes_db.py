"""
notes_db.py - Controller for SQLModel-based notes CRUD operations.

Provides database operations for notes with user scoping via session_id.
"""

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ChatOS.database.notes_models import NoteDB
from ChatOS.api.schemas_notes import NoteCreate, NoteUpdate


def create_note(db: Session, session_id: str, note_in: NoteCreate) -> NoteDB:
    """
    Create a new note.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        note_in: Note creation data
        
    Returns:
        Created NoteDB instance
    """
    note = NoteDB(
        session_id=session_id,
        title=note_in.title,
        content=note_in.content,
        tags=note_in.tags or [],
        source_conversation_id=note_in.source_conversation_id,
        source_attachment_id=note_in.source_attachment_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(
    db: Session,
    session_id: str,
    query: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[NoteDB]:
    """
    List notes for a user with optional filtering.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        query: Optional search query (searches title and content)
        tag: Optional tag filter
        
    Returns:
        List of NoteDB instances
    """
    q = db.query(NoteDB).filter(NoteDB.session_id == session_id)
    
    # Search in title and content
    if query:
        search_term = f"%{query}%"
        q = q.filter(
            or_(
                NoteDB.title.ilike(search_term),
                NoteDB.content.ilike(search_term),
            )
        )
    
    # Filter by tag (JSON contains)
    if tag:
        # For SQLite/PostgreSQL JSON support
        # This works with the JSONType which stores as text in SQLite
        q = q.filter(NoteDB.tags.contains([tag]))
    
    return q.order_by(NoteDB.updated_at.desc()).all()


def get_note(db: Session, session_id: str, note_id: int) -> NoteDB:
    """
    Get a specific note by ID.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        note_id: Note ID
        
    Returns:
        NoteDB instance
        
    Raises:
        HTTPException: If note not found or access denied
    """
    note = db.query(NoteDB).filter(NoteDB.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return note


def update_note(
    db: Session,
    session_id: str,
    note_id: int,
    note_in: NoteUpdate,
) -> NoteDB:
    """
    Update a note.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        note_id: Note ID
        note_in: Update data (only non-None fields are updated)
        
    Returns:
        Updated NoteDB instance
        
    Raises:
        HTTPException: If note not found or access denied
    """
    note = get_note(db, session_id, note_id)
    
    # Update only provided fields
    update_data = note_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)
    
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, session_id: str, note_id: int) -> None:
    """
    Delete a note.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        note_id: Note ID
        
    Raises:
        HTTPException: If note not found or access denied
    """
    note = get_note(db, session_id, note_id)
    db.delete(note)
    db.commit()


def count_notes(db: Session, session_id: str) -> int:
    """
    Count notes for a user.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        
    Returns:
        Number of notes
    """
    return db.query(NoteDB).filter(NoteDB.session_id == session_id).count()

