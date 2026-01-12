"""
schemas_notes.py - Pydantic schemas for Notes and Transcripts API.

Defines request/response models for the notes and transcripts endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Note Schemas
# =============================================================================

class NoteCreate(BaseModel):
    """Schema for creating a new note."""
    session_id: str = Field(..., description="User session ID for scoping")
    title: Optional[str] = Field(None, max_length=500, description="Note title")
    content: str = Field(..., description="Note content")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    source_conversation_id: Optional[str] = Field(None, description="Linked conversation ID")
    source_attachment_id: Optional[str] = Field(None, description="Linked attachment ID")


class NoteUpdate(BaseModel):
    """Schema for updating a note (all fields optional)."""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    source_conversation_id: Optional[str] = None
    source_attachment_id: Optional[str] = None


class NoteRead(BaseModel):
    """Schema for reading a note."""
    id: int
    session_id: str
    title: Optional[str]
    content: str
    tags: List[str]
    source_conversation_id: Optional[str]
    source_attachment_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """Response schema for listing notes."""
    notes: List[NoteRead]
    total: int


# =============================================================================
# Transcript Schemas
# =============================================================================

class TranscriptCreate(BaseModel):
    """Schema for creating a new transcript record."""
    session_id: str = Field(..., description="User session ID for scoping")
    audio_path: str = Field(..., description="Path to the audio file")
    language: Optional[str] = Field(None, max_length=20, description="Audio language code")


class TranscriptRead(BaseModel):
    """Schema for reading a transcript."""
    id: int
    session_id: str
    audio_path: str
    transcript_text: Optional[str]
    language: Optional[str]
    speaker_info: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TranscriptListResponse(BaseModel):
    """Response schema for listing transcripts."""
    transcripts: List[TranscriptRead]
    total: int

