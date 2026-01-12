"""
uploads.py - File upload controller.

Handles file uploads for audio recordings and other attachments.
Files are stored in ~/ChatOS-Memory/uploads/ with unique IDs.
"""

import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

# Default upload directory
DEFAULT_UPLOAD_DIR = Path.home() / "ChatOS-Memory" / "uploads"

# Allowed audio file extensions
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".aac"}

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024


@dataclass
class UploadedFile:
    """Represents an uploaded file."""
    id: str
    original_filename: str
    stored_path: str
    mime_type: str
    size: int
    session_id: str
    created_at: datetime


class UploadManager:
    """
    Manages file uploads with session scoping.
    
    Files are stored in subdirectories by session_id for isolation.
    """
    
    def __init__(self, upload_dir: Optional[Path] = None):
        """
        Initialize the upload manager.
        
        Args:
            upload_dir: Directory to store uploads (default: ~/ChatOS-Memory/uploads/)
        """
        self.upload_dir = upload_dir or DEFAULT_UPLOAD_DIR
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Upload manager initialized with directory: {self.upload_dir}")
    
    def _get_session_dir(self, session_id: str) -> Path:
        """Get or create the upload directory for a session."""
        session_dir = self.upload_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def _generate_file_id(self) -> str:
        """Generate a unique file ID."""
        return f"upload_{uuid.uuid4().hex[:12]}"
    
    def _get_mime_type(self, filename: str) -> str:
        """Determine MIME type from filename extension."""
        ext = Path(filename).suffix.lower()
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".webm": "audio/webm",
            ".aac": "audio/aac",
        }
        return mime_types.get(ext, "application/octet-stream")
    
    def validate_audio_file(self, filename: str, size: int) -> tuple[bool, str]:
        """
        Validate an audio file before upload.
        
        Args:
            filename: Original filename
            size: File size in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        ext = Path(filename).suffix.lower()
        
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            return False, f"File type '{ext}' not allowed. Allowed types: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        
        if size > MAX_FILE_SIZE:
            return False, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
        
        if size == 0:
            return False, "File is empty"
        
        return True, ""
    
    async def save_file(
        self,
        session_id: str,
        filename: str,
        content: bytes,
    ) -> UploadedFile:
        """
        Save an uploaded file.
        
        Args:
            session_id: User session ID for scoping
            filename: Original filename
            content: File content as bytes
            
        Returns:
            UploadedFile with metadata
            
        Raises:
            ValueError: If file validation fails
        """
        # Validate
        is_valid, error = self.validate_audio_file(filename, len(content))
        if not is_valid:
            raise ValueError(error)
        
        # Generate unique ID and path
        file_id = self._generate_file_id()
        ext = Path(filename).suffix.lower()
        stored_filename = f"{file_id}{ext}"
        
        session_dir = self._get_session_dir(session_id)
        stored_path = session_dir / stored_filename
        
        # Write file
        try:
            with open(stored_path, "wb") as f:
                f.write(content)
            logger.info(f"Saved file {filename} as {stored_path}")
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise
        
        return UploadedFile(
            id=file_id,
            original_filename=filename,
            stored_path=str(stored_path),
            mime_type=self._get_mime_type(filename),
            size=len(content),
            session_id=session_id,
            created_at=datetime.utcnow(),
        )
    
    async def save_file_from_path(
        self,
        session_id: str,
        source_path: str,
        original_filename: Optional[str] = None,
    ) -> UploadedFile:
        """
        Save a file from an existing path (copy).
        
        Args:
            session_id: User session ID
            source_path: Path to the source file
            original_filename: Original filename (defaults to source filename)
            
        Returns:
            UploadedFile with metadata
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        filename = original_filename or source.name
        
        with open(source, "rb") as f:
            content = f.read()
        
        return await self.save_file(session_id, filename, content)
    
    def get_file_path(self, session_id: str, file_id: str) -> Optional[str]:
        """
        Get the stored path for a file.
        
        Args:
            session_id: User session ID
            file_id: File ID
            
        Returns:
            Full path to the file, or None if not found
        """
        session_dir = self._get_session_dir(session_id)
        
        # Search for file with matching ID prefix
        for file_path in session_dir.iterdir():
            if file_path.stem == file_id:
                return str(file_path)
        
        return None
    
    def list_files(self, session_id: str) -> List[dict]:
        """
        List all uploaded files for a session.
        
        Args:
            session_id: User session ID
            
        Returns:
            List of file metadata dicts
        """
        session_dir = self._get_session_dir(session_id)
        files = []
        
        for file_path in session_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "id": file_path.stem,
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                })
        
        return sorted(files, key=lambda f: f["created_at"], reverse=True)
    
    def delete_file(self, session_id: str, file_id: str) -> bool:
        """
        Delete an uploaded file.
        
        Args:
            session_id: User session ID
            file_id: File ID
            
        Returns:
            True if deleted, False if not found
        """
        file_path = self.get_file_path(session_id, file_id)
        if file_path and Path(file_path).exists():
            Path(file_path).unlink()
            logger.info(f"Deleted file: {file_path}")
            return True
        return False


# Global upload manager instance
_upload_manager: Optional[UploadManager] = None


def get_upload_manager() -> UploadManager:
    """Get the global upload manager instance."""
    global _upload_manager
    if _upload_manager is None:
        _upload_manager = UploadManager()
    return _upload_manager

