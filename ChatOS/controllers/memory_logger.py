"""
memory_logger.py - Conversation logging and memory enhancement system.

Logs all ChatOS interactions for:
- Conversation history & analytics
- Training data generation
- Model improvement feedback loop

Features:
- Structured JSON logging
- Conversation quality scoring
- Automatic training data export
- Session tracking
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum
import threading


# =============================================================================
# Configuration
# =============================================================================

MEMORY_DIR = Path.home() / "ChatOS-Memory"
LOGS_DIR = MEMORY_DIR / "logs"
TRAINING_DIR = MEMORY_DIR / "training_data"
FEEDBACK_DIR = MEMORY_DIR / "feedback"
ANALYTICS_DIR = MEMORY_DIR / "analytics"

# Ensure directories exist
for d in [MEMORY_DIR, LOGS_DIR, TRAINING_DIR, FEEDBACK_DIR, ANALYTICS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class InteractionQuality(str, Enum):
    """Quality rating for interactions."""
    EXCELLENT = "excellent"  # Perfect response, user satisfied
    GOOD = "good"           # Good response with minor issues
    ACCEPTABLE = "acceptable"  # Response worked but could be better
    POOR = "poor"           # Response missed the mark
    FAILED = "failed"       # Error or complete failure
    UNRATED = "unrated"     # Not yet rated


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model: Optional[str] = None
    tokens: Optional[int] = None
    latency_ms: Optional[float] = None


@dataclass
class ConversationLog:
    """Complete conversation log with metadata."""
    
    session_id: str
    conversation_id: str
    started_at: str
    messages: List[Message] = field(default_factory=list)
    
    # Context
    mode: str = "normal"  # normal, code, research, deepthinking, swarm
    rag_enabled: bool = False
    rag_context: Optional[str] = None
    
    # Model info
    models_used: List[str] = field(default_factory=list)
    chosen_model: Optional[str] = None
    council_votes: Dict[str, Any] = field(default_factory=dict)
    
    # Quality & feedback
    quality: InteractionQuality = InteractionQuality.UNRATED
    user_feedback: Optional[str] = None
    thumbs_up: Optional[bool] = None
    
    # Metadata
    ended_at: Optional[str] = None
    total_tokens: int = 0
    total_latency_ms: float = 0
    error: Optional[str] = None
    
    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """Add a message to the conversation."""
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        if kwargs.get("tokens"):
            self.total_tokens += kwargs["tokens"]
        if kwargs.get("latency_ms"):
            self.total_latency_ms += kwargs["latency_ms"]
        return msg
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "messages": [asdict(m) for m in self.messages],
            "mode": self.mode,
            "rag_enabled": self.rag_enabled,
            "rag_context": self.rag_context,
            "models_used": self.models_used,
            "chosen_model": self.chosen_model,
            "council_votes": self.council_votes,
            "quality": self.quality.value,
            "user_feedback": self.user_feedback,
            "thumbs_up": self.thumbs_up,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "error": self.error,
        }
    
    def to_training_format(self) -> Optional[Dict[str, Any]]:
        """Convert to training data format if quality is good enough."""
        if self.quality in [InteractionQuality.POOR, InteractionQuality.FAILED]:
            return None
        
        if len(self.messages) < 2:
            return None
        
        # Build chat messages for training
        chat_messages = []
        for msg in self.messages:
            if msg.role in ["user", "assistant"]:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        if not chat_messages:
            return None
        
        return {
            "messages": chat_messages,
            "metadata": {
                "source": "chatos_interaction",
                "conversation_id": self.conversation_id,
                "mode": self.mode,
                "quality": self.quality.value,
                "model": self.chosen_model,
                "timestamp": self.started_at,
            }
        }


@dataclass 
class SessionStats:
    """Statistics for a session."""
    session_id: str
    started_at: str
    total_conversations: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    models_usage: Dict[str, int] = field(default_factory=dict)
    modes_usage: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# Memory Logger
# =============================================================================

class MemoryLogger:
    """
    Central logging system for ChatOS interactions.
    
    Handles:
    - Real-time conversation logging
    - Quality rating and feedback
    - Training data export
    - Analytics generation
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
        
        self.session_id = self._generate_session_id()
        self.session_start = datetime.now()
        self.active_conversations: Dict[str, ConversationLog] = {}
        self.session_stats = SessionStats(
            session_id=self.session_id,
            started_at=self.session_start.isoformat()
        )
        
        # Auto-save interval
        self._save_lock = threading.Lock()
        self._initialized = True
        
        print(f"📝 MemoryLogger initialized: Session {self.session_id[:8]}...")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        data = f"{datetime.now().isoformat()}-{id(self)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _generate_conversation_id(self) -> str:
        """Generate unique conversation ID."""
        data = f"{self.session_id}-{datetime.now().isoformat()}-{len(self.active_conversations)}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]
    
    # =========================================================================
    # Conversation Management
    # =========================================================================
    
    def start_conversation(
        self,
        mode: str = "normal",
        rag_enabled: bool = False,
    ) -> str:
        """Start a new conversation and return its ID."""
        conv_id = self._generate_conversation_id()
        
        self.active_conversations[conv_id] = ConversationLog(
            session_id=self.session_id,
            conversation_id=conv_id,
            started_at=datetime.now().isoformat(),
            mode=mode,
            rag_enabled=rag_enabled,
        )
        
        self.session_stats.total_conversations += 1
        self.session_stats.modes_usage[mode] = self.session_stats.modes_usage.get(mode, 0) + 1
        
        return conv_id
    
    def log_user_message(
        self,
        conversation_id: str,
        content: str,
    ) -> None:
        """Log a user message."""
        if conversation_id not in self.active_conversations:
            conversation_id = self.start_conversation()
        
        conv = self.active_conversations[conversation_id]
        conv.add_message("user", content)
        self.session_stats.total_messages += 1
    
    def log_assistant_response(
        self,
        conversation_id: str,
        content: str,
        model: str,
        tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        council_responses: Optional[List[Dict]] = None,
    ) -> None:
        """Log an assistant response."""
        if conversation_id not in self.active_conversations:
            return
        
        conv = self.active_conversations[conversation_id]
        conv.add_message(
            "assistant",
            content,
            model=model,
            tokens=tokens,
            latency_ms=latency_ms,
        )
        
        if model not in conv.models_used:
            conv.models_used.append(model)
        conv.chosen_model = model
        
        if council_responses:
            conv.council_votes = {r["model"]: len(r.get("text", "")) for r in council_responses}
        
        # Update stats
        self.session_stats.total_messages += 1
        if tokens:
            self.session_stats.total_tokens += tokens
        self.session_stats.models_usage[model] = self.session_stats.models_usage.get(model, 0) + 1
    
    def log_rag_context(self, conversation_id: str, context: str) -> None:
        """Log RAG context used."""
        if conversation_id in self.active_conversations:
            self.active_conversations[conversation_id].rag_context = context
    
    def log_error(self, conversation_id: str, error: str) -> None:
        """Log an error."""
        if conversation_id in self.active_conversations:
            self.active_conversations[conversation_id].error = error
            self.active_conversations[conversation_id].quality = InteractionQuality.FAILED
    
    # =========================================================================
    # Quality & Feedback
    # =========================================================================
    
    def rate_conversation(
        self,
        conversation_id: str,
        quality: InteractionQuality,
        feedback: Optional[str] = None,
        thumbs_up: Optional[bool] = None,
    ) -> None:
        """Rate a conversation's quality."""
        if conversation_id not in self.active_conversations:
            return
        
        conv = self.active_conversations[conversation_id]
        conv.quality = quality
        conv.user_feedback = feedback
        conv.thumbs_up = thumbs_up
        
        # Update stats
        q = quality.value
        self.session_stats.quality_distribution[q] = self.session_stats.quality_distribution.get(q, 0) + 1
    
    def thumbs_up(self, conversation_id: str) -> None:
        """Quick thumbs up rating."""
        self.rate_conversation(conversation_id, InteractionQuality.GOOD, thumbs_up=True)
    
    def thumbs_down(self, conversation_id: str, feedback: Optional[str] = None) -> None:
        """Quick thumbs down rating."""
        self.rate_conversation(conversation_id, InteractionQuality.POOR, feedback=feedback, thumbs_up=False)
    
    # =========================================================================
    # Persistence
    # =========================================================================
    
    def end_conversation(self, conversation_id: str) -> Optional[ConversationLog]:
        """End and save a conversation."""
        if conversation_id not in self.active_conversations:
            return None
        
        conv = self.active_conversations[conversation_id]
        conv.ended_at = datetime.now().isoformat()
        
        # Save to disk
        self._save_conversation(conv)
        
        # Remove from active
        del self.active_conversations[conversation_id]
        
        return conv
    
    def _save_conversation(self, conv: ConversationLog) -> None:
        """Save conversation to disk."""
        with self._save_lock:
            # Daily log file
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = LOGS_DIR / f"conversations_{date_str}.jsonl"
            
            with open(log_file, "a") as f:
                f.write(json.dumps(conv.to_dict()) + "\n")
            
            # If quality is good, also save to training data
            if conv.quality in [InteractionQuality.EXCELLENT, InteractionQuality.GOOD, InteractionQuality.UNRATED]:
                training_data = conv.to_training_format()
                if training_data:
                    training_file = TRAINING_DIR / f"training_{date_str}.jsonl"
                    with open(training_file, "a") as f:
                        f.write(json.dumps(training_data) + "\n")
    
    def save_all_active(self) -> int:
        """Save all active conversations (e.g., on shutdown)."""
        count = 0
        for conv_id in list(self.active_conversations.keys()):
            self.end_conversation(conv_id)
            count += 1
        return count
    
    # =========================================================================
    # Training Data Export
    # =========================================================================
    
    def export_training_data(
        self,
        output_file: Optional[Path] = None,
        min_quality: InteractionQuality = InteractionQuality.ACCEPTABLE,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export logged conversations as training data.
        
        Returns stats about the export.
        """
        if output_file is None:
            output_file = TRAINING_DIR / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        quality_order = [
            InteractionQuality.EXCELLENT,
            InteractionQuality.GOOD,
            InteractionQuality.ACCEPTABLE,
            InteractionQuality.UNRATED,
            InteractionQuality.POOR,
            InteractionQuality.FAILED,
        ]
        min_idx = quality_order.index(min_quality)
        acceptable_qualities = set(q.value for q in quality_order[:min_idx + 1])
        
        training_samples = []
        stats = {"total_logs": 0, "exported": 0, "skipped_quality": 0, "skipped_format": 0}
        
        # Read all log files
        for log_file in sorted(LOGS_DIR.glob("conversations_*.jsonl")):
            # Filter by date if specified
            file_date = log_file.stem.replace("conversations_", "")
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue
            
            with open(log_file) as f:
                for line in f:
                    stats["total_logs"] += 1
                    try:
                        data = json.loads(line)
                        
                        # Check quality
                        if data.get("quality") not in acceptable_qualities:
                            stats["skipped_quality"] += 1
                            continue
                        
                        # Convert to training format
                        messages = data.get("messages", [])
                        if len(messages) < 2:
                            stats["skipped_format"] += 1
                            continue
                        
                        chat_messages = []
                        for msg in messages:
                            if msg["role"] in ["user", "assistant"]:
                                chat_messages.append({
                                    "role": msg["role"],
                                    "content": msg["content"]
                                })
                        
                        if chat_messages:
                            training_samples.append({
                                "messages": chat_messages,
                                "metadata": {
                                    "source": "chatos",
                                    "quality": data.get("quality"),
                                    "mode": data.get("mode"),
                                    "model": data.get("chosen_model"),
                                }
                            })
                            stats["exported"] += 1
                            
                    except json.JSONDecodeError:
                        continue
        
        # Write output
        with open(output_file, "w") as f:
            json.dump(training_samples, f, indent=2)
        
        stats["output_file"] = str(output_file)
        return stats
    
    # =========================================================================
    # Analytics
    # =========================================================================
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        return asdict(self.session_stats)
    
    def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "session": self.get_session_stats(),
            "historical": self._analyze_historical_data(),
        }
        
        # Save report
        report_file = ANALYTICS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _analyze_historical_data(self) -> Dict[str, Any]:
        """Analyze all historical conversation data."""
        stats = {
            "total_conversations": 0,
            "total_messages": 0,
            "quality_distribution": {},
            "models_usage": {},
            "modes_usage": {},
            "daily_activity": {},
        }
        
        for log_file in LOGS_DIR.glob("conversations_*.jsonl"):
            file_date = log_file.stem.replace("conversations_", "")
            daily_count = 0
            
            with open(log_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        stats["total_conversations"] += 1
                        daily_count += 1
                        
                        msg_count = len(data.get("messages", []))
                        stats["total_messages"] += msg_count
                        
                        quality = data.get("quality", "unrated")
                        stats["quality_distribution"][quality] = stats["quality_distribution"].get(quality, 0) + 1
                        
                        model = data.get("chosen_model", "unknown")
                        stats["models_usage"][model] = stats["models_usage"].get(model, 0) + 1
                        
                        mode = data.get("mode", "normal")
                        stats["modes_usage"][mode] = stats["modes_usage"].get(mode, 0) + 1
                        
                    except json.JSONDecodeError:
                        continue
            
            stats["daily_activity"][file_date] = daily_count
        
        return stats


# =============================================================================
# Singleton Access
# =============================================================================

_logger: Optional[MemoryLogger] = None


def get_memory_logger() -> MemoryLogger:
    """Get the singleton memory logger."""
    global _logger
    if _logger is None:
        _logger = MemoryLogger()
    return _logger

