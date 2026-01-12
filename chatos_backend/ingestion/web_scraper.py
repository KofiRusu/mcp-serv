"""
web_scraper.py - Web scraping module for training data collection.

Scrapes content from documentation, Q&A sites, tutorials, and code examples.
Includes rate limiting, content extraction, and conversion to training format.
"""

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import (
    DataSource,
    ExampleStatus,
    KnowledgeDomain,
    ScrapeResult,
    ScrapeTarget,
    SourceType,
    TrainingExample,
)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ScrapeConfig:
    """Configuration for web scraping."""
    # Rate limiting
    rate_limit_seconds: float = 1.0
    max_concurrent: int = 3
    max_retries: int = 3
    timeout_seconds: float = 30.0
    
    # Content extraction
    min_content_length: int = 100
    max_content_length: int = 50000
    
    # User agent
    user_agent: str = "ChatOS-LearningLoop/1.0 (Training Data Collection)"
    
    # Selectors for different site types
    selectors: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "documentation": {
            "content": "article, .content, .documentation, main",
            "title": "h1, .title, .page-title",
            "code": "pre code, .highlight code",
        },
        "qa": {
            "question": ".question, .post-text",
            "answer": ".answer, .accepted-answer",
            "title": "h1, .question-title",
        },
        "tutorial": {
            "content": "article, .tutorial-content, .post-body",
            "title": "h1, .entry-title",
            "code": "pre code, .code-block",
        },
        "code": {
            "content": ".readme, .markdown-body",
            "code": "pre code",
            "title": "h1, .repo-name",
        },
    })


# Pre-configured scrape targets for common sources
DEFAULT_SCRAPE_TARGETS = [
    {
        "name": "MDN Web Docs",
        "url_pattern": "https://developer.mozilla.org/en-US/docs/Web/",
        "scrape_type": "documentation",
        "target_domain": "javascript",
        "selectors": {
            "content": "article.main-page-content",
            "title": "h1",
            "code": "pre code",
        },
    },
    {
        "name": "React Documentation",
        "url_pattern": "https://react.dev/learn/",
        "scrape_type": "documentation",
        "target_domain": "react",
        "selectors": {
            "content": "article",
            "title": "h1",
            "code": "pre code",
        },
    },
    {
        "name": "Python Documentation",
        "url_pattern": "https://docs.python.org/3/",
        "scrape_type": "documentation",
        "target_domain": "python",
        "selectors": {
            "content": ".body",
            "title": "h1",
            "code": ".highlight pre",
        },
    },
    {
        "name": "Stack Overflow Python",
        "url_pattern": "https://stackoverflow.com/questions/tagged/python",
        "scrape_type": "qa",
        "target_domain": "python",
        "selectors": {
            "question": ".s-prose.js-post-body",
            "answer": ".accepted-answer .s-prose",
            "title": "#question-header h1",
        },
    },
    {
        "name": "Dev.to Tutorials",
        "url_pattern": "https://dev.to/t/tutorial",
        "scrape_type": "tutorial",
        "target_domain": "instruction_following",
        "selectors": {
            "content": "#article-body",
            "title": "h1",
            "code": "pre code",
        },
    },
]


# =============================================================================
# Web Scraper
# =============================================================================

