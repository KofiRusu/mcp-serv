"""
Action Item Extractor for AGI Core

Uses LLM to extract action items from notes.
"""

import json
import re
from typing import List, Optional

from .models import Note, ActionItem, ActionPriority


# Extraction prompt template
EXTRACTION_PROMPT = """Extract action items from this note. For each action item, identify:
- description: What needs to be done (required)
- assignee: Who should do it (if mentioned, otherwise null)
- due_date: When it's due (if mentioned, otherwise null)
- priority: LOW, MEDIUM, or HIGH based on urgency indicators

Note Title: {title}

Note Content:
{content}

Respond with a JSON array of action items. Example format:
[
  {{"description": "Review the proposal", "assignee": "John", "due_date": "Friday", "priority": "HIGH"}},
  {{"description": "Send follow-up email", "assignee": null, "due_date": "tomorrow", "priority": "MEDIUM"}}
]

If there are no action items, respond with an empty array: []

JSON Response:"""


class ActionItemExtractor:
    """
    Extracts action items from notes using LLM.
    
    Usage:
        extractor = ActionItemExtractor()
        actions = await extractor.extract(note)
    """
    
    def __init__(self):
        """Initialize the extractor."""
        self._llm_client = None
        self._model_config = None
    
    def _get_llm_client(self):
        """Lazy-load LLM client."""
        if self._llm_client is None:
            from ChatOS.controllers.llm_client import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client
    
    def _get_model_config(self):
        """Get the best available model for extraction."""
        if self._model_config is None:
            from ChatOS.controllers.model_config import get_model_config_manager, ModelProvider
            
            mgr = get_model_config_manager()
            
            # Try to get an enabled model
            models = mgr.list_models(enabled_only=True)
            
            # Filter out dummy models
            real_models = [m for m in models if m.provider != ModelProvider.DUMMY]
            
            if real_models:
                # Prefer Ollama for local speed
                ollama_models = [m for m in real_models if m.provider == ModelProvider.OLLAMA]
                if ollama_models:
                    self._model_config = ollama_models[0]
                else:
                    self._model_config = real_models[0]
            else:
                # Fall back to any model including dummy
                if models:
                    self._model_config = models[0]
        
        return self._model_config
    
    async def extract(self, note: Note) -> List[ActionItem]:
        """
        Extract action items from a note.
        
        Args:
            note: The note to extract from
            
        Returns:
            List of extracted ActionItem objects
        """
        # Try LLM extraction first
        try:
            llm_actions = await self._extract_with_llm(note)
            if llm_actions:
                return llm_actions
        except Exception as e:
            print(f"LLM extraction failed: {e}")
        
        # Fall back to pattern-based extraction
        return self._extract_with_patterns(note)
    
    async def _extract_with_llm(self, note: Note) -> Optional[List[ActionItem]]:
        """Extract using LLM."""
        model_config = self._get_model_config()
        if not model_config:
            return None
        
        client = self._get_llm_client()
        
        # Build prompt
        prompt = EXTRACTION_PROMPT.format(
            title=note.title,
            content=note.content[:3000],  # Limit content length
        )
        
        messages = [
            {"role": "system", "content": "You are an action item extraction assistant. Extract tasks and to-dos from notes. Always respond with valid JSON."},
            {"role": "user", "content": prompt},
        ]
        
        response = await client.generate(
            model_config,
            messages,
            temperature=0.2,  # Low temperature for consistent extraction
            max_tokens=1000,
        )
        
        if response.success and response.text:
            return self._parse_llm_response(response.text, note.id)
        
        return None
    
    def _parse_llm_response(self, text: str, note_id: str) -> List[ActionItem]:
        """Parse LLM response into ActionItem objects."""
        actions = []
        
        # Try to extract JSON from the response
        # Handle cases where the LLM wraps JSON in markdown code blocks
        json_match = re.search(r'\[[\s\S]*\]', text)
        if not json_match:
            return actions
        
        try:
            json_str = json_match.group(0)
            items = json.loads(json_str)
            
            if not isinstance(items, list):
                return actions
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                description = item.get("description", "").strip()
                if not description:
                    continue
                
                # Parse priority
                priority_str = item.get("priority", "medium").upper()
                priority_map = {
                    "LOW": ActionPriority.LOW,
                    "MEDIUM": ActionPriority.MEDIUM,
                    "HIGH": ActionPriority.HIGH,
                }
                priority = priority_map.get(priority_str, ActionPriority.MEDIUM)
                
                action = ActionItem(
                    description=description,
                    source_note_id=note_id,
                    assignee=item.get("assignee"),
                    due_date=item.get("due_date"),
                    priority=priority,
                )
                actions.append(action)
                
        except json.JSONDecodeError:
            pass
        
        return actions
    
    def _extract_with_patterns(self, note: Note) -> List[ActionItem]:
        """
        Fallback pattern-based extraction.
        
        Uses regex patterns to find action items when LLM is unavailable.
        """
        actions = []
        text = note.content
        
        # Patterns that indicate action items
        patterns = [
            # TODO/FIXME style
            r'(?:TODO|FIXME|ACTION|TASK):\s*(.+?)(?:\n|$)',
            # Checkbox style (markdown)
            r'[-*]\s*\[\s*\]\s*(.+?)(?:\n|$)',
            # "Need to" style
            r'(?:need to|needs to|must|should|have to)\s+(.+?)(?:\.|,|\n|$)',
            # "Action:" style
            r'(?:action|task|todo):\s*(.+?)(?:\n|$)',
            # "@person" assignment style
            r'@(\w+)\s+(?:to\s+)?(.+?)(?:\n|$)',
            # Bullet with action verb
            r'[-*]\s*((?:review|send|create|update|fix|implement|schedule|call|email|write|prepare|complete|finish|follow up|check|verify|confirm|submit|draft|plan|organize|coordinate|set up|arrange)\s+.+?)(?:\n|$)',
        ]
        
        seen_descriptions = set()
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Handle @person pattern differently
                if '@' in pattern:
                    assignee = match.group(1)
                    description = match.group(2).strip()
                else:
                    assignee = None
                    description = match.group(1).strip()
                
                # Clean up description
                description = description.strip('.,;:')
                
                # Skip if too short or already seen
                if len(description) < 5 or description.lower() in seen_descriptions:
                    continue
                
                seen_descriptions.add(description.lower())
                
                # Determine priority from keywords
                priority = self._infer_priority(description)
                
                # Try to extract due date
                due_date = self._extract_due_date(description)
                
                action = ActionItem(
                    description=description,
                    source_note_id=note.id,
                    assignee=assignee,
                    due_date=due_date,
                    priority=priority,
                )
                actions.append(action)
        
        return actions
    
    def _infer_priority(self, text: str) -> ActionPriority:
        """Infer priority from text content."""
        text_lower = text.lower()
        
        # High priority indicators
        high_keywords = [
            "urgent", "asap", "immediately", "critical", "important",
            "priority", "deadline", "today", "now", "must"
        ]
        
        # Low priority indicators
        low_keywords = [
            "eventually", "someday", "maybe", "consider", "nice to have",
            "optional", "if time", "low priority", "when possible"
        ]
        
        for kw in high_keywords:
            if kw in text_lower:
                return ActionPriority.HIGH
        
        for kw in low_keywords:
            if kw in text_lower:
                return ActionPriority.LOW
        
        return ActionPriority.MEDIUM
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Try to extract a due date from text."""
        text_lower = text.lower()
        
        # Common date patterns
        date_patterns = [
            r'by\s+([\w\s,]+)',
            r'due\s+([\w\s,]+)',
            r'before\s+([\w\s,]+)',
            r'on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(today|tomorrow|tonight)',
            r'(this week|next week|end of week)',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+',
            r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_sync(self, note: Note) -> List[ActionItem]:
        """
        Synchronous extraction using patterns only.
        
        Useful when async is not available.
        """
        return self._extract_with_patterns(note)

