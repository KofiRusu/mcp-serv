"""
project_memory.py - Project-specific memory storage.

Each coding project has its own separate memory database to:
- Track conversation history specific to that project
- Store project context and decisions
- Remember file changes and their reasons
- Maintain task progress and notes
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ChatOS.config import SANDBOX_DIR


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry for a project."""
    
    id: int
    project_id: str
    entry_type: str  # "conversation", "decision", "file_change", "task", "note"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "entry_type": self.entry_type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ProjectContext:
    """Aggregated context for a project."""
    
    project_id: str
    project_name: str
    summary: str = ""
    recent_conversations: List[Dict[str, str]] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    active_tasks: List[str] = field(default_factory=list)
    file_history: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "summary": self.summary,
            "recent_conversations": self.recent_conversations,
            "key_decisions": self.key_decisions,
            "active_tasks": self.active_tasks,
            "file_history": self.file_history,
            "notes": self.notes,
        }
    
    def to_prompt_context(self) -> str:
        """Format context for inclusion in prompts."""
        lines = [
            f"=== Project Context: {self.project_name} ===",
        ]
        
        if self.summary:
            lines.append(f"\nSummary: {self.summary}")
        
        if self.key_decisions:
            lines.append("\nKey Decisions:")
            for decision in self.key_decisions[-5:]:
                lines.append(f"  - {decision}")
        
        if self.active_tasks:
            lines.append("\nActive Tasks:")
            for task in self.active_tasks:
                lines.append(f"  - {task}")
        
        if self.recent_conversations:
            lines.append("\nRecent Conversation:")
            for conv in self.recent_conversations[-3:]:
                lines.append(f"  User: {conv.get('user', '')[:100]}...")
                lines.append(f"  Assistant: {conv.get('assistant', '')[:100]}...")
        
        if self.file_history:
            lines.append("\nRecent File Changes:")
            for change in self.file_history[-5:]:
                lines.append(f"  - {change.get('file')}: {change.get('action')}")
        
        lines.append("\n=== End Project Context ===")
        
        return "\n".join(lines)


# =============================================================================
# Project Memory Database
# =============================================================================

