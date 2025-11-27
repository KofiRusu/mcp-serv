"""
attachments.py - File attachment handling for chat.

Allows users to attach files to their chat messages for context.
Supports various file types with content extraction.
"""

import base64
import hashlib
import mimetypes
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ChatOS.config import SANDBOX_DIR


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
        data["path"] = Path(data["path"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


# =============================================================================
# Attachment Manager
# =============================================================================

class AttachmentManager:
    """
    Manages file attachments for chat sessions.
    
    Features:
    - Upload and store files
    - Content extraction for context
    - Session-based organization
    - File validation
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or ATTACHMENTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory index (could be backed by SQLite)
        self.attachments: Dict[str, Attachment] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load attachment index from disk."""
        index_file = self.storage_dir / "index.json"
        if index_file.exists():
            import json
            try:
                data = json.loads(index_file.read_text())
                for att_data in data.get("attachments", []):
                    att = Attachment.from_dict(att_data)
                    if att.path.exists():
                        self.attachments[att.id] = att
            except Exception:
                pass
    
    def _save_index(self) -> None:
        """Save attachment index to disk."""
        import json
        index_file = self.storage_dir / "index.json"
        data = {
            "attachments": [a.to_dict() for a in self.attachments.values()]
        }
        index_file.write_text(json.dumps(data, indent=2))
    
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
        
        # Calculate checksum
        checksum = hashlib.md5(content).hexdigest()
        
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
        
        self.attachments[att_id] = attachment
        self._save_index()
        
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
    # Retrieval
    # =========================================================================
    
    def get_attachment(self, attachment_id: str) -> Optional[Attachment]:
        """Get an attachment by ID."""
        return self.attachments.get(attachment_id)
    
    def get_session_attachments(self, session_id: str) -> List[Attachment]:
        """Get all attachments for a session."""
        return [
            att for att in self.attachments.values()
            if att.session_id == session_id
        ]
    
    def read_attachment(self, attachment_id: str) -> Optional[bytes]:
        """Read attachment content."""
        attachment = self.attachments.get(attachment_id)
        if attachment and attachment.path.exists():
            return attachment.path.read_bytes()
        return None
    
    def read_attachment_text(self, attachment_id: str) -> Optional[str]:
        """Read attachment content as text."""
        attachment = self.attachments.get(attachment_id)
        if not attachment:
            return None
        
        ext = Path(attachment.original_filename).suffix.lower()
        if ext not in TEXT_EXTENSIONS:
            return None
        
        try:
            return attachment.path.read_text(encoding="utf-8")
        except Exception:
            return None
    
    def get_full_content(self, attachment_id: str) -> str:
        """Get full content for inclusion in prompts."""
        attachment = self.attachments.get(attachment_id)
        if not attachment:
            return ""
        
        ext = Path(attachment.original_filename).suffix.lower()
        
        if ext in TEXT_EXTENSIONS:
            try:
                content = attachment.path.read_text(encoding="utf-8")
                return f"=== File: {attachment.original_filename} ===\n{content}\n=== End File ==="
            except Exception:
                return f"[Unable to read {attachment.original_filename}]"
        else:
            return f"[Attached file: {attachment.original_filename} ({attachment.mime_type}, {attachment.size} bytes)]"
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment."""
        attachment = self.attachments.get(attachment_id)
        if not attachment:
            return False
        
        # Remove file
        if attachment.path.exists():
            attachment.path.unlink()
        
        # Remove from index
        del self.attachments[attachment_id]
        self._save_index()
        
        return True
    
    def delete_session_attachments(self, session_id: str) -> int:
        """Delete all attachments for a session."""
        to_delete = [
            att_id for att_id, att in self.attachments.items()
            if att.session_id == session_id
        ]
        
        for att_id in to_delete:
            self.delete_attachment(att_id)
        
        # Remove session directory if empty
        session_dir = self.storage_dir / session_id
        if session_dir.exists() and not any(session_dir.iterdir()):
            session_dir.rmdir()
        
        return len(to_delete)
    
    def cleanup_old_attachments(self, days: int = 7) -> int:
        """Remove attachments older than specified days."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        to_delete = [
            att_id for att_id, att in self.attachments.items()
            if att.created_at < cutoff
        ]
        
        for att_id in to_delete:
            self.delete_attachment(att_id)
        
        return len(to_delete)


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

