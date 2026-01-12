"""
ChatOS Data Ingestion Module

Provides loaders for various training data sources:
- HuggingFace datasets
- Web scraping
- ChatOS conversation sync
- Deduplication utilities
"""

from chatos_backend.ingestion.huggingface_loader import (
    HuggingFaceLoader,
    RECOMMENDED_DATASETS,
    load_huggingface_dataset,
)
from chatos_backend.ingestion.web_scraper import (
    WebScraper,
    ScrapeConfig,
    scrape_url,
)
from chatos_backend.ingestion.chatos_sync import (
    ChatOSSync,
    sync_chatos_conversations,
    sync_persrm_data,
)
from chatos_backend.ingestion.deduplicator import (
    Deduplicator,
    compute_content_hash,
    find_duplicates,
)

__all__ = [
    # HuggingFace
    "HuggingFaceLoader",
    "RECOMMENDED_DATASETS",
    "load_huggingface_dataset",
    # Web Scraper
    "WebScraper",
    "ScrapeConfig",
    "scrape_url",
    # ChatOS Sync
    "ChatOSSync",
    "sync_chatos_conversations",
    "sync_persrm_data",
    # Deduplication
    "Deduplicator",
    "compute_content_hash",
    "find_duplicates",
]

