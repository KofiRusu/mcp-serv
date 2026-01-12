"""
Knowledge Base for AGI Core

Provides RAG (Retrieval-Augmented Generation) capabilities:
- Document indexing
- Vector search (when embeddings available)
- Keyword-based fallback
"""

from .rag_store import RAGStore, Document

__all__ = [
    "RAGStore",
    "Document",
]

