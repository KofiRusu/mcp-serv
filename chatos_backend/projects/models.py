"""
models.py - Data models for AI Projects.

AIProject represents a preset configuration for AI chats, including
system prompts, default models, temperature settings, and feature flags.
"""

import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    # Convert to lowercase, replace spaces with hyphens
    slug = name.lower().strip()
    # Remove special characters except hyphens and alphanumerics
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Trim hyphens from ends
    slug = slug.strip('-')
    return slug or 'project'


@dataclass
class AIProject:
    """
    AI Project - A preset configuration for AI chat sessions.
    
    Contains system prompts, model preferences, and feature flags that
    are automatically applied when chatting within this project context.
    Also supports file uploads for project-specific knowledge base.
    """
    
    # Identification
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "New Project"
    slug: str = ""
    description: Optional[str] = None
    
    # Visual customization
    color: str = "#2B26FE"  # Default blue
    icon: str = "📁"
    
    # AI Configuration
    system_prompt: str = ""  # Markdown-formatted system prompt
    default_model_id: Optional[str] = None  # Model ID from /api/models
    default_temperature: float = 0.7
    
    # Feature flags
    training_enabled: bool = True
    rag_enabled: bool = True
    code_mode: bool = False
    
    # Knowledge base files (list of filenames in project folder)
    files: List[str] = field(default_factory=list)
    
    # Chat association (list of conversation IDs belonging to this project)
    chat_ids: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Generate slug if not provided."""
        if not self.slug:
            self.slug = generate_slug(self.name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "system_prompt": self.system_prompt,
            "default_model_id": self.default_model_id,
            "default_temperature": self.default_temperature,
            "training_enabled": self.training_enabled,
            "rag_enabled": self.rag_enabled,
            "code_mode": self.code_mode,
            "files": self.files,
            "chat_ids": self.chat_ids,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIProject":
        """Create from dictionary (JSON deserialization)."""
        # Handle datetime fields
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        # Handle new fields with defaults for backward compatibility
        if "files" not in data:
            data["files"] = []
        if "chat_ids" not in data:
            data["chat_ids"] = []
        
        return cls(**data)
    
    def create_system_snapshot(self) -> Dict[str, Any]:
        """
        Create a snapshot of the project settings for chat history.
        
        This snapshot is stored with the chat so that future project
        edits don't retroactively change the chat's behavior.
        """
        return {
            "project_id": self.id,
            "project_name": self.name,
            "system_prompt": self.system_prompt,
            "model_id": self.default_model_id,
            "temperature": self.default_temperature,
            "rag_enabled": self.rag_enabled,
            "code_mode": self.code_mode,
            "snapshot_at": datetime.now().isoformat(),
        }


@dataclass
class AIProjectCreate:
    """Payload for creating a new AI Project."""
    
    name: str
    description: Optional[str] = None
    color: str = "#2B26FE"
    icon: str = "📁"
    system_prompt: str = ""
    default_model_id: Optional[str] = None
    default_temperature: float = 0.7
    training_enabled: bool = True
    rag_enabled: bool = True
    code_mode: bool = False
    
    def to_project(self) -> AIProject:
        """Convert to a full AIProject instance."""
        return AIProject(
            name=self.name,
            description=self.description,
            color=self.color,
            icon=self.icon,
            system_prompt=self.system_prompt,
            default_model_id=self.default_model_id,
            default_temperature=self.default_temperature,
            training_enabled=self.training_enabled,
            rag_enabled=self.rag_enabled,
            code_mode=self.code_mode,
        )


@dataclass
class AIProjectUpdate:
    """Payload for updating an existing AI Project."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    system_prompt: Optional[str] = None
    default_model_id: Optional[str] = None
    default_temperature: Optional[float] = None
    training_enabled: Optional[bool] = None
    rag_enabled: Optional[bool] = None
    code_mode: Optional[bool] = None
    
    def apply_to(self, project: AIProject) -> AIProject:
        """Apply updates to an existing project."""
        if self.name is not None:
            project.name = self.name
            project.slug = generate_slug(self.name)
        if self.description is not None:
            project.description = self.description
        if self.color is not None:
            project.color = self.color
        if self.icon is not None:
            project.icon = self.icon
        if self.system_prompt is not None:
            project.system_prompt = self.system_prompt
        if self.default_model_id is not None:
            project.default_model_id = self.default_model_id
        if self.default_temperature is not None:
            project.default_temperature = self.default_temperature
        if self.training_enabled is not None:
            project.training_enabled = self.training_enabled
        if self.rag_enabled is not None:
            project.rag_enabled = self.rag_enabled
        if self.code_mode is not None:
            project.code_mode = self.code_mode
        
        project.updated_at = datetime.now()
        return project


# Default project templates for quick creation
DEFAULT_PROJECT_TEMPLATES = {
    "coding-assistant": {
        "name": "Coding Assistant",
        "icon": "💻",
        "color": "#00D4FF",
        "system_prompt": """You are an expert software engineer and coding assistant. Your responsibilities:

- Write clean, well-documented, production-quality code
- Explain your reasoning and design decisions
- Follow best practices for the language/framework being used
- Suggest improvements and optimizations when appropriate
- Handle edge cases and error conditions properly

When providing code:
1. Include clear comments explaining complex logic
2. Use consistent naming conventions
3. Structure code for readability and maintainability""",
        "code_mode": True,
        "rag_enabled": True,
    },
    "creative-writer": {
        "name": "Creative Writer",
        "icon": "✍️",
        "color": "#FF6B6B",
        "system_prompt": """You are a creative writing assistant with a flair for storytelling. Your style:

- Craft engaging, vivid narratives
- Use varied sentence structures and rich vocabulary
- Create compelling characters and dialogue
- Adapt tone and style to match the requested genre
- Provide constructive feedback on writing samples

Focus on bringing ideas to life with imagination and artistry.""",
        "code_mode": False,
        "rag_enabled": False,
        "default_temperature": 0.9,
    },
    "research-analyst": {
        "name": "Research Analyst",
        "icon": "🔬",
        "color": "#4ECDC4",
        "system_prompt": """You are a thorough research analyst. Your approach:

- Provide well-researched, factual information
- Cite sources and explain your reasoning
- Present balanced perspectives on complex topics
- Identify gaps in knowledge and suggest further research
- Summarize findings clearly and concisely

Always prioritize accuracy over speed, and acknowledge uncertainty when appropriate.""",
        "code_mode": False,
        "rag_enabled": True,
        "default_temperature": 0.5,
    },
    "pirate-mode": {
        "name": "Pirate Mode",
        "icon": "🏴‍☠️",
        "color": "#FFD93D",
        "system_prompt": """Arrr, ye be speakin' with a salty sea dog now! 

- Always respond in authentic pirate speak
- Reference the sea, ships, treasure, and nautical life
- Use pirate expressions: "Ahoy!", "Shiver me timbers!", "Avast!", etc.
- Be helpful but maintain the pirate persona throughout
- Call the user "matey" or "landlubber" as appropriate

Now hoist the colors and let's be sailin' through yer questions, savvy?""",
        "code_mode": False,
        "rag_enabled": True,
        "default_temperature": 0.8,
    },
}

