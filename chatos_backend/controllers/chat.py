"""
chat.py - Orchestrates the conversation between user and multiple models.

This module implements the "council of bots" pattern and integrates
special command modes: /research, /deepthinking, /swarm

Enhanced with memory logging for continuous model improvement.
Enhanced with AI Project system prompt integration.
"""

import asyncio
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Tuple

from chatos_backend.config import COUNCIL_STRATEGY, DATA_DIR, COMMAND_MODES
from chatos_backend.models.loader import load_models
from chatos_backend.utils.memory import ChatMemory, get_memory
from chatos_backend.utils.rag import RagEngine

from .commands import CommandProcessor, ParsedCommand, get_command_processor
from .research import ResearchEngine, get_research_engine
from .deepthinking import DeepThinkingEngine, get_deepthinking_engine
from .swarm import SwarmCoordinator, get_swarm_coordinator
from .memory_logger import get_memory_logger, InteractionQuality
from .llm_client import get_model_council, get_llm_client
from .interaction_logger import get_interaction_logger
from .model_config import get_model_config_manager, ModelProvider
from .project_memory import get_project_memory_manager
from .projects import get_project_manager
from .reasoning import handle_reason_command, format_reasoning_response

# AI Projects integration
from chatos_backend.projects import get_ai_project_store, AIProject


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


