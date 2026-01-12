#!/usr/bin/env python3
"""
persrm_data_pipeline.py - Convert PersRM reasoning data to Unsloth training format.

This module provides functions to:
1. Load PersRM reasoning data from JSONL files
2. Load PersRM feedback data (if available)
3. Convert to Unsloth-compatible chat format
4. Support versioned dataset generation

Data sources:
- /home/kr/PersRM-V0.2/data/reasoning.jsonl (input + expected_reasoning)
- /home/kr/PersRM-V0.2/data/reasoning_instruction.jsonl (instruction + output)
- /home/kr/PersRM-V0.2/data/feedback/ (optional feedback logs)

Usage:
    from chatos_backend.training.persrm_data_pipeline import generate_persrm_dataset
    stats = generate_persrm_dataset()
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import random

from chatos_backend.config.settings import settings


# =============================================================================
# Configuration
# =============================================================================

# PersRM data locations
PERSRM_ROOT = Path.home() / "PersRM-V0.2"
PERSRM_DATA_DIR = PERSRM_ROOT / "data"
PERSRM_REASONING_FILE = PERSRM_DATA_DIR / "reasoning.jsonl"
PERSRM_INSTRUCTION_FILE = PERSRM_DATA_DIR / "reasoning_instruction.jsonl"
PERSRM_FEEDBACK_DIR = PERSRM_DATA_DIR / "feedback"

# PersRM dataset output (separate from ChatOS datasets)
PERSRM_DATASETS_DIR = settings.unsloth_datasets_dir / "persrm"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PersRMExample:
    """A single PersRM reasoning example."""
    input_text: str
    output_text: str
    source: str  # "reasoning", "instruction", or "feedback"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_unsloth_format(self) -> Dict[str, Any]:
        """
        Convert to Unsloth chat format.
        
        Returns:
            {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}
        """
        # Add a system prompt for UI/UX reasoning context
        messages = [
            {
                "role": "system",
                "content": "You are an expert UI/UX designer and developer. Provide detailed, structured reasoning about design decisions, component architecture, and user experience considerations."
            },
            {
                "role": "user",
                "content": self.input_text
            },
            {
                "role": "assistant",
                "content": self.output_text
            }
        ]
        return {"messages": messages}


@dataclass
class PersRMDatasetStats:
    """Statistics about generated PersRM dataset."""
    total_examples: int = 0
    reasoning_examples: int = 0
    instruction_examples: int = 0
    feedback_examples: int = 0
    train_count: int = 0
    eval_count: int = 0
    version: int = 0
    train_path: Optional[str] = None
    eval_path: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_examples": self.total_examples,
            "reasoning_examples": self.reasoning_examples,
            "instruction_examples": self.instruction_examples,
            "feedback_examples": self.feedback_examples,
            "train_count": self.train_count,
            "eval_count": self.eval_count,
            "version": self.version,
            "train_path": self.train_path,
            "eval_path": self.eval_path,
            "created_at": self.created_at,
        }


# =============================================================================
# Versioning
# =============================================================================

def _get_persrm_version_file() -> Path:
    """Get path to PersRM version tracking file."""
    return PERSRM_DATASETS_DIR / ".version"


def get_current_persrm_version() -> int:
    """Get current PersRM dataset version number."""
    version_file = _get_persrm_version_file()
    if version_file.exists():
        try:
            return int(version_file.read_text().strip())
        except (ValueError, IOError):
            pass
    return 0


def get_next_persrm_version() -> int:
    """Get next PersRM dataset version number."""
    return get_current_persrm_version() + 1


def _increment_persrm_version(version: int) -> None:
    """Save new PersRM version number."""
    version_file = _get_persrm_version_file()
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(str(version))


def get_persrm_dataset_dir(version: int) -> Path:
    """Get directory for a specific PersRM dataset version."""
    return PERSRM_DATASETS_DIR / f"persrm_v{version}"


def list_persrm_dataset_versions() -> List[Dict[str, Any]]:
    """List all available PersRM dataset versions."""
    if not PERSRM_DATASETS_DIR.exists():
        return []
    
    versions = []
    for path in PERSRM_DATASETS_DIR.glob("persrm_v*"):
        if path.is_dir():
            try:
                version = int(path.name.replace("persrm_v", ""))
                train_file = path / "persrm_train.jsonl"
                eval_file = path / "persrm_eval.jsonl"
                stats_file = path / "stats.json"
                
                info = {
                    "version": version,
                    "path": str(path),
                    "train_path": str(train_file) if train_file.exists() else None,
                    "eval_path": str(eval_file) if eval_file.exists() else None,
                    "train_count": _count_jsonl_lines(train_file),
                    "eval_count": _count_jsonl_lines(eval_file),
                }
                
                if stats_file.exists():
                    try:
                        with open(stats_file) as f:
                            info["stats"] = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        pass
                
                versions.append(info)
            except ValueError:
                continue
    
    versions.sort(key=lambda v: v["version"], reverse=True)
    return versions


def _count_jsonl_lines(path: Path) -> int:
    """Count lines in a JSONL file."""
    if not path.exists():
        return 0
    try:
        with open(path) as f:
            return sum(1 for line in f if line.strip())
    except IOError:
        return 0


# =============================================================================
# Data Loading
# =============================================================================

def load_reasoning_data() -> List[PersRMExample]:
    """
    Load examples from reasoning.jsonl.
    
    Format: {"input": "...", "expected_reasoning": "..."}
    """
    examples = []
    
    if not PERSRM_REASONING_FILE.exists():
        print(f"Warning: PersRM reasoning file not found: {PERSRM_REASONING_FILE}")
        return examples
    
    try:
        with open(PERSRM_REASONING_FILE, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    input_text = data.get("input", "")
                    output_text = data.get("expected_reasoning", "")
                    
                    if input_text and output_text:
                        examples.append(PersRMExample(
                            input_text=input_text,
                            output_text=output_text,
                            source="reasoning",
                            metadata={"line": line_num}
                        ))
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON at {PERSRM_REASONING_FILE}:{line_num}: {e}")
    except Exception as e:
        print(f"Warning: Could not read {PERSRM_REASONING_FILE}: {e}")
    
    print(f"Loaded {len(examples)} examples from reasoning.jsonl")
    return examples


def load_instruction_data() -> List[PersRMExample]:
    """
    Load examples from reasoning_instruction.jsonl.
    
    Format: {"instruction": "...", "output": "..."}
    """
    examples = []
    
    if not PERSRM_INSTRUCTION_FILE.exists():
        print(f"Warning: PersRM instruction file not found: {PERSRM_INSTRUCTION_FILE}")
        return examples
    
    try:
        with open(PERSRM_INSTRUCTION_FILE, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    input_text = data.get("instruction", "")
                    output_text = data.get("output", "")
                    
                    if input_text and output_text:
                        examples.append(PersRMExample(
                            input_text=input_text,
                            output_text=output_text,
                            source="instruction",
                            metadata={"line": line_num}
                        ))
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON at {PERSRM_INSTRUCTION_FILE}:{line_num}: {e}")
    except Exception as e:
        print(f"Warning: Could not read {PERSRM_INSTRUCTION_FILE}: {e}")
    
    print(f"Loaded {len(examples)} examples from reasoning_instruction.jsonl")
    return examples


def load_persrm_reasoning() -> List[PersRMExample]:
    """Backwards-compatible alias for load_reasoning_data."""
    return load_reasoning_data()


def load_persrm_instructions() -> List[PersRMExample]:
    """Backwards-compatible alias for load_instruction_data."""
    return load_instruction_data()


def load_feedback_data() -> List[PersRMExample]:
    """
    Load examples from PersRM feedback logs (if available).
    
    Looks for feedback_log.json in PersRM data directory.
    """
    examples = []
    feedback_file = PERSRM_FEEDBACK_DIR / "feedback_log.json"
    
    if not feedback_file.exists():
        # Try the root data dir
        feedback_file = PERSRM_DATA_DIR / "feedback_log.json"
    
    if not feedback_file.exists():
        return examples
    
    try:
        with open(feedback_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle different feedback formats
        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict) and "entries" in data:
            entries = data["entries"]
        else:
            return examples
        
        for entry in entries:
            # Only use positive feedback (score >= 0.7 or result == "success")
            score = entry.get("score", 0)
            result = entry.get("result", "")
            
            if score >= 0.7 or result == "success":
                input_text = entry.get("input", {}).get("prompt", "")
                output_text = entry.get("output", {}).get("reasoning", "") or entry.get("output", {}).get("code", "")
                
                if input_text and output_text:
                    examples.append(PersRMExample(
                        input_text=input_text,
                        output_text=output_text,
                        source="feedback",
                        metadata={
                            "score": score,
                            "result": result,
                            "component": entry.get("component", "unknown")
                        }
                    ))
    except Exception as e:
        print(f"Warning: Could not load feedback data: {e}")
    
    print(f"Loaded {len(examples)} examples from feedback logs")
    return examples


def load_all_persrm_data(include_feedback: bool = True) -> Tuple[List[PersRMExample], PersRMDatasetStats]:
    """
    Load all PersRM training data from all sources.
    
    Args:
        include_feedback: Whether to include feedback-derived examples
    
    Returns:
        Tuple of (examples, stats)
    """
    stats = PersRMDatasetStats()
    all_examples = []
    
    # Load reasoning examples
    reasoning = load_reasoning_data()
    stats.reasoning_examples = len(reasoning)
    all_examples.extend(reasoning)
    
    # Load instruction examples
    instructions = load_instruction_data()
    stats.instruction_examples = len(instructions)
    all_examples.extend(instructions)
    
    # Optionally load feedback
    if include_feedback:
        feedback = load_feedback_data()
        stats.feedback_examples = len(feedback)
        all_examples.extend(feedback)
    
    stats.total_examples = len(all_examples)
    
    return all_examples, stats


# =============================================================================
# Dataset Generation
# =============================================================================

def split_train_eval(
    examples: List[PersRMExample],
    eval_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[PersRMExample], List[PersRMExample]]:
    """Split examples into training and evaluation sets."""
    random.seed(seed)
    examples_copy = examples.copy()
    random.shuffle(examples_copy)
    
    split_idx = int(len(examples_copy) * (1 - eval_ratio))
    train = examples_copy[:split_idx]
    eval_set = examples_copy[split_idx:]
    
    return train, eval_set


def write_persrm_jsonl(
    examples: List[PersRMExample],
    output_path: Path,
) -> int:
    """Write PersRM examples to JSONL file in Unsloth format."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for example in examples:
            data = example.to_unsloth_format()
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            count += 1
    
    print(f"Wrote {count} examples to {output_path}")
    return count


