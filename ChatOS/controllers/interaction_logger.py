"""
Interaction Logger for ChatOS → PersRM Integration

This module captures all user interactions in ChatOS and forwards them
to PersRM for knowledge building and continuous learning.

Captured interactions:
- Chat messages (user queries and AI responses)
- Code edits and file operations
- Command executions
- Model assist requests
- Session metadata
"""

import os
import json
import time
import asyncio
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Types of interactions that can be logged."""
    CHAT_MESSAGE = "chat_message"
    CHAT_RESPONSE = "chat_response"
    CODE_EDIT = "code_edit"
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    COMMAND_EXECUTE = "command_execute"
    MODEL_ASSIST = "model_assist"
    TERMINAL_COMMAND = "terminal_command"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    FEEDBACK = "feedback"
    ERROR = "error"
    # PersRM reasoning types
    REASONING_TRACE = "reasoning_trace"
    UI_ANALYSIS = "ui_analysis"
    CODE_REVIEW = "code_review"


class ReasoningCategory(str, Enum):
    """Categories for PersRM reasoning interactions."""
    UI_ANALYSIS = "ui_analysis"
    CODE_GENERATION = "code_generation"
    ACCESSIBILITY = "accessibility"
    LAYOUT_DESIGN = "layout_design"
    UX_REASONING = "ux_reasoning"
    DEBUG = "debug"
    REFACTOR = "refactor"
    GENERAL = "general"


@dataclass
class Interaction:
    """A single user interaction with PersRM reasoning support."""
    type: str
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    user_id: str = "default"
    
    # Content fields
    content: Optional[str] = None
    response: Optional[str] = None
    
    # Context fields
    model: Optional[str] = None
    file_path: Optional[str] = None
    language: Optional[str] = None
    
    # Execution fields
    command: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Quality signals
    success: bool = True
    error_message: Optional[str] = None
    
    # PersRM Reasoning fields
    reasoning_trace: Optional[str] = None
    reasoning_category: Optional[str] = None
    reasoning_steps: Optional[List[str]] = None
    quality_score: float = 0.7  # Default quality
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def extract_reasoning(self) -> Optional[str]:
        """Extract <think>...</think> content from response."""
        if not self.response:
            return None
        
        import re
        match = re.search(r'<think>(.*?)</think>', self.response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def extract_answer(self) -> Optional[str]:
        """Extract <answer>...</answer> content from response."""
        if not self.response:
            return None
        
        import re
        match = re.search(r'<answer>(.*?)</answer>', self.response, re.DOTALL)
        if match:
            return match.group(1).strip()
        # If no answer tags, return the response without thinking
        if '<think>' in self.response:
            # Return everything after </think>
            parts = self.response.split('</think>')
            if len(parts) > 1:
                return parts[1].strip()
        return self.response
    
    def has_reasoning_trace(self) -> bool:
        """Check if response contains reasoning trace."""
        return self.reasoning_trace is not None or (
            self.response and '<think>' in self.response
        )
    
    def to_training_format(self) -> Optional[Dict[str, Any]]:
        """Convert to format suitable for training with reasoning traces."""
        if self.type == InteractionType.CHAT_MESSAGE.value and self.response:
            # Include reasoning trace if available
            output = self.response
            if self.reasoning_trace and '<think>' not in output:
                output = f"<think>\n{self.reasoning_trace}\n</think>\n\n{output}"
            
            return {
                "instruction": self.content,
                "output": output,
                "model": self.model,
                "timestamp": self.timestamp,
                "session_id": self.session_id,
                "success": self.success,
                "reasoning_category": self.reasoning_category,
                "quality_score": self.quality_score,
                "has_reasoning": self.has_reasoning_trace(),
            }
        elif self.type == InteractionType.CODE_EDIT.value:
            return {
                "instruction": f"Edit code in {self.file_path}",
                "input": self.metadata.get("before", ""),
                "output": self.content,
                "language": self.language,
                "timestamp": self.timestamp,
                "reasoning_category": ReasoningCategory.CODE_GENERATION.value,
            }
        elif self.type == InteractionType.MODEL_ASSIST.value:
            return {
                "instruction": self.metadata.get("instruction", ""),
                "input": self.content,
                "output": self.response,
                "language": self.language,
                "timestamp": self.timestamp,
                "reasoning_category": self.reasoning_category or ReasoningCategory.GENERAL.value,
            }
        elif self.type == InteractionType.REASONING_TRACE.value:
            return {
                "instruction": self.content,
                "output": self.response,
                "reasoning_trace": self.reasoning_trace,
                "reasoning_category": self.reasoning_category,
                "reasoning_steps": self.reasoning_steps,
                "timestamp": self.timestamp,
                "quality_score": self.quality_score,
            }
        return None
    
    def to_persrm_format(self) -> Dict[str, Any]:
        """Convert to PersRM standalone training format with <think>/<answer> tags."""
        output = self.response or ""
        
        # Ensure response has reasoning structure
        if '<think>' not in output and self.reasoning_trace:
            output = f"<think>\n{self.reasoning_trace}\n</think>\n\n<answer>\n{output}\n</answer>"
        elif '<think>' not in output:
            # Generate minimal reasoning wrapper
            output = f"<think>\nAnalyzing the request and formulating response.\n</think>\n\n<answer>\n{output}\n</answer>"
        
        return {
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt_for_category()
                },
                {
                    "role": "user",
                    "content": self.content or ""
                },
                {
                    "role": "assistant",
                    "content": output
                }
            ],
            "metadata": {
                "reasoning_category": self.reasoning_category,
                "quality_score": self.quality_score,
                "timestamp": self.timestamp,
                "source": "chatos_interaction",
            }
        }
    
    def _get_system_prompt_for_category(self) -> str:
        """Get appropriate system prompt based on reasoning category."""
        prompts = {
            ReasoningCategory.UI_ANALYSIS.value: "You are PersRM, an expert UI/UX analyst. Analyze components for usability, accessibility, and best practices. Structure your response with <think>...</think> for reasoning and <answer>...</answer> for recommendations.",
            ReasoningCategory.CODE_GENERATION.value: "You are PersRM, an expert code generator. Write clean, accessible, well-typed code. Structure your response with <think>...</think> for planning and <answer>...</answer> for the code.",
            ReasoningCategory.ACCESSIBILITY.value: "You are PersRM, an accessibility expert. Identify WCAG violations and provide fixes. Structure your response with <think>...</think> for analysis and <answer>...</answer> for recommendations.",
            ReasoningCategory.DEBUG.value: "You are PersRM, a debugging expert. Systematically identify and fix issues. Structure your response with <think>...</think> for analysis and <answer>...</answer> for the solution.",
        }
        return prompts.get(
            self.reasoning_category,
            "You are PersRM, an AI reasoning assistant. Provide structured reasoning with <think>...</think> and conclusions with <answer>...</answer>."
        )


class InteractionLogger:
    """
    Logs all ChatOS interactions and forwards them to PersRM.
    
    Features:
    - Real-time logging of all user interactions
    - Batched forwarding to PersRM for efficiency
    - Local storage fallback when PersRM is unavailable
    - Training data generation from interactions
    """
    
    def __init__(
        self,
        persrm_url: Optional[str] = None,
        storage_dir: Optional[str] = None,
        batch_size: int = 10,
        flush_interval: float = 30.0,
        auto_forward: bool = True,
    ):
        """
        Initialize the interaction logger.
        
        Args:
            persrm_url: URL of the PersRM API (default: http://localhost:3001/api)
            storage_dir: Directory for local storage
            batch_size: Number of interactions to batch before forwarding
            flush_interval: Seconds between automatic flushes
            auto_forward: Whether to automatically forward to PersRM
        """
        self.persrm_url = persrm_url or os.environ.get(
            "PERSRM_API_URL", "http://localhost:3001/api"
        )
        self.storage_dir = Path(storage_dir or os.environ.get(
            "CHATOS_INTERACTION_LOG_DIR", 
            str(Path.home() / "ChatOS-Data" / "interactions")
        ))
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.auto_forward = auto_forward
        
        # Create storage directory
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Interaction buffer
        self._buffer: List[Interaction] = []
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "total_logged": 0,
            "total_forwarded": 0,
            "total_errors": 0,
            "last_flush": None,
        }
        
        # Session tracking
        self._current_session_id = self._generate_session_id()
        
        logger.info(f"InteractionLogger initialized (storage={self.storage_dir})")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:6]
        return f"session_{timestamp}_{hash_suffix}"
    
    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self._current_session_id
    
    def new_session(self) -> str:
        """Start a new session and return the session ID."""
        self._current_session_id = self._generate_session_id()
        # Log session start
        asyncio.create_task(self.log(
            InteractionType.SESSION_START,
            metadata={"session_id": self._current_session_id}
        ))
        return self._current_session_id
    
    async def log(
        self,
        interaction_type: Union[InteractionType, str],
        content: Optional[str] = None,
        response: Optional[str] = None,
        model: Optional[str] = None,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        execution_time: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Interaction:
        """
        Log an interaction.
        
        Args:
            interaction_type: Type of interaction
            content: Main content (user input, code, etc.)
            response: AI response or output
            model: Model used for generation
            file_path: File involved in the interaction
            language: Programming language
            command: Command executed
            exit_code: Exit code of command
            execution_time: Time taken for execution
            success: Whether the interaction was successful
            error_message: Error message if failed
            metadata: Additional metadata
            user_id: User identifier
            
        Returns:
            The logged interaction
        """
        # Convert enum to string if needed
        if isinstance(interaction_type, InteractionType):
            interaction_type = interaction_type.value
        
        interaction = Interaction(
            type=interaction_type,
            timestamp=time.time(),
            session_id=self._current_session_id,
            user_id=user_id,
            content=content,
            response=response,
            model=model,
            file_path=file_path,
            language=language,
            command=command,
            exit_code=exit_code,
            execution_time=execution_time,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )
        
        async with self._lock:
            self._buffer.append(interaction)
            self._stats["total_logged"] += 1
            
            # Auto-flush if buffer is full
            if len(self._buffer) >= self.batch_size:
                await self._flush()
        
        logger.debug(f"Logged {interaction_type}: {content[:50] if content else 'N/A'}...")
        return interaction
    
    async def log_chat(
        self,
        user_message: str,
        ai_response: str,
        model: str,
        **kwargs
    ) -> Interaction:
        """Log a chat interaction."""
        return await self.log(
            InteractionType.CHAT_MESSAGE,
            content=user_message,
            response=ai_response,
            model=model,
            **kwargs
        )
    
    async def log_code_edit(
        self,
        file_path: str,
        new_content: str,
        old_content: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> Interaction:
        """Log a code edit interaction."""
        # Detect language from file extension if not provided
        if not language:
            ext = Path(file_path).suffix.lower()
            language_map = {
                ".py": "python", ".js": "javascript", ".ts": "typescript",
                ".jsx": "jsx", ".tsx": "tsx", ".html": "html", ".css": "css",
                ".json": "json", ".md": "markdown", ".sh": "bash",
            }
            language = language_map.get(ext, "text")
        
        return await self.log(
            InteractionType.CODE_EDIT,
            content=new_content,
            file_path=file_path,
            language=language,
            metadata={"before": old_content} if old_content else {},
            **kwargs
        )
    
    async def log_command(
        self,
        command: str,
        output: str,
        exit_code: int,
        execution_time: float,
        cwd: Optional[str] = None,
        **kwargs
    ) -> Interaction:
        """Log a command execution."""
        return await self.log(
            InteractionType.COMMAND_EXECUTE,
            command=command,
            response=output,
            exit_code=exit_code,
            execution_time=execution_time,
            success=exit_code == 0,
            metadata={"cwd": cwd} if cwd else {},
            **kwargs
        )
    
    async def log_model_assist(
        self,
        instruction: str,
        code: str,
        response: str,
        language: str,
        model: str,
        file_path: Optional[str] = None,
        **kwargs
    ) -> Interaction:
        """Log a model assist request."""
        return await self.log(
            InteractionType.MODEL_ASSIST,
            content=code,
            response=response,
            model=model,
            language=language,
            file_path=file_path,
            metadata={"instruction": instruction},
            **kwargs
        )
    
    async def log_feedback(
        self,
        interaction_id: str,
        rating: Optional[str] = None,
        score: Optional[float] = None,
        comment: Optional[str] = None,
        **kwargs
    ) -> Interaction:
        """Log user feedback on an interaction."""
        return await self.log(
            InteractionType.FEEDBACK,
            content=comment,
            metadata={
                "interaction_id": interaction_id,
                "rating": rating,
                "score": score,
            },
            **kwargs
        )
    
    # =========================================================================
    # PersRM Reasoning Methods
    # =========================================================================
    
    async def log_reasoning(
        self,
        user_message: str,
        ai_response: str,
        model: str,
        reasoning_trace: Optional[str] = None,
        reasoning_category: Optional[str] = None,
        reasoning_steps: Optional[List[str]] = None,
        quality_score: float = 0.7,
        **kwargs
    ) -> Interaction:
        """
        Log a chat interaction with PersRM reasoning trace.
        
        Args:
            user_message: The user's input
            ai_response: The AI's response
            model: Model used for generation
            reasoning_trace: The chain-of-thought reasoning (extracted or provided)
            reasoning_category: Category of reasoning (ui_analysis, code_generation, etc.)
            reasoning_steps: List of individual reasoning steps
            quality_score: Quality score for training data filtering (0-1)
        
        Returns:
            The logged interaction with reasoning data
        """
        # Auto-detect reasoning category if not provided
        if not reasoning_category:
            reasoning_category = self._classify_reasoning(user_message)
        
        # Auto-extract reasoning trace from response if not provided
        if not reasoning_trace and ai_response:
            reasoning_trace = self._extract_reasoning_from_response(ai_response)
        
        # Convert enum to string if needed
        if isinstance(reasoning_category, ReasoningCategory):
            reasoning_category = reasoning_category.value
        
        interaction = Interaction(
            type=InteractionType.REASONING_TRACE.value,
            timestamp=time.time(),
            session_id=self._current_session_id,
            user_id=kwargs.get("user_id", "default"),
            content=user_message,
            response=ai_response,
            model=model,
            reasoning_trace=reasoning_trace,
            reasoning_category=reasoning_category,
            reasoning_steps=reasoning_steps,
            quality_score=quality_score,
            metadata=kwargs.get("metadata", {}),
            success=kwargs.get("success", True),
        )
        
        async with self._lock:
            self._buffer.append(interaction)
            self._stats["total_logged"] += 1
            self._stats["reasoning_logged"] = self._stats.get("reasoning_logged", 0) + 1
            
            if len(self._buffer) >= self.batch_size:
                await self._flush()
        
        logger.debug(f"Logged reasoning ({reasoning_category}): {user_message[:50]}...")
        return interaction
    
    async def log_chat_with_reasoning(
        self,
        user_message: str,
        ai_response: str,
        model: str,
        **kwargs
    ) -> Interaction:
        """
        Log a chat message and auto-extract reasoning traces.
        Convenience wrapper for log_reasoning that auto-extracts.
        """
        return await self.log_reasoning(
            user_message=user_message,
            ai_response=ai_response,
            model=model,
            **kwargs
        )
    
    def _classify_reasoning(self, text: str) -> str:
        """Classify the reasoning category based on text content."""
        text_lower = text.lower()
        
        # UI/Component analysis
        if any(kw in text_lower for kw in ["button", "input", "component", "modal", "card", "form", "ui"]):
            return ReasoningCategory.UI_ANALYSIS.value
        
        # Accessibility
        if any(kw in text_lower for kw in ["accessibility", "wcag", "aria", "screen reader", "a11y"]):
            return ReasoningCategory.ACCESSIBILITY.value
        
        # Code generation
        if any(kw in text_lower for kw in ["create", "generate", "build", "implement", "write code", "component"]):
            return ReasoningCategory.CODE_GENERATION.value
        
        # Layout
        if any(kw in text_lower for kw in ["layout", "grid", "flexbox", "responsive", "spacing"]):
            return ReasoningCategory.LAYOUT_DESIGN.value
        
        # Debug
        if any(kw in text_lower for kw in ["debug", "fix", "error", "bug", "issue", "not working"]):
            return ReasoningCategory.DEBUG.value
        
        # Refactor
        if any(kw in text_lower for kw in ["refactor", "clean up", "improve code", "optimize"]):
            return ReasoningCategory.REFACTOR.value
        
        # UX
        if any(kw in text_lower for kw in ["user experience", "usability", "ux", "user flow"]):
            return ReasoningCategory.UX_REASONING.value
        
        return ReasoningCategory.GENERAL.value
    
    def _extract_reasoning_from_response(self, response: str) -> Optional[str]:
        """Extract reasoning trace from response with <think> tags."""
        import re
        match = re.search(r'<think>(.*?)</think>', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    async def rate_interaction(
        self,
        interaction: Interaction,
        thumbs_up: bool,
        feedback: Optional[str] = None,
    ) -> None:
        """
        Rate an interaction for quality scoring.
        
        Args:
            interaction: The interaction to rate
            thumbs_up: True for positive, False for negative
            feedback: Optional feedback text
        """
        # Update quality score
        if thumbs_up:
            interaction.quality_score = min(1.0, interaction.quality_score + 0.2)
        else:
            interaction.quality_score = max(0.0, interaction.quality_score - 0.3)
        
        # Log the feedback
        await self.log_feedback(
            interaction_id=f"{interaction.session_id}_{interaction.timestamp}",
            rating="positive" if thumbs_up else "negative",
            score=interaction.quality_score,
            comment=feedback,
        )
    
    async def _flush(self) -> int:
        """
        Flush the buffer to storage and optionally forward to PersRM.
        
        Returns:
            Number of interactions flushed
        """
        if not self._buffer:
            return 0
        
        # Take the current buffer
        to_flush = self._buffer.copy()
        self._buffer.clear()
        
        count = len(to_flush)
        
        # Save to local storage
        await self._save_to_local(to_flush)
        
        # Forward to PersRM if enabled
        if self.auto_forward:
            success = await self._forward_to_persrm(to_flush)
            if success:
                self._stats["total_forwarded"] += count
        
        self._stats["last_flush"] = time.time()
        logger.info(f"Flushed {count} interactions")
        
        return count
    
    async def _save_to_local(self, interactions: List[Interaction]) -> bool:
        """Save interactions to local storage."""
        try:
            # Group by date for organized storage
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = self.storage_dir / f"interactions_{date_str}.jsonl"
            
            with open(log_file, "a") as f:
                for interaction in interactions:
                    f.write(json.dumps(interaction.to_dict()) + "\n")
            
            return True
        except Exception as e:
            logger.error(f"Failed to save to local storage: {e}")
            self._stats["total_errors"] += 1
            return False
    
    async def _forward_to_persrm(self, interactions: List[Interaction]) -> bool:
        """Forward interactions to PersRM."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Send to PersRM's interaction ingestion endpoint
                response = await client.post(
                    f"{self.persrm_url}/interactions/ingest",
                    json={
                        "source": "chatos",
                        "session_id": self._current_session_id,
                        "interactions": [i.to_dict() for i in interactions],
                    }
                )
                
                if response.status_code == 200:
                    logger.debug(f"Forwarded {len(interactions)} interactions to PersRM")
                    return True
                else:
                    logger.warning(f"PersRM returned {response.status_code}")
                    return False
                    
        except httpx.ConnectError:
            logger.debug("PersRM not available, storing locally only")
            return False
        except Exception as e:
            logger.error(f"Failed to forward to PersRM: {e}")
            self._stats["total_errors"] += 1
            return False
    
    async def flush(self) -> int:
        """Manually flush the buffer."""
        async with self._lock:
            return await self._flush()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            **self._stats,
            "buffer_size": len(self._buffer),
            "session_id": self._current_session_id,
        }
    
    async def export_training_data(
        self,
        output_path: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        Export interactions as training data.
        
        Args:
            output_path: Path for output file
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            
        Returns:
            Path to the exported file
        """
        output_path = output_path or str(
            self.storage_dir / f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        
        training_data = []
        
        # Read from local storage
        for log_file in sorted(self.storage_dir.glob("interactions_*.jsonl")):
            # Filter by date if specified
            file_date = log_file.stem.split("_")[1]
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue
            
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        interaction = Interaction(**data)
                        training_format = interaction.to_training_format()
                        if training_format:
                            training_data.append(training_format)
                    except Exception as e:
                        logger.warning(f"Failed to parse interaction: {e}")
        
        # Write training data
        with open(output_path, "w") as f:
            for item in training_data:
                f.write(json.dumps(item) + "\n")
        
        logger.info(f"Exported {len(training_data)} training examples to {output_path}")
        return output_path
    
    async def export_persrm_training_data(
        self,
        output_path: Optional[str] = None,
        min_quality: float = 0.5,
        include_reasoning_only: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export interactions as PersRM standalone training data with reasoning traces.
        
        Args:
            output_path: Path for output file
            min_quality: Minimum quality score to include (0-1)
            include_reasoning_only: If True, only export interactions with reasoning traces
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            
        Returns:
            Dict with path and statistics
        """
        output_path = output_path or str(
            self.storage_dir / f"persrm_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        
        training_data = []
        stats = {
            "total_processed": 0,
            "exported": 0,
            "filtered_quality": 0,
            "filtered_no_reasoning": 0,
            "by_category": {},
        }
        
        # Read from local storage
        for log_file in sorted(self.storage_dir.glob("interactions_*.jsonl")):
            # Filter by date if specified
            file_date = log_file.stem.split("_")[1]
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue
            
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        stats["total_processed"] += 1
                        
                        # Reconstruct interaction
                        interaction = Interaction(
                            type=data.get("type", "chat_message"),
                            timestamp=data.get("timestamp", 0),
                            session_id=data.get("session_id"),
                            content=data.get("content"),
                            response=data.get("response"),
                            model=data.get("model"),
                            reasoning_trace=data.get("reasoning_trace"),
                            reasoning_category=data.get("reasoning_category"),
                            quality_score=data.get("quality_score", 0.7),
                            metadata=data.get("metadata", {}),
                        )
                        
                        # Filter by quality
                        if interaction.quality_score < min_quality:
                            stats["filtered_quality"] += 1
                            continue
                        
                        # Filter by reasoning if requested
                        if include_reasoning_only and not interaction.has_reasoning_trace():
                            stats["filtered_no_reasoning"] += 1
                            continue
                        
                        # Only include chat-type interactions
                        if interaction.type not in [
                            InteractionType.CHAT_MESSAGE.value,
                            InteractionType.REASONING_TRACE.value,
                            InteractionType.MODEL_ASSIST.value,
                        ]:
                            continue
                        
                        # Skip if no content/response
                        if not interaction.content or not interaction.response:
                            continue
                        
                        # Convert to PersRM format
                        persrm_data = interaction.to_persrm_format()
                        training_data.append(persrm_data)
                        
                        # Track category stats
                        cat = interaction.reasoning_category or "general"
                        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
                        stats["exported"] += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse interaction: {e}")
        
        # Write training data
        with open(output_path, "w") as f:
            for item in training_data:
                f.write(json.dumps(item) + "\n")
        
        stats["output_path"] = output_path
        logger.info(f"Exported {stats['exported']} PersRM training examples to {output_path}")
        
        return stats
    
    def get_reasoning_stats(self) -> Dict[str, Any]:
        """Get statistics about logged reasoning interactions."""
        stats = {
            "total_logged": self._stats.get("total_logged", 0),
            "reasoning_logged": self._stats.get("reasoning_logged", 0),
            "forwarded": self._stats.get("total_forwarded", 0),
            "buffer_size": len(self._buffer),
            "session_id": self._current_session_id,
        }
        return stats


# Global logger instance
_interaction_logger: Optional[InteractionLogger] = None


def get_interaction_logger() -> InteractionLogger:
    """Get or create the global interaction logger."""
    global _interaction_logger
    if _interaction_logger is None:
        _interaction_logger = InteractionLogger()
    return _interaction_logger


async def init_interaction_logger(**kwargs) -> InteractionLogger:
    """Initialize the global interaction logger with custom settings."""
    global _interaction_logger
    _interaction_logger = InteractionLogger(**kwargs)
    return _interaction_logger