def _is_test_mode() -> bool:
    """Return True when tests should bypass real LLM calls."""
    value = os.getenv("CHATOS_TEST_MODE", "")
    return value.lower() in {"1", "true", "yes", "on"}


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
    ai_project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a chat turn with the model council or a specific model.
    
    This handles both normal chat and special /commands.
    If model_id is provided, only that specific model will be used.
    If ai_project_id is provided, the project's system prompt and settings are applied.
    
    Args:
        message: User message
        mode: Chat mode (normal, code, etc.)
        use_rag: Whether to include RAG context
        session_id: Session identifier for memory
        model_id: Specific model to use (bypasses council)
        ai_project_id: AI project ID for system prompt presets
    """
    # Load AI project if specified
    ai_project: Optional[AIProject] = None
    if ai_project_id:
        store = get_ai_project_store()
        ai_project = store.get_project(ai_project_id)
        
        # Apply project settings if no explicit overrides
        if ai_project:
            # Use project's RAG setting if not explicitly set
            use_rag = ai_project.rag_enabled
            # Use project's code mode if enabled
            if ai_project.code_mode:
                mode = "code"
            # Use project's default model if no model_id specified
            if not model_id and ai_project.default_model_id:
                model_id = ai_project.default_model_id
    
    # Parse for commands
    processor = get_command_processor()
    parsed = processor.parse(message)
    
    # Handle special commands
    if parsed.is_command:
        return await _handle_command(parsed, session_id, model_id, ai_project)
    
    # Normal chat flow
    return await _normal_chat(message, mode, use_rag, session_id, model_id, ai_project)


async def _normal_chat(
    message: str,
    mode: str,
    use_rag: bool,
    session_id: Optional[str],
    model_id: Optional[str] = None,
    ai_project: Optional[AIProject] = None,
) -> Dict[str, Any]:
    """Handle normal chat messages with memory logging and real LLM support.
    
    If model_id is provided, only that specific model will be used instead of the council.
    If ai_project is provided, its system prompt and settings are applied.
    
    Performance: Uses parallel execution for independent operations (RAG, project files).
    """
    rag = _get_rag()
    memory = get_memory(session_id)
    logger = get_memory_logger()
    config_mgr = get_model_config_manager()
    test_mode = _is_test_mode()
    
    # Start logging this conversation
    conv_id = logger.start_conversation(mode=mode, rag_enabled=use_rag)
    logger.log_user_message(conv_id, message)
    
    start_time = time.time()
    
    rag_context = await _collect_combined_context(
        message,
        use_rag,
        ai_project,
        rag,
        logger,
        conv_id,
    )
    
    # Build AI project system prompt if present
    project_system_prompt = ""
    project_temperature = None
    if ai_project:
        project_system_prompt = ai_project.system_prompt or ""
        project_temperature = ai_project.default_temperature
    
    # Check if a specific model was requested
    if model_id:
        # Use specific model only
        specific_model = config_mgr.get_model(model_id)
        if specific_model and specific_model.provider != ModelProvider.DUMMY:
            if test_mode:
                result = await _chat_with_dummy_models(
                    message,
                    mode,
                    rag_context,
                    memory,
                    logger,
                    conv_id,
                    specific_model_name=specific_model.name,
                    project_system_prompt=project_system_prompt,
                )
            else:
                result = await _chat_with_real_models(
                    message,
                    mode,
                    rag_context,
                    memory,
                    [specific_model],
                    logger,
                    conv_id,
                    project_system_prompt=project_system_prompt,
                    project_temperature=project_temperature,
                )
        elif specific_model:
            # It's a dummy model
            result = await _chat_with_dummy_models(
                message, mode, rag_context, memory, logger, conv_id,
                specific_model_name=specific_model.name,
                project_system_prompt=project_system_prompt,
            )
        else:
            # Model not found, fall back to council
            all_models = config_mgr.list_models(enabled_only=True, council_only=True)
            real_models = [m for m in all_models if m.provider != ModelProvider.DUMMY]
            if real_models:
                result = await _chat_with_real_models(
                    message, mode, rag_context, memory, real_models, logger, conv_id,
                    project_system_prompt=project_system_prompt,
                    project_temperature=project_temperature,
                )
            else:
                result = await _chat_with_dummy_models(
                    message, mode, rag_context, memory, logger, conv_id,
                    project_system_prompt=project_system_prompt,
                )
    else:
        # Use council (multiple models)
        all_models = config_mgr.list_models(enabled_only=True, council_only=True)
        real_models = [m for m in all_models if m.provider != ModelProvider.DUMMY]
        
        if test_mode:
            real_models = []
        
        if real_models:
            # Use real LLM models via the model council
            result = await _chat_with_real_models(
                message, mode, rag_context, memory, real_models, logger, conv_id,
                project_system_prompt=project_system_prompt,
                project_temperature=project_temperature,
            )
        else:
            # Fall back to dummy models
            result = await _chat_with_dummy_models(
                message, mode, rag_context, memory, logger, conv_id,
                project_system_prompt=project_system_prompt,
            )
    
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
    
    # Log to PersRM interaction logger (async, non-blocking)
    try:
        interaction_logger = get_interaction_logger()
        asyncio.create_task(interaction_logger.log_chat(
            user_message=message,
            ai_response=result["answer"],
            model=result["chosen_model"],
            metadata={
                "mode": mode,
                "conversation_id": conv_id,
                "latency_ms": latency_ms,
                "rag_enabled": use_rag,
                "ai_project_id": ai_project.id if ai_project else None,
            }
        ))
    except Exception as e:
        # Don't fail the chat if logging fails
        pass
    
    response = {
        "answer": result["answer"],
        "chosen_model": result["chosen_model"],
        "responses": result["responses"],
        "memory_summary": memory.get_summary(),
        "mode": mode,
        "command": None,
        "conversation_id": conv_id,
    }
    
    # Add AI project info if present
    if ai_project:
        response["ai_project_id"] = ai_project.id
        response["ai_project_name"] = ai_project.name
    
    return response


async def _chat_with_real_models(
    message: str,
    mode: str,
    rag_context: str,
    memory: ChatMemory,
    models: list,
    logger,
    conv_id: str,
    project_system_prompt: str = "",
    project_temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """Chat using configured LLM models via the shared client."""
    llm_client = get_llm_client()
    system_prompt, messages = _build_chat_messages(
        mode,
        rag_context,
        memory,
        message,
        project_system_prompt,
    )
    
    responses: List[Dict[str, str]] = []
    
    async def _query_model(model_config):
        try:
            response = await llm_client.generate(
                model_config,
                messages,
                temperature=project_temperature if project_temperature is not None else model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
            if response.error:
                responses.append({
                    "model": model_config.name,
                    "text": f"[Error: {response.error}]",
                })
                logger.log_error(conv_id, f"Model {model_config.name}: {response.error}")
            else:
                responses.append({
                    "model": model_config.name,
                    "text": response.text,
                })
        except Exception as e:
            error_msg = str(e) or repr(e) or "Unknown error"
            responses.append({
                "model": model_config.name,
                "text": f"[Error: {error_msg}]",
            })
            logger.log_error(conv_id, f"Model {model_config.name}: {error_msg}")
    
    await asyncio.gather(*[_query_model(model_config) for model_config in models])
    
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


async def stream_chat_response(
    message: str,
    mode: str,
    use_rag: bool,
    session_id: Optional[str] = None,
    model_id: Optional[str] = None,
    ai_project_id: Optional[str] = None,
    project_id: Optional[str] = None,
    attachment_ids: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream chat responses as server-sent events.
    
    Yields serialized SSE payloads.
    """
    # Load AI project similar to chat_endpoint
    ai_project: Optional[AIProject] = None
    if ai_project_id:
        store = get_ai_project_store()
        ai_project = store.get_project(ai_project_id)
        if ai_project:
            use_rag = ai_project.rag_enabled
            if ai_project.code_mode:
                mode = "code"
            if not model_id and ai_project.default_model_id:
                model_id = ai_project.default_model_id
    
    processor = get_command_processor()
    parsed = processor.parse(message)
    
    if parsed.is_command:
        result = await _handle_command(parsed, session_id, model_id, ai_project)
        yield _sse_event({
            "type": "done",
            "answer": result["answer"],
            "chosen_model": result["chosen_model"],
            "mode": result.get("mode", mode),
            "metadata": result,
        })
        return
    
    rag = _get_rag()
    memory = get_memory(session_id)
    logger = get_memory_logger()
    config_mgr = get_model_config_manager()
    
    conv_id = logger.start_conversation(mode=mode, rag_enabled=use_rag)
    logger.log_user_message(conv_id, message)
    start_time = time.time()
    
    rag_context = await _collect_combined_context(
        message,
        use_rag,
        ai_project,
        rag,
        logger,
        conv_id,
    )
    
    project_system_prompt = ai_project.system_prompt if ai_project else ""
    project_temperature = ai_project.default_temperature if ai_project else None
    
    # Determine target model
    target_model = None
    if model_id:
        target_model = config_mgr.get_model(model_id)
    else:
        for model in config_mgr.list_models(enabled_only=True, council_only=True):
            if model.provider != ModelProvider.DUMMY:
                target_model = model
                break
    
    if not target_model:
        # Fall back to dummy streaming (single chunk)
        result = await _chat_with_dummy_models(
            message,
            mode,
            rag_context,
            memory,
            logger,
            conv_id,
            specific_model_name=model_id,
            project_system_prompt=project_system_prompt or "",
        )
        await _finalize_streaming_conversation(
            message,
            result["answer"],
            mode,
            memory,
            logger,
            conv_id,
            result["chosen_model"],
            start_time,
            use_rag,
            ai_project,
            project_id,
            attachment_ids,
        )
        yield _sse_event({
            "type": "done",
            "answer": result["answer"],
            "chosen_model": result["chosen_model"],
            "mode": mode,
        })
        return
    
    llm_client = get_llm_client()
    _, messages = _build_chat_messages(
        mode,
        rag_context,
        memory,
        message,
        project_system_prompt or "",
    )
    
    async def event_stream():
        answer_parts: List[str] = []
        yield _sse_event({
            "type": "metadata",
            "conversation_id": conv_id,
            "model": target_model.name,
            "mode": mode,
        })
        try:
            async for chunk in llm_client.stream_generate(
                target_model,
                messages,
                temperature=project_temperature if project_temperature is not None else target_model.temperature,
                max_tokens=target_model.max_tokens,
            ):
                if chunk.text:
                    answer_parts.append(chunk.text)
                    yield _sse_event({"type": "token", "text": chunk.text})
                if chunk.done:
                    break
            final_answer = "".join(answer_parts).strip()
            await _finalize_streaming_conversation(
                message,
                final_answer,
                mode,
                memory,
                logger,
                conv_id,
                target_model.name,
                start_time,
                use_rag,
                ai_project,
                project_id,
                attachment_ids,
            )
            yield _sse_event({
                "type": "done",
                "answer": final_answer,
                "chosen_model": target_model.name,
                "mode": mode,
            })
        except Exception as exc:
            logger.log_error(conv_id, f"Streaming error: {exc}")
            logger.end_conversation(conv_id)
            yield _sse_event({
                "type": "error",
                "message": str(exc),
            })
    
    async for payload in event_stream():
        yield payload


