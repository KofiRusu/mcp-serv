"""
rag.py - Retrieval-Augmented Generation support.

Features:
- Keyword-based retrieval (fast, always available)
- Embedding-based retrieval with sentence-transformers and FAISS (optional, higher quality)
- Document chunking for better precision
- Result caching with TTL
- Hybrid retrieval combining both methods

Usage:
    # Basic keyword retrieval
    rag = RagEngine(data_dir="./data")
    results = rag.retrieve("How do I configure logging?")
    
    # Enable embeddings for better results
    rag = RagEngine(data_dir="./data", use_embeddings=True)
    results = rag.retrieve("semantic search query")
"""

import asyncio
import glob
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from chatos_backend.config import (
    DATA_DIR,
    RAG_FILE_EXTENSIONS,
    RAG_MIN_QUERY_LENGTH,
    RAG_SNIPPET_MAX_LENGTH,
)
from chatos_backend.controllers.cache import (
    CacheKeys,
    CacheTTL,
    cache_key,
    get_cache,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Embedding model to use (small, fast, good quality)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Chunking configuration
DEFAULT_CHUNK_SIZE = 500  # characters
DEFAULT_CHUNK_OVERLAP = 50  # characters

RAG_CACHE_TTL = CacheTTL.MEDIUM


# =============================================================================
# Document Chunk
# =============================================================================

@dataclass
class DocumentChunk:
    """A chunk of a document for retrieval."""
    doc_name: str
    content: str
    chunk_index: int
    start_pos: int
    end_pos: int
    
    def __str__(self) -> str:
        return f"[{self.doc_name}] {self.content}"


# =============================================================================
# RAG Engine (Enhanced with Embeddings)
# =============================================================================

class RagEngine:
    """
    Enhanced retrieval engine supporting both keyword and embedding-based search.
    
    Features:
    - Keyword-based retrieval (fast, always available)
    - Embedding-based retrieval with FAISS (optional, higher quality)
    - Document chunking for better precision
    - Result caching
    - Hybrid retrieval mode
    
    Attributes:
        data_dir: Path to the directory containing documents
        use_embeddings: Whether to use embedding-based retrieval
        chunk_size: Size of document chunks in characters
        chunk_overlap: Overlap between chunks
    """
    
    def __init__(
        self,
        data_dir: Path = DATA_DIR,
        use_embeddings: bool = False,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        use_cache: bool = True,
    ):
        """
        Initialize the RAG engine.
        
        Args:
            data_dir: Directory containing documents to index
            use_embeddings: Enable embedding-based retrieval (requires sentence-transformers)
            embedding_model: Name of the sentence-transformers model to use
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between consecutive chunks
            use_cache: Enable result caching
        """
        self.data_dir = Path(data_dir) if isinstance(data_dir, str) else data_dir
        self.use_embeddings = use_embeddings
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_cache = use_cache
        self._cache = get_cache()
        
        # Document storage
        self.docs: List[Tuple[str, str]] = []  # (name, full_content)
        self.chunks: List[DocumentChunk] = []
        
        # Embedding components (lazy loaded)
        self._encoder = None
        self._embeddings = None
        self._index = None
        self._embeddings_initialized = False
        
        # Load documents
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
                    doc_name = os.path.basename(path)
                    self.docs.append((doc_name, text))
                    
                    # Create chunks
                    doc_chunks = self._chunk_text(doc_name, text)
                    self.chunks.extend(doc_chunks)
                except Exception as e:
                    logger.debug(f"Failed to load {path}: {e}")
                    continue
        
        logger.info(f"Loaded {len(self.docs)} documents, {len(self.chunks)} chunks")
    
    def _chunk_text(self, doc_name: str, text: str) -> List[DocumentChunk]:
        """
        Split text into overlapping chunks for better retrieval.
        
        Args:
            doc_name: Name of the source document
            text: Full document text
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at a sentence boundary
            if end < len(text):
                # Look for sentence boundary within the last 100 chars
                boundary_region = text[end - 100:end + 100] if end + 100 <= len(text) else text[end - 100:]
                for boundary in ['. ', '.\n', '? ', '! ', '\n\n']:
                    pos = boundary_region.find(boundary)
                    if pos != -1:
                        end = end - 100 + pos + len(boundary)
                        break
            
            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append(DocumentChunk(
                    doc_name=doc_name,
                    content=chunk_content,
                    chunk_index=chunk_idx,
                    start_pos=start,
                    end_pos=end,
                ))
                chunk_idx += 1
            
            # Move start with overlap
            start = end - self.chunk_overlap
            if start <= chunks[-1].start_pos if chunks else 0:
                start = end  # Prevent infinite loop
        
        return chunks
    
    def _init_embeddings(self) -> bool:
        """
        Lazy initialize embedding model and FAISS index.
        
        Returns:
            True if successfully initialized, False otherwise
        """
        if self._embeddings_initialized:
            return self._encoder is not None
        
        self._embeddings_initialized = True
        
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._encoder = SentenceTransformer(self.embedding_model_name)
            
            if not self.chunks:
                logger.warning("No chunks to embed")
                return True
            
            # Encode all chunks
            texts = [chunk.content for chunk in self.chunks]
            logger.info(f"Encoding {len(texts)} chunks...")
            self._embeddings = self._encoder.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            
            # Build FAISS index
            try:
                import faiss
                
                dim = self._embeddings.shape[1]
                # Use IVF index for faster search with many documents
                if len(self.chunks) > 1000:
                    nlist = min(100, len(self.chunks) // 10)
                    quantizer = faiss.IndexFlatL2(dim)
                    self._index = faiss.IndexIVFFlat(quantizer, dim, nlist)
                    self._index.train(self._embeddings.astype(np.float32))
                    self._index.add(self._embeddings.astype(np.float32))
                else:
                    self._index = faiss.IndexFlatL2(dim)
                    self._index.add(self._embeddings.astype(np.float32))
                
                logger.info(f"FAISS index built with {self._index.ntotal} vectors")
            except ImportError:
                logger.warning("FAISS not installed, using numpy for similarity search")
                self._index = None
            
            return True
            
        except ImportError as e:
            logger.warning(f"Embedding dependencies not available: {e}")
            logger.warning("Install with: pip install sentence-transformers faiss-cpu")
            self._encoder = None
            return False
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            self._encoder = None
            return False
    
    def retrieve(
        self,
        query: str,
        max_results: int = 3,
        use_embeddings: Optional[bool] = None,
    ) -> str:
        """Synchronous wrapper that runs the async retrieval."""
        return asyncio.run(self.retrieve_async(query, max_results, use_embeddings))

    async def retrieve_async(
        self,
        query: str,
        max_results: int = 3,
        use_embeddings: Optional[bool] = None,
    ) -> str:
        """
        Asynchronously retrieve document snippets for a query with unified caching.
        """
        normalized = query.strip()
        if len(normalized) < RAG_MIN_QUERY_LENGTH:
            return ""
        
        should_use_embeddings = use_embeddings if use_embeddings is not None else self.use_embeddings
        cache_result = None
        cache_key_value = None
        
        if self.use_cache:
            cache_key_value = cache_key(
                CacheKeys.RAG,
                normalized.lower(),
                max_results,
                should_use_embeddings,
            )
            cache_result = await self._cache.get(cache_key_value)
            if cache_result is not None:
                return cache_result
        
        result = await asyncio.to_thread(
            self._retrieve_internal,
            normalized,
            max_results,
            should_use_embeddings,
        )
        
        if self.use_cache and cache_key_value and result:
            await self._cache.set(cache_key_value, result, ttl=CacheTTL.MEDIUM)
        
        return result

    def _retrieve_internal(
        self,
        query: str,
        max_results: int,
        should_use_embeddings: bool,
    ) -> str:
        """Internal synchronous retrieval implementation."""
        if should_use_embeddings and self._init_embeddings() and self._encoder is not None:
            return self._retrieve_embeddings(query, max_results)
        return self._retrieve_keywords(query, max_results)
    
    def _retrieve_embeddings(self, query: str, max_results: int) -> str:
        """Retrieve using embedding similarity."""
        import numpy as np
        
        # Encode query
        query_embedding = self._encoder.encode([query], convert_to_numpy=True)
        
        if self._index is not None:
            # FAISS search
            distances, indices = self._index.search(
                query_embedding.astype(np.float32),
                min(max_results * 2, len(self.chunks)),  # Get extra for deduplication
            )
            indices = indices[0]
        else:
            # Fallback to numpy cosine similarity
            similarities = np.dot(self._embeddings, query_embedding.T).flatten()
            indices = np.argsort(similarities)[::-1][:max_results * 2]
        
        # Deduplicate by document and collect results
        seen_docs = set()
        results = []
        
        for idx in indices:
            if idx < 0 or idx >= len(self.chunks):
                continue
            
            chunk = self.chunks[idx]
            
            # Skip if we already have content from this document
            if chunk.doc_name in seen_docs and len(results) < max_results:
                continue
            
            seen_docs.add(chunk.doc_name)
            results.append(f"[{chunk.doc_name}] {chunk.content}")
            
            if len(results) >= max_results:
                break
        
        return "\n\n".join(results)
    
    def _retrieve_keywords(self, query: str, max_results: int) -> str:
        """Retrieve using keyword matching (original algorithm)."""
        q_lower = query.lower()
        words = [w for w in q_lower.split() if len(w) > 2]  # Filter short words
        
        matches: List[Tuple[str, str, float]] = []
        
        for chunk in self.chunks:
            text_lower = chunk.content.lower()
            
            # Count keyword matches with weighting
            match_score = 0
            for word in words:
                if word in text_lower:
                    # Bonus for exact word matches
                    match_score += text_lower.count(word)
            
            if match_score > 0:
                matches.append((chunk.doc_name, chunk.content, match_score))
        
        if not matches:
            # Fallback to full documents
            return self._retrieve_keywords_full_docs(query, max_results)
        
        # Sort by score and deduplicate by document
        matches.sort(key=lambda x: x[2], reverse=True)
        
        seen_docs = set()
        results = []
        
        for name, content, _ in matches:
            if name in seen_docs and len(results) < max_results:
                continue
            
            seen_docs.add(name)
            results.append(f"[{name}] {content}")
            
            if len(results) >= max_results:
                break
        
        return "\n\n".join(results)
    
    def _retrieve_keywords_full_docs(self, query: str, max_results: int) -> str:
        """Fallback keyword search on full documents."""
        q_lower = query.lower()
        words = q_lower.split()
        
        matches: List[Tuple[str, str, int]] = []
        
        for name, text in self.docs:
            text_lower = text.lower()
            match_count = sum(1 for word in words if word in text_lower)
            
            if match_count > 0:
                snippet = self._extract_snippet(text, words)
                matches.append((name, snippet, match_count))
        
        if not matches:
            return ""
        
        matches.sort(key=lambda x: x[2], reverse=True)
        top_matches = matches[:max_results]
        
        results = []
        for name, snippet, _ in top_matches:
            results.append(f"[{name}] {snippet}")
        
        return "\n\n".join(results)
    
    def _extract_snippet(self, text: str, keywords: List[str]) -> str:
        """Extract a relevant snippet from text around keyword matches."""
        text_lower = text.lower()
        
        # Find the first keyword occurrence
        first_pos = len(text)
        for word in keywords:
            pos = text_lower.find(word)
            if pos != -1 and pos < first_pos:
                first_pos = pos
        
        if first_pos == len(text):
            snippet = text[:RAG_SNIPPET_MAX_LENGTH]
        else:
            start = max(0, first_pos - 50)
            end = min(len(text), first_pos + RAG_SNIPPET_MAX_LENGTH - 50)
            snippet = text[start:end]
            
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
        
        snippet = " ".join(snippet.split())
        return snippet
    
    def add_document(self, name: str, content: str) -> None:
        """
        Add a document to the RAG engine dynamically.
        
        Note: If embeddings are enabled, they will need to be rebuilt.
        """
        self.docs.append((name, content))
        doc_chunks = self._chunk_text(name, content)
        self.chunks.extend(doc_chunks)
        
        # Invalidate embeddings
        if self._embeddings_initialized:
            self._embeddings_initialized = False
            self._embeddings = None
            self._index = None
        
        # Clear cache
        _rag_cache.clear()
    
    def list_documents(self) -> List[str]:
        """List all loaded document names."""
        return [name for name, _ in self.docs]
    
    def reload(self) -> None:
        """Reload documents from the data directory."""
        self.docs.clear()
        self.chunks.clear()
        self._embeddings_initialized = False
        self._embeddings = None
        self._index = None
        _rag_cache.clear()
        self._load_docs()
    
    def enable_embeddings(self) -> bool:
        """
        Enable embedding-based retrieval.
        
        Returns:
            True if embeddings were successfully initialized
        """
        self.use_embeddings = True
        return self._init_embeddings()
    
    def stats(self) -> Dict[str, Any]:
        """Get RAG engine statistics."""
        return {
            "documents": len(self.docs),
            "chunks": len(self.chunks),
            "embeddings_enabled": self.use_embeddings,
            "embeddings_initialized": self._embeddings_initialized,
            "embedding_model": self.embedding_model_name if self._encoder else None,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
    
    def __len__(self) -> int:
        """Return the number of loaded documents."""
        return len(self.docs)