class WebScraper:
    """
    Web scraper for collecting training data from various sources.
    
    Uses httpx for async HTTP requests and BeautifulSoup for parsing.
    """
    
    def __init__(self, config: Optional[ScrapeConfig] = None):
        """Initialize the scraper."""
        self.config = config or ScrapeConfig()
        self._last_request_time: Dict[str, float] = {}
        
        # Check dependencies
        self._httpx_available = False
        self._bs4_available = False
        
        try:
            import httpx
            self._httpx_available = True
        except ImportError:
            print("Warning: 'httpx' not installed. Run: pip install httpx")
        
        try:
            from bs4 import BeautifulSoup
            self._bs4_available = True
        except ImportError:
            print("Warning: 'beautifulsoup4' not installed. Run: pip install beautifulsoup4")
    
    def _ensure_dependencies(self):
        """Ensure required dependencies are available."""
        if not self._httpx_available or not self._bs4_available:
            raise RuntimeError(
                "Web scraping requires 'httpx' and 'beautifulsoup4'. "
                "Install with: pip install httpx beautifulsoup4"
            )
    
    def _compute_url_hash(self, url: str) -> str:
        """Compute hash of URL for deduplication."""
        return hashlib.sha256(url.encode()).hexdigest()
    
    def _get_domain_id(self, domain_name: str) -> Optional[int]:
        """Get domain ID by name."""
        with DatabaseSession() as db:
            domain = db.query(KnowledgeDomain).filter(
                KnowledgeDomain.name == domain_name
            ).first()
            return domain.id if domain else None
    
    async def _rate_limit(self, domain: str):
        """Apply rate limiting per domain."""
        now = time.time()
        last_time = self._last_request_time.get(domain, 0)
        wait_time = self.config.rate_limit_seconds - (now - last_time)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self._last_request_time[domain] = time.time()
    
    async def _fetch_url(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Fetch a URL with rate limiting.
        
        Returns:
            Tuple of (content, status_code, error_message)
        """
        import httpx
        
        domain = urlparse(url).netloc
        await self._rate_limit(domain)
        
        headers = {"User-Agent": self.config.user_agent}
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                if response.status_code == 200:
                    return response.text, response.status_code, None
                else:
                    return None, response.status_code, f"HTTP {response.status_code}"
        
        except httpx.TimeoutException:
            return None, 0, "Timeout"
        except Exception as e:
            return None, 0, str(e)
    
    def _extract_content(
        self,
        html: str,
        scrape_type: str,
        custom_selectors: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract content from HTML based on scrape type.
        
        Returns:
            Dict with extracted content fields
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        
        # Get selectors
        selectors = custom_selectors or self.config.selectors.get(scrape_type, {})
        
        extracted = {}
        
        # Extract title
        title_selector = selectors.get("title", "h1")
        title_elem = soup.select_one(title_selector)
        extracted["title"] = title_elem.get_text(strip=True) if title_elem else ""
        
        if scrape_type == "qa":
            # Extract Q&A format
            question_selector = selectors.get("question", ".question")
            answer_selector = selectors.get("answer", ".answer")
            
            question_elem = soup.select_one(question_selector)
            answer_elem = soup.select_one(answer_selector)
            
            extracted["question"] = question_elem.get_text(strip=True) if question_elem else ""
            extracted["answer"] = answer_elem.get_text(strip=True) if answer_elem else ""
            extracted["content"] = extracted["question"]
        else:
            # Extract main content
            content_selector = selectors.get("content", "article, main, .content")
            content_elem = soup.select_one(content_selector)
            
            if content_elem:
                extracted["content"] = content_elem.get_text(separator="\n", strip=True)
            else:
                # Fallback to body
                body = soup.find("body")
                extracted["content"] = body.get_text(separator="\n", strip=True) if body else ""
        
        # Extract code blocks
        code_selector = selectors.get("code", "pre code")
        code_blocks = soup.select(code_selector)
        extracted["code_blocks"] = [
            block.get_text(strip=True) for block in code_blocks
        ]
        
        return extracted
    
    def _content_to_training_example(
        self,
        extracted: Dict[str, Any],
        scrape_type: str,
        url: str,
    ) -> Optional[Dict[str, str]]:
        """
        Convert extracted content to training example format.
        
        Returns:
            Dict with system_prompt, user_input, assistant_output
        """
        title = extracted.get("title", "")
        content = extracted.get("content", "")
        
        # Skip if content too short
        if len(content) < self.config.min_content_length:
            return None
        
        # Truncate if too long
        if len(content) > self.config.max_content_length:
            content = content[:self.config.max_content_length] + "..."
        
        if scrape_type == "qa":
            # Q&A format
            question = extracted.get("question", "")
            answer = extracted.get("answer", "")
            
            if not question or not answer:
                return None
            
            return {
                "system_prompt": "You are a helpful programming assistant that provides clear, accurate answers to technical questions.",
                "user_input": question,
                "assistant_output": answer,
            }
        
        elif scrape_type == "documentation":
            # Documentation format - create explanation task
            if not title or not content:
                return None
            
            return {
                "system_prompt": "You are a technical documentation expert. Explain concepts clearly with examples when appropriate.",
                "user_input": f"Explain: {title}",
                "assistant_output": content,
            }
        
        elif scrape_type == "tutorial":
            # Tutorial format
            if not title or not content:
                return None
            
            # Add code examples if available
            code_blocks = extracted.get("code_blocks", [])
            if code_blocks:
                content += "\n\nCode Examples:\n" + "\n\n".join(code_blocks[:3])
            
            return {
                "system_prompt": "You are a programming instructor. Provide step-by-step tutorials with clear explanations.",
                "user_input": f"Write a tutorial about: {title}",
                "assistant_output": content,
            }
        
        elif scrape_type == "code":
            # Code repository format
            code_blocks = extracted.get("code_blocks", [])
            if not code_blocks:
                return None
            
            return {
                "system_prompt": "You are an expert programmer. Explain code clearly and provide working examples.",
                "user_input": f"Explain this code:\n```\n{code_blocks[0][:2000]}\n```",
                "assistant_output": content[:5000] if content else "This code demonstrates...",
            }
        
        return None
    
    async def scrape_url(
        self,
        url: str,
        scrape_type: str = "documentation",
        target_id: Optional[int] = None,
        custom_selectors: Optional[Dict[str, str]] = None,
    ) -> Optional[ScrapeResult]:
        """
        Scrape a single URL.
        
        Args:
            url: URL to scrape
            scrape_type: Type of content (documentation, qa, tutorial, code)
            target_id: Optional ScrapeTarget ID
            custom_selectors: Optional custom CSS selectors
        
        Returns:
            ScrapeResult object or None if failed
        """
        self._ensure_dependencies()
        
        url_hash = self._compute_url_hash(url)
        
        # Check if already scraped
        with DatabaseSession() as db:
            existing = db.query(ScrapeResult).filter(
                ScrapeResult.url_hash == url_hash
            ).first()
            
            if existing:
                print(f"URL already scraped: {url}")
                return existing
        
        # Fetch the page
        html, status_code, error = await self._fetch_url(url)
        
        # Create result record
        with DatabaseSession() as db:
            result = ScrapeResult(
                target_id=target_id or 0,
                url=url,
                url_hash=url_hash,
                http_status=status_code,
                error_message=error,
                scraped_at=datetime.utcnow(),
            )
            
            if html and status_code == 200:
                # Extract content
                extracted = self._extract_content(html, scrape_type, custom_selectors)
                
                result.title = extracted.get("title")
                result.raw_content = html[:100000]  # Limit raw storage
                result.extracted_content = extracted
                result.content_type = "text/html"
            
            db.add(result)
            db.flush()
            result_id = result.id
        
        return result
    
    async def scrape_target(
        self,
        target: ScrapeTarget,
        max_pages: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, int]:
        """
        Scrape all pages from a scrape target.
        
        This is a simplified implementation - in production you'd want
        to implement proper crawling with link discovery.
        
        Args:
            target: ScrapeTarget configuration
            max_pages: Maximum pages to scrape
            progress_callback: Optional progress callback
        
        Returns:
            Tuple of (pages_scraped, examples_generated)
        """
        self._ensure_dependencies()
        
        max_pages = max_pages or target.max_pages or 10
        pages_scraped = 0
        examples_generated = 0
        
        # For now, just scrape the base URL
        # A full implementation would discover and follow links
        result = await self.scrape_url(
            target.url_pattern,
            target.scrape_type or "documentation",
            target.id,
            target.selector_config,
        )
        
        if result and result.extracted_content:
            pages_scraped += 1
            
            # Convert to training example
            example_data = self._content_to_training_example(
                result.extracted_content,
                target.scrape_type or "documentation",
                target.url_pattern,
            )
            
            if example_data:
                # Get or create source
                source_id = self._ensure_source(target)
                domain_id = target.target_domain_id
                
                # Create training example
                self._create_training_example(
                    example_data,
                    source_id,
                    domain_id,
                    target.url_pattern,
                )
                examples_generated += 1
                
                # Mark result as processed
                with DatabaseSession() as db:
                    result_record = db.query(ScrapeResult).filter(
                        ScrapeResult.id == result.id
                    ).first()
                    if result_record:
                        result_record.is_processed = True
                        result_record.examples_generated = 1
                        result_record.processed_at = datetime.utcnow()
        
        # Update target stats
        with DatabaseSession() as db:
            target_record = db.query(ScrapeTarget).filter(
                ScrapeTarget.id == target.id
            ).first()
            if target_record:
                target_record.last_scraped_at = datetime.utcnow()
                target_record.total_pages_scraped = (
                    target_record.total_pages_scraped or 0
                ) + pages_scraped
                target_record.total_examples_extracted = (
                    target_record.total_examples_extracted or 0
                ) + examples_generated
        
        return pages_scraped, examples_generated
    
    def _ensure_source(self, target: ScrapeTarget) -> int:
        """Get or create a DataSource for web scraping."""
        source_name = f"web_{target.name.lower().replace(' ', '_')}"
        
        with DatabaseSession() as db:
            source = db.query(DataSource).filter(
                DataSource.name == source_name
            ).first()
            
            if not source:
                source = DataSource(
                    name=source_name,
                    source_type=SourceType.WEB_SCRAPE,
                    description=f"Web scraped from {target.name}",
                    config={
                        "url_pattern": target.url_pattern,
                        "scrape_type": target.scrape_type,
                    },
                    is_active=True,
                )
                db.add(source)
                db.flush()
            
            return source.id
    
    def _create_training_example(
        self,
        example_data: Dict[str, str],
        source_id: int,
        domain_id: Optional[int],
        url: str,
    ) -> Optional[int]:
        """Create a training example from scraped content."""
        content_hash = hashlib.sha256(
            f"{example_data['user_input']}|||{example_data['assistant_output']}".encode()
        ).hexdigest()
        
        with DatabaseSession() as db:
            # Check for duplicate
            existing = db.query(TrainingExample).filter(
                TrainingExample.content_hash == content_hash
            ).first()
            
            if existing:
                return None
            
            example = TrainingExample(
                source_id=source_id,
                external_id=self._compute_url_hash(url),
                system_prompt=example_data.get("system_prompt"),
                user_input=example_data["user_input"],
                assistant_output=example_data["assistant_output"],
                domain_id=domain_id,
                quality_score=0.6,  # Default quality for scraped
                status=ExampleStatus.PENDING,  # Needs review
                content_hash=content_hash,
                extra_data={
                    "source_url": url,
                    "scraped": True,
                },
            )
            db.add(example)
            db.flush()
            
            return example.id
    
    def add_scrape_target(
        self,
        name: str,
        url_pattern: str,
        scrape_type: str = "documentation",
        target_domain: str = "instruction_following",
        selectors: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Add a new scrape target to the database.
        
        Args:
            name: Display name for the target
            url_pattern: URL or URL pattern to scrape
            scrape_type: Type of content
            target_domain: Knowledge domain for extracted content
            selectors: Custom CSS selectors
        
        Returns:
            Created ScrapeTarget ID
        """
        domain_id = self._get_domain_id(target_domain)
        
        with DatabaseSession() as db:
            # Check if exists
            existing = db.query(ScrapeTarget).filter(
                ScrapeTarget.url_pattern == url_pattern
            ).first()
            
            if existing:
                return existing.id
            
            target = ScrapeTarget(
                name=name,
                url_pattern=url_pattern,
                scrape_type=scrape_type,
                selector_config=selectors,
                target_domain_id=domain_id,
                is_active=True,
            )
            db.add(target)
            db.flush()
            
            return target.id
    
    def list_scrape_targets(self) -> List[Dict[str, Any]]:
        """List all configured scrape targets."""
        with DatabaseSession() as db:
            targets = db.query(ScrapeTarget).filter(
                ScrapeTarget.is_active == True
            ).all()
            
            return [t.to_dict() for t in targets]
    
    def setup_default_targets(self) -> int:
        """
        Set up default scrape targets.
        
        Returns:
            Number of targets created
        """
        created = 0
        
        for target_config in DEFAULT_SCRAPE_TARGETS:
            target_id = self.add_scrape_target(
                name=target_config["name"],
                url_pattern=target_config["url_pattern"],
                scrape_type=target_config["scrape_type"],
                target_domain=target_config["target_domain"],
                selectors=target_config.get("selectors"),
            )
            if target_id:
                created += 1
        
        return created


# =============================================================================
# Convenience Functions
# =============================================================================

async def scrape_url(
    url: str,
    scrape_type: str = "documentation",
) -> Optional[Dict[str, Any]]:
    """
    Scrape a single URL and return extracted content.
    
    Args:
        url: URL to scrape
        scrape_type: Type of content
    
    Returns:
        Extracted content dict or None
    """
    scraper = WebScraper()
    result = await scraper.scrape_url(url, scrape_type)
    
    if result and result.extracted_content:
        return result.extracted_content
    return None


def setup_default_scrape_targets() -> int:
    """Set up default web scraping targets."""
    scraper = WebScraper()
    return scraper.setup_default_targets()


def list_scrape_targets() -> List[Dict[str, Any]]:
    """List all configured scrape targets."""
    scraper = WebScraper()
    return scraper.list_scrape_targets()

