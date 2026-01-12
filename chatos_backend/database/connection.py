"""
connection.py - PostgreSQL database connection management.

Provides SQLAlchemy engine and session management for the learning loop database.
Supports Docker secrets for credential management.
"""

import os
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


def _read_secret(file_path: str) -> str:
    """Read a secret from a file path, stripping whitespace."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(f"Secret file not found: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Error reading secret from {file_path}: {e}")
        return ""


def _build_database_url() -> str:
    """
    Build database URL from environment variables.
    Supports Docker secrets (reading from files) or direct values.
    """
    # Check for direct URL first
    direct_url = os.environ.get("CHATOS_DATABASE_URL")
    if direct_url:
        return direct_url
    
    # Build from components (supports Docker secrets)
    host = os.environ.get("CHATOS_DATABASE_HOST", "localhost")
    port = os.environ.get("CHATOS_DATABASE_PORT", "5432")
    db_name = os.environ.get("CHATOS_DATABASE_NAME", "chatos")
    
    # User - try file first, then env, then default
    user_file = os.environ.get("CHATOS_DATABASE_USER_FILE")
    if user_file and Path(user_file).exists():
        user = _read_secret(user_file)
    else:
        user = os.environ.get("CHATOS_DATABASE_USER", "chatos")
    
    # Password - try file first, then env, then default
    password_file = os.environ.get("CHATOS_DATABASE_PASSWORD_FILE")
    if password_file and Path(password_file).exists():
        password = _read_secret(password_file)
    else:
        password = os.environ.get("CHATOS_DATABASE_PASSWORD", "chatos")
    
    url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    logger.debug(f"Built database URL: postgresql://{user}:***@{host}:{port}/{db_name}")
    return url


# For testing, allow SQLite fallback
USE_SQLITE_FALLBACK = os.environ.get("CHATOS_USE_SQLITE", "false").lower() == "true"
SQLITE_PATH = os.environ.get(
    "CHATOS_SQLITE_PATH",
    os.path.expanduser("~/ChatOS-Memory/learning_loop.db")
)

# Global engine instance
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_url() -> str:
    """Get the database URL based on configuration."""
    if USE_SQLITE_FALLBACK:
        return f"sqlite:///{SQLITE_PATH}"
    return _build_database_url()


def get_engine() -> Engine:
    """
    Get or create the SQLAlchemy engine.
    
    Uses connection pooling for PostgreSQL, or StaticPool for SQLite.
    
    Returns:
        SQLAlchemy Engine instance
    """
    global _engine
    
    if _engine is None:
        url = get_database_url()
        
        if url.startswith("sqlite"):
            # SQLite configuration for local development/testing
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )
            # Enable foreign keys for SQLite
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL configuration with connection pooling
            _engine = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
            )
    
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _SessionLocal
    
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    
    return _SessionLocal


def get_session() -> Session:
    """
    Create a new database session.
    
    Note: Caller is responsible for closing the session.
    
    Returns:
        New SQLAlchemy Session
    """
    SessionLocal = get_session_factory()
    return SessionLocal()


@contextmanager
def DatabaseSession() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Automatically handles commit/rollback and session cleanup.
    
    Usage:
        with DatabaseSession() as db:
            db.query(TrainingExample).all()
    
    Yields:
        SQLAlchemy Session
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(drop_existing: bool = False) -> None:
    """
    Initialize the database schema.
    
    Creates all tables defined in models.py.
    
    Args:
        drop_existing: If True, drop all existing tables first (DANGEROUS!)
    """
    from chatos_backend.database.models import Base
    
    engine = get_engine()
    
    if drop_existing:
        Base.metadata.drop_all(bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    # Insert default knowledge domains if empty
    _seed_default_data(engine)


def _seed_default_data(engine: Engine) -> None:
    """Seed the database with default data."""
    from chatos_backend.database.models import KnowledgeDomain, DataSource
    
    SessionLocal = get_session_factory()
    session = SessionLocal()
    
    try:
        # Check if domains already exist
        existing_domains = session.query(KnowledgeDomain).count()
        if existing_domains == 0:
            # Insert default knowledge domains
            default_domains = [
                # Programming
                KnowledgeDomain(name="python", category="programming", description="Python programming language"),
                KnowledgeDomain(name="javascript", category="programming", description="JavaScript/TypeScript"),
                KnowledgeDomain(name="react", category="programming", description="React framework"),
                KnowledgeDomain(name="sql", category="programming", description="SQL and databases"),
                KnowledgeDomain(name="algorithms", category="programming", description="Data structures and algorithms"),
                # UI/UX
                KnowledgeDomain(name="ui_components", category="ui_ux", description="UI component design"),
                KnowledgeDomain(name="layout", category="ui_ux", description="Layout and visual hierarchy"),
                KnowledgeDomain(name="accessibility", category="ui_ux", description="Web accessibility (WCAG)"),
                KnowledgeDomain(name="design_systems", category="ui_ux", description="Design tokens and systems"),
                # General
                KnowledgeDomain(name="reasoning", category="general", description="Logical reasoning and problem solving"),
                KnowledgeDomain(name="conversation", category="general", description="General conversation"),
                KnowledgeDomain(name="instruction_following", category="general", description="Following complex instructions"),
            ]
            session.add_all(default_domains)
        
        # Check if default data sources exist
        existing_sources = session.query(DataSource).count()
        if existing_sources == 0:
            default_sources = [
                DataSource(
                    name="chatos_conversations",
                    source_type="internal",
                    description="ChatOS conversation logs",
                    config={"path": "~/ChatOS-Memory/training_data"},
                    is_active=True,
                ),
                DataSource(
                    name="persrm_data",
                    source_type="internal",
                    description="PersRM reasoning data",
                    config={"path": "~/PersRM-V0.2/data"},
                    is_active=True,
                ),
            ]
            session.add_all(default_sources)
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Warning: Could not seed default data: {e}")
    finally:
        session.close()


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def close_database() -> None:
    """Close the database engine and cleanup connections."""
    global _engine, _SessionLocal
    
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None

