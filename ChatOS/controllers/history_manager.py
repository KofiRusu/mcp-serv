"""
history_manager.py - Chat history management for viewing, searching, and managing past conversations.

Provides functionality to:
- List conversations with pagination and filtering
- Get full conversation details
- Search across all conversations
- Delete conversations
- Export conversations
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import threading


# =============================================================================
# Configuration
# =============================================================================

MEMORY_DIR = Path.home() / "ChatOS-Memory"
LOGS_DIR = MEMORY_DIR / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ConversationSummary:
    """Summary of a conversation for list views."""
    conversation_id: str
    session_id: str
    started_at: str
    ended_at: Optional[str]
    mode: str
    message_count: int
    preview: str  # First user message truncated
    chosen_model: Optional[str]
    quality: str
    has_feedback: bool
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "mode": self.mode,
            "message_count": self.message_count,
            "preview": self.preview,
            "chosen_model": self.chosen_model,
            "quality": self.quality,
            "has_feedback": self.has_feedback,
            "project_id": self.project_id,
            "project_name": self.project_name,
        }


@dataclass
class ConversationDetail:
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
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "mode": self.mode,
            "rag_enabled": self.rag_enabled,
            "rag_context": self.rag_context,
            "messages": self.messages,
            "models_used": self.models_used,
            "chosen_model": self.chosen_model,
            "council_votes": self.council_votes,
            "quality": self.quality,
            "user_feedback": self.user_feedback,
            "thumbs_up": self.thumbs_up,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "error": self.error,
            "project_id": self.project_id,
            "project_name": self.project_name,
        }


@dataclass
class SearchResult:
    """Search result with matched context."""
    conversation_id: str
    session_id: str
    started_at: str
    mode: str
    chosen_model: Optional[str]
    matched_message: Dict[str, Any]
    match_context: str  # Highlighted snippet
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "mode": self.mode,
            "chosen_model": self.chosen_model,
            "matched_message": self.matched_message,
            "match_context": self.match_context,
        }


@dataclass
class PaginatedResult:
    """Paginated list result."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }


# =============================================================================
# History Manager
# =============================================================================

