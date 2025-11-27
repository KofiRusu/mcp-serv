"""
rag.py - Retrieval-Augmented Generation support.

The RagEngine scans a directory of text files and retrieves relevant
snippets based on keyword matches. This simple implementation can be
extended to use embeddings and vector stores for better results.

============================================================================
FUTURE: EMBEDDING-BASED RAG
============================================================================

To upgrade to embedding-based retrieval:

1. Install dependencies:
   pip install sentence-transformers faiss-cpu  # or chromadb

2. Modify RagEngine:

```python
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class EmbeddingRagEngine:
    def __init__(self, data_dir: str):
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.docs = []
        self.embeddings = None
        self.index = None
        self._load_and_embed(data_dir)
    
    def _load_and_embed(self, data_dir: str):
        # Load documents
        for path in Path(data_dir).glob("*.txt"):
            text = path.read_text()
            # Chunk the document
            chunks = self._chunk_text(text, chunk_size=500)
            for chunk in chunks:
                self.docs.append((path.name, chunk))
        
        # Create embeddings
        texts = [doc[1] for doc in self.docs]
        self.embeddings = self.encoder.encode(texts)
        
        # Build FAISS index
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(self.embeddings)
    
    def retrieve(self, query: str, top_k: int = 3) -> str:
        query_embedding = self.encoder.encode([query])
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for idx in indices[0]:
            if idx < len(self.docs):
                name, chunk = self.docs[idx]
                results.append(f"From {name}: {chunk}")
        
        return "\\n\\n".join(results)
```

============================================================================
"""

import glob
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from ChatOS.config import (
    DATA_DIR,
    RAG_FILE_EXTENSIONS,
    RAG_MIN_QUERY_LENGTH,
    RAG_SNIPPET_MAX_LENGTH,
)


@dataclass
class RagEngine:
    """
    A simple keyword-based retrieval engine.
    
    Scans a directory for text files and performs naive keyword matching
    to find relevant context for user queries.
    
    Attributes:
        data_dir: Path to the directory containing documents
        docs: List of (filename, content) tuples
    """
    
    data_dir: Path = field(default=DATA_DIR)
    docs: List[Tuple[str, str]] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Load documents after initialization."""
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        self._load_docs()

    def _load_docs(self) -> None:
        """Load all text documents from the data directory."""
        if not self.data_dir.is_dir():
            return
        
        for ext in RAG_FILE_EXTENSIONS:
            pattern = self.data_dir / f"*{ext}"
            for path in glob.glob(str(pattern)):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        text = fh.read()
                    self.docs.append((os.path.basename(path), text))
                except Exception:
                    # Skip unreadable files silently
                    continue

    def retrieve(self, query: str, max_results: int = 3) -> str:
        """
        Retrieve relevant document snippets for a query.
        
        Performs case-insensitive keyword matching across all loaded
        documents and returns matching snippets.
        
        Args:
            query: The search query
            max_results: Maximum number of snippets to return
            
        Returns:
            Formatted string of matching snippets, or empty string if none found
        """
        # Skip very short queries
        if len(query.strip()) < RAG_MIN_QUERY_LENGTH:
            return ""
        
        q_lower = query.lower()
        words = q_lower.split()
        
        matches: List[Tuple[str, str, int]] = []
        
        for name, text in self.docs:
            text_lower = text.lower()
            
            # Count keyword matches
            match_count = sum(1 for word in words if word in text_lower)
            
            if match_count > 0:
                # Extract relevant snippet
                snippet = self._extract_snippet(text, words)
                matches.append((name, snippet, match_count))
        
        if not matches:
            return ""
        
        # Sort by match count (descending) and take top results
        matches.sort(key=lambda x: x[2], reverse=True)
        top_matches = matches[:max_results]
        
        # Format results
        results = []
        for name, snippet, _ in top_matches:
            results.append(f"[{name}] {snippet}")
        
        return "\n\n".join(results)

    def _extract_snippet(self, text: str, keywords: List[str]) -> str:
        """
        Extract a relevant snippet from text around keyword matches.
        
        Args:
            text: The full document text
            keywords: List of keywords to find
            
        Returns:
            A snippet of text around the first keyword match
        """
        text_lower = text.lower()
        
        # Find the first keyword occurrence
        first_pos = len(text)
        for word in keywords:
            pos = text_lower.find(word)
            if pos != -1 and pos < first_pos:
                first_pos = pos
        
        if first_pos == len(text):
            # No match found, return beginning of text
            snippet = text[:RAG_SNIPPET_MAX_LENGTH]
        else:
            # Extract snippet centered around the match
            start = max(0, first_pos - 50)
            end = min(len(text), first_pos + RAG_SNIPPET_MAX_LENGTH - 50)
            snippet = text[start:end]
            
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
        
        # Clean up whitespace
        snippet = " ".join(snippet.split())
        
        return snippet

    def add_document(self, name: str, content: str) -> None:
        """
        Add a document to the RAG engine dynamically.
        
        Args:
            name: Display name for the document
            content: The document text content
        """
        self.docs.append((name, content))

    def list_documents(self) -> List[str]:
        """
        List all loaded document names.
        
        Returns:
            List of document filenames
        """
        return [name for name, _ in self.docs]

    def reload(self) -> None:
        """Reload documents from the data directory."""
        self.docs.clear()
        self._load_docs()

    def __len__(self) -> int:
        """Return the number of loaded documents."""
        return len(self.docs)

