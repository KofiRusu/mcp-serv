"""
MCP Memory Store - SQLite-based persistent memory system
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager

from .models import Memory, MemoryQuery, MemoryStats


class MemoryStore:
    """SQLite-based persistent memory store"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                workspace TEXT,
                repository TEXT,
                status TEXT DEFAULT 'active',
                priority TEXT DEFAULT 'medium',
                metadata TEXT,
                access_count INTEGER DEFAULT 0
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (memory_id, tag),
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON memories(domain)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workspace ON memories(workspace)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON memories(priority)")
            
            conn.commit()
    
    def set_memory(self, domain: str, title: str, content: str, **kwargs) -> str:
        """Store a memory"""
        memory_id = kwargs.get('memory_id') or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO memories 
            (id, domain, title, content, created_at, updated_at, workspace, 
             repository, status, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id, domain, title, content, now, now,
                kwargs.get('workspace'), kwargs.get('repository'),
                kwargs.get('status', 'active'),
                kwargs.get('priority', 'medium'),
                json.dumps(kwargs.get('metadata', {}))
            ))
            
            # Handle tags
            for tag in kwargs.get('tags', []):
                cursor.execute("""
                INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)
                """, (memory_id, tag.lower()))
            
            conn.commit()
        
        return memory_id
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            cursor.execute("SELECT tag FROM memory_tags WHERE memory_id = ?", (memory_id,))
            tags = [t[0] for t in cursor.fetchall()]
            
            return Memory(
                id=row['id'],
                domain=row['domain'],
                title=row['title'],
                content=row['content'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                workspace=row['workspace'],
                repository=row['repository'],
                tags=tags,
                metadata=json.loads(row['metadata'] or '{}'),
                status=row['status'],
                priority=row['priority'],
            )
    
    def list_memories(self, query: MemoryQuery) -> Tuple[List[Memory], int]:
        """List memories with optional filters"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            where_clauses = []
            params = []
            
            if query.domain:
                where_clauses.append("domain = ?")
                params.append(query.domain)
            
            if query.workspace:
                where_clauses.append("workspace = ?")
                params.append(query.workspace)
            
            if query.repository:
                where_clauses.append("repository = ?")
                params.append(query.repository)
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM memories WHERE {where_clause}", params)
            total = cursor.fetchone()[0]
            
            # Get results
            cursor.execute(f"""
            SELECT * FROM memories 
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """, params + [query.limit, query.offset])
            
            rows = cursor.fetchall()
            memories = []
            
            for row in rows:
                cursor.execute(
                    "SELECT tag FROM memory_tags WHERE memory_id = ?",
                    (row['id'],)
                )
                tags = [t[0] for t in cursor.fetchall()]
                
                memories.append(Memory(
                    id=row['id'],
                    domain=row['domain'],
                    title=row['title'],
                    content=row['content'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    workspace=row['workspace'],
                    repository=row['repository'],
                    tags=tags,
                    metadata=json.loads(row['metadata'] or '{}'),
                    status=row['status'],
                    priority=row['priority'],
                ))
            
            return memories, total
    
    def search(self, query: str, limit: int = 10) -> List[Memory]:
        """Search memories by title/content"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            search_term = f"%{query}%"
            cursor.execute("""
            SELECT * FROM memories 
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """, (search_term, search_term, limit))
            
            rows = cursor.fetchall()
            memories = []
            
            for row in rows:
                cursor.execute(
                    "SELECT tag FROM memory_tags WHERE memory_id = ?",
                    (row['id'],)
                )
                tags = [t[0] for t in cursor.fetchall()]
                
                memories.append(Memory(
                    id=row['id'],
                    domain=row['domain'],
                    title=row['title'],
                    content=row['content'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    workspace=row['workspace'],
                    repository=row['repository'],
                    tags=tags,
                    metadata=json.loads(row['metadata'] or '{}'),
                    status=row['status'],
                    priority=row['priority'],
                ))
            
            return memories
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0
    
    def get_stats(self) -> MemoryStats:
        """Get memory statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]
            
            cursor.execute("""
            SELECT domain, COUNT(*) FROM memories GROUP BY domain
            """)
            by_domain = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute("""
            SELECT workspace, COUNT(*) FROM memories 
            WHERE workspace IS NOT NULL GROUP BY workspace
            """)
            by_workspace = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute("SELECT SUM(LENGTH(content)) FROM memories")
            total_chars = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT MAX(updated_at) FROM memories")
            last_updated_str = cursor.fetchone()[0]
            last_updated = datetime.fromisoformat(last_updated_str) if last_updated_str else None
            
            return MemoryStats(
                total_memories=total,
                by_domain=by_domain,
                by_workspace=by_workspace,
                total_content_chars=total_chars,
                last_updated=last_updated,
            )
