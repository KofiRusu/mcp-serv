"""
Controllers package for ChatOS.

Contains the chat orchestration logic and API endpoint handlers.
"""

from .chat import chat_endpoint, CouncilVoter
from .commands import CommandProcessor
from .sandbox import SandboxManager
from .research import ResearchEngine
from .deepthinking import DeepThinkingEngine
from .swarm import SwarmCoordinator
from .projects import ProjectManager, get_project_manager
from .attachments import AttachmentManager, get_attachment_manager
from .project_memory import ProjectMemoryManager, get_project_memory_manager
from .model_config import ModelConfigManager, get_model_config_manager
from .llm_client import LLMClient, get_llm_client, ModelCouncil, get_model_council

__all__ = [
    "chat_endpoint",
    "CouncilVoter", 
    "CommandProcessor",
    "SandboxManager",
    "ResearchEngine",
    "DeepThinkingEngine",
    "SwarmCoordinator",
    "ProjectManager",
    "get_project_manager",
    "AttachmentManager",
    "get_attachment_manager",
    "ProjectMemoryManager",
    "get_project_memory_manager",
    "ModelConfigManager",
    "get_model_config_manager",
    "LLMClient",
    "get_llm_client",
    "ModelCouncil",
    "get_model_council",
]