def _get_project_files_context(ai_project, message: str) -> str:
    """
    Retrieve relevant content from project files as RAG context.
    
    Args:
        ai_project: The AI project with files
        message: User message to match against
        
    Returns:
        Relevant context from project files
    """
    from chatos_backend.projects import get_ai_project_store
    
    if not ai_project or not ai_project.files:
        return ""
    
    store = get_ai_project_store()
    context_parts = []
    keywords = set(message.lower().split())
    
    for filename in ai_project.files[:10]:  # Limit to 10 files for performance
        try:
            content = store.get_file_content(ai_project.id, filename)
            if content is None:
                continue
            
            # Decode text files
            try:
                text = content.decode('utf-8', errors='ignore')
            except:
                continue
            
            # Simple keyword matching for relevance
            text_lower = text.lower()
            relevance_score = sum(1 for kw in keywords if kw in text_lower and len(kw) > 2)
            
            if relevance_score > 0:
                # Include first 1500 chars of relevant files
                snippet = text[:1500].strip()
                if len(text) > 1500:
                    snippet += "..."
                context_parts.append(f"[{filename}]:\n{snippet}")
        except Exception:
            continue
    
    # Limit total context
    if not context_parts:
        return ""
    
    return "\n\n".join(context_parts[:5])  # Max 5 file snippets


