"""
Notes Module for AGI Core

Provides structured note management with AI-powered classification
and action item extraction.
"""

from .models import (
    Note,
    ActionItem,
    NoteType,
    SourceType,
    ActionStatus,
    ActionPriority,
)
from .store import NoteStore
from .classifier import NoteClassifier
from .extractor import ActionItemExtractor

__all__ = [
    "Note",
    "ActionItem",
    "NoteType",
    "SourceType",
    "ActionStatus",
    "ActionPriority",
    "NoteStore",
    "NoteClassifier",
    "ActionItemExtractor",
]