class HistoryManager:
    """
    Manages chat history operations.
    
    Handles reading, searching, and managing conversation logs
    stored in JSONL format.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._cache: Dict[str, Dict[str, Any]] = {}  # conversation_id -> data
        self._cache_timestamp: Optional[datetime] = None
        self._cache_lock = threading.Lock()
        self._initialized = True
    
    def _get_log_files(self) -> List[Path]:
        """Get all log files sorted by date (newest first)."""
        files = list(LOGS_DIR.glob("conversations_*.jsonl"))
        return sorted(files, reverse=True)
    
    def _parse_log_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse a single JSONL log file."""
        conversations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            conversations.append(data)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"Error reading log file {file_path}: {e}")
        return conversations
    
    def _refresh_cache(self, force: bool = False) -> None:
        """Refresh the conversation cache if needed."""
        with self._cache_lock:
            # Check if cache needs refresh (every 30 seconds or if forced)
            now = datetime.now()
            if not force and self._cache_timestamp:
                elapsed = (now - self._cache_timestamp).total_seconds()
                if elapsed < 30:
                    return
            
            self._cache.clear()
            
            for log_file in self._get_log_files():
                conversations = self._parse_log_file(log_file)
                for conv in conversations:
                    conv_id = conv.get("conversation_id")
                    if conv_id:
                        self._cache[conv_id] = conv
            
            self._cache_timestamp = now
    
    def _get_preview(self, messages: List[Dict[str, Any]], max_length: int = 100) -> str:
        """Get a preview from the first user message."""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if len(content) > max_length:
                    return content[:max_length] + "..."
                return content
        return "No preview available"
    
    def _conversation_to_summary(self, data: Dict[str, Any]) -> ConversationSummary:
        """Convert raw conversation data to summary."""
        messages = data.get("messages", [])
        return ConversationSummary(
            conversation_id=data.get("conversation_id", ""),
            session_id=data.get("session_id", ""),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at"),
            mode=data.get("mode", "normal"),
            message_count=len(messages),
            preview=self._get_preview(messages),
            chosen_model=data.get("chosen_model"),
            quality=data.get("quality", "unrated"),
            has_feedback=data.get("thumbs_up") is not None or data.get("user_feedback") is not None,
            project_id=data.get("project_id"),
            project_name=data.get("project_name"),
        )
    
    def _conversation_to_detail(self, data: Dict[str, Any]) -> ConversationDetail:
        """Convert raw conversation data to full detail."""
        return ConversationDetail(
            conversation_id=data.get("conversation_id", ""),
            session_id=data.get("session_id", ""),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at"),
            mode=data.get("mode", "normal"),
            rag_enabled=data.get("rag_enabled", False),
            rag_context=data.get("rag_context"),
            messages=data.get("messages", []),
            models_used=data.get("models_used", []),
            chosen_model=data.get("chosen_model"),
            council_votes=data.get("council_votes", {}),
            quality=data.get("quality", "unrated"),
            user_feedback=data.get("user_feedback"),
            thumbs_up=data.get("thumbs_up"),
            total_tokens=data.get("total_tokens", 0),
            total_latency_ms=data.get("total_latency_ms", 0),
            error=data.get("error"),
            project_id=data.get("project_id"),
            project_name=data.get("project_name"),
        )
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def list_conversations(
        self,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        mode: Optional[str] = None,
        quality: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> PaginatedResult:
        """
        List conversations with pagination and filtering.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            mode: Filter by mode (normal, code, research, etc.)
            quality: Filter by quality rating
            project_id: Filter by project ID
            
        Returns:
            Paginated list of conversation summaries
        """
        self._refresh_cache()
        
        # Filter conversations
        filtered = []
        for conv_id, data in self._cache.items():
            # Date filtering
            started_at = data.get("started_at", "")
            if start_date and started_at < start_date:
                continue
            if end_date and started_at > end_date:
                continue
            
            # Mode filtering
            if mode and data.get("mode") != mode:
                continue
            
            # Quality filtering
            if quality and data.get("quality") != quality:
                continue
            
            # Project filtering
            if project_id and data.get("project_id") != project_id:
                continue
            
            filtered.append(data)
        
        # Sort by date (newest first)
        filtered.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        
        # Calculate pagination
        total = len(filtered)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = filtered[start_idx:end_idx]
        
        # Convert to summaries
        summaries = [self._conversation_to_summary(data) for data in page_items]
        
        return PaginatedResult(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationDetail]:
        """
        Get full conversation details by ID.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Full conversation details or None if not found
        """
        self._refresh_cache()
        
        data = self._cache.get(conversation_id)
        if data:
            return self._conversation_to_detail(data)
        return None
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation from the logs.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            True if deleted, False if not found
        """
        self._refresh_cache()
        
        if conversation_id not in self._cache:
            return False
        
        # Find which file contains this conversation
        deleted = False
        for log_file in self._get_log_files():
            conversations = self._parse_log_file(log_file)
            original_count = len(conversations)
            
            # Filter out the conversation to delete
            remaining = [c for c in conversations if c.get("conversation_id") != conversation_id]
            
            if len(remaining) < original_count:
                # Rewrite the file without the deleted conversation
                if remaining:
                    with open(log_file, 'w', encoding='utf-8') as f:
                        for conv in remaining:
                            f.write(json.dumps(conv) + "\n")
                else:
                    # Remove empty file
                    log_file.unlink()
                
                deleted = True
                break
        
        # Update cache
        if deleted:
            with self._cache_lock:
                self._cache.pop(conversation_id, None)
        
        return deleted
    
    def search_conversations(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        mode: Optional[str] = None,
    ) -> PaginatedResult:
        """
        Search conversations by content.
        
        Args:
            query: Search query (case-insensitive)
            page: Page number
            page_size: Items per page
            mode: Optional mode filter
            
        Returns:
            Paginated search results
        """
        self._refresh_cache()
        
        query_lower = query.lower()
        results: List[SearchResult] = []
        
        for conv_id, data in self._cache.items():
            # Mode filter
            if mode and data.get("mode") != mode:
                continue
            
            messages = data.get("messages", [])
            for msg in messages:
                content = msg.get("content", "")
                if query_lower in content.lower():
                    # Create highlighted context
                    idx = content.lower().find(query_lower)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 50)
                    context = content[start:end]
                    if start > 0:
                        context = "..." + context
                    if end < len(content):
                        context = context + "..."
                    
                    results.append(SearchResult(
                        conversation_id=conv_id,
                        session_id=data.get("session_id", ""),
                        started_at=data.get("started_at", ""),
                        mode=data.get("mode", "normal"),
                        chosen_model=data.get("chosen_model"),
                        matched_message=msg,
                        match_context=context,
                    ))
                    break  # One result per conversation
        
        # Sort by date (newest first)
        results.sort(key=lambda x: x.started_at, reverse=True)
        
        # Paginate
        total = len(results)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = results[start_idx:end_idx]
        
        return PaginatedResult(
            items=page_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    
    def export_conversations(
        self,
        conversation_ids: Optional[List[str]] = None,
        format: str = "json",
        include_rag_context: bool = False,
    ) -> Dict[str, Any]:
        """
        Export conversations to JSON format.
        
        Args:
            conversation_ids: Specific IDs to export, or None for all
            format: Export format ("json" or "jsonl")
            include_rag_context: Whether to include RAG context in export
            
        Returns:
            Export data with conversations and metadata
        """
        self._refresh_cache()
        
        conversations_to_export = []
        
        if conversation_ids:
            for conv_id in conversation_ids:
                if conv_id in self._cache:
                    conversations_to_export.append(self._cache[conv_id])
        else:
            conversations_to_export = list(self._cache.values())
        
        # Sort by date
        conversations_to_export.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        
        # Optionally strip RAG context
        if not include_rag_context:
            for conv in conversations_to_export:
                conv = dict(conv)  # Make a copy
                conv.pop("rag_context", None)
        
        return {
            "exported_at": datetime.now().isoformat(),
            "total_conversations": len(conversations_to_export),
            "format": format,
            "conversations": conversations_to_export,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall conversation statistics."""
        self._refresh_cache()
        
        total = len(self._cache)
        modes = {}
        models = {}
        quality_dist = {}
        
        for data in self._cache.values():
            # Mode stats
            mode = data.get("mode", "normal")
            modes[mode] = modes.get(mode, 0) + 1
            
            # Model stats
            model = data.get("chosen_model", "unknown")
            models[model] = models.get(model, 0) + 1
            
            # Quality stats
            quality = data.get("quality", "unrated")
            quality_dist[quality] = quality_dist.get(quality, 0) + 1
        
        return {
            "total_conversations": total,
            "modes": modes,
            "models": models,
            "quality_distribution": quality_dist,
        }


# =============================================================================
# Singleton Access
# =============================================================================

_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    """Get the singleton history manager."""
    global _manager
    if _manager is None:
        _manager = HistoryManager()
    return _manager

