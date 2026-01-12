"""
ChatOS Learning Loop Database

PostgreSQL-based database for organizing, storing, and processing
training data from multiple sources with active learning capabilities.
Also includes authentication and usage logging models.
"""

from chatos_backend.database.connection import (
    get_engine,
    get_session,
    init_database,
    DatabaseSession,
)
from chatos_backend.database.models import (
    DataSource,
    TrainingExample,
    KnowledgeDomain,
    CoverageAnalysis,
    ScrapeTarget,
    ScrapeResult,
    ActiveLearningTask,
    TrainingRun,
)
from chatos_backend.database.auth_models import (
    UserSession,
    APIUsageLog,
    FeatureUsage,
    AuditLog,
)

__all__ = [
    # Connection
    "get_engine",
    "get_session",
    "init_database",
    "DatabaseSession",
    # Training Models
    "DataSource",
    "TrainingExample",
    "KnowledgeDomain",
    "CoverageAnalysis",
    "ScrapeTarget",
    "ScrapeResult",
    "ActiveLearningTask",
    "TrainingRun",
    # Auth & Logging Models
    "UserSession",
    "APIUsageLog",
    "FeatureUsage",
    "AuditLog",
]

