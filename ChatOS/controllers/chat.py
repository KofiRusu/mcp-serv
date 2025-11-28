"""
chat.py - Orchestrates the conversation between user and multiple models.

This module implements the "council of bots" pattern and integrates
special command modes: /research, /deepthinking, /swarm

Enhanced with memory logging for continuous model improvement.
"""

import random
import time
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
from .memory_logger import get_memory_logger, InteractionQuality
from .llm_client import get_model_council, get_llm_client
from .model_config import get_model_config_manager, ModelProvider


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
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a chat turn with the model council or a specific model.
    
    This handles both normal chat and special /commands.
    If model_id is provided, only that specific model will be used.
    """
    # Parse for commands
    processor = get_command_processor()
    parsed = processor.parse(message)
    
    # Handle special commands
    if parsed.is_command:
        return await _handle_command(parsed, session_id, model_id)
    
    # Normal chat flow
    return await _normal_chat(message, mode, use_rag, session_id, model_id)


async def _normal_chat(
    message: str,
    mode: str,
    use_rag: bool,
    session_id: Optional[str],
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle normal chat messages with memory logging and real LLM support.
    
    If model_id is provided, only that specific model will be used instead of the council.
    """
    rag = _get_rag()
    memory = get_memory(session_id)
    logger = get_memory_logger()
    config_mgr = get_model_config_manager()
    
    # Start logging this conversation
    conv_id = logger.start_conversation(mode=mode, rag_enabled=use_rag)
    logger.log_user_message(conv_id, message)
    
    start_time = time.time()
    
    # Build RAG context if enabled
    rag_context = ""
    if use_rag:
        rag_context = rag.retrieve(message)
        if rag_context:
            logger.log_rag_context(conv_id, rag_context)
    
    # Check if a specific model was requested
    if model_id:
        # Use specific model only
        specific_model = config_mgr.get_model(model_id)
        if specific_model and specific_model.provider != ModelProvider.DUMMY:
            result = await _chat_with_real_models(message, mode, rag_context, memory, [specific_model], logger, conv_id)
        elif specific_model:
            # It's a dummy model
            result = await _chat_with_dummy_models(message, mode, rag_context, memory, logger, conv_id, specific_model_name=specific_model.name)
        else:
            # Model not found, fall back to council
            all_models = config_mgr.list_models(enabled_only=True, council_only=True)
            real_models = [m for m in all_models if m.provider != ModelProvider.DUMMY]
            if real_models:
                result = await _chat_with_real_models(message, mode, rag_context, memory, real_models, logger, conv_id)
            else:
                result = await _chat_with_dummy_models(message, mode, rag_context, memory, logger, conv_id)
    else:
        # Use council (multiple models)
        all_models = config_mgr.list_models(enabled_only=True, council_only=True)
        real_models = [m for m in all_models if m.provider != ModelProvider.DUMMY]
        
        if real_models:
            # Use real LLM models via the model council
            result = await _chat_with_real_models(message, mode, rag_context, memory, real_models, logger, conv_id)
        else:
            # Fall back to dummy models
            result = await _chat_with_dummy_models(message, mode, rag_context, memory, logger, conv_id)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Log the assistant response
    logger.log_assistant_response(
        conv_id,
        result["answer"],
        model=result["chosen_model"],
        latency_ms=latency_ms,
        council_responses=result["responses"],
    )
    
    # Update memory
    memory.add_turn(message, result["answer"])
    
    # End conversation logging (saves to disk)
    logger.end_conversation(conv_id)
    
    return {
        "answer": result["answer"],
        "chosen_model": result["chosen_model"],
        "responses": result["responses"],
        "memory_summary": memory.get_summary(),
        "mode": mode,
        "command": None,
        "conversation_id": conv_id,
    }