def _save_persrm_stats(stats: PersRMDatasetStats, path: Path) -> None:
    """Save dataset statistics to JSON file."""
    with open(path, "w") as f:
        json.dump(stats.to_dict(), f, indent=2)


def generate_persrm_dataset(
    include_feedback: bool = True,
    eval_ratio: float = 0.1,
    use_versioning: bool = True,
) -> PersRMDatasetStats:
    """
    Generate complete PersRM training dataset.
    
    This is the main entry point for PersRM dataset generation.
    
    Args:
        include_feedback: Whether to include feedback-derived examples
        eval_ratio: Fraction of data for evaluation
        use_versioning: If True, create versioned dataset directory
    
    Returns:
        PersRMDatasetStats with generation statistics
    """
    # Determine version and output directory
    if use_versioning:
        version = get_next_persrm_version()
        output_dir = get_persrm_dataset_dir(version)
    else:
        version = 0
        output_dir = PERSRM_DATASETS_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load all data
    examples, stats = load_all_persrm_data(include_feedback=include_feedback)
    
    if not examples:
        print("Warning: No PersRM training examples found!")
        return stats
    
    # Split into train/eval
    train_examples, eval_examples = split_train_eval(examples, eval_ratio)
    
    # Write files
    train_path = output_dir / "persrm_train.jsonl"
    eval_path = output_dir / "persrm_eval.jsonl"
    
    write_persrm_jsonl(train_examples, train_path)
    if eval_examples:
        write_persrm_jsonl(eval_examples, eval_path)
    
    # Update stats
    stats.version = version
    stats.train_path = str(train_path)
    stats.eval_path = str(eval_path)
    stats.train_count = len(train_examples)
    stats.eval_count = len(eval_examples)
    stats.created_at = datetime.now().isoformat()
    
    # Save stats
    stats_path = output_dir / "stats.json"
    _save_persrm_stats(stats, stats_path)
    
    # Update version tracker
    if use_versioning:
        _increment_persrm_version(version)
    
    print(f"\nPersRM Dataset generation complete (v{version}):")
    print(f"  Total examples: {stats.total_examples}")
    print(f"  - Reasoning: {stats.reasoning_examples}")
    print(f"  - Instruction: {stats.instruction_examples}")
    print(f"  - Feedback: {stats.feedback_examples}")
    print(f"  Training examples: {stats.train_count}")
    print(f"  Evaluation examples: {stats.eval_count}")
    
    return stats


