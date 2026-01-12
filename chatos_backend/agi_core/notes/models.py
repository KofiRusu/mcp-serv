"""
Notes Models for AGI Core

Data structures for notes and action items.
"""

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NoteType(str, Enum):
    """Types of notes for classification."""
    MEETING = "meeting"
    BRAINSTORM = "brainstorm"
    LECTURE = "lecture"
    JOURNAL = "journal"
    GENERAL = "general"


class SourceType(str, Enum):
    """Source of the note content."""
    TEXT = "text"
    AUDIO = "audio"
    IMPORTED = "imported"


class ActionStatus(str, Enum):
    """Status of an action item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActionPriority(str, Enum):
    """Priority levels for action items."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ActionItem:
    """
    An action item extracted from a note.
    
    Attributes:
        id: Unique identifier
        description: What needs to be done
        assignee: Who should do it (if mentioned)
        due_date: When it's due (if mentioned)
        priority: LOW, MEDIUM, or HIGH
        status: Current status
        source_note_id: ID of the note this was extracted from
        linked_task_id: ID of linked AGI task (if converted)
        created_at: Creation timestamp
        completed_at: Completion timestamp
        metadata: Additional data
    """
    description: str
    source_note_id: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: ActionPriority = ActionPriority.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    linked_task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = f"action_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "assignee": self.assignee,
            "due_date": self.due_date,
            "priority": self.priority.value if isinstance(self.priority, ActionPriority) else self.priority,
            "status": self.status.value if isinstance(self.status, ActionStatus) else self.status,
            "source_note_id": self.source_note_id,
            "linked_task_id": self.linked_task_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionItem":
        """Create from dictionary."""
        priority = data.get("priority", "medium")
        if isinstance(priority, str):
            priority = ActionPriority(priority)
        
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = ActionStatus(status)
        
        return cls(
            id=data.get("id", ""),
            description=data["description"],
            assignee=data.get("assignee"),
            due_date=data.get("due_date"),
            priority=priority,
            status=status,
            source_note_id=data.get("source_note_id", ""),
            linked_task_id=data.get("linked_task_id"),
            created_at=data.get("created_at", time.time()),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {}),
        )
    
    def complete(self) -> None:
        """Mark action item as completed."""
        self.status = ActionStatus.COMPLETED
        self.completed_at = time.time()
    
    def cancel(self) -> None:
        """Mark action item as cancelled."""
        self.status = ActionStatus.CANCELLED
        self.completed_at = time.time()
    
    def start(self) -> None:
        """Mark action item as in progress."""
        self.status = ActionStatus.IN_PROGRESS


@dataclass
class Note:
    """
    A structured note with AI-powered features.
    
    Attributes:
        id: Unique identifier
        title: Note title
        content: Note content (markdown/plain text)
        note_type: Type of note (meeting, brainstorm, etc.)
        source_type: How the note was created
        tags: Tags for categorization
        action_items: Extracted action items
        linked_note_ids: IDs of related notes
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional data
    """
    title: str
    content: str = ""
    note_type: NoteType = NoteType.GENERAL
    source_type: SourceType = SourceType.TEXT
    tags: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    linked_note_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = f"note_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "note_type": self.note_type.value if isinstance(self.note_type, NoteType) else self.note_type,
            "source_type": self.source_type.value if isinstance(self.source_type, SourceType) else self.source_type,
            "tags": self.tags,
            "action_items": [a.to_dict() for a in self.action_items],
            "linked_note_ids": self.linked_note_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Note":
        """Create from dictionary."""
        note_type = data.get("note_type", "general")
        if isinstance(note_type, str):
            note_type = NoteType(note_type)
        
        source_type = data.get("source_type", "text")
        if isinstance(source_type, str):
            source_type = SourceType(source_type)
        
        action_items = [
            ActionItem.from_dict(a) if isinstance(a, dict) else a
            for a in data.get("action_items", [])
        ]
        
        return cls(
            id=data.get("id", ""),
            title=data["title"],
            content=data.get("content", ""),
            note_type=note_type,
            source_type=source_type,
            tags=data.get("tags", []),
            action_items=action_items,
            linked_note_ids=data.get("linked_note_ids", []),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {}),
        )
    
    def update_content(self, content: str) -> None:
        """Update note content and timestamp."""
        self.content = content
        self.updated_at = time.time()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = time.time()
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag. Returns True if removed."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = time.time()
            return True
        return False
    
    def add_action_item(self, action: ActionItem) -> None:
        """Add an action item to the note."""
        action.source_note_id = self.id
        self.action_items.append(action)
        self.updated_at = time.time()
    
    def remove_action_item(self, action_id: str) -> bool:
        """Remove an action item by ID. Returns True if removed."""
        for i, action in enumerate(self.action_items):
            if action.id == action_id:
                self.action_items.pop(i)
                self.updated_at = time.time()
                return True
        return False
    
    def get_action_item(self, action_id: str) -> Optional[ActionItem]:
        """Get an action item by ID."""
        for action in self.action_items:
            if action.id == action_id:
                return action
        return None
    
    def link_note(self, note_id: str) -> None:
        """Link another note to this one."""
        if note_id not in self.linked_note_ids and note_id != self.id:
            self.linked_note_ids.append(note_id)
            self.updated_at = time.time()
    
    def unlink_note(self, note_id: str) -> bool:
        """Unlink a note. Returns True if unlinked."""
        if note_id in self.linked_note_ids:
            self.linked_note_ids.remove(note_id)
            self.updated_at = time.time()
            return True
        return False
    
    def pending_actions_count(self) -> int:
        """Count pending action items."""
        return sum(1 for a in self.action_items if a.status == ActionStatus.PENDING)
    
    def completed_actions_count(self) -> int:
        """Count completed action items."""
        return sum(1 for a in self.action_items if a.status == ActionStatus.COMPLETED)
    
    def summary(self) -> str:
        """Get a one-line summary of the note."""
        type_emoji = {
            NoteType.MEETING: "📅",
            NoteType.BRAINSTORM: "💡",
            NoteType.LECTURE: "📚",
            NoteType.JOURNAL: "📔",
            NoteType.GENERAL: "📝",
        }
        emoji = type_emoji.get(self.note_type, "📝")
        actions = f" ({self.pending_actions_count()} actions)" if self.action_items else ""
        return f"{emoji} {self.title}{actions}"
    
    def word_count(self) -> int:
        """Get word count of content."""
        return len(self.content.split())
    
    def age_hours(self) -> float:
        """Get age of note in hours."""
        return (time.time() - self.created_at) / 3600

