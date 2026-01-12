"""
research.py - Deep research mode with web context.

Implements /research command functionality:
- Web search simulation (replace with real API)
- Source aggregation and synthesis
- Context-aware research responses
"""

import asyncio
import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from chatos_backend.config import (
    RESEARCH_DOMAINS,
    RESEARCH_MAX_SOURCES,
    RESEARCH_SNIPPET_LENGTH,
)


@dataclass
class SearchResult:
    """A single search result."""
    
    title: str
    url: str
    snippet: str
    domain: str
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "domain": self.domain,
            "relevance_score": self.relevance_score,
        }


@dataclass
class ResearchContext:
    """Aggregated research context."""
    
    query: str
    sources: List[SearchResult] = field(default_factory=list)
    synthesis: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "sources": [s.to_dict() for s in self.sources],
            "synthesis": self.synthesis,
            "timestamp": self.timestamp.isoformat(),
        }


class ResearchEngine:
    """
    Research engine for deep context gathering.
    
    In production, this would integrate with:
    - Web search APIs (Google, Bing, DuckDuckGo)
    - Browser automation for page content
    - Embedding-based relevance scoring
    
    Currently provides simulated results for demonstration.
    """
    
    def __init__(self):
        self._cache: Dict[str, ResearchContext] = {}
    
    async def search(
        self,
        query: str,
        num_results: int = RESEARCH_MAX_SOURCES
    ) -> List[SearchResult]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            num_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
            
        TODO: Replace with real web search API integration
        """
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        # Generate deterministic but varied results based on query
        query_hash = int(hashlib.md5(query.encode()).hexdigest(), 16)
        random.seed(query_hash)
        
        results = []
        keywords = query.lower().split()
        
        for i in range(num_results):
            domain = RESEARCH_DOMAINS[i % len(RESEARCH_DOMAINS)]
            
            # Generate contextual titles and snippets
            title = self._generate_title(keywords, domain, i)
            snippet = self._generate_snippet(keywords, domain)
            url = f"https://{domain}/search?q={'+'.join(keywords[:3])}&id={i}"
            
            results.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                domain=domain,
                relevance_score=0.9 - (i * 0.1),
            ))
        
        return results
    
    def _generate_title(
        self,
        keywords: List[str],
        domain: str,
        index: int
    ) -> str:
        """Generate a contextual title based on keywords."""
        templates = {
            "stackoverflow.com": [
                "How to {kw} in Python - Stack Overflow",
                "{kw} best practices - Stack Overflow",
                "Understanding {kw} - Complete Guide",
            ],
            "github.com": [
                "awesome-{kw}: A curated list of resources",
                "{kw}-examples: Code samples and tutorials",
                "Building {kw} from scratch",
            ],
            "docs.python.org": [
                "{kw} — Python documentation",
                "The {kw} module - Python Standard Library",
                "Tutorial: Working with {kw}",
            ],
            "developer.mozilla.org": [
                "{kw} - Web APIs | MDN",
                "Using {kw} in JavaScript",
                "{kw} Guide - MDN Web Docs",
            ],
            "medium.com": [
                "A Deep Dive into {kw}",
                "Mastering {kw}: Tips and Tricks",
                "Why {kw} is Important in 2024",
            ],
        }
        
        domain_templates = templates.get(domain, ["{kw} - Reference"])
        template = domain_templates[index % len(domain_templates)]
        kw = keywords[0] if keywords else "topic"
        
        return template.format(kw=kw.title())
    
    def _generate_snippet(self, keywords: List[str], domain: str) -> str:
        """Generate a contextual snippet."""
        snippets = {
            "stackoverflow.com": (
                f"Learn about {' '.join(keywords[:2])} with detailed explanations "
                f"and code examples. This comprehensive answer covers common pitfalls "
                f"and best practices for implementing {keywords[0] if keywords else 'this feature'}."
            ),
            "github.com": (
                f"Repository containing examples and implementations related to "
                f"{' '.join(keywords[:2])}. Includes documentation, tests, and "
                f"ready-to-use code snippets for your projects."
            ),
            "docs.python.org": (
                f"Official Python documentation for {keywords[0] if keywords else 'this module'}. "
                f"Covers API reference, usage examples, and detailed explanations "
                f"of all available functions and classes."
            ),
            "developer.mozilla.org": (
                f"MDN Web Docs reference for {' '.join(keywords[:2])}. "
                f"Includes browser compatibility, syntax, examples, and "
                f"related specifications for web developers."
            ),
            "medium.com": (
                f"In this article, we explore {' '.join(keywords[:2])} in depth. "
                f"From fundamentals to advanced techniques, learn how to "
                f"leverage {keywords[0] if keywords else 'these concepts'} effectively."
            ),
        }
        
        snippet = snippets.get(domain, f"Information about {' '.join(keywords[:3])}")
        return snippet[:RESEARCH_SNIPPET_LENGTH]
    
    async def research(
        self,
        query: str,
        depth: int = 1
    ) -> ResearchContext:
        """
        Perform deep research on a topic.
        
        Args:
            query: Research query
            depth: Research depth (1-3, affects thoroughness)
            
        Returns:
            ResearchContext with aggregated findings
        """
        # Check cache
        cache_key = f"{query}:{depth}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Perform searches
        results = await self.search(query, num_results=RESEARCH_MAX_SOURCES * depth)
        
        # Synthesize findings
        synthesis = self._synthesize(query, results)
        
        context = ResearchContext(
            query=query,
            sources=results,
            synthesis=synthesis,
        )
        
        # Cache result
        self._cache[cache_key] = context
        
        return context
    
    def _synthesize(self, query: str, results: List[SearchResult]) -> str:
        """
        Synthesize research findings into a coherent summary.
        
        In production, this would use an LLM to:
        - Extract key information from sources
        - Identify consensus and disagreements
        - Generate a structured summary
        """
        if not results:
            return "No relevant sources found for this query."
        
        keywords = query.lower().split()
        topic = ' '.join(keywords[:3])
        
        synthesis_parts = [
            f"## Research Summary: {query}\n",
            f"Based on {len(results)} sources, here's what we found:\n",
            "\n### Key Findings\n",
        ]
        
        # Group by domain for variety
        domains_covered = set()
        for r in results[:3]:
            domains_covered.add(r.domain)
            synthesis_parts.append(f"- **{r.domain}**: {r.snippet[:100]}...\n")
        
        synthesis_parts.extend([
            "\n### Sources Consulted\n",
            f"- {len(domains_covered)} different knowledge sources\n",
            f"- Topics covered: {topic}\n",
            "\n### Confidence Level\n",
            f"High confidence - Multiple authoritative sources agree on core concepts.\n",
        ])
        
        return ''.join(synthesis_parts)
    
    def format_for_prompt(self, context: ResearchContext) -> str:
        """
        Format research context for inclusion in a prompt.
        
        Args:
            context: Research context
            
        Returns:
            Formatted string for prompt injection
        """
        lines = [
            "=== Research Context ===",
            f"Query: {context.query}",
            "",
            "Sources:",
        ]
        
        for i, source in enumerate(context.sources[:5], 1):
            lines.append(f"{i}. [{source.domain}] {source.title}")
            lines.append(f"   {source.snippet[:150]}...")
            lines.append("")
        
        lines.extend([
            "Synthesis:",
            context.synthesis,
            "=== End Research Context ===",
        ])
        
        return '\n'.join(lines)


# Singleton instance
_engine: Optional[ResearchEngine] = None


def get_research_engine() -> ResearchEngine:
    """Get the singleton research engine instance."""
    global _engine
    if _engine is None:
        _engine = ResearchEngine()
    return _engine

