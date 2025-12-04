"""
routes_transcripts.py - API routes for audio transcripts.

Provides REST API endpoints for transcript management with user scoping.
Includes background processing for transcription and summarisation.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from ChatOS.database.connection import get_session
from ChatOS.api.schemas_notes import (
    TranscriptCreate,
    TranscriptRead,
    TranscriptListResponse,
)
from ChatOS.controllers import transcripts
from ChatOS.controllers.transcripts import process_transcript


router = APIRouter(prefix="/api/transcripts", tags=["Transcripts"])


def get_db():
    """Dependency to get database session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=TranscriptRead, status_code=201)
async def create_transcript(
    transcript_in: TranscriptCreate,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
):
    """
    Create a new transcript record and trigger background processing.
    
    The transcript is created with status='pending' and immediately returned.
    A background task is scheduled to:
    1. Transcribe the audio file
    2. Summarise the transcript and extract action items
    3. Create a Note with the summary
    
    Poll GET /api/transcripts/{id} to check processing status.
    """
    transcript = transcripts.create_transcript(
        db=db,
        session_id=transcript_in.session_id,
        audio_path=transcript_in.audio_path,
        language=transcript_in.language,
    )
    
    # Schedule background processing
    background_tasks.add_task(
        process_transcript,
        transcript_id=transcript.id,
        session_id=transcript_in.session_id,
    )
    
    return TranscriptRead.model_validate(transcript)


@router.get("", response_model=TranscriptListResponse)
async def list_transcripts(
    session_id: str = Query(..., description="User session ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db=Depends(get_db),
):
    """
    List transcripts for a user with optional status filter.
    
    - **session_id**: Required. User session ID for scoping.
    - **status**: Optional. Filter by status (pending, processing, done, error).
    """
    transcript_list = transcripts.list_transcripts(
        db=db,
        session_id=session_id,
        status=status,
    )
    return TranscriptListResponse(
        transcripts=[TranscriptRead.model_validate(t) for t in transcript_list],
        total=len(transcript_list),
    )


@router.get("/{transcript_id}", response_model=TranscriptRead)
async def get_transcript(
    transcript_id: int,
    session_id: str = Query(..., description="User session ID"),
    db=Depends(get_db),
):
    """
    Get a specific transcript by ID.
    
    Returns 404 if not found, 403 if access denied.
    """
    transcript = transcripts.get_transcript(
        db=db,
        session_id=session_id,
        transcript_id=transcript_id,
    )
    return TranscriptRead.model_validate(transcript)

