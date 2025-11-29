"""
Tests for ChatOS.training.data_pipeline module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestDataPipeline:
    """Test cases for the data pipeline module."""
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation for testing."""
        return {
            "conversation_id": "test_conv_001",
            "timestamp": "2025-01-01T12:00:00",
            "mode": "normal",
            "model": "qwen2.5:7b",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm doing well, thank you!"},
            ],
            "quality": "good",
            "thumbs_up": True,
        }
    
    @pytest.fixture
    def temp_log_dir(self, sample_conversation):
        """Create a temporary directory with sample log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "conversation_test_conv_001.jsonl"
            with open(log_path, "w") as f:
                f.write(json.dumps(sample_conversation) + "\n")
            yield Path(tmpdir)
    
    def test_message_dataclass(self):
        """Test Message dataclass creation."""
        from ChatOS.training.data_pipeline import Message
        
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_conversation_dataclass(self):
        """Test Conversation dataclass creation."""
        from ChatOS.training.data_pipeline import Conversation, Message
        
        messages = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello!"),
        ]
        conv = Conversation(
            conversation_id="test_001",
            messages=messages,
        )
        
        assert conv.conversation_id == "test_001"
        assert len(conv.messages) == 2
        assert conv.has_valid_exchange()
    
    def test_conversation_feedback_score(self):
        """Test feedback score calculation."""
        from ChatOS.training.data_pipeline import Conversation, Message
        
        messages = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello!"),
        ]
        
        # Test positive feedback
        conv_positive = Conversation(
            conversation_id="test_001",
            messages=messages,
            thumbs_up=True,
        )
        assert conv_positive.feedback_score >= 1
        
        # Test negative feedback
        conv_negative = Conversation(
            conversation_id="test_002",
            messages=messages,
            thumbs_up=False,
        )
        assert conv_negative.feedback_score < 0
        
        # Test unrated
        conv_unrated = Conversation(
            conversation_id="test_003",
            messages=messages,
        )
        assert conv_unrated.feedback_score == 0
    
    def test_training_example_to_unsloth_format(self):
        """Test TrainingExample conversion to Unsloth format."""
        from ChatOS.training.data_pipeline import TrainingExample
        
        example = TrainingExample(
            messages=[
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "2+2 equals 4."},
            ]
        )
        
        unsloth_format = example.to_unsloth_format()
        
        assert "messages" in unsloth_format
        assert len(unsloth_format["messages"]) == 2
        assert unsloth_format["messages"][0]["role"] == "user"
    
    def test_filter_for_training_with_score(self):
        """Test filtering conversations by feedback score."""
        from ChatOS.training.data_pipeline import (
            Conversation, Message, filter_for_training
        )
        
        messages = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello!"),
        ]
        
        conversations = [
            Conversation("c1", messages, thumbs_up=True),   # Score 1
            Conversation("c2", messages, thumbs_up=False),  # Score -1
            Conversation("c3", messages),                    # Score 0
        ]
        
        # Filter for positive only
        examples, stats = filter_for_training(conversations, min_score=1)
        assert len(examples) == 1
        
        # Filter for neutral and above
        examples, stats = filter_for_training(conversations, min_score=0)
        assert len(examples) == 2
        
        # Include all
        examples, stats = filter_for_training(conversations, min_score=-1)
        assert len(examples) == 3
    
    def test_split_train_eval(self):
        """Test train/eval split."""
        from ChatOS.training.data_pipeline import (
            TrainingExample, split_train_eval
        )
        
        examples = [
            TrainingExample(messages=[
                {"role": "user", "content": f"Message {i}"},
                {"role": "assistant", "content": f"Response {i}"},
            ])
            for i in range(100)
        ]
        
        train, eval = split_train_eval(examples, eval_ratio=0.1, seed=42)
        
        assert len(train) == 90
        assert len(eval) == 10
        
        # Reproducibility test
        train2, eval2 = split_train_eval(examples, eval_ratio=0.1, seed=42)
        assert len(train2) == len(train)
    
    def test_to_unsloth_jsonl(self, tmp_path):
        """Test JSONL export."""
        from ChatOS.training.data_pipeline import TrainingExample, to_unsloth_jsonl
        
        examples = [
            TrainingExample(messages=[
                {"role": "user", "content": "Question 1"},
                {"role": "assistant", "content": "Answer 1"},
            ]),
            TrainingExample(messages=[
                {"role": "user", "content": "Question 2"},
                {"role": "assistant", "content": "Answer 2"},
            ]),
        ]
        
        output_path = tmp_path / "test_output.jsonl"
        count = to_unsloth_jsonl(examples, output_path)
        
        assert count == 2
        assert output_path.exists()
        
        # Verify format
        with open(output_path) as f:
            lines = f.readlines()
            assert len(lines) == 2
            
            data = json.loads(lines[0])
            assert "messages" in data


class TestDatasetStats:
    """Test DatasetStats dataclass."""
    
    def test_stats_creation(self):
        """Test DatasetStats creation."""
        from ChatOS.training.data_pipeline import DatasetStats
        
        stats = DatasetStats(
            total_conversations=100,
            filtered_conversations=80,
            training_examples=72,
            eval_examples=8,
            positive_examples=50,
            neutral_examples=30,
            negative_examples=20,
        )
        
        assert stats.total_conversations == 100
        assert stats.training_examples + stats.eval_examples == 80

