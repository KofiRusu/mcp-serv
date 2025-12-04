"""
transcripts.py - Controller for transcript CRUD operations.

Provides database operations for audio transcripts with user scoping via session_id.
Includes background processing pipeline for transcription and summarisation.
"""

import asyncio
import logging
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ChatOS.database.notes_models import TranscriptDB
from ChatOS.api.schemas_notes import TranscriptCreate

logger = logging.getLogger(__name__)


def create_transcript(
    db: Session,
    session_id: str,
    audio_path: str,
    language: Optional[str] = None,
) -> TranscriptDB:
    """
    Create a new transcript record with status='pending'.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        audio_path: Path to the audio file
        language: Optional language code
        
    Returns:
        Created TranscriptDB instance
    """
    transcript = TranscriptDB(
        session_id=session_id,
        audio_path=audio_path,
        language=language,
        status="pending",
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def get_transcript(db: Session, session_id: str, transcript_id: int) -> TranscriptDB:
    """
    Get a specific transcript by ID.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        transcript_id: Transcript ID
        
    Returns:
        TranscriptDB instance
        
    Raises:
        HTTPException: If transcript not found or access denied
    """
    transcript = db.query(TranscriptDB).filter(TranscriptDB.id == transcript_id).first()
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    if transcript.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return transcript


def list_transcripts(
    db: Session,
    session_id: str,
    status: Optional[str] = None,
) -> List[TranscriptDB]:
    """
    List transcripts for a user with optional status filter.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        status: Optional status filter (pending, processing, done, error)
        
    Returns:
        List of TranscriptDB instances
    """
    q = db.query(TranscriptDB).filter(TranscriptDB.session_id == session_id)
    
    if status:
        q = q.filter(TranscriptDB.status == status)
    
    return q.order_by(TranscriptDB.created_at.desc()).all()


def update_transcript_status(
    db: Session,
    transcript_id: int,
    status: str,
    transcript_text: Optional[str] = None,
    error_message: Optional[str] = None,
) -> TranscriptDB:
    """
    Update transcript status (used by background ASR job).
    
    Note: This function does NOT check session_id, as it's meant to be called
    by the background job processor. Use with caution.
    
    Args:
        db: Database session
        transcript_id: Transcript ID
        status: New status (pending, processing, done, error)
        transcript_text: Transcribed text (for status='done')
        error_message: Error message (for status='error')
        
    Returns:
        Updated TranscriptDB instance
        
    Raises:
        HTTPException: If transcript not found
    """
    transcript = db.query(TranscriptDB).filter(TranscriptDB.id == transcript_id).first()
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    transcript.status = status
    
    if transcript_text is not None:
        transcript.transcript_text = transcript_text
    
    if error_message is not None:
        transcript.error_message = error_message
    
    db.commit()
    db.refresh(transcript)
    return transcript


def update_transcript_speaker_info(
    db: Session,
    transcript_id: int,
    speaker_info: dict,
) -> TranscriptDB:
    """
    Update transcript speaker information.
    
    Args:
        db: Database session
        transcript_id: Transcript ID
        speaker_info: Speaker diarization info
        
    Returns:
        Updated TranscriptDB instance
    """
    transcript = db.query(TranscriptDB).filter(TranscriptDB.id == transcript_id).first()
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    transcript.speaker_info = speaker_info
    db.commit()
    db.refresh(transcript)
    return transcript


def count_transcripts(db: Session, session_id: str) -> int:
    """
    Count transcripts for a user.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        
    Returns:
        Number of transcripts
    """
    return db.query(TranscriptDB).filter(TranscriptDB.session_id == session_id).count()


def count_transcripts_by_status(db: Session, session_id: str) -> dict:
    """
    Count transcripts by status for a user.
    
    Args:
        db: Database session
        session_id: User session ID for scoping
        
    Returns:
        Dict with counts per status
    """
    from sqlalchemy import func
    
    results = (
        db.query(TranscriptDB.status, func.count(TranscriptDB.id))
        .filter(TranscriptDB.session_id == session_id)
        .group_by(TranscriptDB.status)
        .all()
    )
    
    return {status: count for status, count in results}


async def process_transcript(transcript_id: int, session_id: str) -> None:
    """
    Background task to process a transcript: transcribe audio, summarise, and create note.
    
    This function is designed to be run as a background task via FastAPI's BackgroundTasks.
    It handles its own database session to avoid issues with session lifecycle.
    
    Pipeline:
    1. Fetch transcript and verify it's pending
    2. Set status to 'processing'
    3. Transcribe audio using transcription service
    4. Summarise transcript and extract action items
    5. Create a Note with the summary
    6. Set status to 'done' (or 'error' on failure)
    
    Args:
        transcript_id: ID of the transcript to process
        session_id: User session ID for ownership verification
    """
    from ChatOS.database.connection import get_session
    from ChatOS.services.transcription import transcribe_audio
    from ChatOS.services.summarization import summarize_text
    from ChatOS.controllers import notes_db
    from ChatOS.api.schemas_notes import NoteCreate
    
    db = get_session()
    
    try:
        # Fetch transcript
        transcript = db.query(TranscriptDB).filter(TranscriptDB.id == transcript_id).first()
        
        if not transcript:
            logger.error(f"Transcript {transcript_id} not found")
            return
        
        # Verify ownership
        if transcript.session_id != session_id:
            logger.error(f"Session mismatch for transcript {transcript_id}")
            return
        
        # Skip if not pending (avoid duplicate processing)
        if transcript.status != "pending":
            logger.info(f"Transcript {transcript_id} already processed (status={transcript.status})")
            return
        
        # Set status to processing
        transcript.status = "processing"
        db.commit()
        logger.info(f"Processing transcript {transcript_id}: {transcript.audio_path}")
        
        try:
            # Step 1: Transcribe audio
            transcript_text = await transcribe_audio(
                transcript.audio_path,
                language=transcript.language,
            )
            
            # Save transcript text
            transcript.transcript_text = transcript_text
            db.commit()
            
            # Step 2: Summarise and extract action items
            summary_result = await summarize_text(transcript_text)
            summary = summary_result["summary"]
            action_items = summary_result["action_items"]
            
            # Step 3: Create a Note with the summary
            action_items_text = "\n".join(f"- {item}" for item in action_items)
            note_content = f"{summary}\n\nAction Items:\n{action_items_text}"
            
            note_in = NoteCreate(
                session_id=session_id,
                title=f"Summary of {transcript.audio_path}",
                content=note_content,
                tags=["meeting", "auto"],
            )
            
            note = notes_db.create_note(db=db, session_id=session_id, note_in=note_in)
            
            # Step 4: Store note in AGI memory for later recall
            try:
                from ChatOS.services.memory import store_note_memory
                store_note_memory(note)
                logger.info(f"Stored note {note.id} in memory")
            except Exception as mem_error:
                # Memory storage is non-critical, log and continue
                logger.warning(f"Failed to store note in memory: {mem_error}")
            
            # Set status to done
            transcript.status = "done"
            db.commit()
            logger.info(f"Transcript {transcript_id} processed successfully")
            
        except Exception as e:
            # Set status to error
            logger.error(f"Error processing transcript {transcript_id}: {e}")
            transcript.status = "error"
            transcript.error_message = str(e)
            db.commit()
            
    except Exception as e:
        logger.error(f"Fatal error processing transcript {transcript_id}: {e}")
    finally:
        db.close()