def _build_chat_messages(
    mode: str,
    rag_context: str,
    memory: ChatMemory,
    user_message: str,
    project_system_prompt: str,
) -> Tuple[str, List[Dict[str, str]]]:
    """Compose system prompt and full message list for LLM invocations."""
    messages: List[Dict[str, str]] = []
    system_prompt_parts = []
    
    if project_system_prompt:
        system_prompt_parts.append(project_system_prompt)
    
    if mode == "code":
        system_prompt_parts.append(
            "You are a helpful coding assistant. Provide clear, well-commented code with explanations."
        )
    elif not project_system_prompt:
        system_prompt_parts.append(
            "You are a helpful AI assistant. Provide clear, informative responses."
        )
    
    system_prompt = "\n\n".join(system_prompt_parts)
    
    history = memory.get_context()
    if history:
        system_prompt += f"\n\nPrevious conversation:\n{history}"
    
    if rag_context:
        system_prompt += f"\n\nRelevant information:\n{rag_context}"
    
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    
    return system_prompt, messages


async def _collect_combined_context(
    message: str,
    use_rag: bool,
    ai_project: Optional[AIProject],
    rag_engine: RagEngine,
    logger,
    conv_id: str,
) -> str:
    """Retrieve RAG and project contexts in parallel."""
    if not use_rag and not (ai_project and ai_project.files):
        return ""
    
    async def _rag_task() -> str:
        if not use_rag:
            return ""
        return await rag_engine.retrieve_async(message)
    
    async def _project_task() -> str:
        if not (ai_project and ai_project.files):
            return ""
        return await asyncio.to_thread(_get_project_files_context, ai_project, message)
    
    rag_context, project_files_context = await asyncio.gather(
        _rag_task(),
        _project_task(),
    )
    
    combined = rag_context
    if project_files_context:
        logger.log_rag_context(
            conv_id,
            f"[Project files added]\n{project_files_context[:500]}...",
        )
        if combined:
            combined = f"{combined}\n\n--- Project Knowledge Base ---\n{project_files_context}"
        else:
            combined = project_files_context
    
    if rag_context:
        logger.log_rag_context(conv_id, rag_context[:500] + "...")
    
    return combined


async def _chat_with_dummy_models(
    message: str,
    mode: str,
    rag_context: str,
    memory: ChatMemory,
    logger,
    conv_id: str,
    specific_model_name: Optional[str] = None,
    project_system_prompt: str = "",
) -> Dict[str, Any]:
    """Fall back to dummy models.
    
    If specific_model_name is provided, only that model will be queried.
    If project_system_prompt is provided, it's prepended to the prompt.
    """
    models = _get_models()
    voter = _get_voter()
    
    # Build prompt with pre-computed RAG context (avoids duplicate retrieval)
    prompt = _build_prompt(message, mode, rag_context, memory, project_system_prompt)
    
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
    ai_project: Optional[AIProject] = None,
) -> Dict[str, Any]:
    """Handle special /commands."""
    memory = get_memory(session_id)
    
    if parsed.command == "research":
        result = await _handle_research(parsed, memory)
    elif parsed.command == "deepthinking":
        result = await _handle_deepthinking(parsed, memory)
    elif parsed.command == "swarm":
        result = await _handle_swarm(parsed, memory)
    elif parsed.command == "code":
        # Code mode uses normal chat with code mode
        result = await _normal_chat(parsed.query, "code", True, session_id, model_id, ai_project)
        return result  # Already has project info
    elif parsed.command == "reason":
        result = await _handle_reason(parsed, memory)
    else:
        result = {
            "answer": f"Unknown command: /{parsed.command}",
            "chosen_model": "System",
            "responses": [],
            "memory_summary": memory.get_summary(),
            "mode": "normal",
            "command": parsed.command,
        }
    
    # Add AI project info if present
    if ai_project:
        result["ai_project_id"] = ai_project.id
        result["ai_project_name"] = ai_project.name
    
    return result


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


