"""
ChatOS AI Projects - System settings presets for AI chats.

This module provides the AIProject entity which allows users to create
preset configurations (system prompts, models, temperature, flags) that
can be applied to chat sessions.

Note: This is separate from ChatOS/controllers/projects.py which handles
coding project scaffolding (templates, venvs, dependencies).
"""

from chatos_backend.projects.models import AIProject, AIProjectCreate, AIProjectUpdate
from chatos_backend.projects.store import AIProjectStore, get_ai_project_store

__all__ = [
    "AIProject",
    "AIProjectCreate",
    "AIProjectUpdate",
    "AIProjectStore",
    "get_ai_project_store",
]

