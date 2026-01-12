"""
Training Data Extraction for AGI Core

Collects training examples from traces and exports for fine-tuning.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..traces.recorder import TraceRecorder, TraceSession


@dataclass
class TrainingExample:
    """
    A training example extracted from traces.
    
    Attributes:
        instruction: The input/instruction
        response: The expected output/response
        source: Where this example came from
        quality_score: Estimated quality (0-1)
        metadata: Additional example data
    """
    instruction: str
    response: str
    source: str = ""
    quality_score: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "response": self.response,
            "source": self.source,
            "quality_score": self.quality_score,
            "metadata": self.metadata,
        }
    
    def to_jsonl_format(self) -> Dict[str, Any]:
        """Convert to standard JSONL training format."""
        return {
            "instruction": self.instruction,
            "input": "",
            "output": self.response,
        }


class TrainingDataCollector:
    """
    Collects training examples from AGI execution traces.
    
    Mines successful executions for instruction-response pairs
    that can be used for fine-tuning.
    
    Usage:
        collector = TrainingDataCollector()
        examples = collector.collect_from_traces(min_quality=0.7)
        collector.export_dataset(Path("training_data.jsonl"))
    """
    
    def __init__(
        self,
        trace_recorder: Optional[TraceRecorder] = None,
        storage_path: Optional[Path] = None,
    ):
        self.trace_recorder = trace_recorder or TraceRecorder()
        self.storage_path = storage_path or Path.home() / "ChatOS-Memory" / "agi" / "training"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._examples: List[TrainingExample] = []
    
    def collect_from_traces(
        self,
        min_quality: float = 0.5,
        status_filter: str = "completed",
        limit: int = 100,
    ) -> List[TrainingExample]:
        """
        Collect training examples from traces.
        
        Args:
            min_quality: Minimum quality score
            status_filter: Only use sessions with this status
            limit: Maximum examples to collect
            
        Returns:
            List of training examples
        """
        sessions = self.trace_recorder.list_sessions(
            limit=limit * 2,
            status=status_filter,
        )
        
        examples = []
        
        for session_info in sessions:
            if len(examples) >= limit:
                break
            
            session = self.trace_recorder.get_session(session_info["session_id"])
            if not session:
                continue
            
            session_examples = self._extract_from_session(session, min_quality)
            examples.extend(session_examples)
        
        self._examples.extend(examples)
        return examples
    
    def _extract_from_session(
        self,
        session: TraceSession,
        min_quality: float,
    ) -> List[TrainingExample]:
        """Extract examples from a single session."""
        examples = []
        
        # Goal → Result pair
        if session.status == "completed" and session.result:
            result_str = str(session.result)[:2000]
            
            example = TrainingExample(
                instruction=session.goal,
                response=result_str,
                source=f"trace:{session.session_id}",
                quality_score=0.7,
                metadata={
                    "session_id": session.session_id,
                    "step_count": len(session.steps),
                },
            )
            
            if example.quality_score >= min_quality:
                examples.append(example)
        
        # Tool usage pairs
        for step in session.steps:
            if step.action == "tool_call" and step.output_data:
                if step.tools_used:
                    tool_name = step.tools_used[0]
                    
                    instruction = f"Use the {tool_name} tool with: {step.input_data}"
                    response = f"Tool result: {step.output_data}"
                    
                    example = TrainingExample(
                        instruction=instruction,
                        response=response,
                        source=f"trace:{session.session_id}:step:{step.step_number}",
                        quality_score=0.6,
                    )
                    
                    if example.quality_score >= min_quality:
                        examples.append(example)
        
        return examples
    
    def add_manual_example(
        self,
        instruction: str,
        response: str,
        quality_score: float = 0.8,
    ) -> TrainingExample:
        """Add a manually created training example."""
        example = TrainingExample(
            instruction=instruction,
            response=response,
            source="manual",
            quality_score=quality_score,
        )
        self._examples.append(example)
        return example
    
    def add_correction_pair(
        self,
        original_instruction: str,
        bad_response: str,
        good_response: str,
    ) -> TrainingExample:
        """
        Add a correction pair (before/after).
        
        These are valuable for training the model to avoid mistakes.
        """
        example = TrainingExample(
            instruction=original_instruction,
            response=good_response,
            source="correction",
            quality_score=0.9,  # Corrections are high value
            metadata={
                "bad_response": bad_response,
                "is_correction": True,
            },
        )
        self._examples.append(example)
        return example
    
    def get_examples(
        self,
        min_quality: float = 0.0,
        source_filter: Optional[str] = None,
    ) -> List[TrainingExample]:
        """Get collected examples with optional filtering."""
        examples = self._examples
        
        if min_quality > 0:
            examples = [e for e in examples if e.quality_score >= min_quality]
        
        if source_filter:
            examples = [e for e in examples if source_filter in e.source]
        
        return examples
    
    def export_dataset(
        self,
        output_path: Optional[Path] = None,
        min_quality: float = 0.5,
        format: str = "jsonl",
    ) -> int:
        """
        Export training examples to a file.
        
        Args:
            output_path: Output file path
            min_quality: Minimum quality threshold
            format: Output format (jsonl or json)
            
        Returns:
            Number of examples exported
        """
        output_path = output_path or self.storage_path / f"examples_{int(time.time())}.jsonl"
        output_path = Path(output_path)
        
        examples = self.get_examples(min_quality=min_quality)
        
        if format == "jsonl":
            with open(output_path, 'w', encoding='utf-8') as f:
                for example in examples:
                    f.write(json.dumps(example.to_jsonl_format()) + "\n")
        else:
            data = {
                "version": 1,
                "exported_at": time.time(),
                "examples": [e.to_dict() for e in examples],
            }
            output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
        return len(examples)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        sources = {}
        quality_sum = 0
        
        for example in self._examples:
            source_type = example.source.split(":")[0]
            sources[source_type] = sources.get(source_type, 0) + 1
            quality_sum += example.quality_score
        
        return {
            "total_examples": len(self._examples),
            "by_source": sources,
            "average_quality": quality_sum / max(len(self._examples), 1),
        }
    
    def clear(self) -> int:
        """Clear collected examples."""
        count = len(self._examples)
        self._examples.clear()
        return count


def export_training_dataset(
    output_path: Path,
    min_quality: float = 0.6,
) -> int:
    """
    Convenience function to export training dataset.
    
    Args:
        output_path: Where to write the dataset
        min_quality: Minimum quality threshold
        
    Returns:
        Number of examples exported
    """
    collector = TrainingDataCollector()
    collector.collect_from_traces(min_quality=min_quality)
    return collector.export_dataset(output_path, min_quality=min_quality)

