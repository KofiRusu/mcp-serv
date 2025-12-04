"""
routes_notes_db.py - API routes for SQLModel-based notes.

Provides REST API endpoints for notes CRUD operations with user scoping.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ChatOS.database.connection import get_session
from ChatOS.api.schemas_notes import (
    NoteCreate,
    NoteUpdate,
    NoteRead,
    NoteListResponse,
)
from ChatOS.controllers import notes_db


router = APIRouter(prefix="/api/notes/db", tags=["Notes (Database)"])


def get_db():
    """Dependency to get database session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=NoteRead, status_code=201)
async def create_note(
    note_in: NoteCreate,
    db=Depends(get_db),
):
    """
    Create a new note.
    
    The session_id in the request body is used for user scoping.
    """
    note = notes_db.create_note(
        db=db,
        session_id=note_in.session_id,
        note_in=note_in,
    )
    return NoteRead.model_validate(note)


@router.get("", response_model=NoteListResponse)
async def list_notes(
    session_id: str = Query(..., description="User session ID"),
    query: Optional[str] = Query(None, description="Search query"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    db=Depends(get_db),
):
    """
    List notes for a user with optional filtering.
    
    - **session_id**: Required. User session ID for scoping.
    - **query**: Optional. Search in title and content.
    - **tag**: Optional. Filter by tag.
    """
    notes = notes_db.list_notes(
        db=db,
        session_id=session_id,
        query=query,
        tag=tag,
    )
    return NoteListResponse(
        notes=[NoteRead.model_validate(n) for n in notes],
        total=len(notes),
    )


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: int,
    session_id: str = Query(..., description="User session ID"),
    db=Depends(get_db),
):
    """
    Get a specific note by ID.
    
    Returns 404 if not found, 403 if access denied.
    """
    note = notes_db.get_note(db=db, session_id=session_id, note_id=note_id)
    return NoteRead.model_validate(note)


@router.put("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: int,
    note_in: NoteUpdate,
    session_id: str = Query(..., description="User session ID"),
    db=Depends(get_db),
):
    """
    Update a note.
    
    Only provided fields are updated.
    Returns 404 if not found, 403 if access denied.
    """
    note = notes_db.update_note(
        db=db,
        session_id=session_id,
        note_id=note_id,
        note_in=note_in,
    )
    return NoteRead.model_validate(note)


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    session_id: str = Query(..., description="User session ID"),
    db=Depends(get_db),
):
    """
    Delete a note.
    
    Returns 404 if not found, 403 if access denied.
    """
    notes_db.delete_note(db=db, session_id=session_id, note_id=note_id)
    return {"success": True, "note_id": note_id}


@router.post("/{note_id}/create_tasks")
async def create_tasks_from_note(
    note_id: int,
    session_id: str = Query(..., description="User session ID"),
    db=Depends(get_db),
):
    """
    Create AGI tasks from action items in a note.
    
    This endpoint extracts action items from the note content and creates
    corresponding tasks in the AGI task system. Tasks are linked back to
    the note via metadata.
    
    If tasks have already been created for this note, returns the existing
    tasks without creating duplicates.
    
    Returns:
        - success: Whether the operation succeeded
        - note_id: ID of the source note
        - tasks_created: Number of new tasks created
        - tasks: List of task objects (new or existing)
        - message: Status message
        - already_exists: True if tasks were previously created
    """
    from ChatOS.services.tasks import create_tasks_from_note as create_tasks
    
    result = create_tasks(db=db, session_id=session_id, note_id=note_id)
    return result


@router.get("/{note_id}/tasks")
async def get_tasks_for_note(
    note_id: int,
    session_id: str = Query(..., description="User session ID"),
    db=Depends(get_db),
):
    """
    Get all tasks created from a note.
    
    Returns a list of tasks that were created from the action items
    in this note.
    """
    from ChatOS.services.tasks import get_tasks_for_note as get_tasks
    
    # Verify note exists and belongs to user
    notes_db.get_note(db=db, session_id=session_id, note_id=note_id)
    
    tasks = get_tasks(session_id=session_id, note_id=note_id)
    return {
        "note_id": note_id,
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks),
    }

