"""
attachments.py - File attachment handling for chat.

Allows users to attach files to their chat messages for context.
Supports various file types with content extraction.

Performance Optimizations:
- SQLite-backed index for fast queries and atomic operations
- xxhash for faster checksums (10x faster than MD5)
- Content caching with LRU eviction
- Async file I/O support
"""

import asyncio
import base64
import logging
import mimetypes
import os
import shutil
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ChatOS.config import SANDBOX_DIR
from ChatOS.controllers.cache import (
    CacheKeys,
    CacheTTL,
    cache_key,
    get_cache,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

ATTACHMENTS_DIR = SANDBOX_DIR / ".attachments"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    # Code files
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".c", ".h",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".xml", ".sql",
    # Text files
    ".txt", ".md", ".rst", ".log", ".csv",
    # Config files
    ".env", ".ini", ".toml", ".cfg",
    # Shell
    ".sh", ".bash", ".zsh",
    # Data
    ".json", ".yaml", ".yml",
}

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".c", ".h",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".xml", ".sql",
    ".txt", ".md", ".rst", ".log", ".csv", ".env", ".ini", ".toml", ".cfg",
    ".sh", ".bash", ".zsh",
}

# =============================================================================
# Fast Hashing (xxhash if available, fallback to MD5)
# =============================================================================

