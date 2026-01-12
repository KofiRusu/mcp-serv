"""
Task Manager for AGI Core

Manages task lifecycle with persistence.
"""

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .models import Task, TaskStatus, TaskPriority


# Default storage location
DEFAULT_TASKS_DIR = Path.home() / "ChatOS-Memory" / "agi" / "tasks"


class TaskManager:
    """
    Manages tasks with CRUD operations and persistence.
    
    Usage:
        tm = TaskManager()
        task = tm.create_task("Write documentation", priority=TaskPriority.HIGH)
        tm.start_task(task.id)
        tm.complete_task(task.id, result="Done!")
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the task manager.
        
        Args:
            storage_path: Path to store tasks (default: ~/ChatOS-Memory/agi/tasks/)
        """
        self.storage_path = storage_path or DEFAULT_TASKS_DIR
        self.storage_path = Path(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.tasks_file = self.storage_path / "tasks.json"
        self._tasks: Dict[str, Task] = {}
        
        # Load existing tasks
        self._load()
    
    def _load(self) -> None:
        """Load tasks from disk."""
        if not self.tasks_file.exists():
            return
        
        try:
            data = json.loads(self.tasks_file.read_text(encoding="utf-8"))
            for task_data in data.get("tasks", []):
                task = Task.from_dict(task_data)
                self._tasks[task.id] = task
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to load tasks: {e}")
    
    def _save(self) -> None:
        """Save tasks to disk."""
        data = {
            "version": 1,
            "updated_at": time.time(),
            "tasks": [t.to_dict() for t in self._tasks.values()],
        }
        
        # Atomic write
        temp_file = self.tasks_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.tasks_file)
    
    # ==========================================================================
    # CRUD Operations
    # ==========================================================================
    
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        parent_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Create a new task.
        
        Args:
            title: Task title
            description: Task description
            priority: Task priority
            parent_id: ID of parent task (for subtasks)
            dependencies: IDs of tasks this depends on
            tags: Tags for categorization
            metadata: Additional task data
            
        Returns:
            The created task
        """
        task = Task(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id,
            dependencies=dependencies or [],
            tags=tags or [],
            metadata=metadata or {},
        )
        
        self._tasks[task.id] = task
        
        # Update parent's subtask list
        if parent_id and parent_id in self._tasks:
            self._tasks[parent_id].add_subtask_id(task.id)
        
        self._save()
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Task]:
        """
        Update a task's properties.
        
        Args:
            task_id: ID of the task to update
            title: New title (if provided)
            description: New description (if provided)
            priority: New priority (if provided)
            tags: New tags (if provided)
            metadata: Metadata to merge (if provided)
            
        Returns:
            The updated task, or None if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if tags is not None:
            task.tags = tags
        if metadata is not None:
            task.metadata.update(metadata)
        
        self._save()
        return task
    
    def delete_task(self, task_id: str, cascade: bool = False) -> bool:
        """
        Delete a task.
        
        Args:
            task_id: ID of the task to delete
            cascade: If True, also delete subtasks
            
        Returns:
            True if deleted, False if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        # Delete subtasks if cascade
        if cascade:
            for subtask_id in task.subtask_ids:
                self.delete_task(subtask_id, cascade=True)
        
        # Remove from parent's subtask list
        if task.parent_id and task.parent_id in self._tasks:
            parent = self._tasks[task.parent_id]
            if task_id in parent.subtask_ids:
                parent.subtask_ids.remove(task_id)
        
        # Remove as dependency from other tasks
        for other_task in self._tasks.values():
            other_task.remove_dependency(task_id)
        
        del self._tasks[task_id]
        self._save()
        return True
    
    # ==========================================================================
    # Status Management
    # ==========================================================================
    
    def start_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as in progress."""
        task = self._tasks.get(task_id)
        if task:
            task.start()
            self._save()
        return task
    
    def complete_task(self, task_id: str, result: Any = None) -> Optional[Task]:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if task:
            task.complete(result)
            
            # Update dependencies in other tasks
            for other_task in self._tasks.values():
                if task_id in other_task.dependencies:
                    other_task.remove_dependency(task_id)
                    # If no more dependencies, unblock
                    if not other_task.dependencies and other_task.status == TaskStatus.BLOCKED:
                        other_task.status = TaskStatus.PENDING
            
            self._save()
        return task
    
    def fail_task(self, task_id: str, error: str) -> Optional[Task]:
        """Mark a task as failed."""
        task = self._tasks.get(task_id)
        if task:
            task.fail(error)
            self._save()
        return task
    
    def cancel_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as cancelled."""
        task = self._tasks.get(task_id)
        if task:
            task.cancel()
            self._save()
        return task
    
    def update_status(self, task_id: str, status: TaskStatus) -> Optional[Task]:
        """Update a task's status."""
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            self._save()
        return task
    
    # ==========================================================================
    # Queries
    # ==========================================================================
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
    ) -> List[Task]:
        """
        List tasks with optional filtering.
        
        Args:
            status: Filter by status
            priority: Filter by priority
            tags: Filter by tags (any match)
            parent_id: Filter by parent task
            
        Returns:
            List of matching tasks
        """
        results = []
        
        for task in self._tasks.values():
            # Apply filters
            if status is not None and task.status != status:
                continue
            if priority is not None and task.priority != priority:
                continue
            if parent_id is not None and task.parent_id != parent_id:
                continue
            if tags:
                if not any(tag in task.tags for tag in tags):
                    continue
            
            results.append(task)
        
        # Sort by priority (descending) then creation time
        results.sort(key=lambda t: (-t.priority.value, t.created_at))
        return results
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (no pending dependencies)."""
        ready = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_satisfied = True
            for dep_id in task.dependencies:
                dep_task = self._tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    deps_satisfied = False
                    break
            
            if deps_satisfied:
                ready.append(task)
        
        # Sort by priority
        ready.sort(key=lambda t: -t.priority.value)
        return ready
    
    def get_subtasks(self, parent_id: str) -> List[Task]:
        """Get all subtasks of a parent task."""
        return self.list_tasks(parent_id=parent_id)
    
    def get_blocked_tasks(self) -> List[Task]:
        """Get tasks that are blocked by dependencies."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.BLOCKED]
    
    def get_active_tasks(self) -> List[Task]:
        """Get tasks that are currently in progress."""
        return self.list_tasks(status=TaskStatus.IN_PROGRESS)
    
    # ==========================================================================
    # Utilities
    # ==========================================================================
    
    def add_subtask(
        self,
        parent_id: str,
        title: str,
        description: str = "",
        priority: Optional[TaskPriority] = None,
    ) -> Optional[Task]:
        """
        Add a subtask to an existing task.
        
        Args:
            parent_id: ID of the parent task
            title: Subtask title
            description: Subtask description
            priority: Subtask priority (inherits from parent if not specified)
            
        Returns:
            The created subtask, or None if parent not found
        """
        parent = self._tasks.get(parent_id)
        if not parent:
            return None
        
        return self.create_task(
            title=title,
            description=description,
            priority=priority or parent.priority,
            parent_id=parent_id,
        )
    
    def add_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """
        Add a dependency to a task.
        
        Args:
            task_id: ID of the task
            depends_on_id: ID of the task it depends on
            
        Returns:
            True if added, False if task not found
        """
        task = self._tasks.get(task_id)
        if not task or depends_on_id not in self._tasks:
            return False
        
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            self._save()
        
        return True
    
    def count(self, status: Optional[TaskStatus] = None) -> int:
        """Count tasks, optionally filtered by status."""
        if status is None:
            return len(self._tasks)
        return len([t for t in self._tasks.values() if t.status == status])
    
    def clear_completed(self, older_than_hours: float = 24) -> int:
        """
        Remove completed tasks older than specified hours.
        
        Args:
            older_than_hours: Remove tasks completed more than this many hours ago
            
        Returns:
            Number of tasks removed
        """
        cutoff = time.time() - (older_than_hours * 3600)
        to_remove = []
        
        for task_id, task in self._tasks.items():
            if task.status == TaskStatus.COMPLETED:
                if task.completed_at and task.completed_at < cutoff:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
        
        if to_remove:
            self._save()
        
        return len(to_remove)
    
    def get_stats(self) -> Dict[str, int]:
        """Get task statistics."""
        stats = {status.value: 0 for status in TaskStatus}
        stats["total"] = len(self._tasks)
        
        for task in self._tasks.values():
            stats[task.status.value] += 1
        
        return stats
    
    def export_tasks(self, output_path: Path) -> int:
        """Export all tasks to a JSON file."""
        data = {
            "exported_at": time.time(),
            "tasks": [t.to_dict() for t in self._tasks.values()],
        }
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return len(self._tasks)

