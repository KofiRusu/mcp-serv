"""
Notes API Routes for ChatOS

Exposes note management with AI-powered classification and action item extraction.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatos_backend.agi_core.notes import (
    Note,
    ActionItem,
    NoteType,
    SourceType,
    ActionStatus,
    ActionPriority,
    NoteStore,
    NoteClassifier,
    ActionItemExtractor,
)
from chatos_backend.agi_core.tasks import TaskManager, TaskPriority as AGITaskPriority

router = APIRouter(prefix="/api/notes", tags=["Notes"])


# =============================================================================
# Singletons
# =============================================================================

_note_store: Optional[NoteStore] = None
_classifier: Optional[NoteClassifier] = None
_extractor: Optional[ActionItemExtractor] = None
_task_manager: Optional[TaskManager] = None


def get_note_store() -> NoteStore:
    global _note_store
    if _note_store is None:
        _note_store = NoteStore()
    return _note_store


def get_classifier() -> NoteClassifier:
    global _classifier
    if _classifier is None:
        _classifier = NoteClassifier()
    return _classifier


def get_extractor() -> ActionItemExtractor:
    global _extractor
    if _extractor is None:
        _extractor = ActionItemExtractor()
    return _extractor


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


# =============================================================================
# Request/Response Models
# =============================================================================

class NoteCreateRequest(BaseModel):
    title: str
    content: str = ""
    note_type: Optional[str] = None  # Will auto-classify if not provided
    source_type: str = "text"
    tags: List[str] = []
    auto_classify: bool = True
    auto_extract_actions: bool = False


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[str] = None
    tags: Optional[List[str]] = None


class ActionItemCreateRequest(BaseModel):
    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"


class ActionItemUpdateRequest(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    note_type: str
    source_type: str
    tags: List[str]
    action_items: List[Dict[str, Any]]
    linked_note_ids: List[str]
    created_at: float
    updated_at: float
    metadata: Dict[str, Any]


class ActionItemResponse(BaseModel):
    id: str
    description: str
    assignee: Optional[str]
    due_date: Optional[str]
    priority: str
    status: str
    source_note_id: str
    linked_task_id: Optional[str]
    created_at: float
    completed_at: Optional[float]


class NoteLinkRequest(BaseModel):
    target_note_id: str


# =============================================================================
# Note CRUD Endpoints
# =============================================================================

@router.get("")
async def list_notes(
    note_type: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
):
    """List all notes with optional filtering."""
    store = get_note_store()
    
    if search:
        notes = store.search(search, k=limit)
    elif note_type:
        try:
            nt = NoteType(note_type)
            notes = store.list_by_type(nt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid note_type: {note_type}")
    elif tag:
        notes = store.list_by_tag(tag)
    else:
        notes = store.all()
    
    # Sort by updated_at descending
    notes.sort(key=lambda n: n.updated_at, reverse=True)
    
    return {
        "notes": [n.to_dict() for n in notes[:limit]],
        "total": len(notes),
        "stats": store.get_stats(),
    }


@router.post("", response_model=NoteResponse)
async def create_note(request: NoteCreateRequest):
    """Create a new note with optional auto-classification."""
    store = get_note_store()
    
    # Parse source type
    try:
        source_type = SourceType(request.source_type)
    except ValueError:
        source_type = SourceType.TEXT
    
    # Parse or auto-classify note type
    if request.note_type:
        try:
            note_type = NoteType(request.note_type)
        except ValueError:
            note_type = NoteType.GENERAL
    elif request.auto_classify and request.content:
        # Create temporary note for classification
        temp_note = Note(title=request.title, content=request.content)
        classifier = get_classifier()
        note_type = await classifier.classify(temp_note)
    else:
        note_type = NoteType.GENERAL
    
    # Create the note
    note = store.create(
        title=request.title,
        content=request.content,
        note_type=note_type,
        source_type=source_type,
        tags=request.tags,
    )
    
    # Auto-extract action items if requested
    if request.auto_extract_actions and request.content:
        extractor = get_extractor()
        actions = await extractor.extract(note)
        for action in actions:
            note.add_action_item(action)
        # Save the updated note
        store._save()
    
    return NoteResponse(**note.to_dict())


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str):
    """Get a specific note by ID."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return NoteResponse(**note.to_dict())


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: str, request: NoteUpdateRequest):
    """Update a note's properties."""
    store = get_note_store()
    
    # Parse note type if provided
    note_type = None
    if request.note_type:
        try:
            note_type = NoteType(request.note_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid note_type: {request.note_type}")
    
    note = store.update(
        note_id,
        title=request.title,
        content=request.content,
        note_type=note_type,
        tags=request.tags,
    )
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return NoteResponse(**note.to_dict())


@router.delete("/{note_id}")
async def delete_note(note_id: str):
    """Delete a note."""
    store = get_note_store()
    
    if store.delete(note_id):
        return {"success": True}
    
    raise HTTPException(status_code=404, detail="Note not found")


# =============================================================================
# AI Classification & Extraction
# =============================================================================

@router.post("/{note_id}/classify")
async def classify_note(note_id: str):
    """Trigger AI classification for a note."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    classifier = get_classifier()
    note_type = await classifier.classify(note)
    
    # Update the note
    store.update(note_id, note_type=note_type)
    
    return {
        "success": True,
        "note_id": note_id,
        "classified_type": note_type.value,
    }


@router.post("/{note_id}/extract-actions")
async def extract_actions(note_id: str):
    """Extract action items from a note using AI."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    extractor = get_extractor()
    actions = await extractor.extract(note)
    
    # Add new actions to the note (avoid duplicates)
    existing_descriptions = {a.description.lower() for a in note.action_items}
    added = []
    
    for action in actions:
        if action.description.lower() not in existing_descriptions:
            note.add_action_item(action)
            added.append(action.to_dict())
            existing_descriptions.add(action.description.lower())
    
    # Save the updated note
    store._save()
    
    return {
        "success": True,
        "note_id": note_id,
        "extracted_count": len(actions),
        "added_count": len(added),
        "actions": added,
    }


# =============================================================================
# Action Item Endpoints
# =============================================================================

@router.get("/{note_id}/actions")
async def list_actions(note_id: str):
    """List action items for a note."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {
        "actions": [a.to_dict() for a in note.action_items],
        "total": len(note.action_items),
        "pending": note.pending_actions_count(),
        "completed": note.completed_actions_count(),
    }


@router.post("/{note_id}/actions", response_model=ActionItemResponse)
async def create_action(note_id: str, request: ActionItemCreateRequest):
    """Manually add an action item to a note."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Parse priority
    try:
        priority = ActionPriority(request.priority.lower())
    except ValueError:
        priority = ActionPriority.MEDIUM
    
    action = ActionItem(
        description=request.description,
        source_note_id=note_id,
        assignee=request.assignee,
        due_date=request.due_date,
        priority=priority,
    )
    
    note.add_action_item(action)
    store._save()
    
    return ActionItemResponse(**action.to_dict())


@router.put("/{note_id}/actions/{action_id}", response_model=ActionItemResponse)
async def update_action(note_id: str, action_id: str, request: ActionItemUpdateRequest):
    """Update an action item."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    action = note.get_action_item(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    # Update fields
    if request.status:
        try:
            action.status = ActionStatus(request.status.lower())
            if action.status == ActionStatus.COMPLETED:
                action.complete()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    if request.assignee is not None:
        action.assignee = request.assignee
    
    if request.due_date is not None:
        action.due_date = request.due_date
    
    if request.priority:
        try:
            action.priority = ActionPriority(request.priority.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {request.priority}")
    
    note.updated_at = __import__("time").time()
    store._save()
    
    return ActionItemResponse(**action.to_dict())


@router.delete("/{note_id}/actions/{action_id}")
async def delete_action(note_id: str, action_id: str):
    """Delete an action item."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note.remove_action_item(action_id):
        store._save()
        return {"success": True}
    
    raise HTTPException(status_code=404, detail="Action item not found")


@router.post("/{note_id}/actions/{action_id}/complete")
async def complete_action(note_id: str, action_id: str):
    """Mark an action item as complete."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    action = note.get_action_item(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    action.complete()
    note.updated_at = __import__("time").time()
    store._save()
    
    return {"success": True, "action": action.to_dict()}


@router.post("/{note_id}/actions/{action_id}/to-task")
async def convert_to_task(note_id: str, action_id: str):
    """Convert an action item to an AGI task."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    action = note.get_action_item(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    # Check if already linked
    if action.linked_task_id:
        return {
            "success": False,
            "message": "Action already linked to a task",
            "task_id": action.linked_task_id,
        }
    
    # Map priority
    priority_map = {
        ActionPriority.LOW: AGITaskPriority.LOW,
        ActionPriority.MEDIUM: AGITaskPriority.MEDIUM,
        ActionPriority.HIGH: AGITaskPriority.HIGH,
    }
    task_priority = priority_map.get(action.priority, AGITaskPriority.MEDIUM)
    
    # Create the task
    tm = get_task_manager()
    task = tm.create_task(
        title=action.description,
        description=f"From note: {note.title}\n\nAssignee: {action.assignee or 'Unassigned'}\nDue: {action.due_date or 'No due date'}",
        priority=task_priority,
        tags=["from-note", f"note:{note_id}"],
        metadata={
            "source_note_id": note_id,
            "source_action_id": action_id,
        },
    )
    
    # Link the action to the task
    action.linked_task_id = task.id
    note.updated_at = __import__("time").time()
    store._save()
    
    return {
        "success": True,
        "task": task.to_dict(),
        "action": action.to_dict(),
    }


# =============================================================================
# Note Linking
# =============================================================================

@router.post("/{note_id}/link")
async def link_notes(note_id: str, request: NoteLinkRequest):
    """Link two notes together."""
    store = get_note_store()
    
    if store.link_notes(note_id, request.target_note_id):
        return {"success": True}
    
    raise HTTPException(status_code=404, detail="One or both notes not found")


@router.delete("/{note_id}/link/{target_id}")
async def unlink_notes(note_id: str, target_id: str):
    """Remove a link between two notes."""
    store = get_note_store()
    
    if store.unlink_notes(note_id, target_id):
        return {"success": True}
    
    raise HTTPException(status_code=404, detail="One or both notes not found")


@router.get("/{note_id}/linked")
async def get_linked_notes(note_id: str):
    """Get all notes linked to this note."""
    store = get_note_store()
    note = store.get(note_id)
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    linked = store.get_linked_notes(note_id)
    
    return {
        "note_id": note_id,
        "linked_notes": [n.to_dict() for n in linked],
        "count": len(linked),
    }


# =============================================================================
# Tags & Search
# =============================================================================

@router.get("/tags/all")
async def get_all_tags():
    """Get all unique tags across all notes."""
    store = get_note_store()
    tags = store.get_all_tags()
    
    return {"tags": tags, "count": len(tags)}


@router.get("/recent")
async def get_recent_notes(hours: float = 24, limit: int = 10):
    """Get recently updated notes."""
    store = get_note_store()
    notes = store.recent(hours=hours, k=limit)
    
    return {
        "notes": [n.to_dict() for n in notes],
        "count": len(notes),
    }


@router.get("/with-pending-actions")
async def get_notes_with_pending_actions():
    """Get notes that have pending action items."""
    store = get_note_store()
    notes = store.list_with_pending_actions()
    
    return {
        "notes": [n.to_dict() for n in notes],
        "count": len(notes),
    }


@router.get("/all-pending-actions")
async def get_all_pending_actions():
    """Get all pending action items across all notes."""
    store = get_note_store()
    actions = store.get_all_pending_actions()
    
    return {
        "actions": [a.to_dict() for a in actions],
        "count": len(actions),
    }


# =============================================================================
# Stats & Overview
# =============================================================================

@router.get("/stats/overview")
async def get_stats():
    """Get notes statistics."""
    store = get_note_store()
    return store.get_stats()

