"""
reasoning.py - /reason command controller.

Implements the /reason command functionality using PersRM integration:
1. Parse the reasoning query
2. Get structured reasoning from PersRM/Ollama
3. Format and return the result

Usage:
    /reason How should I design a user authentication flow?
    /reason What's the best approach for state management in React?
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ChatOS.plugins.persrm_bridge import PersRMBridge, ReasoningResult

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResponse:
    """Response from reasoning command."""
    query: str
    reasoning: str
    model_used: str
    source: str
    execution_time: float
    timestamp: str
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "reasoning": self.reasoning,
            "model_used": self.model_used,
            "source": self.source,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
            "success": self.success,
            "error": self.error,
        }


# Global bridge instance (reused across requests)
_bridge: Optional[PersRMBridge] = None


def get_bridge() -> PersRMBridge:
    """Get or create the PersRM bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = PersRMBridge()
    return _bridge


async def handle_reason_command(
    query: str,
    context: Optional[str] = None,
    model: Optional[str] = None,
    memory = None,
) -> ReasoningResponse:
    """
    Handle /reason command.
    
    Args:
        query: The reasoning question/challenge
        context: Optional additional context
        model: Optional model override
        memory: Optional ConversationMemory for context
        
    Returns:
        ReasoningResponse with structured reasoning
    """
    logger.info(f"[/reason] Processing: {query[:100]}...")
    start_time = datetime.now()
    
    # Get additional context from memory if available
    memory_context = None
    if memory:
        try:
            memory_context = memory.get_context()
        except Exception:
            pass
    
    # Combine contexts
    full_context = ""
    if memory_context:
        full_context += f"Conversation context: {memory_context}\n"
    if context:
        full_context += f"Additional context: {context}"
    
    bridge = get_bridge()
    
    try:
        result: ReasoningResult = await bridge.reason(
            prompt=query,
            context=full_context if full_context else None,
            model=model,
        )
        
        response = ReasoningResponse(
            query=query,
            reasoning=result.reasoning,
            model_used=result.model_used,
            source=result.source,
            execution_time=result.execution_time,
            timestamp=datetime.now().isoformat(),
            success=result.success,
            error=result.error,
        )
        
        # Add to memory if available
        if memory and result.success:
            memory.add_turn(
                f"/reason {query}",
                result.reasoning[:500] + "..." if len(result.reasoning) > 500 else result.reasoning
            )
        
        logger.info(
            f"[/reason] Completed in {result.execution_time:.2f}s "
            f"using {result.model_used} via {result.source}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"[/reason] Error: {e}")
        return ReasoningResponse(
            query=query,
            reasoning="",
            model_used="none",
            source="error",
            execution_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now().isoformat(),
            success=False,
            error=str(e),
        )


def format_reasoning_response(response: ReasoningResponse) -> str:
    """
    Format reasoning response for display.
    
    Args:
        response: The ReasoningResponse to format
        
    Returns:
        Formatted string for display
    """
    if not response.success:
        return f"❌ Reasoning failed: {response.error}"
    
    lines = [
        f"💡 **PersRM Reasoning** ({response.model_used})",
        "",
        response.reasoning,
        "",
        f"---",
        f"_Source: {response.source} | Time: {response.execution_time:.2f}s_",
    ]
    
    return "\n".join(lines)


# Synchronous wrapper for non-async contexts
def handle_reason_command_sync(
    query: str,
    context: Optional[str] = None,
    model: Optional[str] = None,
    memory = None,
) -> ReasoningResponse:
    """Synchronous wrapper for handle_reason_command."""
    import asyncio
    return asyncio.run(handle_reason_command(query, context, model, memory))