def generate_persrm_training_dataset(
    include_feedback: bool = True,
    eval_ratio: float = 0.1,
    use_versioning: bool = True,
) -> PersRMDatasetStats:
    """Compatibility wrapper for older import paths."""
    return generate_persrm_dataset(
        include_feedback=include_feedback,
        eval_ratio=eval_ratio,
        use_versioning=use_versioning,
    )


def get_persrm_training_stats() -> Dict[str, Any]:
    """
    Get statistics about available PersRM training data.
    
    Returns:
        Dict with stats about examples and readiness
    """
    try:
        examples, stats = load_all_persrm_data(include_feedback=True)
        
        # PersRM has lower requirements since it's specialized data
        min_samples = 10  # Lower threshold for reasoning data
        ready_to_train = stats.total_examples >= min_samples
        
        return {
            "total_examples": stats.total_examples,
            "reasoning_examples": stats.reasoning_examples,
            "instruction_examples": stats.instruction_examples,
            "feedback_examples": stats.feedback_examples,
            "min_samples_required": min_samples,
            "ready_to_train": ready_to_train,
            "persrm_data_dir": str(PERSRM_DATA_DIR),
            "training_enabled": settings.enable_training_features,
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_examples": 0,
            "ready_to_train": False,
            "training_enabled": settings.enable_training_features,
        }


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """CLI entry point for PersRM dataset generation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate Unsloth training dataset from PersRM data"
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        help="Exclude feedback-derived examples"
    )
    parser.add_argument(
        "--eval-ratio",
        type=float,
        default=0.1,
        help="Fraction of data for evaluation (default: 0.1)"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show stats, don't generate dataset"
    )
    
    args = parser.parse_args()
    
    if args.stats_only:
        stats = get_persrm_training_stats()
        print(json.dumps(stats, indent=2))
        return 0
    
    stats = generate_persrm_dataset(
        include_feedback=not args.no_feedback,
        eval_ratio=args.eval_ratio,
    )
    
    return 0 if stats.total_examples > 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
