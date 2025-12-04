"""
notes_models.py - SQLAlchemy models for Notes and Transcripts.

Provides relational storage for user-scoped notes and audio transcripts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)

from ChatOS.database.models import Base, JSONType


# =============================================================================
# Note Model
# =============================================================================

class NoteDB(Base):
    """
    SQLAlchemy model for user notes.
    
    Stores notes with user scoping via session_id.
    Supports linking to conversations and attachments.
    """
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500))
    content = Column(Text, nullable=False)
    tags = Column(JSONType, default=list)
    source_conversation_id = Column(String(100))
    source_attachment_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_notes_session_created", "session_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags or [],
            "source_conversation_id": self.source_conversation_id,
            "source_attachment_id": self.source_attachment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# Transcript Model
# =============================================================================

class TranscriptDB(Base):
    """
    SQLAlchemy model for audio transcripts.
    
    Stores transcript records with status tracking for async processing.
    """
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    audio_path = Column(String(1024), nullable=False)
    transcript_text = Column(Text)
    language = Column(String(20))
    speaker_info = Column(JSONType)
    status = Column(String(20), default="pending")  # pending | processing | done | error
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_transcripts_session_status", "session_id", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "audio_path": self.audio_path,
            "transcript_text": self.transcript_text,
            "language": self.language,
            "speaker_info": self.speaker_info,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

