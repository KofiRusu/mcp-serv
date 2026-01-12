"""
tasks.py - Task creation service for notes.

Provides functionality to create AGI tasks from action items extracted from notes.
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from chatos_backend.database.notes_models import NoteDB
from chatos_backend.agi_core.tasks.manager import TaskManager
from chatos_backend.agi_core.tasks.models import Task, TaskPriority

logger = logging.getLogger(__name__)

# Session-scoped task managers
_task_managers: Dict[str, TaskManager] = {}


def get_task_manager(session_id: str) -> TaskManager:
    """
    Get or create a TaskManager for a session.
    
    Args:
        session_id: User session ID
        
    Returns:
        TaskManager instance for the session
    """
    if session_id not in _task_managers:
        from pathlib import Path
        storage_path = Path.home() / "ChatOS-Memory" / "agi" / "tasks" / session_id
        _task_managers[session_id] = TaskManager(storage_path=storage_path)
    return _task_managers[session_id]


def parse_action_items_from_content(content: str) -> List[str]:
    """
    Parse action items from note content.
    
    The note content format from the summarisation pipeline is:
    <summary text>
    
    Action Items:
    - Item 1
    - Item 2
    
    Args:
        content: Note content string
        
    Returns:
        List of action item strings
    """
    action_items = []
    
    # Look for "Action Items:" section
    if "Action Items:" in content:
        parts = content.split("Action Items:")
        if len(parts) > 1:
            action_section = parts[1].strip()
            
            # Parse bullet points
            for line in action_section.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    action_items.append(line[2:].strip())
                elif line.startswith("• "):
                    action_items.append(line[2:].strip())
                elif line and not line.startswith("#"):
                    # Stop at next section header or empty lines
                    if line.startswith("\n\n"):
                        break
    
    return action_items


def create_tasks_from_note(
    db: Session,
    session_id: str,
    note_id: int,
) -> Dict[str, Any]:
    """
    Create AGI tasks from action items in a note.
    
    This function:
    1. Fetches the note and extracts action items
    2. Creates a task for each action item
    3. Links tasks back to the note via metadata
    4. Tracks created task IDs in note metadata to prevent duplicates
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        note_id: ID of the note to create tasks from
        
    Returns:
        Dictionary with created tasks and metadata
        
    Raises:
        HTTPException: If note not found or access denied
    """
    from fastapi import HTTPException
    
    # Fetch the note
    note = db.query(NoteDB).filter(NoteDB.id == note_id).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if tasks were already created for this note
    # We store task IDs in a JSON field or check by metadata
    task_manager = get_task_manager(session_id)
    
    # Check for existing tasks linked to this note
    existing_tasks = task_manager.list_tasks(tags=[f"note:{note_id}"])
    if existing_tasks:
        return {
            "success": True,
            "note_id": note_id,
            "tasks_created": 0,
            "tasks": [t.to_dict() for t in existing_tasks],
            "message": "Tasks already exist for this note",
            "already_exists": True,
        }
    
    # Parse action items from content
    action_items = parse_action_items_from_content(note.content)
    
    if not action_items:
        return {
            "success": True,
            "note_id": note_id,
            "tasks_created": 0,
            "tasks": [],
            "message": "No action items found in note",
            "already_exists": False,
        }
    
    # Create tasks for each action item
    created_tasks = []
    
    for item in action_items:
        task = task_manager.create_task(
            title=item,
            description=f"Action item from note: {note.title}",
            priority=TaskPriority.MEDIUM,
            tags=[f"note:{note_id}", "from-note", "action-item"],
            metadata={
                "source_note_id": note_id,
                "source_note_title": note.title,
                "session_id": session_id,
            },
        )
        created_tasks.append(task)
        logger.info(f"Created task {task.id} from note {note_id}: {item}")
    
    return {
        "success": True,
        "note_id": note_id,
        "tasks_created": len(created_tasks),
        "tasks": [t.to_dict() for t in created_tasks],
        "message": f"Created {len(created_tasks)} tasks from action items",
        "already_exists": False,
    }


def get_tasks_for_note(session_id: str, note_id: int) -> List[Task]:
    """
    Get all tasks associated with a note.
    
    Args:
        session_id: User session ID
        note_id: Note ID
        
    Returns:
        List of Task objects
    """
    task_manager = get_task_manager(session_id)
    return task_manager.list_tasks(tags=[f"note:{note_id}"])


def get_tasks_for_session(
    session_id: str,
    status: Optional[str] = None,
) -> List[Task]:
    """
    Get all tasks for a session.
    
    Args:
        session_id: User session ID
        status: Optional status filter
        
    Returns:
        List of Task objects
    """
    from chatos_backend.agi_core.tasks.models import TaskStatus
    
    task_manager = get_task_manager(session_id)
    
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            pass
    
    return task_manager.list_tasks(status=status_filter)


def update_task_status(
    session_id: str,
    task_id: str,
    status: str,
) -> Optional[Task]:
    """
    Update a task's status.
    
    Args:
        session_id: User session ID
        task_id: Task ID
        status: New status (pending, in_progress, completed, failed, cancelled)
        
    Returns:
        Updated Task or None if not found
    """
    from chatos_backend.agi_core.tasks.models import TaskStatus
    
    task_manager = get_task_manager(session_id)
    
    try:
        task_status = TaskStatus(status)
    except ValueError:
        return None
    
    return task_manager.update_status(task_id, task_status)

