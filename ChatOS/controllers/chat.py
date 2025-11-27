"""
chat.py - Orchestrates the conversation between user and multiple models.

This module implements the "council of bots" pattern and integrates
special command modes: /research, /deepthinking, /swarm
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from ChatOS.config import COUNCIL_STRATEGY, DATA_DIR, COMMAND_MODES
from ChatOS.models.loader import load_models
from ChatOS.utils.memory import ChatMemory, get_memory
from ChatOS.utils.rag import RagEngine

from .commands import CommandProcessor, ParsedCommand, get_command_processor
from .research import ResearchEngine, get_research_engine
from .deepthinking import DeepThinkingEngine, get_deepthinking_engine
from .swarm import SwarmCoordinator, get_swarm_coordinator


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
            return responses[0]
        
        if self.strategy == "longest":
            return max(valid_responses, key=lambda x: len(x[1]))
        elif self.strategy == "shortest":
            return min(valid_responses, key=lambda x: len(x[1]))
        elif self.strategy == "random":
            return random.choice(valid_responses)
        elif self.strategy == "first":
            return valid_responses[0]
        
        return valid_responses[0]


# =============================================================================
# Global instances (loaded once at module import)
# =============================================================================

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
    
    This handles both normal chat and special /commands.
    """
    # Parse for commands
    processor = get_command_processor()
    parsed = processor.parse(message)
    
    # Handle special commands
    if parsed.is_command:
        return await _handle_command(parsed, session_id)
    
    # Normal chat flow
    return await _normal_chat(message, mode, use_rag, session_id)


async def _normal_chat(
    message: str,
    mode: str,
    use_rag: bool,
    session_id: Optional[str],
) -> Dict[str, Any]:
    """Handle normal chat messages."""
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
    
    # Update memory
    memory.add_turn(message, chosen_answer)
    
    return {
        "answer": chosen_answer,
        "chosen_model": chosen_name,
        "responses": [
            {"model": name, "text": text}
            for name, text in responses
        ],
        "memory_summary": memory.get_summary(),
        "mode": mode,
        "command": None,
    }


async def _handle_command(
    parsed: ParsedCommand,
    session_id: Optional[str],
) -> Dict[str, Any]:
    """Handle special /commands."""
    memory = get_memory(session_id)
    
    if parsed.command == "research":
        return await _handle_research(parsed, memory)
    elif parsed.command == "deepthinking":
        return await _handle_deepthinking(parsed, memory)
    elif parsed.command == "swarm":
        return await _handle_swarm(parsed, memory)
    elif parsed.command == "code":
        # Code mode uses normal chat with code mode
        return await _normal_chat(parsed.query, "code", True, session_id)
    else:
        return {
            "answer": f"Unknown command: /{parsed.command}",
            "chosen_model": "System",
            "responses": [],
            "memory_summary": memory.get_summary(),
            "mode": "normal",
            "command": parsed.command,
        }


async def _handle_research(
    parsed: ParsedCommand,
    memory: ChatMemory,
) -> Dict[str, Any]:
    """Handle /research command."""
    engine = get_research_engine()
    
    # Perform research
    depth = int(parsed.args.get("depth", "1"))
    context = await engine.research(parsed.query, depth=depth)
    
    # Build response
    answer = f"""## 🔬 Research Results

{context.synthesis}

### Sources ({len(context.sources)} found)

"""
    for i, source in enumerate(context.sources[:5], 1):
        answer += f"{i}. **[{source.domain}]** {source.title}\n"
        answer += f"   {source.snippet[:150]}...\n\n"
    
    # Update memory
    memory.add_turn(f"/research {parsed.query}", answer[:200] + "...")
    
    return {
        "answer": answer,
        "chosen_model": "Research Engine",
        "responses": [{
            "model": "Research Engine",
            "text": answer,
        }],
        "memory_summary": memory.get_summary(),
        "mode": "research",
        "command": "research",
        "research_context": context.to_dict(),
    }


async def _handle_deepthinking(
    parsed: ParsedCommand,
    memory: ChatMemory,
) -> Dict[str, Any]:
    """Handle /deepthinking command."""
    engine = get_deepthinking_engine()
    
    # Perform deep thinking
    thought = await engine.think(parsed.query)
    
    # Format response
    answer = engine.format_for_display(thought)
    
    # Update memory
    memory.add_turn(f"/deepthinking {parsed.query}", thought.final_answer[:200] + "...")
    
    return {
        "answer": answer,
        "chosen_model": "Deep Thinking Engine",
        "responses": [{
            "model": f"Phase: {step.phase}",
            "text": step.content,
        } for step in thought.thoughts],
        "memory_summary": memory.get_summary(),
        "mode": "deepthinking",
        "command": "deepthinking",
        "thinking_result": thought.to_dict(),
    }


async def _handle_swarm(
    parsed: ParsedCommand,
    memory: ChatMemory,
) -> Dict[str, Any]:
    """Handle /swarm command."""
    coordinator = get_swarm_coordinator()
    
    # Execute swarm
    result = await coordinator.execute(parsed.query)
    
    # Format response
    answer = coordinator.format_result(result)
    
    # Update memory
    memory.add_turn(f"/swarm {parsed.query}", f"Swarm completed with {len(result.responses)} agents")
    
    return {
        "answer": answer,
        "chosen_model": "Swarm Coordinator",
        "responses": [{
            "model": f"{r.agent_name} ({r.agent_role})",
            "text": r.content,
        } for r in result.responses],
        "memory_summary": memory.get_summary(),
        "mode": "swarm",
        "command": "swarm",
        "swarm_result": result.to_dict(),
    }


def _build_prompt(
    message: str,
    mode: str,
    use_rag: bool,
    memory: ChatMemory,
    rag: RagEngine,
) -> str:
    """Build the full prompt including context, memory, and user message."""
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
    """Get information about the current council configuration."""
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
        "available_commands": list(COMMAND_MODES.keys()),
    }


def get_available_commands() -> Dict[str, Any]:
    """Get information about available commands."""
    return COMMAND_MODES
