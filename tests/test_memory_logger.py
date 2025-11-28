"""
Memory Logger tests for ChatOS.

Tests the MemoryLogger conversation logging and training data export.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from ChatOS.controllers.memory_logger import (
    MemoryLogger,
    InteractionQuality,
    Message,
    ConversationLog,
    SessionStats,
    get_memory_logger,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create temporary directories for memory logging."""
    logs_dir = tmp_path / "logs"
    training_dir = tmp_path / "training_data"
    feedback_dir = tmp_path / "feedback"
    analytics_dir = tmp_path / "analytics"
    
    for d in [logs_dir, training_dir, feedback_dir, analytics_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    return {
        "base": tmp_path,
        "logs": logs_dir,
        "training": training_dir,
        "feedback": feedback_dir,
        "analytics": analytics_dir,
    }


@pytest.fixture
def memory_logger(temp_memory_dir):
    """Create a fresh MemoryLogger with temp directories."""
    # Patch the directory constants
    with patch("ChatOS.controllers.memory_logger.MEMORY_DIR", temp_memory_dir["base"]), \
         patch("ChatOS.controllers.memory_logger.LOGS_DIR", temp_memory_dir["logs"]), \
         patch("ChatOS.controllers.memory_logger.TRAINING_DIR", temp_memory_dir["training"]), \
         patch("ChatOS.controllers.memory_logger.FEEDBACK_DIR", temp_memory_dir["feedback"]), \
         patch("ChatOS.controllers.memory_logger.ANALYTICS_DIR", temp_memory_dir["analytics"]):
        
        # Reset singleton for fresh instance
        MemoryLogger._instance = None
        logger = MemoryLogger()
        logger._initialized = False
        logger.__init__()
        
        yield logger
        
        # Cleanup
        MemoryLogger._instance = None


# =============================================================================
# InteractionQuality Enum Tests
# =============================================================================

class TestInteractionQuality:
    """Tests for the InteractionQuality enum."""

    def test_all_qualities_defined(self):
        """All expected quality levels should be defined."""
        expected = ["excellent", "good", "acceptable", "poor", "failed", "unrated"]
        actual = [q.value for q in InteractionQuality]
        assert sorted(actual) == sorted(expected)

    def test_quality_string_values(self):
        """Quality values should be lowercase strings."""
        assert InteractionQuality.EXCELLENT.value == "excellent"
        assert InteractionQuality.GOOD.value == "good"
        assert InteractionQuality.POOR.value == "poor"
        assert InteractionQuality.FAILED.value == "failed"
        assert InteractionQuality.UNRATED.value == "unrated"


# =============================================================================
# Message Dataclass Tests
# =============================================================================

class TestMessage:
    """Tests for the Message dataclass."""

    def test_message_creation(self):
        """Should create message with required fields."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_timestamp_auto_generated(self):
        """Timestamp should be auto-generated if not provided."""
        msg = Message(role="user", content="Test")
        assert msg.timestamp is not None
        # Should be valid ISO format
        datetime.fromisoformat(msg.timestamp)

    def test_message_optional_fields(self):
        """Optional fields should default to None."""
        msg = Message(role="user", content="Test")
        assert msg.model is None
        assert msg.tokens is None
        assert msg.latency_ms is None

    def test_message_with_metadata(self):
        """Should store model and performance metadata."""
        msg = Message(
            role="assistant",
            content="Response",
            model="qwen-7b",
            tokens=50,
            latency_ms=150.5
        )
        assert msg.model == "qwen-7b"
        assert msg.tokens == 50
        assert msg.latency_ms == 150.5


# =============================================================================
# ConversationLog Tests
# =============================================================================

class TestConversationLog:
    """Tests for the ConversationLog dataclass."""

    def test_conversation_creation(self):
        """Should create conversation with required fields."""
        conv = ConversationLog(
            session_id="session123",
            conversation_id="conv456",
            started_at=datetime.now().isoformat()
        )
        assert conv.session_id == "session123"
        assert conv.conversation_id == "conv456"
        assert conv.messages == []

    def test_add_message(self):
        """Should add messages to conversation."""
        conv = ConversationLog(
            session_id="s1",
            conversation_id="c1",
            started_at=datetime.now().isoformat()
        )
        
        msg = conv.add_message("user", "Hello")
        assert len(conv.messages) == 1
        assert conv.messages[0].content == "Hello"
        assert isinstance(msg, Message)

    def test_add_message_with_tokens(self):
        """Should accumulate token counts."""
        conv = ConversationLog(
            session_id="s1",
            conversation_id="c1",
            started_at=datetime.now().isoformat()
        )
        
        conv.add_message("user", "Hello", tokens=10)
        conv.add_message("assistant", "Hi there!", tokens=20)
        
        assert conv.total_tokens == 30

    def test_add_message_with_latency(self):
        """Should accumulate latency."""
        conv = ConversationLog(
            session_id="s1",
            conversation_id="c1",
            started_at=datetime.now().isoformat()
        )
        
        conv.add_message("assistant", "Response 1", latency_ms=100.0)
        conv.add_message("assistant", "Response 2", latency_ms=150.0)
        
        assert conv.total_latency_ms == 250.0

    def test_to_dict(self):
        """Should convert to dictionary for JSON serialization."""
        conv = ConversationLog(
            session_id="s1",
            conversation_id="c1",
            started_at="2024-01-01T12:00:00",
            mode="code"
        )
        conv.add_message("user", "Write a function")
        conv.quality = InteractionQuality.GOOD
        
        d = conv.to_dict()
        
        assert d["session_id"] == "s1"
        assert d["conversation_id"] == "c1"
        assert d["mode"] == "code"
        assert d["quality"] == "good"
        assert len(d["messages"]) == 1

    def test_to_training_format_good_quality(self):
        """Should export training data for good quality conversations."""
        conv = ConversationLog(
            session_id="s1",
            conversation_id="c1",
            started_at="2024-01-01T12:00:00"
        )
        conv.add_message("user", "What is Python?")
        conv.add_message("assistant", "Python is a programming language.")
        conv.quality = InteractionQuality.GOOD
        conv.chosen_model = "qwen-7b"
        
        training = conv.to_training_format()
        
        assert training is not None
        assert "messages" in training
        assert len(training["messages"]) == 2
        assert training["messages"][0]["role"] == "user"
        assert training["messages"][1]["role"] == "assistant"
        assert training["metadata"]["quality"] == "good"

    def test_to_training_format_poor_quality_returns_none(self):
        """Should not export training data for poor quality conversations."""
        conv = ConversationLog(
            session_id="s1",
            conversation_id="c1",
            started_at="2024-01-01T12:00:00"
        )
        conv.add_message("user", "Test")
        conv.add_message("assistant", "Bad response")
        conv.quality = InteractionQuality.POOR
        
        training = conv.to_training_format()
        assert training is None

    def test_to_training_format_too_few_messages(self):
        """Should not export if fewer than 2 messages."""
        conv = ConversationLog(
            session_id="s1",
            conversation_id="c1",
            started_at="2024-01-01T12:00:00"
        )
        conv.add_message("user", "Hello")
        conv.quality = InteractionQuality.GOOD
        
        training = conv.to_training_format()
        assert training is None


# =============================================================================
# MemoryLogger Tests
# =============================================================================

class TestMemoryLogger:
    """Tests for the MemoryLogger class."""

    def test_session_id_generated(self, memory_logger):
        """Should generate unique session ID."""
        assert memory_logger.session_id is not None
        assert len(memory_logger.session_id) == 16  # SHA256 truncated

    def test_start_conversation(self, memory_logger):
        """Should create new conversation and return ID."""
        conv_id = memory_logger.start_conversation()
        
        assert conv_id is not None
        assert len(conv_id) == 12
        assert conv_id in memory_logger.active_conversations

    def test_start_conversation_with_mode(self, memory_logger):
        """Should set conversation mode."""
        conv_id = memory_logger.start_conversation(mode="code", rag_enabled=True)
        
        conv = memory_logger.active_conversations[conv_id]
        assert conv.mode == "code"
        assert conv.rag_enabled is True

    def test_log_user_message(self, memory_logger):
        """Should log user message to conversation."""
        conv_id = memory_logger.start_conversation()
        memory_logger.log_user_message(conv_id, "Hello, world!")
        
        conv = memory_logger.active_conversations[conv_id]
        assert len(conv.messages) == 1
        assert conv.messages[0].role == "user"
        assert conv.messages[0].content == "Hello, world!"

    def test_log_user_message_auto_creates_conversation(self, memory_logger):
        """Should auto-create conversation if ID doesn't exist."""
        # Use a non-existent ID
        memory_logger.log_user_message("nonexistent", "Test message")
        
        # Should have created a new conversation
        assert memory_logger.session_stats.total_conversations >= 1

    def test_log_assistant_response(self, memory_logger):
        """Should log assistant response with metadata."""
        conv_id = memory_logger.start_conversation()
        memory_logger.log_user_message(conv_id, "Hi")
        memory_logger.log_assistant_response(
            conv_id,
            content="Hello! How can I help?",
            model="qwen-7b",
            tokens=15,
            latency_ms=200.5
        )
        
        conv = memory_logger.active_conversations[conv_id]
        assert len(conv.messages) == 2
        assert conv.messages[1].role == "assistant"
        assert conv.messages[1].model == "qwen-7b"
        assert conv.chosen_model == "qwen-7b"
        assert "qwen-7b" in conv.models_used

    def test_log_assistant_response_with_council(self, memory_logger):
        """Should log council votes."""
        conv_id = memory_logger.start_conversation()
        memory_logger.log_user_message(conv_id, "Test")
        
        council_responses = [
            {"model": "model1", "text": "Short response"},
            {"model": "model2", "text": "This is a longer response with more text"},
        ]
        
        memory_logger.log_assistant_response(
            conv_id,
            content="Chosen response",
            model="model2",
            council_responses=council_responses
        )
        
        conv = memory_logger.active_conversations[conv_id]
        assert conv.council_votes == {"model1": 14, "model2": 40}

    def test_log_rag_context(self, memory_logger):
        """Should log RAG context."""
        conv_id = memory_logger.start_conversation(rag_enabled=True)
        memory_logger.log_rag_context(conv_id, "Relevant document content here")
        
        conv = memory_logger.active_conversations[conv_id]
        assert conv.rag_context == "Relevant document content here"

    def test_log_error(self, memory_logger):
        """Should log errors and mark quality as failed."""
        conv_id = memory_logger.start_conversation()
        memory_logger.log_error(conv_id, "Model timeout")
        
        conv = memory_logger.active_conversations[conv_id]
        assert conv.error == "Model timeout"
        assert conv.quality == InteractionQuality.FAILED

    def test_rate_conversation(self, memory_logger):
        """Should rate conversation quality."""
        conv_id = memory_logger.start_conversation()
        memory_logger.rate_conversation(
            conv_id,
            quality=InteractionQuality.EXCELLENT,
            feedback="Great response!",
            thumbs_up=True
        )
        
        conv = memory_logger.active_conversations[conv_id]
        assert conv.quality == InteractionQuality.EXCELLENT
        assert conv.user_feedback == "Great response!"
        assert conv.thumbs_up is True

    def test_thumbs_up(self, memory_logger):
        """Should set good quality with thumbs up."""
        conv_id = memory_logger.start_conversation()
        memory_logger.thumbs_up(conv_id)
        
        conv = memory_logger.active_conversations[conv_id]
        assert conv.quality == InteractionQuality.GOOD
        assert conv.thumbs_up is True

    def test_thumbs_down(self, memory_logger):
        """Should set poor quality with thumbs down."""
        conv_id = memory_logger.start_conversation()
        memory_logger.thumbs_down(conv_id, feedback="Not helpful")
        
        conv = memory_logger.active_conversations[conv_id]
        assert conv.quality == InteractionQuality.POOR
        assert conv.thumbs_up is False
        assert conv.user_feedback == "Not helpful"


# =============================================================================
# Persistence Tests
# =============================================================================

class TestMemoryLoggerPersistence:
    """Tests for saving and loading conversations."""

    def test_end_conversation_saves_to_disk(self, memory_logger, temp_memory_dir):
        """Should save conversation to JSONL file on end."""
        conv_id = memory_logger.start_conversation()
        memory_logger.log_user_message(conv_id, "Hello")
        memory_logger.log_assistant_response(conv_id, "Hi there!", model="test-model")
        
        with patch("ChatOS.controllers.memory_logger.LOGS_DIR", temp_memory_dir["logs"]), \
             patch("ChatOS.controllers.memory_logger.TRAINING_DIR", temp_memory_dir["training"]):
            memory_logger.end_conversation(conv_id)
        
        # Check log file exists
        log_files = list(temp_memory_dir["logs"].glob("conversations_*.jsonl"))
        assert len(log_files) >= 1
        
        # Verify content
        with open(log_files[0]) as f:
            data = json.loads(f.readline())
            assert data["conversation_id"] == conv_id
            assert len(data["messages"]) == 2

    def test_end_conversation_removes_from_active(self, memory_logger, temp_memory_dir):
        """Should remove conversation from active list."""
        conv_id = memory_logger.start_conversation()
        assert conv_id in memory_logger.active_conversations
        
        with patch("ChatOS.controllers.memory_logger.LOGS_DIR", temp_memory_dir["logs"]), \
             patch("ChatOS.controllers.memory_logger.TRAINING_DIR", temp_memory_dir["training"]):
            memory_logger.end_conversation(conv_id)
        
        assert conv_id not in memory_logger.active_conversations

    def test_save_all_active(self, memory_logger, temp_memory_dir):
        """Should save all active conversations."""
        # Create multiple conversations
        conv1 = memory_logger.start_conversation()
        conv2 = memory_logger.start_conversation()
        memory_logger.log_user_message(conv1, "Message 1")
        memory_logger.log_user_message(conv2, "Message 2")
        
        with patch("ChatOS.controllers.memory_logger.LOGS_DIR", temp_memory_dir["logs"]), \
             patch("ChatOS.controllers.memory_logger.TRAINING_DIR", temp_memory_dir["training"]):
            count = memory_logger.save_all_active()
        
        assert count == 2
        assert len(memory_logger.active_conversations) == 0


# =============================================================================
# Training Data Export Tests
# =============================================================================

class TestTrainingDataExport:
    """Tests for training data export functionality."""

    def test_export_training_data_basic(self, memory_logger, temp_memory_dir):
        """Should export good quality conversations."""
        # Create and save a conversation
        conv_id = memory_logger.start_conversation()
        memory_logger.log_user_message(conv_id, "What is AI?")
        memory_logger.log_assistant_response(
            conv_id,
            "AI is artificial intelligence.",
            model="test"
        )
        memory_logger.rate_conversation(conv_id, InteractionQuality.GOOD)
        
        with patch("ChatOS.controllers.memory_logger.LOGS_DIR", temp_memory_dir["logs"]), \
             patch("ChatOS.controllers.memory_logger.TRAINING_DIR", temp_memory_dir["training"]):
            memory_logger.end_conversation(conv_id)
            
            output_file = temp_memory_dir["training"] / "test_export.json"
            stats = memory_logger.export_training_data(output_file=output_file)
        
        assert stats["exported"] >= 1
        assert Path(output_file).exists()
        
        with open(output_file) as f:
            data = json.load(f)
            assert len(data) >= 1
            assert "messages" in data[0]

    def test_export_filters_by_quality(self, memory_logger, temp_memory_dir):
        """Should filter out poor quality conversations."""
        # Create good conversation
        conv1 = memory_logger.start_conversation()
        memory_logger.log_user_message(conv1, "Good question")
        memory_logger.log_assistant_response(conv1, "Good answer", model="test")
        memory_logger.rate_conversation(conv1, InteractionQuality.GOOD)
        
        # Create poor conversation
        conv2 = memory_logger.start_conversation()
        memory_logger.log_user_message(conv2, "Bad question")
        memory_logger.log_assistant_response(conv2, "Bad answer", model="test")
        memory_logger.rate_conversation(conv2, InteractionQuality.POOR)
        
        with patch("ChatOS.controllers.memory_logger.LOGS_DIR", temp_memory_dir["logs"]), \
             patch("ChatOS.controllers.memory_logger.TRAINING_DIR", temp_memory_dir["training"]):
            memory_logger.end_conversation(conv1)
            memory_logger.end_conversation(conv2)
            
            output_file = temp_memory_dir["training"] / "filtered_export.json"
            stats = memory_logger.export_training_data(
                output_file=output_file,
                min_quality=InteractionQuality.ACCEPTABLE
            )
        
        # Only good quality should be exported
        assert stats["skipped_quality"] >= 1


# =============================================================================
# Session Stats Tests
# =============================================================================

class TestSessionStats:
    """Tests for session statistics."""

    def test_initial_stats(self, memory_logger):
        """Should have zero initial stats."""
        stats = memory_logger.get_session_stats()
        assert stats["total_conversations"] == 0
        assert stats["total_messages"] == 0

    def test_stats_update_on_conversation(self, memory_logger):
        """Should update stats as conversations progress."""
        conv_id = memory_logger.start_conversation(mode="code")
        memory_logger.log_user_message(conv_id, "Test")
        memory_logger.log_assistant_response(conv_id, "Response", model="model1", tokens=10)
        
        stats = memory_logger.get_session_stats()
        assert stats["total_conversations"] == 1
        assert stats["total_messages"] == 2
        assert stats["total_tokens"] == 10
        assert stats["modes_usage"]["code"] == 1
        assert stats["models_usage"]["model1"] == 1


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_memory_logger_returns_singleton(self):
        """get_memory_logger should return the same instance."""
        # Reset singleton
        MemoryLogger._instance = None
        
        logger1 = get_memory_logger()
        logger2 = get_memory_logger()
        
        assert logger1 is logger2
        
        # Cleanup
        MemoryLogger._instance = None

