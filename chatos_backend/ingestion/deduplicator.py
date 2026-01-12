"""
deduplicator.py - Deduplication utilities for training data.

Provides methods for:
- Content hashing
- Finding and marking duplicates
- Similarity detection (optional, with embeddings)
"""

import hashlib
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import ExampleStatus, TrainingExample


def compute_content_hash(user_input: str, assistant_output: str) -> str:
    """
    Compute a SHA-256 hash for training example content.
    
    Args:
        user_input: The user's input/question
        assistant_output: The assistant's response
    
    Returns:
        64-character hex hash string
    """
    # Normalize content
    user_input = user_input.strip().lower()
    assistant_output = assistant_output.strip().lower()
    
    content = f"{user_input}|||{assistant_output}"
    return hashlib.sha256(content.encode()).hexdigest()


def compute_input_hash(user_input: str) -> str:
    """
    Compute hash based only on user input (for finding similar questions).
    
    Args:
        user_input: The user's input/question
    
    Returns:
        64-character hex hash string
    """
    normalized = user_input.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


class Deduplicator:
    """
    Handle deduplication of training examples.
    """
    
    def __init__(self):
        """Initialize the deduplicator."""
        self._hash_cache: Set[str] = set()
        self._input_hash_cache: Dict[str, List[int]] = defaultdict(list)
    
    def build_hash_cache(self) -> int:
        """
        Build an in-memory cache of all content hashes.
        
        Returns:
            Number of hashes cached
        """
        self._hash_cache.clear()
        
        with DatabaseSession() as db:
            results = db.query(TrainingExample.content_hash).filter(
                TrainingExample.content_hash.isnot(None)
            ).all()
            
            for (content_hash,) in results:
                self._hash_cache.add(content_hash)
        
        return len(self._hash_cache)
    
    def is_duplicate(self, content_hash: str) -> bool:
        """
        Check if a content hash already exists.
        
        Args:
            content_hash: Hash to check
        
        Returns:
            True if duplicate exists
        """
        # Check memory cache first
        if content_hash in self._hash_cache:
            return True
        
        # Check database
        with DatabaseSession() as db:
            exists = db.query(TrainingExample).filter(
                TrainingExample.content_hash == content_hash
            ).first() is not None
        
        if exists:
            self._hash_cache.add(content_hash)
        
        return exists
    
    def check_content(self, user_input: str, assistant_output: str) -> bool:
        """
        Check if content is a duplicate.
        
        Args:
            user_input: User input text
            assistant_output: Assistant output text
        
        Returns:
            True if duplicate exists
        """
        content_hash = compute_content_hash(user_input, assistant_output)
        return self.is_duplicate(content_hash)
    
    def add_to_cache(self, content_hash: str) -> None:
        """Add a hash to the memory cache."""
        self._hash_cache.add(content_hash)
    
    def find_duplicates(
        self,
        batch_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Find all duplicate examples in the database.
        
        Returns:
            List of duplicate groups with example IDs
        """
        duplicates = []
        hash_groups: Dict[str, List[int]] = defaultdict(list)
        
        with DatabaseSession() as db:
            # Query all examples with hashes
            offset = 0
            while True:
                results = db.query(
                    TrainingExample.id,
                    TrainingExample.content_hash
                ).filter(
                    TrainingExample.content_hash.isnot(None)
                ).offset(offset).limit(batch_size).all()
                
                if not results:
                    break
                
                for example_id, content_hash in results:
                    hash_groups[content_hash].append(example_id)
                
                offset += batch_size
        
        # Find groups with more than one example
        for content_hash, ids in hash_groups.items():
            if len(ids) > 1:
                duplicates.append({
                    "content_hash": content_hash,
                    "example_ids": ids,
                    "count": len(ids),
                })
        
        return duplicates
    
    def mark_duplicates(
        self,
        keep_strategy: str = "first",
    ) -> int:
        """
        Find and mark duplicate examples as excluded.
        
        Args:
            keep_strategy: Which duplicate to keep ("first", "highest_quality", "newest")
        
        Returns:
            Number of examples marked as excluded
        """
        duplicates = self.find_duplicates()
        marked = 0
        
        for group in duplicates:
            ids = group["example_ids"]
            
            if keep_strategy == "first":
                # Keep the first (lowest ID), exclude rest
                ids_to_exclude = ids[1:]
            elif keep_strategy == "highest_quality":
                # Keep highest quality score
                ids_to_exclude = self._find_lower_quality(ids)
            elif keep_strategy == "newest":
                # Keep newest (highest ID), exclude rest
                ids_to_exclude = ids[:-1]
            else:
                ids_to_exclude = ids[1:]
            
            with DatabaseSession() as db:
                db.query(TrainingExample).filter(
                    TrainingExample.id.in_(ids_to_exclude)
                ).update(
                    {TrainingExample.status: ExampleStatus.EXCLUDED},
                    synchronize_session=False
                )
            
            marked += len(ids_to_exclude)
        
        return marked
    
    def _find_lower_quality(self, ids: List[int]) -> List[int]:
        """Find IDs with lower quality scores."""
        with DatabaseSession() as db:
            examples = db.query(
                TrainingExample.id,
                TrainingExample.quality_score
            ).filter(
                TrainingExample.id.in_(ids)
            ).all()
        
        # Sort by quality (highest first), then by ID (lowest first)
        sorted_examples = sorted(
            examples,
            key=lambda x: (-(x[1] or 0), x[0])
        )
        
        # Keep the first one, exclude rest
        return [ex[0] for ex in sorted_examples[1:]]
    
    def get_duplicate_stats(self) -> Dict[str, Any]:
        """
        Get statistics about duplicates in the database.
        
        Returns:
            Dict with duplicate statistics
        """
        duplicates = self.find_duplicates()
        
        total_duplicates = sum(d["count"] - 1 for d in duplicates)
        
        return {
            "duplicate_groups": len(duplicates),
            "total_duplicate_examples": total_duplicates,
            "largest_group": max((d["count"] for d in duplicates), default=0),
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def find_duplicates() -> List[Dict[str, Any]]:
    """
    Find all duplicate examples in the database.
    
    Returns:
        List of duplicate groups
    """
    dedup = Deduplicator()
    return dedup.find_duplicates()


def remove_duplicates(keep_strategy: str = "first") -> int:
    """
    Find and mark duplicate examples as excluded.
    
    Args:
        keep_strategy: Which duplicate to keep
    
    Returns:
        Number of examples excluded
    """
    dedup = Deduplicator()
    return dedup.mark_duplicates(keep_strategy)


def get_duplicate_stats() -> Dict[str, Any]:
    """Get duplicate statistics."""
    dedup = Deduplicator()
    return dedup.get_duplicate_stats()

