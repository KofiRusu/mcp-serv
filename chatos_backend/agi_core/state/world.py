"""
World State Manager for AGI Core

Tracks the current state of the system and environment.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StateEvent:
    """
    An event that changed the world state.
    
    Attributes:
        event_type: Type of event (task_complete, error, user_input, etc.)
        description: What happened
        timestamp: When it happened
        metadata: Additional event data
    """
    event_type: str
    description: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "description": self.description,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateEvent":
        return cls(
            event_type=data["event_type"],
            description=data["description"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class WorldState:
    """
    Manages the current state of the AGI system.
    
    Tracks:
    - Active goals and tasks
    - Recent events
    - Environment variables
    - System status
    
    Usage:
        state = WorldState()
        state.set("current_goal", "Research quantum computing")
        state.record_event("task_complete", "Finished literature review")
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / "ChatOS-Memory" / "agi" / "state"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.storage_path / "world_state.json"
        
        self._state: Dict[str, Any] = {}
        self._events: List[StateEvent] = []
        self._max_events = 100
        
        self._load()
    
    def _load(self) -> None:
        """Load state from disk."""
        if not self.state_file.exists():
            return
        
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._state = data.get("state", {})
            self._events = [
                StateEvent.from_dict(e)
                for e in data.get("events", [])
            ]
        except Exception as e:
            print(f"Warning: Failed to load world state: {e}")
    
    def _save(self) -> None:
        """Save state to disk."""
        data = {
            "version": 1,
            "updated_at": time.time(),
            "state": self._state,
            "events": [e.to_dict() for e in self._events[-self._max_events:]],
        }
        
        temp_file = self.state_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.state_file)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a state value."""
        self._state[key] = value
        self._save()
    
    def delete(self, key: str) -> bool:
        """Delete a state value."""
        if key in self._state:
            del self._state[key]
            self._save()
            return True
        return False
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple state values."""
        self._state.update(updates)
        self._save()
    
    def record_event(
        self,
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an event."""
        event = StateEvent(
            event_type=event_type,
            description=description,
            metadata=metadata or {},
        )
        self._events.append(event)
        
        # Trim old events
        if len(self._events) > self._max_events * 2:
            self._events = self._events[-self._max_events:]
        
        self._save()
    
    def get_recent_events(self, limit: int = 10, event_type: Optional[str] = None) -> List[StateEvent]:
        """Get recent events, optionally filtered by type."""
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def get_state_summary(self) -> str:
        """Get a text summary of current state."""
        lines = ["Current World State:"]
        
        for key, value in self._state.items():
            value_str = str(value)[:100]
            lines.append(f"  {key}: {value_str}")
        
        recent = self.get_recent_events(5)
        if recent:
            lines.append("\nRecent Events:")
            for event in recent:
                lines.append(f"  [{event.event_type}] {event.description[:50]}")
        
        return "\n".join(lines)
    
    def to_context(self) -> Dict[str, Any]:
        """Convert state to context dict for agents."""
        return {
            "state": dict(self._state),
            "recent_events": [
                {"type": e.event_type, "description": e.description}
                for e in self.get_recent_events(5)
            ],
        }
    
    def clear(self) -> None:
        """Clear all state."""
        self._state.clear()
        self._events.clear()
        self._save()

