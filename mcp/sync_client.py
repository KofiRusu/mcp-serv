"""
SSH-based Remote SQLite Database Client
Handles remote database queries and operations over SSH
"""

import subprocess
import json
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RemoteSyncClient:
    """Client for remote database operations via SSH"""
    
    def __init__(self, remote_host: str, remote_db_path: str):
        """
        Initialize SSH client
        
        Args:
            remote_host: SSH connection string (e.g., 'kr@192.168.18.40')
            remote_db_path: Path to database on remote machine
        """
        self.remote_host = remote_host
        self.remote_db_path = remote_db_path
    
    def _execute_remote_command(self, command: str, timeout: int = 10) -> tuple[bool, str]:
        """
        Execute a command on remote host via SSH
        
        Returns:
            (success, output) tuple
        """
        try:
            full_command = f'ssh {self.remote_host} "{command}"'
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                logger.error(f"Remote command failed: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Remote command timeout: {command}")
            return False, "Timeout"
        except Exception as e:
            logger.error(f"SSH execution error: {e}")
            return False, str(e)
    
    def _build_sqlite_query(self, query: str) -> str:
        """Build SQLite query command"""
        # Escape for shell
        query_escaped = query.replace('"', '\\"')
        return f'sqlite3 "{self.remote_db_path}" "{query_escaped}"'
    
    def get_pending_syncs(self, machine_id: str) -> Optional[List[Dict]]:
        """Get pending sync entries for a specific machine"""
        query = f"""
        SELECT id, operation, memory_id, sync_version, machine_id, timestamp
        FROM sync_log 
        WHERE synced = 0 AND machine_id != '{machine_id}'
        ORDER BY id ASC
        LIMIT 100
        """
        
        success, output = self._execute_remote_command(self._build_sqlite_query(query))
        if not success or not output:
            return None
        
        # Parse SQLite output
        entries = []
        for line in output.split('\n'):
            if line.strip():
                try:
                    parts = line.split('|')
                    entries.append({
                        'id': parts[0],
                        'operation': parts[1],
                        'memory_id': parts[2],
                        'sync_version': int(parts[3]),
                        'machine_id': parts[4],
                        'timestamp': parts[5]
                    })
                except Exception as e:
                    logger.error(f"Error parsing sync entry: {e}")
        
        return entries if entries else None
    
    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Retrieve a specific memory from remote database"""
        query = f"""
        SELECT id, domain, title, content, created_at, updated_at, 
               status, priority, machine_id, sync_version, deleted
        FROM memories 
        WHERE id = '{memory_id}'
        """
        
        success, output = self._execute_remote_command(self._build_sqlite_query(query))
        if not success or not output:
            return None
        
        try:
            parts = output.split('|')
            return {
                'id': parts[0],
                'domain': parts[1],
                'title': parts[2],
                'content': parts[3],
                'created_at': parts[4],
                'updated_at': parts[5],
                'status': parts[6],
                'priority': parts[7],
                'machine_id': parts[8],
                'sync_version': int(parts[9]),
                'deleted': int(parts[10])
            }
        except Exception as e:
            logger.error(f"Error parsing memory: {e}")
            return None
    
    def apply_memory_change(self, operation: str, memory_data: Dict) -> bool:
        """Apply a memory change (INSERT, UPDATE, DELETE) on remote"""
        try:
            if operation == 'INSERT' or operation == 'UPDATE':
                query = f"""
                INSERT OR REPLACE INTO memories 
                (id, domain, title, content, created_at, updated_at, status, priority, 
                 machine_id, sync_version, deleted)
                VALUES (
                    '{memory_data['id']}',
                    '{memory_data['domain'].replace("'", "''")}',
                    '{memory_data['title'].replace("'", "''")}',
                    '{memory_data['content'].replace("'", "''")}',
                    '{memory_data['created_at']}',
                    '{memory_data['updated_at']}',
                    '{memory_data['status']}',
                    '{memory_data['priority']}',
                    '{memory_data['machine_id']}',
                    {memory_data['sync_version']},
                    {memory_data['deleted']}
                )
                """
            elif operation == 'DELETE':
                query = f"""
                UPDATE memories 
                SET deleted = 1, sync_version = sync_version + 1
                WHERE id = '{memory_data['id']}'
                """
            else:
                logger.error(f"Unknown operation: {operation}")
                return False
            
            success, output = self._execute_remote_command(self._build_sqlite_query(query))
            return success
        except Exception as e:
            logger.error(f"Error applying change: {e}")
            return False
    
    def mark_sync_as_complete(self, sync_ids: List[int]) -> bool:
        """Mark sync_log entries as synced on remote"""
        try:
            ids_str = ','.join(str(i) for i in sync_ids)
            query = f"UPDATE sync_log SET synced = 1 WHERE id IN ({ids_str})"
            
            success, output = self._execute_remote_command(self._build_sqlite_query(query))
            return success
        except Exception as e:
            logger.error(f"Error marking syncs complete: {e}")
            return False
    
    def get_remote_stats(self) -> Optional[Dict]:
        """Get remote database statistics"""
        query = "SELECT COUNT(*) FROM memories WHERE deleted = 0"
        success, output = self._execute_remote_command(self._build_sqlite_query(query))
        
        if success and output:
            try:
                return {'memory_count': int(output.strip())}
            except:
                pass
        
        return None
    
    def test_connection(self) -> bool:
        """Test SSH connection and database access"""
        try:
            success, output = self._execute_remote_command(
                self._build_sqlite_query("SELECT COUNT(*) FROM memories")
            )
            if success and output:
                logger.info(f"SSH connection test successful: {output} memories on remote")
                return True
            else:
                logger.error(f"SSH connection test failed: {output}")
                return False
        except Exception as e:
            logger.error(f"SSH connection test error: {e}")
            return False
