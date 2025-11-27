"""
Memory module tests for ChatOS.

Tests the ChatMemory sliding window functionality.
"""

import pytest

from ChatOS.utils.memory import ChatMemory, clear_session, get_memory


class TestChatMemory:
    """Tests for the ChatMemory class."""

    def test_initial_state(self):
        """New memory should be empty."""
        memory = ChatMemory()
        assert len(memory) == 0
        assert memory.get_context() == ""

    def test_add_single_turn(self):
        """Should store a single conversation turn."""
        memory = ChatMemory()
        memory.add_turn("Hello", "Hi there!")
        assert len(memory) == 1

    def test_get_context_formats_correctly(self):
        """Context should be formatted as User/Assistant pairs."""
        memory = ChatMemory()
        memory.add_turn("Hello", "Hi!")
        context = memory.get_context()
        assert "User: Hello" in context
        assert "Assistant: Hi!" in context

    def test_respects_max_turns(self):
        """Memory should not exceed max_turns."""
        memory = ChatMemory(max_turns=3)
        for i in range(5):
            memory.add_turn(f"Message {i}", f"Response {i}")
        assert len(memory) == 3

    def test_keeps_most_recent_turns(self):
        """When truncating, should keep most recent turns."""
        memory = ChatMemory(max_turns=2)
        memory.add_turn("First", "Response 1")
        memory.add_turn("Second", "Response 2")
        memory.add_turn("Third", "Response 3")
        
        context = memory.get_context()
        assert "First" not in context
        assert "Second" in context
        assert "Third" in context

    def test_clear(self):
        """clear() should remove all history."""
        memory = ChatMemory()
        memory.add_turn("Hello", "Hi")
        memory.add_turn("Bye", "Goodbye")
        memory.clear()
        assert len(memory) == 0

    def test_get_summary(self):
        """get_summary should return conversation state info."""
        memory = ChatMemory()
        summary = memory.get_summary()
        assert "no conversation" in summary.lower() or "0" in summary
        
        memory.add_turn("What is Python?", "A programming language.")
        summary = memory.get_summary()
        assert "1" in summary or "turn" in summary.lower()

    def test_get_last_n_turns(self):
        """get_last_n_turns should return specified number of turns."""
        memory = ChatMemory()
        memory.add_turn("A", "1")
        memory.add_turn("B", "2")
        memory.add_turn("C", "3")
        
        last_two = memory.get_last_n_turns(2)
        assert len(last_two) == 2
        assert last_two[0][0] == "B"
        assert last_two[1][0] == "C"

    def test_get_last_n_turns_exceeds_history(self):
        """get_last_n_turns with n > history length returns all."""
        memory = ChatMemory()
        memory.add_turn("A", "1")
        turns = memory.get_last_n_turns(10)
        assert len(turns) == 1


class TestSessionMemory:
    """Tests for session-based memory management."""

    def test_get_memory_default_session(self):
        """get_memory without session_id uses default session."""
        memory1 = get_memory()
        memory2 = get_memory()
        assert memory1 is memory2

    def test_get_memory_different_sessions(self):
        """Different session_ids get different memory instances."""
        memory1 = get_memory("session1")
        memory2 = get_memory("session2")
        assert memory1 is not memory2

    def test_session_memory_persists(self):
        """Memory should persist for the same session."""
        memory = get_memory("test_session")
        memory.add_turn("Hello", "World")
        
        memory_again = get_memory("test_session")
        assert len(memory_again) == 1

    def test_clear_session(self):
        """clear_session should clear specific session memory."""
        memory = get_memory("clear_test")
        memory.add_turn("Test", "Response")
        assert len(memory) == 1
        
        clear_session("clear_test")
        memory = get_memory("clear_test")
        assert len(memory) == 0

    def test_clear_default_session(self):
        """clear_session without arg clears default session."""
        memory = get_memory()
        memory.add_turn("Test", "Response")
        
        clear_session()
        memory = get_memory()
        assert len(memory) == 0

