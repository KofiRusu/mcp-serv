"""
routes_search.py - API routes for unified search.

Provides search endpoints across notes, transcripts, and memory.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ChatOS.database.connection import get_session
from ChatOS.controllers import search


router = APIRouter(prefix="/api/search", tags=["Search"])


def get_db():
    """Dependency to get database session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.get("")
async def unified_search(
    query: str = Query(..., min_length=2, description="Search query"),
    session_id: str = Query(..., description="User session ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    include_notes: bool = Query(True, description="Include notes in search"),
    include_transcripts: bool = Query(True, description="Include transcripts in search"),
    include_memory: bool = Query(True, description="Include memory in search"),
    db=Depends(get_db),
):
    """
    Search across notes, transcripts, and memory.
    
    Returns results grouped by type and a combined ranked list.
    
    - **query**: Required. Search query (minimum 2 characters).
    - **session_id**: Required. User session ID for scoping.
    - **limit**: Maximum total results (default 20).
    - **include_notes**: Include notes in search (default true).
    - **include_transcripts**: Include transcripts in search (default true).
    - **include_memory**: Include memory in search (default true).
    
    Response:
    - **query**: The search query
    - **results**: Combined ranked list of all results
    - **by_type**: Results grouped by type (notes, transcripts, memory)
    - **total**: Total number of results
    """
    result = search.search_all(
        db=db,
        session_id=session_id,
        query=query,
        limit=limit,
        include_notes=include_notes,
        include_transcripts=include_transcripts,
        include_memory=include_memory,
    )
    return result


@router.get("/notes")
async def search_notes(
    query: str = Query(..., min_length=2, description="Search query"),
    session_id: str = Query(..., description="User session ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db=Depends(get_db),
):
    """
    Search notes only.
    
    Searches in note titles and content.
    """
    results = search.search_notes(
        db=db,
        session_id=session_id,
        query=query,
        limit=limit,
    )
    return {
        "query": query,
        "results": results,
        "total": len(results),
    }


@router.get("/transcripts")
async def search_transcripts(
    query: str = Query(..., min_length=2, description="Search query"),
    session_id: str = Query(..., description="User session ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db=Depends(get_db),
):
    """
    Search transcripts only.
    
    Searches in transcript text content.
    """
    results = search.search_transcripts(
        db=db,
        session_id=session_id,
        query=query,
        limit=limit,
    )
    return {
        "query": query,
        "results": results,
        "total": len(results),
    }


@router.get("/memory")
async def search_memory(
    query: str = Query(..., min_length=2, description="Search query"),
    session_id: str = Query(..., description="User session ID"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results"),
):
    """
    Search AGI memory only.
    
    Searches memories stored from notes and other sources.
    """
    results = search.search_memory(
        session_id=session_id,
        query=query,
        limit=limit,
    )
    return {
        "query": query,
        "results": results,
        "total": len(results),
    }

