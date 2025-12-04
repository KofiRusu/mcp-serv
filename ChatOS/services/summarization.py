"""
summarization.py - Text summarisation service.

Provides text summarisation and action item extraction functionality using:
1. LLM client (Ollama, OpenAI, etc.) when available
2. Stub implementation for offline/testing mode

Environment variables:
- CHATOS_USE_STUB_SUMMARIZATION: Force stub mode for testing - default: false
- CHATOS_SUMMARIZATION_MODEL: Model to use for summarization (default: auto-detect)
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from ChatOS.controllers.cache import get_cache

logger = logging.getLogger(__name__)

# Configuration from environment
USE_STUB = os.getenv("CHATOS_USE_STUB_SUMMARIZATION", "false").lower() == "true"
SUMMARIZATION_MODEL = os.getenv("CHATOS_SUMMARIZATION_MODEL", "")

# Prompt templates
MEETING_SUMMARY_PROMPT = """You are an AI assistant that summarizes meeting transcripts and extracts action items.

Analyze the following transcript and provide:
1. A concise summary (2-4 sentences) capturing the key points discussed
2. A list of action items (tasks that need to be done, with owners if mentioned)
3. Key decisions made during the meeting

TRANSCRIPT:
{text}

Respond in this exact JSON format:
{{
  "summary": "Your summary here",
  "action_items": ["Action item 1", "Action item 2"],
  "decisions": ["Decision 1", "Decision 2"],
  "topics": ["Topic 1", "Topic 2"]
}}"""

GENERAL_SUMMARY_PROMPT = """You are an AI assistant that summarizes text and extracts action items.

Analyze the following text and provide:
1. A concise summary (2-4 sentences) capturing the key points
2. A list of action items or tasks mentioned (if any)

TEXT:
{text}

Respond in this exact JSON format:
{{
  "summary": "Your summary here",
  "action_items": ["Action item 1", "Action item 2"]
}}"""


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM response, handling various formats."""
    # Try to extract JSON from the response
    response_text = response_text.strip()
    
    # Try direct JSON parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON block in markdown
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in text
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Fallback: create structured response from plain text
    lines = response_text.split('\n')
    summary_lines = []
    action_items = []
    
    in_actions = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if 'action item' in line.lower() or line.startswith('-') or line.startswith('*'):
            in_actions = True
            if line.startswith('-') or line.startswith('*'):
                action_items.append(line[1:].strip())
        elif not in_actions:
            summary_lines.append(line)
    
    return {
        "summary": ' '.join(summary_lines[:3]),  # First 3 lines as summary
        "action_items": action_items or ["Review the content", "Follow up as needed"],
    }


async def _get_llm_model_config():
    """Get the best available model config for summarization."""
    try:
        from ChatOS.controllers.model_config import get_model_config_manager, ModelProvider
        
        manager = get_model_config_manager()
        
        # If specific model requested
        if SUMMARIZATION_MODEL:
            config = manager.get_model(SUMMARIZATION_MODEL)
            if config:
                return config
        
        # Try to get an available model (prefer local)
        available = manager.get_available_models()
        
        # Prefer Ollama models for local processing
        for model in available:
            if model.provider == ModelProvider.OLLAMA:
                return model
        
        # Fall back to any available model
        if available:
            return available[0]
        
        return None
    except Exception as e:
        logger.warning(f"Failed to get model config: {e}")
        return None


async def _summarize_with_llm(text: str, prompt_template: str) -> Dict[str, Any]:
    """Summarize using LLM client."""
    try:
        from ChatOS.controllers.llm_client import get_llm_client
        
        model_config = await _get_llm_model_config()
        if not model_config:
            logger.warning("No LLM model available, falling back to stub")
            return None
        
        client = get_llm_client()
        
        prompt = prompt_template.format(text=text[:8000])  # Limit text length
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = await client.generate(
            model_config=model_config,
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=1000,
        )
        
        if response.error:
            logger.warning(f"LLM error: {response.error}")
            return None
        
        return _parse_llm_response(response.text)
        
    except Exception as e:
        logger.warning(f"LLM summarization failed: {e}")
        return None


