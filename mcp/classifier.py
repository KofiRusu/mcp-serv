"""
MCP Classifier - Intelligent content classification and tagging
"""

import re
from typing import List, Dict, Any, Optional
from .models import MemoryDomain


class MemoryClassifier:
    """Classify content into memory domains and extract tags"""
    
    DOMAIN_KEYWORDS = {
        MemoryDomain.PROJECT_KNOWLEDGE: [
            "architecture", "design", "pattern", "decision", "api",
            "deployment", "configuration", "database", "schema",
        ],
        MemoryDomain.COMMUNICATION_STYLE: [
            "tone", "format", "style", "prefer", "convention", "documentation",
        ],
        MemoryDomain.PROGRESS_TRACKING: [
            "completed", "pending", "blocker", "task", "milestone", "progress",
        ],
        MemoryDomain.DOMAIN_SPECIFIC: [
            "algorithm", "optimization", "performance", "machine learning",
            "security", "best practice",
        ],
        MemoryDomain.CODE_PATTERNS: [
            "pattern", "implementation", "refactor", "code review", "example",
        ],
        MemoryDomain.TOOLS_CONFIG: [
            "tool", "configuration", "setup", "environment", "build",
        ],
    }
    
    TAG_PATTERNS = {
        "database": r"\b(?:sql|postgresql|mysql|mongodb|redis|dynamodb)\b",
        "framework": r"\b(?:react|angular|django|fastapi|flask)\b",
        "language": r"\b(?:python|javascript|typescript|java|go)\b",
        "cloud": r"\b(?:aws|gcp|azure|kubernetes|docker)\b",
        "performance": r"\b(?:optimization|cache|caching|speed|performance)\b",
        "security": r"\b(?:encryption|auth|security|oauth|jwt)\b",
    }
    
    def classify(self, content: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Classify content and extract metadata"""
        
        full_text = f"{title or ''} {content}".lower()
        
        # Determine domain
        domain_scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(
                1 for kw in keywords
                if re.search(r'\b' + re.escape(kw) + r'\b', full_text)
            )
            if score > 0:
                domain_scores[domain.value] = score
        
        domains = [d for d, _ in sorted(
            domain_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]]
        
        domain = domains[0] if domains else MemoryDomain.DOMAIN_SPECIFIC.value
        
        # Extract tags
        tags = []
        for tag_name, pattern in self.TAG_PATTERNS.items():
            if re.search(pattern, full_text, re.IGNORECASE):
                tags.append(tag_name)
        
        # Determine priority
        priority = "medium"
        if any(word in full_text for word in ["critical", "urgent", "important", "must"]):
            priority = "high"
        elif any(word in full_text for word in ["optional", "nice", "could"]):
            priority = "low"
        
        # Generate title if not provided
        suggested_title = None
        if not title:
            sentences = re.split(r'[.!?]', content)
            suggested_title = sentences[0][:80] if sentences else content[:80]
        
        return {
            "domain": domain,
            "tags": tags,
            "priority": priority,
            "suggested_title": suggested_title,
        }
