"""
Sync Daemon - Real-Time Bidirectional SQLite Synchronization
Runs on both machines to sync memory databases in real-time
"""

import sqlite3
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import sys
import signal

from .sync_config import SyncConfig
from .sync_client import RemoteSyncClient
from .sync_schema import SyncSchemaMigration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / ".cursor" / "sync_daemon.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SyncDaemon:
    """Main synchronization daemon"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize sync daemon"""
        self.config = SyncConfig(config_path)
        
        if not self.config.config:
            raise RuntimeError("No configuration found. Please create sync_config.json")
        
        is_valid, message = self.config.validate()
        if not is_valid:
            raise RuntimeError(f"Configuration invalid: {message}")
        
        self.machine_id = self.config.get("machine_id")
        self.local_db_path = self.config.get("local_db_path")
        self.remote_host = self.config.get("remote_host")
        self.remote_db_path = self.config.get("remote_db_path")
        self.sync_interval = self.config.get("sync_interval_seconds", 2)
        
        self.remote_client = RemoteSyncClient(self.remote_host, self.remote_db_path)
        self.running = False
        self.last_sync_time = 0
        
        logger.info(f"Sync daemon initialized for machine: {self.machine_id}")
    
    def _get_connection(self):
        """Get local database connection"""
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_schema(self) -> bool:
        """Ensure database schema is up to date"""
        try:
            migration = SyncSchemaMigration(self.local_db_path)
            return migration.migrate(self.machine_id)
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return False
    
    def _get_pending_local_syncs(self) -> Optional[List[Dict]]:
        """Get pending sync entries from local database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT id, operation, memory_id, sync_version, machine_id, timestamp
            FROM sync_log
            WHERE synced = 0
            ORDER BY id ASC
            LIMIT 100
            """)
            
            entries = []
            for row in cursor.fetchall():
                entries.append({
                    'id': row['id'],
                    'operation': row['operation'],
                    'memory_id': row['memory_id'],
                    'sync_version': row['sync_version'],
                    'machine_id': row['machine_id'],
                    'timestamp': row['timestamp']
                })
            
            conn.close()
            return entries if entries else None
        except Exception as e:
            logger.error(f"Error getting pending syncs: {e}")
            return None
    
    def _get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get memory from local database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT id, domain, title, content, created_at, updated_at,
                   status, priority, machine_id, sync_version, deleted
            FROM memories
            WHERE id = ?
            """, (memory_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'id': row['id'],
                'domain': row['domain'],
                'title': row['title'],
                'content': row['content'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'status': row['status'],
                'priority': row['priority'],
                'machine_id': row['machine_id'],
                'sync_version': row['sync_version'],
                'deleted': row['deleted']
            }
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return None
    
    def _apply_memory_change(self, operation: str, memory: Dict) -> bool:
        """Apply a memory change locally"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if operation == 'INSERT' or operation == 'UPDATE':
                cursor.execute("""
                INSERT OR REPLACE INTO memories
                (id, domain, title, content, created_at, updated_at, status, priority,
                 machine_id, sync_version, deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory['id'], memory['domain'], memory['title'], memory['content'],
                    memory['created_at'], memory['updated_at'], memory['status'],
                    memory['priority'], memory['machine_id'], memory['sync_version'],
                    memory['deleted']
                ))
            elif operation == 'DELETE':
                cursor.execute("""
                UPDATE memories
                SET deleted = 1, sync_version = sync_version + 1
                WHERE id = ?
                """, (memory['id'],))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error applying change: {e}")
            return False
    
    def _mark_synced(self, sync_ids: List[int]) -> bool:
        """Mark sync_log entries as synced"""
        try:
            if not sync_ids:
                return True
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(sync_ids))
            cursor.execute(
                f"UPDATE sync_log SET synced = 1 WHERE id IN ({placeholders})",
                sync_ids
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error marking synced: {e}")
            return False
    
    def _resolve_conflict(self, local: Dict, remote: Dict) -> Dict:
        """Resolve conflict between local and remote versions"""
        local_time = datetime.fromisoformat(local['updated_at'])
        remote_time = datetime.fromisoformat(remote['updated_at'])
        
        if local_time > remote_time:
            logger.info(f"Keeping local version of {local['id']} (newer)")
            return local
        elif remote_time > local_time:
            logger.info(f"Accepting remote version of {local['id']} (newer)")
            return remote
        else:
            # Same timestamp, use machine_id as tiebreaker
            if self.machine_id < remote['machine_id']:
                logger.info(f"Keeping local version of {local['id']} (machine_id tiebreaker)")
                return local
            else:
                logger.info(f"Accepting remote version of {local['id']} (machine_id tiebreaker)")
                return remote
    
    def push_changes(self) -> int:
        """Push local pending changes to remote"""
        pending = self._get_pending_local_syncs()
        if not pending:
            return 0
        
        synced_count = 0
        
        for sync_entry in pending:
            memory = self._get_memory(sync_entry['memory_id'])
            if not memory:
                logger.warning(f"Memory not found: {sync_entry['memory_id']}")
                continue
            
            # Apply change to remote
            if self.remote_client.apply_memory_change(sync_entry['operation'], memory):
                synced_count += 1
            else:
                logger.error(f"Failed to sync {sync_entry['operation']} for {sync_entry['memory_id']}")
        
        # Mark as synced
        if synced_count > 0:
            sync_ids = [s['id'] for s in pending[:synced_count]]
            self._mark_synced(sync_ids)
            self.remote_client.mark_sync_as_complete(sync_ids)
            logger.info(f"Pushed {synced_count} changes to remote")
        
        return synced_count
    
    def pull_changes(self) -> int:
        """Pull remote pending changes and apply locally"""
        try:
            remote_syncs = self.remote_client.get_pending_syncs(self.machine_id)
            if not remote_syncs:
                return 0
            
            applied_count = 0
            
            for remote_sync in remote_syncs:
                remote_memory = self.remote_client.get_memory(remote_sync['memory_id'])
                if not remote_memory:
                    logger.warning(f"Remote memory not found: {remote_sync['memory_id']}")
                    continue
                
                # Check for conflict
                local_memory = self._get_memory(remote_sync['memory_id'])
                if local_memory and local_memory['updated_at'] != remote_memory['updated_at']:
                    resolved = self._resolve_conflict(local_memory, remote_memory)
                else:
                    resolved = remote_memory
                
                # Apply change locally
                if self._apply_memory_change(remote_sync['operation'], resolved):
                    applied_count += 1
                else:
                    logger.error(f"Failed to apply {remote_sync['operation']} locally")
            
            # Mark as synced on remote
            if applied_count > 0:
                sync_ids = [s['id'] for s in remote_syncs[:applied_count]]
                self.remote_client.mark_sync_as_complete(sync_ids)
                logger.info(f"Pulled and applied {applied_count} changes from remote")
            
            return applied_count
        except Exception as e:
            logger.error(f"Error pulling changes: {e}")
            return 0
    
    def sync_cycle(self):
        """Execute one sync cycle"""
        try:
            pushed = self.push_changes()
            pulled = self.pull_changes()
            
            if pushed > 0 or pulled > 0:
                logger.info(f"Sync cycle: pushed {pushed}, pulled {pulled}")
            
            return pushed + pulled
        except Exception as e:
            logger.error(f"Sync cycle error: {e}")
            return 0
    
    def run(self):
        """Run sync daemon"""
        logger.info(f"Starting sync daemon for {self.machine_id}")
        
        # Ensure schema is current
        if not self._ensure_schema():
            logger.error("Failed to ensure schema")
            return
        
        # Test remote connection
        if not self.remote_client.test_connection():
            logger.error("Failed to connect to remote")
            return
        
        self.running = True
        
        try:
            while self.running:
                start_time = time.time()
                self.sync_cycle()
                
                elapsed = time.time() - start_time
                sleep_time = max(0, self.sync_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            logger.info("Sync daemon stopped by user")
        except Exception as e:
            logger.error(f"Sync daemon error: {e}")
        finally:
            self.running = False
            logger.info("Sync daemon stopped")
    
    def stop(self):
        """Stop the sync daemon"""
        self.running = False


def main():
    """Main entry point"""
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    daemon = SyncDaemon(config_path)
    
    def signal_handler(sig, frame):
        logger.info("Stopping daemon...")
        daemon.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    daemon.run()


if __name__ == "__main__":
    main()