def _stub_summarize(text: str) -> Dict[str, Any]:
    """Stub summarization for testing."""
    # First 80 chars as summary
    summary = (text[:80] + "...") if len(text) > 80 else text
    
    # Deterministic action items for testing
    action_items: List[str] = [
        "Follow up on key points",
        "Schedule next meeting",
    ]
    
    return {
        "summary": summary,
        "action_items": action_items,
        "engine": "stub",
    }


async def summarize_text(
    text: str,
    note_type: str = "general",
    force_stub: bool = False,
) -> Dict[str, Any]:
    """
    Summarize the given text and extract action items.

    Uses LLM when available, falls back to stub for testing.

    Args:
        text: The text to summarize
        note_type: Type of note ("meeting", "brainstorm", "lecture", "general")
        force_stub: Force stub mode regardless of LLM availability

    Returns:
        Dictionary with 'summary', 'action_items', and optionally 'decisions', 'topics'
    """
    if not text or not text.strip():
        return {
            "summary": "",
            "action_items": [],
            "engine": "empty",
        }
    
    cache = get_cache()
    cache_key = f"summary:{hash(text)}:{note_type}"
    
    # Check cache first
    cached = await cache.get(cache_key)
    if cached:
        logger.debug("Cache hit for summarization")
        return cached

    # Use stub if forced or configured
    if force_stub or USE_STUB:
        logger.info("Using stub summarization")
        result = _stub_summarize(text)
        await cache.set(cache_key, result, ttl=3600)
        return result

    # Select prompt template based on note type
    if note_type == "meeting":
        prompt_template = MEETING_SUMMARY_PROMPT
    else:
        prompt_template = GENERAL_SUMMARY_PROMPT

    # Try LLM summarization
    logger.info(f"Summarizing text ({note_type}, {len(text)} chars)")
    result = await _summarize_with_llm(text, prompt_template)
    
    if result:
        result["engine"] = "llm"
    else:
        # Fall back to stub
        logger.info("Falling back to stub summarization")
        result = _stub_summarize(text)
    
    # Cache the result
    await cache.set(cache_key, result, ttl=3600)
    
    return result


async def classify_note_type(text: str) -> str:
    """
    Classify the type of note based on content.
    
    Args:
        text: The note content
        
    Returns:
        Note type: "meeting", "brainstorm", "lecture", or "general"
    """
    text_lower = text.lower()
    
    # Simple keyword-based classification
    meeting_keywords = ["meeting", "agenda", "attendees", "minutes", "discussed", "action items"]
    brainstorm_keywords = ["ideas", "brainstorm", "concept", "possibility", "what if"]
    lecture_keywords = ["lecture", "class", "professor", "chapter", "lesson", "topic"]
    
    meeting_score = sum(1 for kw in meeting_keywords if kw in text_lower)
    brainstorm_score = sum(1 for kw in brainstorm_keywords if kw in text_lower)
    lecture_score = sum(1 for kw in lecture_keywords if kw in text_lower)
    
    if meeting_score >= 2:
        return "meeting"
    elif brainstorm_score >= 2:
        return "brainstorm"
    elif lecture_score >= 2:
        return "lecture"
    else:
        return "general"


def get_summarization_status() -> Dict[str, Any]:
    """Get status of summarization service."""
    import asyncio
    
    async def _check():
        model_config = await _get_llm_model_config()
        return {
            "llm_available": model_config is not None,
            "model": model_config.model_id if model_config else None,
            "provider": model_config.provider.value if model_config else None,
            "stub_mode": USE_STUB,
        }
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return {"llm_available": "unknown", "stub_mode": USE_STUB}
        return loop.run_until_complete(_check())
    except Exception:
        return {"llm_available": "unknown", "stub_mode": USE_STUB}
