"""
Long-Term Memory for AGI Core

Provides persistent memory storage with optional embedding-based search.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import MemoryItem, MemoryStore


# Default storage location
DEFAULT_MEMORY_DIR = Path.home() / "ChatOS-Memory" / "agi" / "memory"


class LongTermMemory(MemoryStore):
    """
    Persistent long-term memory with JSON storage.
    
    Optionally supports embedding-based semantic search when
    sentence-transformers is available.
    
    Attributes:
        storage_path: Path to the memory JSON file
        use_embeddings: Whether to use embedding-based search
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        use_embeddings: bool = False,
    ):
        """
        Initialize long-term memory.
        
        Args:
            storage_path: Path to store memories (default: ~/ChatOS-Memory/agi/memory/)
            use_embeddings: Enable embedding-based search (requires sentence-transformers)
        """
        self.storage_path = storage_path or DEFAULT_MEMORY_DIR
        self.storage_path = Path(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.memories_file = self.storage_path / "long_term.json"
        self.use_embeddings = use_embeddings
        
        self._memories: Dict[str, MemoryItem] = {}
        self._encoder = None
        self._embeddings: Dict[str, List[float]] = {}
        
        # Load existing memories
        self._load()
        
        # Initialize embeddings if requested
        if use_embeddings:
            self._init_embeddings()
    
    def _load(self) -> None:
        """Load memories from disk."""
        if not self.memories_file.exists():
            return
        
        try:
            data = json.loads(self.memories_file.read_text(encoding="utf-8"))
            for item_data in data.get("memories", []):
                item = MemoryItem.from_dict(item_data)
                self._memories[item.id] = item
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to load long-term memory: {e}")
    
    def _save(self) -> None:
        """Save memories to disk."""
        data = {
            "version": 1,
            "updated_at": time.time(),
            "memories": [m.to_dict() for m in self._memories.values()],
        }
        
        # Atomic write
        temp_file = self.memories_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.memories_file)
    
    def _init_embeddings(self) -> None:
        """Initialize the embedding encoder."""
        try:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Generate embeddings for existing memories
            for memory in self._memories.values():
                if memory.id not in self._embeddings:
                    embedding = self._encoder.encode(memory.content).tolist()
                    self._embeddings[memory.id] = embedding
                    
        except ImportError:
            print("Warning: sentence-transformers not available, using keyword search")
            self.use_embeddings = False
    
    def _compute_embedding(self, text: str) -> Optional[List[float]]:
        """Compute embedding for text."""
        if self._encoder is None:
            return None
        return self._encoder.encode(text).tolist()
    
    def add(self, item: MemoryItem) -> str:
        """Add a memory item and persist to disk."""
        self._memories[item.id] = item
        
        # Compute embedding if enabled
        if self.use_embeddings and self._encoder:
            self._embeddings[item.id] = self._compute_embedding(item.content)
        
        self._save()
        return item.id
    
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a memory by ID."""
        return self._memories.get(memory_id)
    
    def search(self, query: str, k: int = 5) -> List[MemoryItem]:
        """
        Search memories using embeddings or keyword matching.
        
        If embeddings are enabled, uses cosine similarity.
        Otherwise, falls back to keyword matching.
        """
        if self.use_embeddings and self._encoder and self._embeddings:
            return self._search_embeddings(query, k)
        return self._search_keywords(query, k)
    
    def _search_embeddings(self, query: str, k: int) -> List[MemoryItem]:
        """Search using embedding similarity."""
        import numpy as np
        
        query_embedding = np.array(self._compute_embedding(query))
        
        scores = []
        for memory_id, embedding in self._embeddings.items():
            if memory_id not in self._memories:
                continue
            
            # Cosine similarity
            emb = np.array(embedding)
            similarity = np.dot(query_embedding, emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(emb)
            )
            scores.append((memory_id, similarity))
        
        # Sort by similarity descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for memory_id, _ in scores[:k]:
            if memory_id in self._memories:
                results.append(self._memories[memory_id])
        
        return results
    
    def _search_keywords(self, query: str, k: int) -> List[MemoryItem]:
        """Search using keyword matching."""
        query_lower = query.lower()
        keywords = query_lower.split()
        
        scored = []
        for memory in self._memories.values():
            content_lower = memory.content.lower()
            
            # Count keyword matches
            score = sum(1 for kw in keywords if kw in content_lower)
            
            # Boost by importance
            score += memory.importance * 0.5
            
            if score > 0:
                scored.append((memory, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:k]]
    
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            self._embeddings.pop(memory_id, None)
            self._save()
            return True
        return False
    
    def all(self) -> List[MemoryItem]:
        """Return all memories."""
        return list(self._memories.values())
    
    def clear(self) -> int:
        """Clear all memories."""
        count = len(self._memories)
        self._memories.clear()
        self._embeddings.clear()
        self._save()
        return count
    
    def consolidate(self, max_age_days: int = 30, min_importance: float = 0.3) -> int:
        """
        Consolidate memories by removing old, low-importance items.
        
        Args:
            max_age_days: Maximum age in days for low-importance memories
            min_importance: Importance threshold for old memories
            
        Returns:
            Number of memories removed
        """
        cutoff = time.time() - (max_age_days * 24 * 3600)
        to_remove = []
        
        for memory_id, memory in self._memories.items():
            if memory.timestamp < cutoff and memory.importance < min_importance:
                to_remove.append(memory_id)
        
        for memory_id in to_remove:
            del self._memories[memory_id]
            self._embeddings.pop(memory_id, None)
        
        if to_remove:
            self._save()
        
        return len(to_remove)
    
    def export(self, output_path: Path) -> int:
        """
        Export all memories to a JSON file.
        
        Args:
            output_path: Path to write the export
            
        Returns:
            Number of memories exported
        """
        data = {
            "exported_at": time.time(),
            "memories": [m.to_dict() for m in self._memories.values()],
        }
        
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return len(self._memories)
    
    def import_memories(self, input_path: Path) -> int:
        """
        Import memories from a JSON file.
        
        Args:
            input_path: Path to the import file
            
        Returns:
            Number of memories imported
        """
        data = json.loads(input_path.read_text(encoding="utf-8"))
        count = 0
        
        for item_data in data.get("memories", []):
            item = MemoryItem.from_dict(item_data)
            if item.id not in self._memories:
                self._memories[item.id] = item
                count += 1
        
        if count > 0:
            self._save()
        
        return count

