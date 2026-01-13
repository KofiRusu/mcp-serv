"""
init_schema.py - Database schema initialization for ChatOS.

Creates the chatos schema and all required tables for:
- User sessions
- API usage logging
- Feature usage tracking
- Security audit logs
- IP whitelist

Usage:
    python -m chatos_backend.database.init_schema
"""

import logging
import sys
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from chatos_backend.database.connection import get_engine, get_session, check_database_connection
from chatos_backend.database.models import Base as ModelsBase
from chatos_backend.database.auth_models import (
    UserSession,
    APIUsageLog,
    FeatureUsage,
    AuditLog,
    IPWhitelist,
)

logger = logging.getLogger(__name__)


def create_schema(engine, schema_name: str = "chatos") -> bool:
    """
    Create the database schema if it doesn't exist.
    
    Args:
        engine: SQLAlchemy engine
        schema_name: Name of schema to create
        
    Returns:
        True if successful
    """
    try:
        with engine.connect() as conn:
            # Check if schema exists
            result = conn.execute(text(
                f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{schema_name}'"
            ))
            
            if result.fetchone() is None:
                logger.info(f"Creating schema '{schema_name}'...")
                conn.execute(text(f"CREATE SCHEMA {schema_name}"))
                conn.commit()
                logger.info(f"Schema '{schema_name}' created successfully")
            else:
                logger.info(f"Schema '{schema_name}' already exists")
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        return False


def create_auth_tables(engine) -> bool:
    """
    Create authentication and logging tables.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        True if successful
    """
    try:
        # Import all auth models to register them with Base
        from chatos_backend.database.auth_models import (
            UserSession,
            APIUsageLog, 
            FeatureUsage,
            AuditLog,
            IPWhitelist,
        )
        
        # Get the Base that has the auth models registered
        from chatos_backend.database.models import Base
        
        # Create all tables in the chatos schema
        logger.info("Creating auth tables...")
        
        # We need to use the same Base that the models are registered with
        # The auth_models import Base from models, so they share the same metadata
        Base.metadata.create_all(
            bind=engine,
            tables=[
                UserSession.__table__,
                APIUsageLog.__table__,
                FeatureUsage.__table__,
                AuditLog.__table__,
                IPWhitelist.__table__,
            ]
        )
        
        logger.info("Auth tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create auth tables: {e}")
        return False


def create_indexes(engine) -> bool:
    """
    Create additional indexes for performance.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        True if successful
    """
    try:
        with engine.connect() as conn:
            indexes = [
                # API usage indexes
                ("ix_api_usage_time", "chatos.api_usage_log", "request_time DESC"),
                ("ix_api_usage_endpoint", "chatos.api_usage_log", "endpoint"),
                
                # Feature usage indexes  
                ("ix_feature_usage_time", "chatos.feature_usage", "created_at DESC"),
                ("ix_feature_usage_feature", "chatos.feature_usage", "feature_name"),
                
                # Audit log indexes
                ("ix_audit_log_time", "chatos.audit_log", "created_at DESC"),
                ("ix_audit_log_action", "chatos.audit_log", "action"),
                
                # Session indexes
                ("ix_user_session_active", "chatos.user_sessions", "is_active"),
                ("ix_user_session_activity", "chatos.user_sessions", "last_activity DESC"),
            ]
            
            for idx_name, table, columns in indexes:
                try:
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})"
                    ))
                except ProgrammingError:
                    # Index might already exist with different syntax
                    pass
            
            conn.commit()
            logger.info("Indexes created successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        return False


def init_auth_schema(drop_existing: bool = False) -> bool:
    """
    Initialize the full auth schema.
    
    Creates schema, tables, and indexes.
    
    Args:
        drop_existing: If True, drop existing tables first (DANGEROUS!)
        
    Returns:
        True if all steps successful
    """
    logger.info("Initializing ChatOS auth schema...")
    
    # Check database connection
    if not check_database_connection():
        logger.error("Cannot connect to database")
        return False
    
    engine = get_engine()
    
    # Create schema
    if not create_schema(engine, "chatos"):
        return False
    
    # Drop existing if requested
    if drop_existing:
        logger.warning("Dropping existing auth tables...")
        try:
            from chatos_backend.database.models import Base
            from chatos_backend.database.auth_models import (
                UserSession, APIUsageLog, FeatureUsage, AuditLog, IPWhitelist
            )
            
            # Drop in reverse order of dependencies
            for model in [IPWhitelist, AuditLog, FeatureUsage, APIUsageLog, UserSession]:
                try:
                    model.__table__.drop(engine)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.warning(f"Error dropping tables: {e}")
    
    # Create tables
    if not create_auth_tables(engine):
        return False
    
    # Create indexes
    if not create_indexes(engine):
        logger.warning("Index creation had issues, but tables exist")
    
    logger.info("Auth schema initialization complete!")
    return True


def verify_schema() -> dict:
    """
    Verify that all required tables exist.
    
    Returns:
        Dict with verification results
    """
    results = {
        "connected": False,
        "schema_exists": False,
        "tables": {},
    }
    
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            results["connected"] = True
            
            # Check schema
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'chatos'"
            ))
            results["schema_exists"] = result.fetchone() is not None
            
            # Check tables
            required_tables = [
                "user_sessions",
                "api_usage_log", 
                "feature_usage",
                "audit_log",
                "ip_whitelist",
            ]
            
            for table in required_tables:
                result = conn.execute(text(
                    f"SELECT table_name FROM information_schema.tables "
                    f"WHERE table_schema = 'chatos' AND table_name = '{table}'"
                ))
                results["tables"][table] = result.fetchone() is not None
                
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        results["error"] = str(e)
    
    return results


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize ChatOS database schema")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating (DANGEROUS!)"
    )
    parser.add_argument(
        "--verify",
        action="store_true", 
        help="Only verify schema exists, don't create"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if args.verify:
        print("Verifying schema...")
        results = verify_schema()
        
        print(f"\nDatabase connected: {results['connected']}")
        print(f"Schema 'chatos' exists: {results['schema_exists']}")
        print("\nTables:")
        for table, exists in results.get("tables", {}).items():
            status = "OK" if exists else "MISSING"
            print(f"  {table}: {status}")
        
        if results.get("error"):
            print(f"\nError: {results['error']}")
            sys.exit(1)
            
        all_ok = results["connected"] and results["schema_exists"] and all(results["tables"].values())
        sys.exit(0 if all_ok else 1)
    
    # Initialize schema
    if args.drop:
        confirm = input("WARNING: This will drop all auth tables. Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(1)
    
    success = init_auth_schema(drop_existing=args.drop)
    
    if success:
        print("\nSchema initialization successful!")
        print("\nVerification:")
        results = verify_schema()
        for table, exists in results.get("tables", {}).items():
            status = "OK" if exists else "MISSING"
            print(f"  {table}: {status}")
    else:
        print("\nSchema initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
