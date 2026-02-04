"""
SQLite Schema Migration for Real-Time Sync Support
Handles upgrading existing databases to include sync metadata and triggers
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SyncSchemaMigration:
    """Manages database schema migrations for sync support"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _column_exists(self, table: str, column: str) -> bool:
        """Check if column exists in table"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = {row[1] for row in cursor.fetchall()}
            return column in columns
        finally:
            conn.close()
    
    def _table_exists(self, table: str) -> bool:
        """Check if table exists"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def migrate_memories_table(self, machine_id: str) -> bool:
        """Add sync columns to memories table"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Add machine_id column if not exists
            if not self._column_exists("memories", "machine_id"):
                logger.info("Adding machine_id column to memories table")
                cursor.execute(
                    f"ALTER TABLE memories ADD COLUMN machine_id TEXT DEFAULT '{machine_id}'"
                )
            
            # Add sync_version column if not exists
            if not self._column_exists("memories", "sync_version"):
                logger.info("Adding sync_version column to memories table")
                cursor.execute(
                    "ALTER TABLE memories ADD COLUMN sync_version INTEGER DEFAULT 0"
                )
            
            # Add deleted column if not exists
            if not self._column_exists("memories", "deleted"):
                logger.info("Adding deleted column to memories table")
                cursor.execute(
                    "ALTER TABLE memories ADD COLUMN deleted INTEGER DEFAULT 0"
                )
            
            conn.commit()
            logger.info("Memories table migration completed")
            return True
        except Exception as e:
            logger.error(f"Error migrating memories table: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def create_sync_log_table(self) -> bool:
        """Create sync_log table for tracking changes"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            if self._table_exists("sync_log"):
                logger.info("sync_log table already exists")
                return True
            
            logger.info("Creating sync_log table")
            cursor.execute("""
            CREATE TABLE sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,              -- INSERT, UPDATE, DELETE
                memory_id TEXT NOT NULL,
                sync_version INTEGER NOT NULL,
                machine_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                synced INTEGER DEFAULT 0,             -- 0=pending, 1=synced
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Add indexes for efficient queries
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sync_log_synced ON sync_log(synced)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sync_log_machine ON sync_log(machine_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sync_log_memory ON sync_log(memory_id)"
            )
            
            conn.commit()
            logger.info("sync_log table created with indexes")
            return True
        except Exception as e:
            logger.error(f"Error creating sync_log table: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def create_sync_triggers(self, machine_id: str) -> bool:
        """Create triggers for automatic change tracking"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Drop existing triggers if they exist
            trigger_names = [
                "after_insert_memory",
                "after_update_memory",
                "after_delete_memory"
            ]
            
            for trigger_name in trigger_names:
                cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
            
            logger.info("Creating INSERT trigger")
            cursor.execute(f"""
            CREATE TRIGGER after_insert_memory
            AFTER INSERT ON memories
            BEGIN
                INSERT INTO sync_log (operation, memory_id, sync_version, machine_id, timestamp, synced)
                VALUES ('INSERT', NEW.id, NEW.sync_version, '{machine_id}', datetime('now'), 0);
            END
            """)
            
            logger.info("Creating UPDATE trigger")
            cursor.execute(f"""
            CREATE TRIGGER after_update_memory
            AFTER UPDATE ON memories
            BEGIN
                UPDATE memories SET sync_version = sync_version + 1 WHERE id = NEW.id;
                INSERT INTO sync_log (operation, memory_id, sync_version, machine_id, timestamp, synced)
                VALUES ('UPDATE', NEW.id, NEW.sync_version + 1, '{machine_id}', datetime('now'), 0);
            END
            """)
            
            logger.info("Creating DELETE trigger (soft delete)")
            cursor.execute(f"""
            CREATE TRIGGER after_delete_memory
            BEFORE DELETE ON memories
            BEGIN
                UPDATE memories SET deleted = 1 WHERE id = OLD.id;
                INSERT INTO sync_log (operation, memory_id, sync_version, machine_id, timestamp, synced)
                VALUES ('DELETE', OLD.id, OLD.sync_version, '{machine_id}', datetime('now'), 0);
            END
            """)
            
            conn.commit()
            logger.info("Sync triggers created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating triggers: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def migrate(self, machine_id: str) -> bool:
        """Execute all migrations"""
        logger.info(f"Starting schema migration for machine: {machine_id}")
        
        success = True
        success = self.migrate_memories_table(machine_id) and success
        success = self.create_sync_log_table() and success
        success = self.create_sync_triggers(machine_id) and success
        
        if success:
            logger.info(f"Schema migration completed successfully for {machine_id}")
        else:
            logger.error("Schema migration encountered errors")
        
        return success


def apply_migration(db_path: str, machine_id: str) -> bool:
    """Convenience function to apply migration"""
    migration = SyncSchemaMigration(db_path)
    return migration.migrate(machine_id)
