"""
routes_uploads.py - API routes for file uploads.

Provides endpoints for uploading audio files for transcription.
"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Query
from pydantic import BaseModel

from chatos_backend.controllers.uploads import get_upload_manager, ALLOWED_AUDIO_EXTENSIONS, MAX_FILE_SIZE


router = APIRouter(prefix="/api/uploads", tags=["Uploads"])


class UploadResponse(BaseModel):
    """Response model for file upload."""
    id: str
    original_filename: str
    stored_path: str
    mime_type: str
    size: int
    session_id: str
    created_at: str


class FileListResponse(BaseModel):
    """Response model for file list."""
    files: list
    total: int


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    Upload an audio file for transcription.
    
    Supported formats: MP3, WAV, M4A, OGG, FLAC, WebM, AAC
    Maximum size: 100MB
    
    The file is stored in ~/ChatOS-Memory/uploads/{session_id}/ with a unique ID.
    Use the returned `stored_path` when creating a transcript.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Read file content
    content = await file.read()
    
    # Validate
    manager = get_upload_manager()
    is_valid, error = manager.validate_audio_file(file.filename, len(content))
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    try:
        uploaded = await manager.save_file(
            session_id=session_id,
            filename=file.filename,
            content=content,
        )
        
        return UploadResponse(
            id=uploaded.id,
            original_filename=uploaded.original_filename,
            stored_path=uploaded.stored_path,
            mime_type=uploaded.mime_type,
            size=uploaded.size,
            session_id=uploaded.session_id,
            created_at=uploaded.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("", response_model=FileListResponse)
async def list_uploads(
    session_id: str = Query(..., description="User session ID"),
):
    """
    List all uploaded files for a session.
    """
    manager = get_upload_manager()
    files = manager.list_files(session_id)
    
    return FileListResponse(
        files=files,
        total=len(files),
    )


@router.get("/{file_id}")
async def get_upload(
    file_id: str,
    session_id: str = Query(..., description="User session ID"),
):
    """
    Get metadata for a specific uploaded file.
    """
    manager = get_upload_manager()
    file_path = manager.get_file_path(session_id, file_id)
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    import os
    from pathlib import Path
    
    path = Path(file_path)
    stat = path.stat()
    
    return {
        "id": file_id,
        "filename": path.name,
        "path": file_path,
        "size": stat.st_size,
        "session_id": session_id,
    }


@router.delete("/{file_id}")
async def delete_upload(
    file_id: str,
    session_id: str = Query(..., description="User session ID"),
):
    """
    Delete an uploaded file.
    """
    manager = get_upload_manager()
    deleted = manager.delete_file(session_id, file_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"success": True, "file_id": file_id}


@router.get("/info/allowed-types")
async def get_allowed_types():
    """
    Get information about allowed file types and size limits.
    """
    return {
        "allowed_extensions": list(ALLOWED_AUDIO_EXTENSIONS),
        "max_size_bytes": MAX_FILE_SIZE,
        "max_size_mb": MAX_FILE_SIZE // (1024 * 1024),
    }

