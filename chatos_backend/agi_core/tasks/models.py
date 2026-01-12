"""
Task Models for AGI Core

Data structures for task management.
"""

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"  # Waiting on dependencies


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3
    
    def __lt__(self, other):
        if isinstance(other, TaskPriority):
            return self.value < other.value
        return NotImplemented


@dataclass
class Task:
    """
    A task to be executed by the AGI system.
    
    Attributes:
        id: Unique task identifier
        title: Short title for the task
        description: Detailed description
        status: Current task status
        priority: Task priority level
        parent_id: ID of parent task (for subtasks)
        subtask_ids: IDs of child tasks
        dependencies: IDs of tasks this depends on
        tags: Tags for categorization
        result: Result after completion
        error: Error message if failed
        created_at: Creation timestamp
        started_at: When execution started
        completed_at: When execution finished
        metadata: Additional task data
    """
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None
    subtask_ids: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "parent_id": self.parent_id,
            "subtask_ids": self.subtask_ids,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            priority=TaskPriority(data.get("priority", 1)),
            parent_id=data.get("parent_id"),
            subtask_ids=data.get("subtask_ids", []),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", time.time()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {}),
        )
    
    def start(self) -> None:
        """Mark task as in progress."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = time.time()
    
    def complete(self, result: Any = None) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()
    
    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = time.time()
    
    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = time.time()
    
    def block(self) -> None:
        """Mark task as blocked."""
        self.status = TaskStatus.BLOCKED
    
    def is_ready(self) -> bool:
        """Check if task is ready to execute (no pending dependencies)."""
        return self.status == TaskStatus.PENDING and len(self.dependencies) == 0
    
    def is_complete(self) -> bool:
        """Check if task is done (completed, failed, or cancelled)."""
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]
    
    def duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def age_seconds(self) -> float:
        """Get age of task in seconds."""
        return time.time() - self.created_at
    
    def add_subtask_id(self, subtask_id: str) -> None:
        """Add a subtask ID."""
        if subtask_id not in self.subtask_ids:
            self.subtask_ids.append(subtask_id)
    
    def remove_dependency(self, dep_id: str) -> bool:
        """Remove a dependency (e.g., when it completes)."""
        if dep_id in self.dependencies:
            self.dependencies.remove(dep_id)
            return True
        return False
    
    def summary(self) -> str:
        """Get a one-line summary."""
        status_emoji = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
            TaskStatus.BLOCKED: "🔒",
        }
        emoji = status_emoji.get(self.status, "❓")
        return f"{emoji} [{self.priority.name}] {self.title}"