class ProjectMemoryDB:
    """
    SQLite-based memory storage for a single project.
    
    Each project has its own .db file in its directory.
    """
    
    def __init__(self, project_id: str, project_path: Path):
        self.project_id = project_id
        self.db_path = project_path / ".chatos_memory.db"
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    mode TEXT DEFAULT 'normal',
                    attachments TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS file_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    action TEXT NOT NULL,
                    description TEXT,
                    diff TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS project_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(entry_type);
                CREATE INDEX IF NOT EXISTS idx_conversations_time ON conversations(created_at);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            """)
    
    # =========================================================================
    # Conversations
    # =========================================================================
    
    def add_conversation(
        self,
        user_message: str,
        assistant_response: str,
        mode: str = "normal",
        attachments: Optional[List[str]] = None,
    ) -> int:
        """Add a conversation turn."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversations (user_message, assistant_response, mode, attachments)
                VALUES (?, ?, ?, ?)
                """,
                (user_message, assistant_response, mode, json.dumps(attachments or [])),
            )
            return cursor.lastrowid
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation turns."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM conversations
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]
    
    def get_conversation_context(self, limit: int = 5) -> str:
        """Get formatted conversation context for prompts."""
        conversations = self.get_recent_conversations(limit)
        
        if not conversations:
            return ""
        
        lines = ["Previous conversation in this project:"]
        for conv in conversations:
            lines.append(f"User: {conv['user_message']}")
            lines.append(f"Assistant: {conv['assistant_response']}")
            lines.append("")
        
        return "\n".join(lines)
    
    # =========================================================================
    # Memory Entries
    # =========================================================================
    
    def add_memory(
        self,
        entry_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add a memory entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO memories (entry_type, content, metadata)
                VALUES (?, ?, ?)
                """,
                (entry_type, content, json.dumps(metadata or {})),
            )
            return cursor.lastrowid
    
    def get_memories(
        self,
        entry_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Get memory entries, optionally filtered by type."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if entry_type:
                cursor = conn.execute(
                    """
                    SELECT * FROM memories
                    WHERE entry_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (entry_type, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM memories
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            
            return [
                MemoryEntry(
                    id=row["id"],
                    project_id=self.project_id,
                    entry_type=row["entry_type"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in cursor.fetchall()
            ]
    
    # =========================================================================
    # Tasks
    # =========================================================================
    
    def add_task(self, title: str, description: str = "") -> int:
        """Add a task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (title, description)
                VALUES (?, ?)
                """,
                (title, description),
            )
            return cursor.lastrowid
    
    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE tasks
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (task_id,),
            )
            return cursor.rowcount > 0
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status = 'pending'
                ORDER BY created_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # =========================================================================
    # File Changes
    # =========================================================================
    
    def record_file_change(
        self,
        file_path: str,
        action: str,
        description: str = "",
        diff: str = "",
    ) -> int:
        """Record a file change."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO file_changes (file_path, action, description, diff)
                VALUES (?, ?, ?, ?)
                """,
                (file_path, action, description, diff),
            )
            return cursor.lastrowid
    
    def get_file_history(self, file_path: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get file change history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if file_path:
                cursor = conn.execute(
                    """
                    SELECT * FROM file_changes
                    WHERE file_path = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (file_path, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM file_changes
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            
            return [dict(row) for row in cursor.fetchall()]
    
    # =========================================================================
    # Project Metadata
    # =========================================================================
    
    def set_meta(self, key: str, value: str) -> None:
        """Set a project metadata value."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO project_meta (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (key, value),
            )
    
    def get_meta(self, key: str) -> Optional[str]:
        """Get a project metadata value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM project_meta WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    # =========================================================================
    # Full Context
    # =========================================================================
    
    def get_full_context(self, project_name: str = "") -> ProjectContext:
        """Get the full context for this project."""
        conversations = self.get_recent_conversations(5)
        decisions = self.get_memories("decision", limit=10)
        tasks = self.get_active_tasks()
        file_history = self.get_file_history(limit=10)
        notes = self.get_memories("note", limit=5)
        
        summary = self.get_meta("summary") or ""
        
        return ProjectContext(
            project_id=self.project_id,
            project_name=project_name,
            summary=summary,
            recent_conversations=[
                {"user": c["user_message"], "assistant": c["assistant_response"]}
                for c in conversations
            ],
            key_decisions=[d.content for d in decisions],
            active_tasks=[t["title"] for t in tasks],
            file_history=[
                {"file": f["file_path"], "action": f["action"], "description": f["description"]}
                for f in file_history
            ],
            notes=[n.content for n in notes],
        )


# =============================================================================
# Project Memory Manager
# =============================================================================

class ProjectMemoryManager:
    """
    Manages memory databases for multiple projects.
    """
    
    def __init__(self):
        self._databases: Dict[str, ProjectMemoryDB] = {}
    
    def get_db(self, project_id: str, project_path: Path) -> ProjectMemoryDB:
        """Get or create a memory database for a project."""
        if project_id not in self._databases:
            self._databases[project_id] = ProjectMemoryDB(project_id, project_path)
        return self._databases[project_id]
    
    def close_db(self, project_id: str) -> None:
        """Close a project's database connection."""
        if project_id in self._databases:
            del self._databases[project_id]
    
    def close_all(self) -> None:
        """Close all database connections."""
        self._databases.clear()


# =============================================================================
# Singleton
# =============================================================================

_memory_manager: Optional[ProjectMemoryManager] = None


def get_project_memory_manager() -> ProjectMemoryManager:
    """Get the singleton project memory manager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ProjectMemoryManager()
    return _memory_manager