async def _handle_reason(
    parsed: ParsedCommand,
    memory: ChatMemory,
) -> Dict[str, Any]:
    """Handle /reason command via PersRM integration."""
    # Get reasoning from PersRM bridge
    response = await handle_reason_command(
        query=parsed.query,
        memory=memory,
    )
    
    # Format for display
    answer = format_reasoning_response(response)
    
    return {
        "answer": answer,
        "chosen_model": f"PersRM ({response.model_used})",
        "responses": [{
            "model": response.model_used,
            "text": response.reasoning,
        }],
        "memory_summary": memory.get_summary(),
        "mode": "reason",
        "command": "reason",
        "reasoning_result": response.to_dict(),
    }


def _build_prompt(
    message: str,
    mode: str,
    rag_context: str,
    memory: ChatMemory,
    project_system_prompt: str = "",
) -> str:
    """Build the full prompt including context, memory, and user message.
    
    OPTIMIZED: Accepts pre-computed RAG context to avoid duplicate retrieval.
    
    Args:
        message: User message
        mode: Chat mode
        rag_context: Pre-computed RAG context (empty string if disabled)
        memory: Chat memory
        project_system_prompt: AI Project system prompt (prepended if provided)
    """
    parts = []
    
    # Start with AI project system prompt if provided
    if project_system_prompt:
        parts.append(project_system_prompt)
    
    # System instruction based on mode
    if mode == "code":
        parts.append(
            "You are a helpful coding assistant. Provide clear, "
            "well-commented code solutions with brief explanations."
        )
    elif not project_system_prompt:
        # Only add generic prompt if no project prompt
        parts.append(
            "You are a helpful AI assistant. Provide clear, "
            "informative responses."
        )
    
    # Add conversation history
    context = memory.get_context()
    if context:
        parts.append(f"Previous conversation:\n{context}")
    
    # Add pre-computed RAG context
    if rag_context:
        parts.append(f"Relevant information:\n{rag_context}")
    
    # Add the current user message
    parts.append(f"User: {message}")
    
    return "\n\n".join(parts)


def _persist_project_memory_entry(
    project_id: Optional[str],
    user_message: str,
    answer: str,
    mode: str,
    attachment_ids: Optional[List[str]],
) -> None:
    """Store the interaction in project-specific memory if configured."""
    if not project_id:
        return
    
    proj_mgr = get_project_manager()
    project = proj_mgr.projects.get(project_id)
    if not project:
        return
    
    mem_mgr = get_project_memory_manager()
    db = mem_mgr.get_db(project_id, project.path)
    db.add_conversation(
        user_message,
        answer,
        mode=mode,
        attachments=attachment_ids,
    )


async def _finalize_streaming_conversation(
    user_message: str,
    answer: str,
    mode: str,
    memory: ChatMemory,
    logger,
    conv_id: str,
    model_name: str,
    start_time: float,
    use_rag: bool,
    ai_project: Optional[AIProject],
    project_id: Optional[str],
    attachment_ids: Optional[List[str]],
) -> None:
    """Common finalization path for streaming responses."""
    latency_ms = (time.time() - start_time) * 1000
    
    logger.log_assistant_response(
        conv_id,
        answer,
        model=model_name,
        latency_ms=latency_ms,
        council_responses=[{"model": model_name, "text": answer}],
    )
    memory.add_turn(user_message, answer)
    logger.end_conversation(conv_id)
    
    try:
        interaction_logger = get_interaction_logger()
        asyncio.create_task(interaction_logger.log_chat(
            user_message=user_message,
            ai_response=answer,
            model=model_name,
            metadata={
                "mode": mode,
                "conversation_id": conv_id,
                "latency_ms": latency_ms,
                "rag_enabled": use_rag,
                "ai_project_id": ai_project.id if ai_project else None,
            }
        ))
    except Exception:
        pass
    
    _persist_project_memory_entry(project_id, user_message, answer, mode, attachment_ids)


def _sse_event(payload: Dict[str, Any]) -> str:
    """Serialize a payload as server-sent event data line."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


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
