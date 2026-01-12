"""
routes_chat_history.py - API routes for chat history management.

Provides endpoints for:
- Listing conversation history
- Getting conversation details
- Searching conversations
- Deleting conversations
- Exporting conversations
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from chatos_backend.controllers.history_manager import get_history_manager


# =============================================================================
# Schemas
# =============================================================================

class ConversationSummaryResponse(BaseModel):
    """Summary of a conversation."""
    conversation_id: str
    session_id: str
    started_at: str
    ended_at: Optional[str]
    mode: str
    message_count: int
    preview: str
    chosen_model: Optional[str]
    quality: str
    has_feedback: bool


class MessageResponse(BaseModel):
    """A message in a conversation."""
    role: str
    content: str
    timestamp: Optional[str] = None
    model: Optional[str] = None
    tokens: Optional[int] = None
    latency_ms: Optional[float] = None


class ConversationDetailResponse(BaseModel):
    """Full conversation details."""
    conversation_id: str
    session_id: str
    started_at: str
    ended_at: Optional[str]
    mode: str
    rag_enabled: bool
    rag_context: Optional[str]
    messages: List[Dict[str, Any]]
    models_used: List[str]
    chosen_model: Optional[str]
    council_votes: Dict[str, Any]
    quality: str
    user_feedback: Optional[str]
    thumbs_up: Optional[bool]
    total_tokens: int
    total_latency_ms: float
    error: Optional[str]


class PaginatedConversationsResponse(BaseModel):
    """Paginated list of conversations."""
    items: List[ConversationSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SearchResultResponse(BaseModel):
    """Search result item."""
    conversation_id: str
    session_id: str
    started_at: str
    mode: str
    chosen_model: Optional[str]
    matched_message: Dict[str, Any]
    match_context: str


class PaginatedSearchResponse(BaseModel):
    """Paginated search results."""
    items: List[SearchResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExportRequest(BaseModel):
    """Request to export conversations."""
    conversation_ids: Optional[List[str]] = Field(None, description="Specific IDs to export, or empty for all")
    format: str = Field(default="json", description="Export format: json or jsonl")
    include_rag_context: bool = Field(default=False, description="Include RAG context in export")


class ExportResponse(BaseModel):
    """Export response with conversations."""
    exported_at: str
    total_conversations: int
    format: str
    conversations: List[Dict[str, Any]]


class HistoryStatsResponse(BaseModel):
    """Statistics about conversation history."""
    total_conversations: int
    modes: Dict[str, int]
    models: Dict[str, int]
    quality_distribution: Dict[str, int]


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/api/history", tags=["Chat History"])


@router.get("", response_model=PaginatedConversationsResponse)
async def list_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    mode: Optional[str] = Query(None, description="Filter by mode"),
    quality: Optional[str] = Query(None, description="Filter by quality rating"),
):
    """
    List all conversations with pagination and filtering.
    
    Returns a paginated list of conversation summaries sorted by date (newest first).
    """
    manager = get_history_manager()
    result = manager.list_conversations(
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        quality=quality,
    )
    
    return PaginatedConversationsResponse(
        items=[ConversationSummaryResponse(**item.to_dict()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get("/search", response_model=PaginatedSearchResponse)
async def search_conversations(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    mode: Optional[str] = Query(None, description="Filter by mode"),
):
    """
    Search conversations by content.
    
    Performs case-insensitive search across all message content.
    Returns matching conversations with context snippets.
    """
    manager = get_history_manager()
    result = manager.search_conversations(
        query=q,
        page=page,
        page_size=page_size,
        mode=mode,
    )
    
    return PaginatedSearchResponse(
        items=[SearchResultResponse(**item.to_dict()) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get("/stats", response_model=HistoryStatsResponse)
async def get_history_stats():
    """
    Get overall statistics about conversation history.
    
    Returns counts by mode, model, and quality rating.
    """
    manager = get_history_manager()
    stats = manager.get_stats()
    return HistoryStatsResponse(**stats)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str):
    """
    Get full details of a specific conversation.
    
    Returns complete conversation including all messages, metadata, and feedback.
    """
    manager = get_history_manager()
    conversation = manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationDetailResponse(**conversation.to_dict())


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation from history.
    
    This permanently removes the conversation from the log files.
    """
    manager = get_history_manager()
    deleted = manager.delete_conversation(conversation_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"success": True, "conversation_id": conversation_id}


@router.post("/export", response_model=ExportResponse)
async def export_conversations(request: ExportRequest):
    """
    Export conversations to JSON format.
    
    Can export specific conversations by ID, or all conversations if no IDs provided.
    """
    manager = get_history_manager()
    result = manager.export_conversations(
        conversation_ids=request.conversation_ids,
        format=request.format,
        include_rag_context=request.include_rag_context,
    )
    
    return ExportResponse(**result)


@router.delete("")
async def clear_all_history(confirm: bool = Query(False, description="Must be true to confirm")):
    """
    Clear all conversation history.
    
    Requires confirm=true query parameter to prevent accidental deletion.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must pass confirm=true to clear all history"
        )
    
    manager = get_history_manager()
    
    # Get all conversation IDs and delete them
    result = manager.list_conversations(page=1, page_size=10000)
    deleted_count = 0
    
    for item in result.items:
        if manager.delete_conversation(item.conversation_id):
            deleted_count += 1
    
    return {"success": True, "deleted_count": deleted_count}

