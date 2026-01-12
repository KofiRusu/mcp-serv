"""
Goal Manager for AGI Core

High-level goal tracking and management.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class GoalStatus(Enum):
    """Status of a goal."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    """
    A high-level goal to pursue.
    
    Attributes:
        id: Unique goal identifier
        description: What the goal is
        status: Current goal status
        priority: Goal priority (1-10)
        created_at: When goal was created
        due_date: Optional deadline
        progress: Completion percentage (0-100)
        task_ids: Associated task IDs
        metadata: Additional goal data
    """
    description: str
    status: GoalStatus = GoalStatus.ACTIVE
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    due_date: Optional[float] = None
    progress: float = 0.0
    task_ids: List[str] = field(default_factory=list)
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"goal_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "due_date": self.due_date,
            "progress": self.progress,
            "task_ids": self.task_ids,
            "notes": self.notes,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        return cls(
            id=data.get("id", ""),
            description=data["description"],
            status=GoalStatus(data.get("status", "active")),
            priority=data.get("priority", 5),
            created_at=data.get("created_at", time.time()),
            due_date=data.get("due_date"),
            progress=data.get("progress", 0.0),
            task_ids=data.get("task_ids", []),
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {}),
        )
    
    def is_overdue(self) -> bool:
        """Check if goal is past due date."""
        if self.due_date and self.status == GoalStatus.ACTIVE:
            return time.time() > self.due_date
        return False
    
    def days_remaining(self) -> Optional[float]:
        """Get days until due date."""
        if self.due_date:
            return (self.due_date - time.time()) / 86400
        return None
    
    def summary(self) -> str:
        """Get a one-line summary."""
        status_emoji = {
            GoalStatus.ACTIVE: "🎯",
            GoalStatus.PAUSED: "⏸️",
            GoalStatus.COMPLETED: "✅",
            GoalStatus.FAILED: "❌",
            GoalStatus.CANCELLED: "🚫",
        }
        emoji = status_emoji.get(self.status, "❓")
        return f"{emoji} [{self.priority}] {self.description[:50]} ({self.progress:.0f}%)"


class GoalManager:
    """
    Manages high-level goals over time.
    
    Usage:
        gm = GoalManager()
        goal = gm.create_goal("Build AGI system", priority=10)
        gm.update_progress(goal.id, 25.0)
        gm.complete_goal(goal.id)
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / "ChatOS-Memory" / "agi" / "goals"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.goals_file = self.storage_path / "goals.json"
        self._goals: Dict[str, Goal] = {}
        
        self._load()
    
    def _load(self) -> None:
        """Load goals from disk."""
        if not self.goals_file.exists():
            return
        
        try:
            data = json.loads(self.goals_file.read_text(encoding="utf-8"))
            for goal_data in data.get("goals", []):
                goal = Goal.from_dict(goal_data)
                self._goals[goal.id] = goal
        except Exception as e:
            print(f"Warning: Failed to load goals: {e}")
    
    def _save(self) -> None:
        """Save goals to disk."""
        data = {
            "version": 1,
            "updated_at": time.time(),
            "goals": [g.to_dict() for g in self._goals.values()],
        }
        
        temp_file = self.goals_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.goals_file)
    
    def create_goal(
        self,
        description: str,
        priority: int = 5,
        due_date: Optional[float] = None,
        notes: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(
            description=description,
            priority=max(1, min(10, priority)),
            due_date=due_date,
            notes=notes,
            metadata=metadata or {},
        )
        
        self._goals[goal.id] = goal
        self._save()
        return goal
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self._goals.get(goal_id)
    
    def update_goal(
        self,
        goal_id: str,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_date: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[Goal]:
        """Update goal properties."""
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        
        if description is not None:
            goal.description = description
        if priority is not None:
            goal.priority = max(1, min(10, priority))
        if due_date is not None:
            goal.due_date = due_date
        if notes is not None:
            goal.notes = notes
        
        self._save()
        return goal
    
    def update_progress(self, goal_id: str, progress: float) -> Optional[Goal]:
        """Update goal progress (0-100)."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.progress = max(0, min(100, progress))
            self._save()
        return goal
    
    def complete_goal(self, goal_id: str) -> Optional[Goal]:
        """Mark goal as completed."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.status = GoalStatus.COMPLETED
            goal.progress = 100.0
            self._save()
        return goal
    
    def fail_goal(self, goal_id: str, reason: str = "") -> Optional[Goal]:
        """Mark goal as failed."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.status = GoalStatus.FAILED
            if reason:
                goal.notes = f"{goal.notes}\nFailed: {reason}"
            self._save()
        return goal
    
    def pause_goal(self, goal_id: str) -> Optional[Goal]:
        """Pause a goal."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.status = GoalStatus.PAUSED
            self._save()
        return goal
    
    def resume_goal(self, goal_id: str) -> Optional[Goal]:
        """Resume a paused goal."""
        goal = self._goals.get(goal_id)
        if goal and goal.status == GoalStatus.PAUSED:
            goal.status = GoalStatus.ACTIVE
            self._save()
        return goal
    
    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal."""
        if goal_id in self._goals:
            del self._goals[goal_id]
            self._save()
            return True
        return False
    
    def add_task_to_goal(self, goal_id: str, task_id: str) -> bool:
        """Associate a task with a goal."""
        goal = self._goals.get(goal_id)
        if goal and task_id not in goal.task_ids:
            goal.task_ids.append(task_id)
            self._save()
            return True
        return False
    
    def list_goals(
        self,
        status: Optional[GoalStatus] = None,
        min_priority: Optional[int] = None,
    ) -> List[Goal]:
        """List goals with optional filtering."""
        goals = list(self._goals.values())
        
        if status:
            goals = [g for g in goals if g.status == status]
        if min_priority:
            goals = [g for g in goals if g.priority >= min_priority]
        
        # Sort by priority (descending) then created_at
        goals.sort(key=lambda g: (-g.priority, g.created_at))
        return goals
    
    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        return self.list_goals(status=GoalStatus.ACTIVE)
    
    def get_overdue_goals(self) -> List[Goal]:
        """Get all overdue goals."""
        return [g for g in self._goals.values() if g.is_overdue()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get goal statistics."""
        stats = {status.value: 0 for status in GoalStatus}
        stats["total"] = len(self._goals)
        
        for goal in self._goals.values():
            stats[goal.status.value] += 1
        
        stats["overdue"] = len(self.get_overdue_goals())
        
        return stats

