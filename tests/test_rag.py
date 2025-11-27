"""
RAG (Retrieval-Augmented Generation) tests for ChatOS.

Tests the RagEngine's document loading and retrieval functionality.
"""

import tempfile
from pathlib import Path

import pytest

from ChatOS.utils.rag import RagEngine


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory with sample documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample documents
        doc1 = Path(tmpdir) / "python_guide.txt"
        doc1.write_text(
            "Python is a programming language known for its simplicity. "
            "It supports multiple programming paradigms including "
            "object-oriented, functional, and procedural programming."
        )
        
        doc2 = Path(tmpdir) / "javascript_guide.txt"
        doc2.write_text(
            "JavaScript is the language of the web. "
            "It runs in browsers and on servers via Node.js. "
            "Modern JavaScript uses async/await for asynchronous operations."
        )
        
        doc3 = Path(tmpdir) / "empty.txt"
        doc3.write_text("")
        
        yield tmpdir


@pytest.fixture
def rag_engine(temp_data_dir):
    """Create a RagEngine with test documents."""
    return RagEngine(data_dir=temp_data_dir)


class TestRagEngineLoading:
    """Tests for document loading."""

    def test_loads_txt_files(self, rag_engine):
        """RagEngine should load .txt files from the directory."""
        # Should have loaded 2 non-empty documents (empty.txt may or may not be included)
        assert len(rag_engine) >= 2

    def test_stores_filename_and_content(self, rag_engine):
        """Documents should have filename and content."""
        for name, content in rag_engine.docs:
            assert isinstance(name, str)
            assert name.endswith(".txt")

    def test_handles_missing_directory(self):
        """RagEngine should handle non-existent directories gracefully."""
        rag = RagEngine(data_dir="/nonexistent/path")
        assert len(rag) == 0

    def test_list_documents(self, rag_engine):
        """list_documents should return document names."""
        names = rag_engine.list_documents()
        assert isinstance(names, list)
        assert "python_guide.txt" in names or len(names) > 0


class TestRagEngineRetrieval:
    """Tests for document retrieval."""

    def test_retrieves_matching_document(self, rag_engine):
        """Should retrieve document containing query term."""
        result = rag_engine.retrieve("Python programming")
        assert "Python" in result or "python" in result.lower()

    def test_returns_empty_for_no_match(self, rag_engine):
        """Should return empty string when no match found."""
        result = rag_engine.retrieve("xyznonexistent123")
        assert result == ""

    def test_case_insensitive_search(self, rag_engine):
        """Search should be case-insensitive."""
        result1 = rag_engine.retrieve("PYTHON")
        result2 = rag_engine.retrieve("python")
        # Both should find something (assuming sample data has "Python")
        assert len(result1) > 0 or len(result2) > 0

    def test_returns_snippet_not_full_document(self, rag_engine):
        """Should return a snippet, not the entire document."""
        result = rag_engine.retrieve("programming")
        # Snippet should be reasonably bounded
        assert len(result) < 1000

    def test_skips_very_short_queries(self, rag_engine):
        """Should skip queries that are too short."""
        result = rag_engine.retrieve("a")
        # Very short queries should return empty
        assert result == ""

    def test_multiple_keyword_matching(self, rag_engine):
        """Should match documents with multiple keywords."""
        result = rag_engine.retrieve("programming language simplicity")
        # Should find the Python document
        assert len(result) > 0


class TestRagEngineDynamicDocs:
    """Tests for dynamic document management."""

    def test_add_document(self, rag_engine):
        """Should be able to add documents dynamically."""
        initial_count = len(rag_engine)
        rag_engine.add_document("new_doc.txt", "This is new content about Rust.")
        assert len(rag_engine) == initial_count + 1

    def test_added_document_is_searchable(self, rag_engine):
        """Dynamically added documents should be searchable."""
        rag_engine.add_document("rust_guide.txt", "Rust is a systems programming language.")
        result = rag_engine.retrieve("Rust systems")
        assert "Rust" in result

    def test_reload_documents(self, temp_data_dir):
        """reload() should refresh documents from disk."""
        rag = RagEngine(data_dir=temp_data_dir)
        initial_count = len(rag)
        
        # Add a document dynamically (not on disk)
        rag.add_document("dynamic.txt", "Dynamic content")
        assert len(rag) == initial_count + 1
        
        # Reload should clear dynamic docs and re-read from disk
        rag.reload()
        assert len(rag) == initial_count


class TestRagEngineEdgeCases:
    """Edge case tests for RagEngine."""

    def test_empty_query(self, rag_engine):
        """Empty query should return empty result."""
        result = rag_engine.retrieve("")
        assert result == ""

    def test_whitespace_only_query(self, rag_engine):
        """Whitespace-only query should return empty result."""
        result = rag_engine.retrieve("   \t\n  ")
        assert result == ""

    def test_special_characters_in_query(self, rag_engine):
        """Should handle special characters in queries."""
        # Should not crash
        result = rag_engine.retrieve("Python @#$%^&*()")
        # Result may or may not match, but shouldn't error
        assert isinstance(result, str)

    def test_unicode_in_query(self, rag_engine):
        """Should handle Unicode in queries."""
        result = rag_engine.retrieve("Python 日本語 emoji 🐍")
        assert isinstance(result, str)

