"""
Tests for AGI Core Memory System
"""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ChatOS.agi_core.memory import (
    MemoryItem,
    ShortTermMemory,
    LongTermMemory,
    MemoryManager,
)


class TestMemoryItem:
    """Tests for MemoryItem dataclass."""
    
    def test_create_memory_item(self):
        item = MemoryItem(content="Test memory")
        assert item.content == "Test memory"
        assert item.id != ""
        assert item.importance == 0.5
        assert item.source == "system"
    
    def test_memory_item_with_importance(self):
        item = MemoryItem(content="Important", importance=0.9)
        assert item.importance == 0.9
    
    def test_memory_item_to_dict(self):
        item = MemoryItem(content="Test", source="user")
        data = item.to_dict()
        assert data["content"] == "Test"
        assert data["source"] == "user"
        assert "timestamp" in data
    
    def test_memory_item_from_dict(self):
        data = {
            "content": "Reconstructed",
            "source": "test",
            "importance": 0.8,
        }
        item = MemoryItem.from_dict(data)
        assert item.content == "Reconstructed"
        assert item.importance == 0.8


class TestShortTermMemory:
    """Tests for ShortTermMemory."""
    
    def test_add_and_get(self):
        stm = ShortTermMemory()
        item = MemoryItem(content="Short term test")
        item_id = stm.add(item)
        
        retrieved = stm.get(item_id)
        assert retrieved is not None
        assert retrieved.content == "Short term test"
    
    def test_max_items_eviction(self):
        stm = ShortTermMemory(max_items=5)
        
        for i in range(10):
            stm.add(MemoryItem(content=f"Memory {i}"))
        
        assert stm.count() == 5
    
    def test_search(self):
        stm = ShortTermMemory()
        stm.add(MemoryItem(content="Python programming is fun"))
        stm.add(MemoryItem(content="Machine learning models"))
        stm.add(MemoryItem(content="Python data analysis"))
        
        results = stm.search("Python", k=2)
        assert len(results) == 2
        assert all("python" in r.content.lower() for r in results)
    
    def test_delete(self):
        stm = ShortTermMemory()
        item = MemoryItem(content="To delete")
        item_id = stm.add(item)
        
        assert stm.delete(item_id)
        assert stm.get(item_id) is None
    
    def test_conversation_turns(self):
        stm = ShortTermMemory()
        stm.add_turn("Hello", "Hi there!")
        stm.add_turn("How are you?", "I'm doing well!")
        
        context = stm.get_context()
        assert "Hello" in context
        assert "Hi there!" in context


class TestLongTermMemory:
    """Tests for LongTermMemory."""
    
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and add
            ltm = LongTermMemory(storage_path=Path(tmpdir))
            item = MemoryItem(content="Persistent memory")
            item_id = ltm.add(item)
            
            # Create new instance and verify
            ltm2 = LongTermMemory(storage_path=Path(tmpdir))
            retrieved = ltm2.get(item_id)
            assert retrieved is not None
            assert retrieved.content == "Persistent memory"
    
    def test_search_keywords(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ltm = LongTermMemory(storage_path=Path(tmpdir))
            
            ltm.add(MemoryItem(content="Neural network training"))
            ltm.add(MemoryItem(content="Data preprocessing steps"))
            ltm.add(MemoryItem(content="Neural architecture search"))
            
            results = ltm.search("neural", k=2)
            assert len(results) == 2


class TestMemoryManager:
    """Tests for unified MemoryManager."""
    
    def test_remember_and_recall(self):
        mm = MemoryManager(session_id="test")
        
        mm.remember("User likes Python", importance=0.8)
        mm.remember("Working on ML project", importance=0.7)
        
        results = mm.recall("Python", k=1)
        assert len(results) >= 1
    
    def test_session_summary(self):
        mm = MemoryManager(session_id="test_session")
        mm.remember("Test memory", importance=0.5)
        
        summary = mm.summarize_session()
        assert "test_session" in summary
    
    def test_forget(self):
        mm = MemoryManager()
        memory_id = mm.remember("To forget")
        
        assert mm.forget(memory_id)
    
    def test_stats(self):
        mm = MemoryManager(session_id="stats_test")
        mm.remember("Memory 1")
        mm.remember("Memory 2")
        
        stats = mm.get_stats()
        assert "short_term_count" in stats
        assert stats["session_id"] == "stats_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

