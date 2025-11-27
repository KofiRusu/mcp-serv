"""
chat.py - Orchestrates the conversation between user and multiple models.

This module implements the "council of bots" pattern:
1. Load multiple models at startup
2. For each user message, query all models
3. Use a voting/selection strategy to pick the best response
4. Maintain conversation memory and RAG context
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from ChatOS.config import COUNCIL_STRATEGY, DATA_DIR
from ChatOS.models.loader import load_models
from ChatOS.utils.memory import ChatMemory, get_memory
from ChatOS.utils.rag import RagEngine


# =============================================================================
# Council Voter - Selects the best response from multiple models
# =============================================================================

@dataclass
class CouncilVoter:
    """
    Implements voting/selection strategies for the model council.
    
    The council queries multiple models and this class determines
    which response to present as the "chosen" answer.
    """
    
    strategy: Literal["longest", "shortest", "random", "first"] = COUNCIL_STRATEGY

    def vote(self, responses: List[Tuple[str, str]]) -> Tuple[str, str]:
        """
        Select the best response from the council.
        
        Args:
            responses: List of (model_name, response_text) tuples
            
        Returns:
            Tuple of (chosen_model_name, chosen_response)
        """
        if not responses:
            return ("", "I apologize, but I couldn't generate a response.")
        
        # Filter out empty or error responses
        valid_responses = [
            (name, text) for name, text in responses 
            if text and not text.startswith("Error")
        ]
        
        if not valid_responses:
            # Fall back to first response even if it's an error
            return responses[0]
        
        if self.strategy == "longest":
            return max(valid_responses, key=lambda x: len(x[1]))
        
        elif self.strategy == "shortest":
            return min(valid_responses, key=lambda x: len(x[1]))
        
        elif self.strategy == "random":
            return random.choice(valid_responses)
        
        elif self.strategy == "first":
            return valid_responses[0]
        
        # Default fallback
        return valid_responses[0]

    def score_response(self, text: str) -> float:
        """
        Calculate a quality score for a response.
        
        This is a placeholder for more sophisticated scoring.
        Could incorporate:
        - Response length (not too short, not too long)
        - Coherence metrics
        - Relevance to query
        - Grammar/spelling
        
        Args:
            text: The response text to score
            
        Returns:
            A quality score between 0.0 and 1.0
        """
        if not text:
            return 0.0
        
        # Simple heuristic: prefer medium-length responses
        length = len(text)
        if length < 10:
            return 0.1
        elif length < 50:
            return 0.5
        elif length < 500:
            return 1.0
        elif length < 1000:
            return 0.8
        else:
            return 0.6


# =============================================================================
# Global instances (loaded once at module import)
# =============================================================================

# Load models once at startup
_models: Optional[Dict[str, Any]] = None
_rag: Optional[RagEngine] = None
_voter: Optional[CouncilVoter] = None


def _get_models() -> Dict[str, Any]:
    """Lazy-load models on first use."""
    global _models
    if _models is None:
        _models = load_models()
    return _models


def _get_rag() -> RagEngine:
    """Lazy-load RAG engine on first use."""
    global _rag
    if _rag is None:
        _rag = RagEngine(data_dir=DATA_DIR)
    return _rag


def _get_voter() -> CouncilVoter:
    """Lazy-load voter on first use."""
    global _voter
    if _voter is None:
        _voter = CouncilVoter()
    return _voter


# =============================================================================
# Main Chat Endpoint
# =============================================================================

async def chat_endpoint(
    message: str,
    mode: str = "normal",
    use_rag: bool = True,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a chat turn with the model council.
    
    This is the main entry point for chat interactions. It:
    1. Retrieves conversation memory and RAG context
    2. Builds the prompt for all models
    3. Queries each model in the council
    4. Uses the voter to select the best response
    5. Updates conversation memory
    
    Args:
        message: The user's message
        mode: Chat mode - "normal" or "code"
        use_rag: Whether to include RAG context
        session_id: Optional session identifier for memory
        
    Returns:
        Dictionary containing:
        - answer: The selected response
        - chosen_model: Name of the model that gave the chosen response
        - responses: List of all model responses
        - memory_summary: Brief summary of conversation state
    """
    models = _get_models()
    rag = _get_rag()
    voter = _get_voter()
    memory = get_memory(session_id)
    
    # Build the prompt with context
    prompt = _build_prompt(message, mode, use_rag, memory, rag)
    
    # Query all models
    responses: List[Tuple[str, str]] = []
    
    for name, model in models.items():
        try:
            resp = model.generate(prompt, mode=mode)
        except Exception as exc:
            resp = f"Error from {name}: {exc}"
        responses.append((name, resp))
    
    # Vote on the best response
    chosen_name, chosen_answer = voter.vote(responses)
    
    # Update memory with this turn
    memory.add_turn(message, chosen_answer)
    
    # Format response for API
    return {
        "answer": chosen_answer,
        "chosen_model": chosen_name,
        "responses": [
            {"model": name, "text": text}
            for name, text in responses
        ],
        "memory_summary": memory.get_summary(),
    }


def _build_prompt(
    message: str,
    mode: str,
    use_rag: bool,
    memory: ChatMemory,
    rag: RagEngine,
) -> str:
    """
    Build the full prompt including context, memory, and user message.
    
    Args:
        message: The user's current message
        mode: Chat mode for instruction tuning
        use_rag: Whether to include RAG context
        memory: The conversation memory
        rag: The RAG engine
        
    Returns:
        Formatted prompt string
    """
    parts = []
    
    # System instruction based on mode
    if mode == "code":
        parts.append(
            "You are a helpful coding assistant. Provide clear, "
            "well-commented code solutions with brief explanations."
        )
    else:
        parts.append(
            "You are a helpful AI assistant. Provide clear, "
            "informative responses."
        )
    
    # Add conversation history
    context = memory.get_context()
    if context:
        parts.append(f"Previous conversation:\n{context}")
    
    # Add RAG context if enabled
    if use_rag:
        retrieved = rag.retrieve(message)
        if retrieved:
            parts.append(f"Relevant information:\n{retrieved}")
    
    # Add the current user message
    parts.append(f"User: {message}")
    
    return "\n\n".join(parts)


def get_council_info() -> Dict[str, Any]:
    """
    Get information about the current council configuration.
    
    Returns:
        Dictionary with model names, voter strategy, and RAG status
    """
    models = _get_models()
    rag = _get_rag()
    voter = _get_voter()
    
    return {
        "models": [
            {
                "name": name,
                "behavior": getattr(model, "behavior", "unknown"),
            }
            for name, model in models.items()
        ],
        "strategy": voter.strategy,
        "rag_documents": len(rag),
    }

