"""
ChatOS Services Package

Provides core services for:
- Audio transcription
- Text summarisation
- Task creation from notes
- Memory storage for notes
"""

from chatos_backend.services.transcription import transcribe_audio
from chatos_backend.services.summarization import summarize_text
from chatos_backend.services.tasks import (
    create_tasks_from_note,
    get_tasks_for_note,
    get_tasks_for_session,
    update_task_status,
)
from chatos_backend.services.memory import (
    store_note_memory,
    recall_notes,
    get_note_context,
    get_memory_stats,
)

__all__ = [
    # Transcription
    "transcribe_audio",
    # Summarization
    "summarize_text",
    # Tasks
    "create_tasks_from_note",
    "get_tasks_for_note",
    "get_tasks_for_session",
    "update_task_status",
    # Memory
    "store_note_memory",
    "recall_notes",
    "get_note_context",
    "get_memory_stats",
]

