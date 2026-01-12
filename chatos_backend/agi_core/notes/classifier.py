"""
Note Classifier for AGI Core

Uses LLM to classify notes into types (meeting, brainstorm, etc.)
"""

import json
from typing import Optional

from .models import Note, NoteType


# Classification prompt template
CLASSIFICATION_PROMPT = """Classify this note into one of the following categories:
- MEETING: Meeting notes, agendas, minutes, action items from meetings
- BRAINSTORM: Creative ideation, brainstorming sessions, idea lists
- LECTURE: Educational content, learning notes, course materials
- JOURNAL: Personal reflections, diary entries, daily logs
- GENERAL: General notes that don't fit other categories

Note Title: {title}

Note Content:
{content}

Respond with ONLY the category name (MEETING, BRAINSTORM, LECTURE, JOURNAL, or GENERAL). Nothing else."""


class NoteClassifier:
    """
    Classifies notes into types using LLM.
    
    Usage:
        classifier = NoteClassifier()
        note_type = await classifier.classify(note)
    """
    
    def __init__(self):
        """Initialize the classifier."""
        self._llm_client = None
        self._model_config = None
    
    def _get_llm_client(self):
        """Lazy-load LLM client."""
        if self._llm_client is None:
            from chatos_backend.controllers.llm_client import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client
    
    def _get_model_config(self):
        """Get the best available model for classification."""
        if self._model_config is None:
            from chatos_backend.controllers.model_config import get_model_config_manager, ModelProvider
            
            mgr = get_model_config_manager()
            
            # Try to get an enabled model (prefer local models for speed)
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
    
    async def classify(self, note: Note) -> NoteType:
        """
        Classify a note into a type.
        
        Args:
            note: The note to classify
            
        Returns:
            The classified NoteType
        """
        # Try LLM classification first
        try:
            llm_type = await self._classify_with_llm(note)
            if llm_type:
                return llm_type
        except Exception as e:
            print(f"LLM classification failed: {e}")
        
        # Fall back to keyword-based classification
        return self._classify_with_keywords(note)
    
    async def _classify_with_llm(self, note: Note) -> Optional[NoteType]:
        """Classify using LLM."""
        model_config = self._get_model_config()
        if not model_config:
            return None
        
        client = self._get_llm_client()
        
        # Build prompt
        prompt = CLASSIFICATION_PROMPT.format(
            title=note.title,
            content=note.content[:2000],  # Limit content length
        )
        
        messages = [
            {"role": "system", "content": "You are a note classification assistant. Respond only with the category name."},
            {"role": "user", "content": prompt},
        ]
        
        response = await client.generate(
            model_config,
            messages,
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=50,
        )
        
        if response.success and response.text:
            # Parse the response
            result = response.text.strip().upper()
            
            # Map to NoteType
            type_map = {
                "MEETING": NoteType.MEETING,
                "BRAINSTORM": NoteType.BRAINSTORM,
                "LECTURE": NoteType.LECTURE,
                "JOURNAL": NoteType.JOURNAL,
                "GENERAL": NoteType.GENERAL,
            }
            
            # Find the type in the response
            for key, value in type_map.items():
                if key in result:
                    return value
        
        return None
    
    def _classify_with_keywords(self, note: Note) -> NoteType:
        """
        Fallback keyword-based classification.
        
        Uses simple keyword matching when LLM is unavailable.
        """
        text = f"{note.title} {note.content}".lower()
        
        # Meeting indicators
        meeting_keywords = [
            "meeting", "agenda", "minutes", "attendees", "action items",
            "discussed", "decision", "follow-up", "scheduled", "call",
            "standup", "sync", "review meeting", "kickoff"
        ]
        
        # Brainstorm indicators
        brainstorm_keywords = [
            "brainstorm", "idea", "concept", "what if", "possibilities",
            "options", "alternatives", "creative", "innovation", "explore",
            "might work", "could try", "proposal"
        ]
        
        # Lecture indicators
        lecture_keywords = [
            "lecture", "lesson", "chapter", "course", "learning",
            "study", "notes from", "professor", "class", "tutorial",
            "definition", "theorem", "example:", "exercise"
        ]
        
        # Journal indicators
        journal_keywords = [
            "today i", "feeling", "reflection", "diary", "personal",
            "my day", "grateful", "thoughts on", "i think", "i feel",
            "morning", "evening", "weekend"
        ]
        
        # Count matches
        scores = {
            NoteType.MEETING: sum(1 for kw in meeting_keywords if kw in text),
            NoteType.BRAINSTORM: sum(1 for kw in brainstorm_keywords if kw in text),
            NoteType.LECTURE: sum(1 for kw in lecture_keywords if kw in text),
            NoteType.JOURNAL: sum(1 for kw in journal_keywords if kw in text),
        }
        
        # Return highest scoring type, or GENERAL if no matches
        max_score = max(scores.values())
        if max_score > 0:
            for note_type, score in scores.items():
                if score == max_score:
                    return note_type
        
        return NoteType.GENERAL
    
    def classify_sync(self, note: Note) -> NoteType:
        """
        Synchronous classification using keywords only.
        
        Useful when async is not available.
        """
        return self._classify_with_keywords(note)

