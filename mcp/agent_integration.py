"""
MCP Agent Integration - Simple API for agent access to memory system
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import os

from .memory_store import MemoryStore
from .classifier import MemoryClassifier
from .models import MemoryQuery


class AgentMemory:
    """Simple agent interface to memory system"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            mcp_home = Path(
                os.environ.get("MCP_HOME", str(Path(__file__).resolve().parent.parent))
            ).expanduser().resolve()
            db_path = str(mcp_home / "data" / "mcp" / "memories.db")
        
        self.store_instance = MemoryStore(db_path)
        self.classifier = MemoryClassifier()
    
    def store(
        self,
        domain: str,
        content: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: str = "medium",
        auto_classify: bool = False,
        **kwargs
    ) -> str:
        """Store a memory"""
        
        if auto_classify:
            classification = self.classifier.classify(content, title)
            domain = classification["domain"]
            tags = (tags or []) + classification["tags"]
            if priority == "medium":
                priority = classification["priority"]
            if not title:
                title = classification["suggested_title"]
        
        if not title:
            title = content[:50]
        
        return self.store_instance.set_memory(
            domain=domain,
            title=title,
            content=content,
            tags=tags or [],
            priority=priority,
            **kwargs
        )
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for memories"""
        results = self.store_instance.search(query, limit)
        return [m.to_dict() for m in results]
    
    def get_context(
        self,
        workspace: Optional[str] = None,
        max_memories: int = 20
    ) -> List[Dict[str, Any]]:
        """Get contextual memories"""
        query = MemoryQuery(workspace=workspace, limit=max_memories)
        memories, _ = self.store_instance.list_memories(query)
        return [m.to_dict() for m in memories]
    
    def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory"""
        memory = self.store_instance.get_memory(memory_id)
        return memory.to_dict() if memory else None
    
    def list_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all memories"""
        query = MemoryQuery(limit=limit)
        memories, _ = self.store_instance.list_memories(query)
        return [m.to_dict() for m in memories]
    
    def list_by_domain(self, domain: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List memories by domain"""
        query = MemoryQuery(domain=domain, limit=limit)
        memories, _ = self.store_instance.list_memories(query)
        return [m.to_dict() for m in memories]
    
    def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        return self.store_instance.delete_memory(memory_id)
    
    def stats(self) -> Dict[str, Any]:
        """Get statistics"""
        s = self.store_instance.get_stats()
        return {
            "total": s.total_memories,
            "by_domain": s.by_domain,
            "by_workspace": s.by_workspace,
            "total_chars": s.total_content_chars,
            "last_updated": s.last_updated.isoformat() if s.last_updated else None,
        }
    
    def classify(self, content: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Classify content"""
        return self.classifier.classify(content, title)


# Global singleton
_memory = None


def get_memory(db_path: Optional[str] = None) -> AgentMemory:
    """Get or create the default memory instance"""
    global _memory
    if _memory is None:
        _memory = AgentMemory(db_path)
    return _memory


# Convenience functions
def store(domain: str, content: str, **kwargs) -> str:
    return get_memory().store(domain, content, **kwargs)

def search(query: str, **kwargs) -> List[Dict]:
    return get_memory().search(query, **kwargs)

def context(**kwargs) -> List[Dict]:
    return get_memory().get_context(**kwargs)

def stats() -> Dict:
    return get_memory().stats()
