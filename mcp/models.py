"""
MCP Core - Models and data structures for the memory system.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class MemoryDomain(str, Enum):
    PROJECT_KNOWLEDGE = "Project Knowledge"
    COMMUNICATION_STYLE = "Communication Style"
    PROGRESS_TRACKING = "Progress Tracking"
    DOMAIN_SPECIFIC = "Domain-Specific Knowledge"
    REPOSITORY_CONTEXT = "Repository-Specific Context"
    LEARNINGS = "Learnings and Insights"
    CODE_PATTERNS = "Code Patterns"
    TOOLS_CONFIG = "Tools and Configuration"


@dataclass
class Memory:
    """Core memory record"""
    id: str
    domain: str
    title: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    workspace: Optional[str] = None
    repository: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    priority: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data


@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval"""
    domain: Optional[str] = None
    workspace: Optional[str] = None
    repository: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 100
    offset: int = 0


@dataclass
class MemoryStats:
    """Memory system statistics"""
    total_memories: int = 0
    by_domain: Dict[str, int] = field(default_factory=dict)
    by_workspace: Dict[str, int] = field(default_factory=dict)
    total_content_chars: int = 0
    last_updated: Optional[datetime] = None
