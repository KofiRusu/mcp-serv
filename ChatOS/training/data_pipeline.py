#!/usr/bin/env python3
"""
data_pipeline.py - Convert ChatOS conversation logs to Unsloth training format.

This module provides functions to:
1. Load raw conversations from ChatOS memory logs
2. Filter conversations based on quality/feedback
3. Export to Unsloth-compatible JSONL format

Usage as module:
    from training.data_pipeline import generate_training_dataset
    stats = generate_training_dataset(min_score=1, output_path="train.jsonl")

Usage as CLI:
    python -m ChatOS.training.data_pipeline --min_score 1 --output train.jsonl
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import random

# Add parent to path for imports when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ChatOS.config.settings import settings


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Message:
    """A single message in a conversation."""
    role: str
    content: str
    timestamp: Optional[str] = None
    model: Optional[str] = None


@dataclass
class Conversation:
    """A complete conversation with metadata."""
    conversation_id: str
    messages: List[Message]
    mode: str = "normal"
    model: Optional[str] = None
    quality: str = "unrated"
    thumbs_up: Optional[bool] = None
    timestamp: Optional[str] = None
    
    @property
    def feedback_score(self) -> int:
        """
        Calculate feedback score.
        Returns:
            1 for positive (thumbs_up=True or quality in [excellent, good])
            0 for neutral (unrated)
            -1 for negative (thumbs_up=False or quality in [poor, failed])
        """
        if self.thumbs_up is True:
            return 1
        if self.thumbs_up is False:
            return -1
        
        quality_scores = {
            "excellent": 1,
            "good": 1,
            "acceptable": 0,
            "unrated": 0,
            "poor": -1,
            "failed": -1,
        }
        return quality_scores.get(self.quality, 0)
    
    def has_valid_exchange(self) -> bool:
        """Check if conversation has at least one user-assistant exchange."""
        has_user = any(m.role == "user" for m in self.messages)
        has_assistant = any(m.role == "assistant" for m in self.messages)
        return has_user and has_assistant


@dataclass
class TrainingExample:
    """A training example in Unsloth format."""
    messages: List[Dict[str, str]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "messages": self.messages,
            "metadata": self.metadata,
        }
    
    def to_unsloth_format(self) -> Dict[str, Any]:
        """
        Convert to Unsloth training format.
        
        Unsloth expects either:
        - {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        - {"instruction": "...", "response": "..."} for alpaca format
        
        We use the messages format for chat models.
        """
        return {"messages": self.messages}


@dataclass
class DatasetStats:
    """Statistics about the generated dataset."""
    total_conversations: int = 0
    filtered_conversations: int = 0
    total_examples: int = 0
    positive_examples: int = 0
    neutral_examples: int = 0
    negative_excluded: int = 0
    by_mode: Dict[str, int] = field(default_factory=dict)
    by_model: Dict[str, int] = field(default_factory=dict)


# =============================================================================
# Core Functions
# =============================================================================

def load_raw_conversations(log_root: Optional[Path] = None) -> List[Conversation]:
    """
    Load all conversations from ChatOS training data logs.
    
    Args:
        log_root: Path to training data directory. Defaults to settings.training_data_dir
    
    Returns:
        List of Conversation objects
    """
    if log_root is None:
        log_root = settings.training_data_dir
    
    log_root = Path(log_root)
    conversations = []
    
    if not log_root.exists():
        print(f"Warning: Training data directory does not exist: {log_root}")
        return conversations
    
    # Load all JSONL files (multi-conversation per file)
    for jsonl_file in sorted(log_root.glob("*.jsonl")):
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        conv = _parse_conversation(data)
                        if conv:
                            conversations.append(conv)
                    except json.JSONDecodeError as e:
                        print(f"Warning: Invalid JSON at {jsonl_file}:{line_num}: {e}")
                    except Exception as e:
                        print(f"Warning: Error parsing {jsonl_file}:{line_num}: {e}")
        except Exception as e:
            print(f"Warning: Could not read {jsonl_file}: {e}")
    
    # Also load individual JSON files (one conversation per file)
    for json_file in sorted(log_root.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                conv = _parse_conversation(data)
                if conv:
                    conversations.append(conv)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {json_file}: {e}")
        except Exception as e:
            print(f"Warning: Could not read {json_file}: {e}")
    
    print(f"Loaded {len(conversations)} conversations from {log_root}")
    return conversations


def _parse_conversation(data: Dict[str, Any]) -> Optional[Conversation]:
    """Parse a single conversation entry from log data."""
    # Handle the ChatOS training data format
    messages_data = data.get("messages", [])
    metadata = data.get("metadata", {})
    
    if not messages_data:
        return None
    
    messages = []
    for msg in messages_data:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append(Message(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp"),
                model=msg.get("model"),
            ))
    
    if not messages:
        return None
    
    # Try to get thumbs_up from multiple sources
    thumbs_up = metadata.get("thumbs_up")
    if thumbs_up is None:
        # Check for feedback_score at top level
        feedback_score = data.get("feedback_score")
        if feedback_score is not None:
            thumbs_up = feedback_score > 0
    
    # Get conversation_id from multiple sources
    conv_id = metadata.get("conversation_id") or data.get("id") or "unknown"
    
    return Conversation(
        conversation_id=conv_id,
        messages=messages,
        mode=metadata.get("mode") or data.get("mode", "normal"),
        model=metadata.get("model") or data.get("model"),
        quality=metadata.get("quality", "unrated"),
        thumbs_up=thumbs_up,
        timestamp=metadata.get("timestamp") or data.get("timestamp"),
    )


def filter_for_training(
    conversations: List[Conversation],
    min_score: int = 0,
    include_unrated: bool = True,
    modes: Optional[List[str]] = None,
) -> Tuple[List[TrainingExample], DatasetStats]:
    """
    Filter conversations and convert to training examples.
    
    Args:
        conversations: List of conversations to filter
        min_score: Minimum feedback score (-1, 0, or 1)
        include_unrated: Whether to include unrated conversations
        modes: List of modes to include (None = all modes)
    
    Returns:
        Tuple of (training examples, statistics)
    """
    stats = DatasetStats(total_conversations=len(conversations))
    examples = []
    
    for conv in conversations:
        # Check for valid exchange
        if not conv.has_valid_exchange():
            continue
        
        # Filter by mode
        if modes and conv.mode not in modes:
            continue
        
        # Filter by feedback score
        score = conv.feedback_score
        
        if score < min_score:
            stats.negative_excluded += 1
            continue
        
        if score == 0 and not include_unrated:
            continue
        
        # Convert to training example
        chat_messages = []
        for msg in conv.messages:
            if msg.role in ["user", "assistant"]:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        if len(chat_messages) < 2:
            continue
        
        example = TrainingExample(
            messages=chat_messages,
            metadata={
                "conversation_id": conv.conversation_id,
                "mode": conv.mode,
                "model": conv.model,
                "quality": conv.quality,
                "feedback_score": score,
            }
        )
        examples.append(example)
        
        # Update stats
        stats.filtered_conversations += 1
        if score > 0:
            stats.positive_examples += 1
        else:
            stats.neutral_examples += 1
        
        # Track by mode
        stats.by_mode[conv.mode] = stats.by_mode.get(conv.mode, 0) + 1
        
        # Track by model
        if conv.model:
            stats.by_model[conv.model] = stats.by_model.get(conv.model, 0) + 1
    
    stats.total_examples = len(examples)
    return examples, stats


def to_unsloth_jsonl(
    examples: List[TrainingExample],
    output_path: Path,
    include_metadata: bool = False,
) -> int:
    """
    Write training examples to JSONL file in Unsloth format.
    
    Args:
        examples: List of training examples
        output_path: Path to output JSONL file
        include_metadata: Whether to include metadata in output
    
    Returns:
        Number of examples written
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for example in examples:
            if include_metadata:
                data = example.to_dict()
            else:
                data = example.to_unsloth_format()
            
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            count += 1
    
    print(f"Wrote {count} examples to {output_path}")
    return count


def split_train_eval(
    examples: List[TrainingExample],
    eval_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[TrainingExample], List[TrainingExample]]:
    """
    Split examples into training and evaluation sets.
    
    Args:
        examples: List of training examples
        eval_ratio: Fraction of examples for evaluation
        seed: Random seed for reproducibility
    
    Returns:
        Tuple of (train_examples, eval_examples)
    """
    random.seed(seed)
    examples_copy = examples.copy()
    random.shuffle(examples_copy)
    
    split_idx = int(len(examples_copy) * (1 - eval_ratio))
    train = examples_copy[:split_idx]
    eval_set = examples_copy[split_idx:]
    
    return train, eval_set


def generate_training_dataset(
    min_score: int = 0,
    include_unrated: bool = True,
    eval_ratio: float = 0.1,
    output_dir: Optional[Path] = None,
    train_filename: str = "chatos_train.jsonl",
    eval_filename: str = "chatos_eval.jsonl",
) -> DatasetStats:
    """
    Generate complete training dataset from ChatOS logs.
    
    This is the main entry point for dataset generation.
    
    Args:
        min_score: Minimum feedback score to include
        include_unrated: Whether to include unrated conversations
        eval_ratio: Fraction of data for evaluation
        output_dir: Output directory (defaults to Unsloth datasets dir)
        train_filename: Name of training file
        eval_filename: Name of evaluation file
    
    Returns:
        DatasetStats with generation statistics
    """
    if output_dir is None:
        output_dir = settings.unsloth_datasets_dir
    
    output_dir = Path(output_dir)
    
    # Load conversations
    conversations = load_raw_conversations()
    
    # Filter and convert
    examples, stats = filter_for_training(
        conversations,
        min_score=min_score,
        include_unrated=include_unrated,
    )
    
    if not examples:
        print("Warning: No training examples generated!")
        return stats
    
    # Split into train/eval
    train_examples, eval_examples = split_train_eval(examples, eval_ratio)
    
    # Write files
    train_path = output_dir / train_filename
    eval_path = output_dir / eval_filename
    
    to_unsloth_jsonl(train_examples, train_path)
    if eval_examples:
        to_unsloth_jsonl(eval_examples, eval_path)
    
    print(f"\nDataset generation complete:")
    print(f"  Total conversations: {stats.total_conversations}")
    print(f"  Filtered: {stats.filtered_conversations}")
    print(f"  Training examples: {len(train_examples)}")
    print(f"  Evaluation examples: {len(eval_examples)}")
    print(f"  Positive feedback: {stats.positive_examples}")
    print(f"  Neutral/unrated: {stats.neutral_examples}")
    print(f"  Excluded (negative): {stats.negative_excluded}")
    
    return stats


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """CLI entry point for dataset generation."""
    parser = argparse.ArgumentParser(
        description="Generate Unsloth training dataset from ChatOS logs"
    )
    parser.add_argument(
        "--min_score",
        type=int,
        default=0,
        choices=[-1, 0, 1],
        help="Minimum feedback score (-1=include negative, 0=neutral+positive, 1=positive only)"
    )
    parser.add_argument(
        "--include_unrated",
        action="store_true",
        default=True,
        help="Include unrated conversations (default: True)"
    )
    parser.add_argument(
        "--no_unrated",
        action="store_true",
        help="Exclude unrated conversations"
    )
    parser.add_argument(
        "--eval_ratio",
        type=float,
        default=0.1,
        help="Fraction of data for evaluation (default: 0.1)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Output directory (default: Unsloth datasets dir)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (overrides output_dir)"
    )
    parser.add_argument(
        "--log_root",
        type=str,
        default=None,
        help="Path to ChatOS training data logs"
    )
    
    args = parser.parse_args()
    
    # Handle include_unrated
    include_unrated = args.include_unrated and not args.no_unrated
    
    # Handle custom log root
    if args.log_root:
        global settings
        # Temporarily override log root
        original_dir = settings.training_data_dir
        settings.memory_dir = Path(args.log_root).parent
    
    # Handle custom output
    output_dir = args.output_dir
    if args.output:
        output_path = Path(args.output)
        output_dir = output_path.parent
        train_filename = output_path.name
    else:
        train_filename = "chatos_train.jsonl"
    
    # Generate dataset
    stats = generate_training_dataset(
        min_score=args.min_score,
        include_unrated=include_unrated,
        eval_ratio=args.eval_ratio,
        output_dir=output_dir,
        train_filename=train_filename,
    )
    
    # Return exit code based on success
    if stats.total_examples > 0:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