def _compute_checksum(data: bytes) -> str:
    """Compute fast checksum using xxhash if available."""
    try:
        import xxhash
        return xxhash.xxh64(data).hexdigest()
    except ImportError:
        import hashlib
        return hashlib.md5(data).hexdigest()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Attachment:
    """Represents a file attachment."""
    
    id: str
    filename: str
    original_filename: str
    mime_type: str
    size: int
    path: Path
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    content_preview: str = ""
    checksum: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "size": self.size,
            "path": str(self.path),
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "content_preview": self.content_preview,
            "checksum": self.checksum,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attachment":
        data = data.copy()
        data["path"] = Path(data["path"])
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Attachment":
        """Create from SQLite row."""
        return cls(
            id=row["id"],
            filename=row["filename"],
            original_filename=row["original_filename"],
            mime_type=row["mime_type"],
            size=row["size"],
            path=Path(row["path"]),
            session_id=row["session_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            content_preview=row["content_preview"] or "",
            checksum=row["checksum"] or "",
        )


# =============================================================================
# SQLite Index
# =============================================================================

class AttachmentIndex:
    """SQLite-backed index for fast attachment queries."""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS attachments (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        size INTEGER NOT NULL,
        path TEXT NOT NULL,
        session_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        content_preview TEXT,
        checksum TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_session_id ON attachments(session_id);
    CREATE INDEX IF NOT EXISTS idx_created_at ON attachments(created_at);
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript(self.SCHEMA)
        conn.commit()
    
    def add(self, attachment: Attachment) -> None:
        """Add attachment to index."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO attachments 
            (id, filename, original_filename, mime_type, size, path, 
             session_id, created_at, content_preview, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment.id,
                attachment.filename,
                attachment.original_filename,
                attachment.mime_type,
                attachment.size,
                str(attachment.path),
                attachment.session_id,
                attachment.created_at.isoformat(),
                attachment.content_preview,
                attachment.checksum,
            )
        )
        conn.commit()
    
    def get(self, attachment_id: str) -> Optional[Attachment]:
        """Get attachment by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM attachments WHERE id = ?",
            (attachment_id,)
        ).fetchone()
        
        if row:
            return Attachment.from_row(row)
        return None
    
    def get_by_session(self, session_id: str) -> List[Attachment]:
        """Get all attachments for a session."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM attachments WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        ).fetchall()
        
        return [Attachment.from_row(row) for row in rows]
    
    def get_all(self) -> List[Attachment]:
        """Get all attachments."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM attachments ORDER BY created_at DESC"
        ).fetchall()
        
        return [Attachment.from_row(row) for row in rows]
    
    def delete(self, attachment_id: str) -> bool:
        """Delete attachment from index."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM attachments WHERE id = ?",
            (attachment_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    def delete_by_session(self, session_id: str) -> int:
        """Delete all attachments for a session."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM attachments WHERE session_id = ?",
            (session_id,)
        )
        conn.commit()
        return cursor.rowcount
    
    def delete_older_than(self, cutoff: datetime) -> List[str]:
        """Delete attachments older than cutoff, return IDs."""
        conn = self._get_conn()
        
        # Get IDs first
        rows = conn.execute(
            "SELECT id FROM attachments WHERE created_at < ?",
            (cutoff.isoformat(),)
        ).fetchall()
        ids = [row["id"] for row in rows]
        
        # Delete
        if ids:
            conn.execute(
                "DELETE FROM attachments WHERE created_at < ?",
                (cutoff.isoformat(),)
            )
            conn.commit()
        
        return ids
    
    def count(self) -> int:
        """Get total attachment count."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as count FROM attachments").fetchone()
        return row["count"]
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# =============================================================================
# Attachment Manager (Optimized)
# =============================================================================

class AttachmentManager:
    """
    Manages file attachments for chat sessions.
    
    Features:
    - Upload and store files
    - Content extraction for context
    - Session-based organization
    - File validation
    - SQLite-backed index for fast queries
    - Content caching for frequently accessed files
    - Fast checksums with xxhash
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or ATTACHMENTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite index
        db_path = self.storage_dir / "attachments.db"
        self._index = AttachmentIndex(db_path)
        self._cache = get_cache()
        
        # Migrate from JSON if exists
        self._migrate_from_json()
    
    def _migrate_from_json(self) -> None:
        """Migrate from old JSON index if it exists."""
        json_index = self.storage_dir / "index.json"
        if json_index.exists():
            try:
                import json
                data = json.loads(json_index.read_text())
                for att_data in data.get("attachments", []):
                    att = Attachment.from_dict(att_data)
                    if att.path.exists():
                        self._index.add(att)
                # Rename old file as backup
                json_index.rename(self.storage_dir / "index.json.bak")
                logger.info("Migrated attachments from JSON to SQLite")
            except Exception as e:
                logger.warning(f"Failed to migrate from JSON index: {e}")
    
    def _cache_key(self, *parts: str) -> str:
        """Build a namespaced cache key for attachments."""
        return cache_key(CacheKeys.ATTACHMENT, *parts)
    
    # =========================================================================
    # Upload & Store
    # =========================================================================
    
    async def upload_file(
        self,
        filename: str,
        content: bytes,
        session_id: str,
    ) -> Attachment:
        """
        Upload and store a file attachment.
        
        Args:
            filename: Original filename
            content: File content as bytes
            session_id: Session ID for organization
            
        Returns:
            Attachment object
        """
        # Validate
        self._validate_file(filename, content)
        
        # Generate unique ID and filename
        att_id = str(uuid.uuid4())[:12]
        ext = Path(filename).suffix.lower()
        stored_filename = f"{att_id}{ext}"
        
        # Create session directory
        session_dir = self.storage_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = session_dir / stored_filename
        file_path.write_bytes(content)
        
        # Calculate checksum (fast xxhash)
        checksum = _compute_checksum(content)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"
        
        # Extract content preview
        content_preview = self._extract_preview(file_path, ext)
        
        # Create attachment
        attachment = Attachment(
            id=att_id,
            filename=stored_filename,
            original_filename=filename,
            mime_type=mime_type,
            size=len(content),
            path=file_path,
            session_id=session_id,
            content_preview=content_preview,
            checksum=checksum,
        )
        
        # Save to index
        self._index.add(attachment)
        
        return attachment
    
    async def upload_base64(
        self,
        filename: str,
        base64_content: str,
        session_id: str,
    ) -> Attachment:
        """Upload a file from base64-encoded content."""
        content = base64.b64decode(base64_content)
        return await self.upload_file(filename, content, session_id)
    
    def _validate_file(self, filename: str, content: bytes) -> None:
        """Validate file before upload."""
        # Check size
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type not allowed: {ext}")
    
    def _extract_preview(self, file_path: Path, ext: str) -> str:
        """Extract content preview for text files."""
        if ext not in TEXT_EXTENSIONS:
            return f"[Binary file: {ext}]"
        
        try:
            content = file_path.read_text(encoding="utf-8")
            # First 1000 characters
            preview = content[:1000]
            if len(content) > 1000:
                preview += "\n... (truncated)"
            return preview
        except Exception:
            return "[Unable to read file content]"
    
    # =========================================================================
    # Retrieval (with caching)
    # =========================================================================
    
    def get_attachment(self, attachment_id: str) -> Optional[Attachment]:
        """Get an attachment by ID."""
        return self._index.get(attachment_id)
    
    def get_session_attachments(self, session_id: str) -> List[Attachment]:
        """Get all attachments for a session."""
        return self._index.get_by_session(session_id)
    
    def read_attachment(self, attachment_id: str) -> Optional[bytes]:
        """Read attachment content."""
        attachment = self._index.get(attachment_id)
        if attachment and attachment.path.exists():
            return attachment.path.read_bytes()
        return None
    
    async def read_attachment_text(self, attachment_id: str) -> Optional[str]:
        """Read attachment content as text (with unified caching)."""
        key = self._cache_key("text", attachment_id)
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        
        attachment = self._index.get(attachment_id)
        if not attachment:
            return None
        
        ext = Path(attachment.original_filename).suffix.lower()
        if ext not in TEXT_EXTENSIONS:
            return None
        
        try:
            content = await asyncio.to_thread(
                attachment.path.read_text,
                encoding="utf-8",
            )
            await self._cache.set(key, content, ttl=CacheTTL.LONG)
            return content
        except Exception:
            return None
    
    async def get_full_content(self, attachment_id: str) -> str:
        """Get full content for inclusion in prompts (with unified caching)."""
        key = self._cache_key("full", attachment_id)
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        
        attachment = self._index.get(attachment_id)
        if not attachment:
            return ""
        
        ext = Path(attachment.original_filename).suffix.lower()
        
        if ext in TEXT_EXTENSIONS:
            try:
                content = await asyncio.to_thread(
                    attachment.path.read_text,
                    encoding="utf-8",
                )
                result = (
                    f"=== File: {attachment.original_filename} ===\n"
                    f"{content}\n=== End File ==="
                )
                await self._cache.set(key, result, ttl=CacheTTL.LONG)
                return result
            except Exception:
                return f"[Unable to read {attachment.original_filename}]"
        else:
            result = (
                f"[Attached file: {attachment.original_filename} "
                f"({attachment.mime_type}, {attachment.size} bytes)]"
            )
            await self._cache.set(key, result, ttl=CacheTTL.LONG)
            return result
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    async def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment."""
        attachment = self._index.get(attachment_id)
        if not attachment:
            return False
        
        # Remove file
        if attachment.path.exists():
            attachment.path.unlink()
        
        # Remove from index
        self._index.delete(attachment_id)
        
        # Invalidate cache
        await self._cache.delete(self._cache_key("text", attachment_id))
        await self._cache.delete(self._cache_key("full", attachment_id))
        
        return True
    
    async def delete_session_attachments(self, session_id: str) -> int:
        """Delete all attachments for a session."""
        attachments = self._index.get_by_session(session_id)
        
        for att in attachments:
            if att.path.exists():
                att.path.unlink()
            await self._cache.delete(self._cache_key("text", att.id))
            await self._cache.delete(self._cache_key("full", att.id))
        
        count = self._index.delete_by_session(session_id)
        
        # Remove session directory if empty
        session_dir = self.storage_dir / session_id
        if session_dir.exists():
            try:
                if not any(session_dir.iterdir()):
                    session_dir.rmdir()
            except Exception:
                pass
        
        return count
    
    async def cleanup_old_attachments(self, days: int = 7) -> int:
        """Remove attachments older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        # Get and delete old attachments
        ids = self._index.delete_older_than(cutoff)
        
        # Delete files and invalidate cache
        for att_id in ids:
            await self._cache.delete(self._cache_key("text", att_id))
            await self._cache.delete(self._cache_key("full", att_id))
        
        return len(ids)
    
    def stats(self) -> Dict[str, Any]:
        """Get attachment statistics."""
        return {
            "total_attachments": self._index.count(),
            "storage_dir": str(self.storage_dir),
        }
    
    def close(self) -> None:
        """Close database connection."""
        self._index.close()


# =============================================================================
# Singleton
# =============================================================================

_manager: Optional[AttachmentManager] = None


def get_attachment_manager() -> AttachmentManager:
    """Get the singleton attachment manager instance."""
    global _manager
    if _manager is None:
        _manager = AttachmentManager()
    return _manager
