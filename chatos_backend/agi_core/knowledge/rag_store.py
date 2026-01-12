"""
RAG Knowledge Store for AGI Core

Provides document indexing and retrieval for knowledge-augmented generation.
"""

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """
    A document in the knowledge base.
    
    Attributes:
        id: Unique document identifier
        content: Document text content
        source: Source path or URL
        title: Document title
        metadata: Additional document metadata
        chunks: Chunked content for retrieval
    """
    content: str
    source: str = ""
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[str] = field(default_factory=list)
    id: str = ""
    indexed_at: float = field(default_factory=time.time)
    
    def __post_init__(self):
        if not self.id:
            data = f"{self.content[:100]}{self.source}{time.time()}"
            self.id = hashlib.sha256(data.encode()).hexdigest()[:12]
        
        if not self.chunks and self.content:
            self.chunks = self._chunk_content()
    
    def _chunk_content(self, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split content into overlapping chunks."""
        chunks = []
        text = self.content
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\n+', text)
        
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "title": self.title,
            "metadata": self.metadata,
            "chunks": self.chunks,
            "indexed_at": self.indexed_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        return cls(
            id=data.get("id", ""),
            content=data["content"],
            source=data.get("source", ""),
            title=data.get("title", ""),
            metadata=data.get("metadata", {}),
            chunks=data.get("chunks", []),
            indexed_at=data.get("indexed_at", time.time()),
        )


class RAGStore:
    """
    Knowledge store with retrieval-augmented generation capabilities.
    
    Indexes documents and retrieves relevant content for queries.
    
    Usage:
        store = RAGStore()
        store.index_document(Document(content="...", source="docs/guide.md"))
        results = store.query("How do I configure X?")
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        use_embeddings: bool = False,
    ):
        self.storage_path = storage_path or Path.home() / "ChatOS-Memory" / "agi" / "knowledge"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.storage_path / "index.json"
        self.use_embeddings = use_embeddings
        
        self._documents: Dict[str, Document] = {}
        self._chunk_index: Dict[str, str] = {}  # chunk_id -> doc_id
        self._encoder = None
        self._embeddings: Dict[str, List[float]] = {}  # chunk_id -> embedding
        
        self._load_index()
        
        if use_embeddings:
            self._init_embeddings()
    
    def _load_index(self) -> None:
        """Load document index from disk."""
        if not self.index_file.exists():
            return
        
        try:
            data = json.loads(self.index_file.read_text(encoding="utf-8"))
            for doc_data in data.get("documents", []):
                doc = Document.from_dict(doc_data)
                self._documents[doc.id] = doc
                for i, chunk in enumerate(doc.chunks):
                    chunk_id = f"{doc.id}_{i}"
                    self._chunk_index[chunk_id] = doc.id
        except Exception as e:
            print(f"Warning: Failed to load RAG index: {e}")
    
    def _save_index(self) -> None:
        """Save document index to disk."""
        data = {
            "version": 1,
            "updated_at": time.time(),
            "documents": [d.to_dict() for d in self._documents.values()],
        }
        
        temp_file = self.index_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_file.replace(self.index_file)
    
    def _init_embeddings(self) -> None:
        """Initialize embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            print("Warning: sentence-transformers not available")
            self.use_embeddings = False
    
    def index_document(self, doc: Document) -> str:
        """
        Index a document for retrieval.
        
        Args:
            doc: Document to index
            
        Returns:
            Document ID
        """
        self._documents[doc.id] = doc
        
        # Index chunks
        for i, chunk in enumerate(doc.chunks):
            chunk_id = f"{doc.id}_{i}"
            self._chunk_index[chunk_id] = doc.id
            
            if self.use_embeddings and self._encoder:
                self._embeddings[chunk_id] = self._encoder.encode(chunk).tolist()
        
        self._save_index()
        return doc.id
    
    def index_file(self, filepath: Path) -> Optional[str]:
        """
        Index a file from disk.
        
        Args:
            filepath: Path to file
            
        Returns:
            Document ID, or None if failed
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            return None
        
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            doc = Document(
                content=content,
                source=str(filepath),
                title=filepath.name,
                metadata={"file_type": filepath.suffix},
            )
            return self.index_document(doc)
        except Exception as e:
            print(f"Warning: Failed to index {filepath}: {e}")
            return None
    
    def index_directory(self, dirpath: Path, patterns: List[str] = None) -> int:
        """
        Index all matching files in a directory.
        
        Args:
            dirpath: Directory to index
            patterns: File patterns to include (default: common text files)
            
        Returns:
            Number of files indexed
        """
        patterns = patterns or ["*.md", "*.txt", "*.py", "*.json", "*.yaml", "*.rst"]
        dirpath = Path(dirpath)
        
        count = 0
        for pattern in patterns:
            for filepath in dirpath.rglob(pattern):
                if self.index_file(filepath):
                    count += 1
        
        return count
    
    def query(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the knowledge base.
        
        Args:
            query: Search query
            k: Maximum results
            
        Returns:
            List of relevant chunks with metadata
        """
        if self.use_embeddings and self._encoder and self._embeddings:
            return self._query_embeddings(query, k)
        return self._query_keywords(query, k)
    
    def _query_embeddings(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Query using embedding similarity."""
        import numpy as np
        
        query_embedding = np.array(self._encoder.encode(query))
        
        scores = []
        for chunk_id, embedding in self._embeddings.items():
            emb = np.array(embedding)
            similarity = np.dot(query_embedding, emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(emb)
            )
            scores.append((chunk_id, similarity))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for chunk_id, score in scores[:k]:
            doc_id = self._chunk_index.get(chunk_id)
            if doc_id and doc_id in self._documents:
                doc = self._documents[doc_id]
                chunk_idx = int(chunk_id.split("_")[-1])
                
                results.append({
                    "content": doc.chunks[chunk_idx] if chunk_idx < len(doc.chunks) else "",
                    "source": doc.source,
                    "title": doc.title,
                    "score": float(score),
                    "doc_id": doc_id,
                })
        
        return results
    
    def _query_keywords(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Query using keyword matching."""
        query_lower = query.lower()
        keywords = query_lower.split()
        
        scored = []
        for chunk_id, doc_id in self._chunk_index.items():
            if doc_id not in self._documents:
                continue
            
            doc = self._documents[doc_id]
            chunk_idx = int(chunk_id.split("_")[-1])
            
            if chunk_idx >= len(doc.chunks):
                continue
            
            chunk = doc.chunks[chunk_idx]
            chunk_lower = chunk.lower()
            
            score = sum(1 for kw in keywords if kw in chunk_lower)
            
            if score > 0:
                scored.append({
                    "content": chunk,
                    "source": doc.source,
                    "title": doc.title,
                    "score": score,
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                })
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self._documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id not in self._documents:
            return False
        
        doc = self._documents[doc_id]
        
        # Remove chunks
        for i in range(len(doc.chunks)):
            chunk_id = f"{doc_id}_{i}"
            self._chunk_index.pop(chunk_id, None)
            self._embeddings.pop(chunk_id, None)
        
        del self._documents[doc_id]
        self._save_index()
        return True
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents."""
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "chunks": len(doc.chunks),
                "indexed_at": doc.indexed_at,
            }
            for doc in self._documents.values()
        ]
    
    def count(self) -> int:
        """Return number of indexed documents."""
        return len(self._documents)
    
    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        """
        Get formatted context for a query.
        
        Args:
            query: The query
            max_tokens: Maximum context length (approximate)
            
        Returns:
            Formatted context string
        """
        results = self.query(query, k=5)
        
        if not results:
            return ""
        
        context_parts = ["Relevant knowledge:"]
        total_len = 0
        
        for result in results:
            content = result["content"]
            if total_len + len(content) > max_tokens * 4:
                break
            
            context_parts.append(f"\n[From {result.get('source', 'unknown')}]")
            context_parts.append(content)
            total_len += len(content)
        
        return "\n".join(context_parts)