async def _chat_with_real_models(
    message: str,
    mode: str,
    rag_context: str,
    memory: ChatMemory,
    models: list,
    logger,
    conv_id: str,
) -> Dict[str, Any]:
    """Chat using real LLM models (Ollama/Qwen)."""
    import httpx
    
    # Build messages for chat
    messages = []
    
    # System prompt based on mode
    if mode == "code":
        system_prompt = "You are a helpful coding assistant. Provide clear, well-commented code with explanations."
    else:
        system_prompt = "You are a helpful AI assistant. Provide clear, informative responses."
    
    # Add conversation history to system prompt
    history = memory.get_context()
    if history:
        system_prompt += f"\n\nPrevious conversation:\n{history}"
    
    # Add RAG context to system prompt
    if rag_context:
        system_prompt += f"\n\nRelevant information:\n{rag_context}"
    
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": message})
    
    # Query models directly via Ollama API for reliability
    responses = []
    
    # Use very long timeouts for LLM responses (Ollama can be slow especially on first query)
    # read timeout is critical - LLM inference can take 30-60+ seconds
    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for model_config in models:
            try:
                if model_config.provider == ModelProvider.OLLAMA:
                    # Direct Ollama API call
                    base_url = model_config.base_url or "http://localhost:11434"
                    
                    # Convert messages to prompt
                    prompt = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
                    
                    resp = await client.post(
                        f"{base_url}/api/generate",
                        json={
                            "model": model_config.model_id,
                            "prompt": prompt,
                            "options": {
                                "temperature": model_config.temperature,
                                "num_predict": model_config.max_tokens,
                            },
                            "stream": False,
                        },
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        responses.append({
                            "model": model_config.name,
                            "text": data.get("response", "").strip(),
                        })
                    else:
                        responses.append({
                            "model": model_config.name,
                            "text": f"[Error: HTTP {resp.status_code}]",
                        })
                        logger.log_error(conv_id, f"Model {model_config.name}: HTTP {resp.status_code}")
                else:
                    # Skip non-Ollama models for now
                    responses.append({
                        "model": model_config.name,
                        "text": f"[Error: Provider {model_config.provider.value} not supported yet]",
                    })
                    
            except Exception as e:
                import traceback
                error_msg = str(e) or repr(e) or "Unknown error"
                print(f"⚠️ Chat error for {model_config.name}: {error_msg}")
                print(f"⚠️ Traceback: {traceback.format_exc()}")
                responses.append({
                    "model": model_config.name,
                    "text": f"[Error: {error_msg}]",
                })
                logger.log_error(conv_id, f"Model {model_config.name}: {error_msg}")
    
    # Select best response (longest non-error)
    valid_responses = [r for r in responses if not r["text"].startswith("[Error")]
    
    if valid_responses:
        chosen = max(valid_responses, key=lambda x: len(x["text"]))
    elif responses:
        chosen = responses[0]
    else:
        chosen = {"model": "System", "text": "No models available to respond."}
    
    return {
        "answer": chosen["text"],
        "chosen_model": chosen["model"],
        "responses": responses,
    }


async def _chat_with_dummy_models(
    message: str,
    mode: str,
    rag_context: str,
    memory: ChatMemory,
    logger,
    conv_id: str,
    specific_model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Fall back to dummy models.
    
    If specific_model_name is provided, only that model will be queried.
    """
    models = _get_models()
    voter = _get_voter()
    
    # Build prompt
    prompt = _build_prompt(message, mode, bool(rag_context), memory, _get_rag())
    
    # Query dummy models
    responses: List[Tuple[str, str]] = []
    
    if specific_model_name:
        # Use only the specific model
        model = models.get(specific_model_name)
        if model:
            try:
                resp = model.generate(prompt, mode=mode)
            except Exception as exc:
                resp = f"Error from {specific_model_name}: {exc}"
                logger.log_error(conv_id, f"Model {specific_model_name}: {exc}")
            responses.append((specific_model_name, resp))
    else:
        # Query all dummy models
        for name, model in models.items():
            try:
                resp = model.generate(prompt, mode=mode)
            except Exception as exc:
                resp = f"Error from {name}: {exc}"
                logger.log_error(conv_id, f"Model {name}: {exc}")
            responses.append((name, resp))
    
    # Vote (or just return single response if specific model)
    if specific_model_name and responses:
        chosen_name, chosen_answer = responses[0]
    else:
        chosen_name, chosen_answer = voter.vote(responses)
    
    return {
        "answer": chosen_answer,
        "chosen_model": chosen_name,
        "responses": [{"model": name, "text": text} for name, text in responses],
    }


async def _handle_command(
    parsed: ParsedCommand,
    session_id: Optional[str],
    model_id: Optional[str] = None,
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
        return await _normal_chat(parsed.query, "code", True, session_id, model_id)
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
