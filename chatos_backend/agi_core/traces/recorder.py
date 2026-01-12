"""
Reasoning Trace Recorder for AGI Core

Records and persists reasoning traces for debugging, analysis, and training.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# Default storage location
DEFAULT_TRACES_DIR = Path.home() / "ChatOS-Memory" / "agi" / "traces"


@dataclass
class TraceStep:
    """
    A single step in a reasoning trace.
    
    Attributes:
        step_number: Sequential step number
        action: What action was taken (think, tool_call, response, etc.)
        input_data: Input to this step
        output_data: Output from this step
        tools_used: List of tools used in this step
        memories_used: List of memory IDs referenced
        duration_ms: Time taken for this step
        notes: Additional notes or reasoning
        metadata: Extra structured data
    """
    step_number: int
    action: str
    input_data: Any = None
    output_data: Any = None
    tools_used: List[str] = field(default_factory=list)
    memories_used: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    id: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"step_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "step_number": self.step_number,
            "action": self.action,
            "input_data": self._serialize(self.input_data),
            "output_data": self._serialize(self.output_data),
            "tools_used": self.tools_used,
            "memories_used": self.memories_used,
            "duration_ms": self.duration_ms,
            "notes": self.notes,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
    
    def _serialize(self, data: Any) -> Any:
        """Safely serialize data for JSON."""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, (list, tuple)):
            return [self._serialize(item) for item in data]
        if isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items()}
        return str(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceStep":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            step_number=data["step_number"],
            action=data["action"],
            input_data=data.get("input_data"),
            output_data=data.get("output_data"),
            tools_used=data.get("tools_used", []),
            memories_used=data.get("memories_used", []),
            duration_ms=data.get("duration_ms", 0.0),
            notes=data.get("notes", ""),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class TraceSession:
    """
    A complete reasoning trace session.
    
    Attributes:
        session_id: Unique session identifier
        goal: The goal or query being processed
        steps: List of trace steps
        started_at: Session start time
        ended_at: Session end time
        status: Session status (running, completed, failed)
        result: Final result
        error: Error message if failed
        metadata: Additional session data
    """
    goal: str
    session_id: str = ""
    steps: List[TraceStep] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    status: str = "running"
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.session_id:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.session_id = f"trace_{timestamp}_{uuid.uuid4().hex[:6]}"
    
    def add_step(self, step: TraceStep) -> None:
        """Add a step to the trace."""
        self.steps.append(step)
    
    def complete(self, result: Any = None) -> None:
        """Mark session as completed."""
        self.status = "completed"
        self.result = result
        self.ended_at = time.time()
    
    def fail(self, error: str) -> None:
        """Mark session as failed."""
        self.status = "failed"
        self.error = error
        self.ended_at = time.time()
    
    def duration_seconds(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self.ended_at:
            return self.ended_at - self.started_at
        return time.time() - self.started_at
    
    def step_count(self) -> int:
        """Get number of steps."""
        return len(self.steps)
    
    def tools_used(self) -> List[str]:
        """Get all unique tools used across all steps."""
        tools = set()
        for step in self.steps:
            tools.update(step.tools_used)
        return list(tools)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "result": self._serialize(self.result),
            "error": self.error,
            "metadata": self.metadata,
            "step_count": len(self.steps),
            "duration_seconds": self.duration_seconds(),
        }
    
    def _serialize(self, data: Any) -> Any:
        """Safely serialize data for JSON."""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, (list, tuple)):
            return [self._serialize(item) for item in data]
        if isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items()}
        return str(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceSession":
        """Create from dictionary."""
        session = cls(
            session_id=data.get("session_id", ""),
            goal=data["goal"],
            started_at=data.get("started_at", time.time()),
            ended_at=data.get("ended_at"),
            status=data.get("status", "running"),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )
        
        for step_data in data.get("steps", []):
            session.steps.append(TraceStep.from_dict(step_data))
        
        return session
    
    def summary(self) -> str:
        """Get a text summary of the session."""
        lines = [
            f"Session: {self.session_id}",
            f"Goal: {self.goal}",
            f"Status: {self.status}",
            f"Steps: {len(self.steps)}",
            f"Duration: {self.duration_seconds():.2f}s" if self.duration_seconds() else "Running...",
        ]
        
        if self.tools_used():
            lines.append(f"Tools: {', '.join(self.tools_used())}")
        
        if self.error:
            lines.append(f"Error: {self.error}")
        
        return "\n".join(lines)


class TraceRecorder:
    """
    Manages recording and persistence of reasoning traces.
    
    Usage:
        recorder = TraceRecorder()
        
        # Start a new trace
        session_id = recorder.start_session("Research quantum computing")
        
        # Record steps
        recorder.record_step(session_id, TraceStep(
            step_number=1,
            action="search",
            input_data="quantum computing papers",
            output_data=["paper1", "paper2"],
        ))
        
        # End the session
        recorder.end_session(session_id, result="Summary of findings...")
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the trace recorder.
        
        Args:
            storage_path: Directory to store traces
        """
        self.storage_path = storage_path or DEFAULT_TRACES_DIR
        self.storage_path = Path(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._active_sessions: Dict[str, TraceSession] = {}
    
    def start_session(
        self,
        goal: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new trace session.
        
        Args:
            goal: The goal or query being processed
            metadata: Additional session metadata
            
        Returns:
            The session ID
        """
        session = TraceSession(
            goal=goal,
            metadata=metadata or {},
        )
        
        self._active_sessions[session.session_id] = session
        return session.session_id
    
    def record_step(
        self,
        session_id: str,
        step: TraceStep = None,
        action: str = None,
        input_data: Any = None,
        output_data: Any = None,
        tools_used: List[str] = None,
        notes: str = "",
        duration_ms: float = 0.0,
    ) -> Optional[TraceStep]:
        """
        Record a step in a session.
        
        Can either pass a TraceStep directly, or provide individual parameters.
        
        Args:
            session_id: The session to record in
            step: A complete TraceStep (if provided, other params ignored)
            action: Action type
            input_data: Input data
            output_data: Output data
            tools_used: Tools used
            notes: Notes
            duration_ms: Duration
            
        Returns:
            The recorded step, or None if session not found
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return None
        
        if step is None:
            step = TraceStep(
                step_number=len(session.steps) + 1,
                action=action or "unknown",
                input_data=input_data,
                output_data=output_data,
                tools_used=tools_used or [],
                notes=notes,
                duration_ms=duration_ms,
            )
        else:
            step.step_number = len(session.steps) + 1
        
        session.add_step(step)
        return step
    
    def end_session(
        self,
        session_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> Optional[TraceSession]:
        """
        End a trace session and save it.
        
        Args:
            session_id: The session to end
            result: Final result (if successful)
            error: Error message (if failed)
            
        Returns:
            The completed session, or None if not found
        """
        session = self._active_sessions.pop(session_id, None)
        if not session:
            return None
        
        if error:
            session.fail(error)
        else:
            session.complete(result)
        
        # Save to disk
        self._save_session(session)
        
        return session
    
    def _save_session(self, session: TraceSession) -> None:
        """Save a session to disk."""
        filename = f"{session.session_id}.json"
        filepath = self.storage_path / filename
        
        filepath.write_text(
            json.dumps(session.to_dict(), indent=2),
            encoding="utf-8",
        )
    
    def get_session(self, session_id: str) -> Optional[TraceSession]:
        """
        Get a session by ID.
        
        Checks active sessions first, then loads from disk.
        """
        # Check active sessions
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        
        # Try loading from disk
        filepath = self.storage_path / f"{session_id}.json"
        if filepath.exists():
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return TraceSession.from_dict(data)
        
        return None
    
    def list_sessions(
        self,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List recent trace sessions.
        
        Args:
            limit: Maximum number of sessions to return
            status: Filter by status
            
        Returns:
            List of session summaries
        """
        sessions = []
        
        # Load from disk
        for filepath in sorted(self.storage_path.glob("trace_*.json"), reverse=True):
            if len(sessions) >= limit:
                break
            
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                if status and data.get("status") != status:
                    continue
                
                sessions.append({
                    "session_id": data.get("session_id"),
                    "goal": data.get("goal", "")[:100],
                    "status": data.get("status"),
                    "step_count": data.get("step_count", 0),
                    "started_at": data.get("started_at"),
                    "duration_seconds": data.get("duration_seconds"),
                })
            except Exception:
                continue
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        # Remove from active if present
        self._active_sessions.pop(session_id, None)
        
        # Delete file
        filepath = self.storage_path / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        
        return False
    
    def export_for_training(
        self,
        output_path: Path,
        status_filter: str = "completed",
        min_steps: int = 2,
    ) -> int:
        """
        Export traces as training data.
        
        Args:
            output_path: Path to write JSONL file
            status_filter: Only export sessions with this status
            min_steps: Minimum steps required
            
        Returns:
            Number of examples exported
        """
        examples = []
        
        for filepath in self.storage_path.glob("trace_*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                
                if data.get("status") != status_filter:
                    continue
                if data.get("step_count", 0) < min_steps:
                    continue
                
                # Convert to training format
                example = {
                    "goal": data.get("goal"),
                    "steps": [
                        {
                            "action": s.get("action"),
                            "input": s.get("input_data"),
                            "output": s.get("output_data"),
                            "tools": s.get("tools_used", []),
                        }
                        for s in data.get("steps", [])
                    ],
                    "result": data.get("result"),
                    "metadata": {
                        "source": "agi_trace",
                        "session_id": data.get("session_id"),
                    }
                }
                
                examples.append(example)
                
            except Exception:
                continue
        
        # Write JSONL
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
        
        return len(examples)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get trace statistics."""
        total = 0
        by_status = {}
        total_steps = 0
        
        for filepath in self.storage_path.glob("trace_*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                total += 1
                status = data.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1
                total_steps += data.get("step_count", 0)
            except Exception:
                continue
        
        return {
            "total_sessions": total,
            "by_status": by_status,
            "total_steps": total_steps,
            "active_sessions": len(self._active_sessions),
        }

